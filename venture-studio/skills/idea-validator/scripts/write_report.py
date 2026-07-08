"""
write_report.py — Final report synthesis by Claude on the local subscription

This is the writing STAGE of the pipeline: it runs AFTER the six MECE roles
and the red team are all gated, and produces the full report markdown that
becomes the PDF. It exists because the Hermes topic orchestrator runs a weak
free model whose prose is the single biggest quality bottleneck in the final
deliverable (2026-07-04 finding) — the orchestrator should orchestrate, not
write.

Like red_team.py, it calls Claude (Sonnet) headlessly through the
locally-authenticated Claude Code CLI (`claude -p`) — i.e. on Mohit's Claude
subscription. No API key is needed or used; ANTHROPIC_API_KEY is deliberately
stripped from the child environment so the CLI cannot silently bill an API
account instead.

Unlike red_team.py there IS a fallback if the CLI is missing: the calling
session may write the report itself following the skeleton in SKILL.md
Step 3, but must then add a Research Process Note saying the report prose was
NOT written by the synthesis model. Report writing is not adversarial review —
a weaker writer degrades style, not integrity, because the verdict rails are
enforced mechanically here and re-checked below.

Usage:
    python write_report.py \
        --idea "Title: one-line description" \
        --inputs demand.json market.json competition.json feasibility.json economics.json external.json \
        --red-team red_team.json \
        --output report.md \
        [--corpus corpus.txt] [--open-questions "q1; q2"] [--timeout 600]

Output:
    Writes the report markdown to --output and prints a JSON envelope:
    {"report_path": ..., "verdict": ..., "kill_likelihood": ..., "model": ...}
    Exits non-zero (with {"error": ...}) if the report is structurally
    incomplete or violates the red-team verdict constraint.
"""

import os
import re
import sys
import json
import shutil
import argparse
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_research_data import check_finding_coverage, check_report_quotes  # noqa: E402

# Same cap as red_team.py (raised with it 2026-07-08): role outputs are the
# primary input; the corpus lets the writer quote real evidence instead of
# paraphrasing it — and the quote-grounding gate rejects anything it invents.
MAX_CORPUS_EXCERPT_CHARS = 80000

REQUIRED_SECTIONS = [
    "## TL;DR",
    "## Executive Summary",
    "## Demand Reality",
    "## Market",
    "## Competition",
    "## Technical Feasibility",
    "## Economics & Path to Market",
    "## Red Team Findings",
    "## Mohit's Edge",
    "## Lowest-Cost Validation Experiment",
    "## Open Questions",
]

VALID_VERDICTS = {"strong", "promising", "weak", "dead"}

REPORT_PROMPT = """You are the report writer for a venture-validation research committee. Six specialist
analysts (demand, market, competition, feasibility, economics, external) and an adversarial
red team have filed their findings on this decision:

{idea}

Write the FULL validation report in markdown, following this exact structure:

# [Idea Title]

**Verdict:** [STRONG / PROMISING / WEAK / DEAD]

## TL;DR
[3 sentences max — verdict first]

## Executive Summary
[2-3 paragraphs synthesizing all dimensions, including what the red team could not break]

## Demand Reality
[from demand: pain points with verbatim quotes + sources, ICP, JTBD, workarounds, WTP signals, solution-demand fit]

## Market
[from market: market size labeled [Directional] with the source spread if sources disagree, growth, why-now, industry structure, demand drivers]

## Competition
[from competition: a markdown table of competitors — name, URL, description, funding stage, geo focus, threat level — plus saturation, funding flows, moats, whitespace, incumbent response]

## Technical Feasibility
[from feasibility: capability maturity, data/infra needs, MVP effort + solo-founder gap, scalability, cost-to-serve drivers]

## Economics & Path to Market
[from economics: pricing thesis, CAC by channel, LTV/retention, margins, sales motion, channels, partnerships, frictions, capital intensity]

## External Constraints (if applicable)
[from external: regulation, platform dependencies, IP/licensing, ethical-backlash risk, timing/macro, risk level]

## Red Team Findings
[hidden assumptions with severity, contradictions between dimensions, evidence-quality attacks, kill likelihood + top kill reasons — report these plainly, do not soften]

## Mohit's Edge
[honest assessment of Mohit's background — fintech PM, India market knowledge, investing experience — against this specific idea; don't force-fit; use feasibility's solo_founder_gap]

## Lowest-Cost Validation Experiment
[built from the red team's falsification_test entries — the cheapest tests of the most severe assumptions: a landing page, 10 cold DMs, a poll — never "build a prototype"]

## Opportunity Expansion (appendix)
[adjacent ideas and long-term directions ONLY if the verdict is promising or strong; this section may NEVER raise the verdict]

## Open Questions
[the red team's unowned_considerations, plus any listed under ADDITIONAL OPEN QUESTIONS below]

Hard rules:
- Verdict is exactly one of: STRONG / PROMISING / WEAK / DEAD.
  strong = real large problem, clear white space, validated pain, founder edge.
  promising = real problem, differentiation possible, pain validated.
  weak = problem exists but market small, competition saturated, or no clear wedge.
  dead = problem not real, already solved well, or regulatory wall is fatal.
- If the red team's kill_likelihood score is >= 70, the verdict CANNOT be STRONG.
- If the red team found a fatal-severity assumption with no cheap falsification test, the
  verdict cannot be better than WEAK.
- If you land more positive than the red team's direction, say explicitly why.
- Every number keeps its source; where sources disagree, show the spread — do not average
  it away. Quote verbatim evidence from the corpus excerpt where it exists; never invent
  quotes.
- Do not soften the red team. Do not let the appendix inflate the verdict.
- INDIA LENS: when the idea's geography includes India (it does by default), every dimension
  section must explicitly address the India angle — India market reality in Market, which
  competitors actually operate in India in Competition, India regulation (DPDP, RBI/SEBI where
  relevant) in External Constraints, India pricing power and willingness-to-pay in Economics,
  India-specific demand signal in Demand Reality. Use the corpus's "INDIA FOCUS" sections as
  the primary source for this. Where India evidence is thin, say so plainly in that section
  ("India-specific evidence: thin — global data may not transfer because ...") rather than
  silently extrapolating global numbers to India. Do not create a separate India section;
  weave it into each dimension.

Return ONLY the markdown report — no preamble, no code fences around the whole document,
no commentary after it.

=== SPECIALIST ANALYSES ===
{role_outputs}

=== RED TEAM REVIEW ===
{red_team}

=== ADDITIONAL OPEN QUESTIONS (from idea parsing) ===
{open_questions}

=== RAW EVIDENCE CORPUS EXCERPT (for verbatim quotes) ===
{corpus_excerpt}
"""


def strip_outer_fence(text: str) -> str:
    """Remove one whole-document ```-fence if the model ignored instructions."""
    stripped = text.strip()
    if stripped.startswith("```"):
        first_nl = stripped.find("\n")
        if first_nl != -1 and stripped.rstrip().endswith("```"):
            return stripped[first_nl + 1:].rstrip()[:-3].strip()
    return stripped


def extract_verdict(report_md: str) -> str:
    m = re.search(r"\*\*Verdict:?\*\*:?\s*\W*(STRONG|PROMISING|WEAK|DEAD)",
                  report_md, re.IGNORECASE)
    if not m:
        raise ValueError("no '**Verdict:** STRONG/PROMISING/WEAK/DEAD' line found")
    return m.group(1).lower()


def main():
    parser = argparse.ArgumentParser(description="Synthesize the final validation report via claude -p")
    parser.add_argument("--idea", required=True, help="Title: one-line description of the decision")
    parser.add_argument("--inputs", required=True, nargs="+",
                        help="Paths to the gated role-output JSON files")
    parser.add_argument("--red-team", required=True, help="Path to the gated red_team.json")
    parser.add_argument("--output", required=True, help="Path to write the report markdown")
    parser.add_argument("--corpus", default=None, help="Optional path to the raw evidence corpus")
    parser.add_argument("--open-questions", default="",
                        help="Semicolon-separated ambiguities from Step 0 parsing")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--model", default="sonnet",
                        help="Claude Code CLI model alias (default: sonnet)")
    args = parser.parse_args()

    role_outputs = []
    for path in args.inputs:
        if not os.path.exists(path):
            print(json.dumps({"error": f"Role output file not found: {path}"}))
            sys.exit(1)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(json.dumps({"error": f"Role output {path} is not valid JSON: {e}"}))
                sys.exit(1)
        role = data.get("analysis_type", os.path.basename(path))
        insights = data.get("consolidated_insights", data)
        role_outputs.append(f"--- {role} ---\n{json.dumps(insights, indent=1)}")

    if not os.path.exists(args.red_team):
        print(json.dumps({"error": f"Red team file not found: {args.red_team}"}))
        sys.exit(1)
    with open(args.red_team, "r", encoding="utf-8", errors="replace") as f:
        red_team_text = f.read()
    try:
        # raw_decode (not json.load/json.loads) tolerates a trailing duplicate
        # JSON blob after the first complete object — this happened for real
        # (2026-07-08): two overlapping red_team.py writes to the same path
        # left a second JSON dump concatenated after the first, which
        # json.load rejects as "Extra data" even though the real result is
        # intact and parseable.
        red_team_data, _ = json.JSONDecoder().raw_decode(red_team_text.strip())
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Red team file is not valid JSON: {e}"}))
        sys.exit(1)
    red_team_insights = red_team_data.get("consolidated_insights", red_team_data)
    kill_score = (red_team_insights.get("kill_likelihood") or {}).get("score_pct")

    corpus_excerpt = "(not provided)"
    if args.corpus and os.path.exists(args.corpus):
        with open(args.corpus, "r", encoding="utf-8", errors="replace") as f:
            corpus_excerpt = f.read()[:MAX_CORPUS_EXCERPT_CHARS]

    # .replace(), never .format(): role outputs and corpus text contain braces.
    prompt = (REPORT_PROMPT
              .replace("{idea}", args.idea)
              .replace("{role_outputs}", "\n\n".join(role_outputs))
              .replace("{red_team}", json.dumps(red_team_insights, indent=1))
              .replace("{open_questions}", args.open_questions or "(none)")
              .replace("{corpus_excerpt}", corpus_excerpt))

    claude = shutil.which("claude")
    if not claude:
        print(json.dumps({"error": (
            "claude CLI not found on PATH — report synthesis runs on the locally-"
            "authenticated Claude Code subscription. Fallback: the calling session may "
            "write the report itself following SKILL.md Step 3, but must add a Research "
            "Process Note stating the prose was not written by the synthesis model."
        )}))
        sys.exit(1)

    # Force subscription auth: if ANTHROPIC_API_KEY leaked into this env the
    # CLI would silently bill the API account instead.
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)

    start_time = datetime.utcnow()
    try:
        proc = subprocess.run(
            [claude, "-p", "--model", args.model],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        print(json.dumps({"error": f"claude -p timed out after {args.timeout}s"}))
        sys.exit(1)

    latency = (datetime.utcnow() - start_time).total_seconds() * 1000

    if proc.returncode != 0:
        print(json.dumps({"error": (
            f"claude -p exited {proc.returncode}: {(proc.stderr or proc.stdout or '')[:500]}"
        )}))
        sys.exit(1)

    report_md = strip_outer_fence(proc.stdout)

    missing = [s for s in REQUIRED_SECTIONS if s.lower() not in report_md.lower()]
    if missing:
        debug_path = args.output + ".rejected"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(json.dumps({"error": f"Report missing required sections: {missing}",
                          "rejected_output": debug_path}))
        sys.exit(1)

    try:
        verdict = extract_verdict(report_md)
    except ValueError as e:
        debug_path = args.output + ".rejected"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(json.dumps({"error": str(e), "rejected_output": debug_path}))
        sys.exit(1)

    # Mechanical re-check of the red-team rail — never trust the writer with it.
    if isinstance(kill_score, (int, float)) and kill_score >= 70 and verdict == "strong":
        debug_path = args.output + ".rejected"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(json.dumps({"error": (
            f"Verdict 'strong' violates the red-team constraint "
            f"(kill_likelihood {kill_score} >= 70). Rerun write_report.py; if it "
            f"recurs, the role outputs and red team genuinely disagree — surface "
            f"that to Mohit instead of overriding."
        ), "rejected_output": debug_path}))
        sys.exit(1)

    # Finding coverage: the writer may not drop or soften fatal/high red-team
    # findings, and the kill score must be stated (2026-07-08 upgrade, item 3).
    with open(args.red_team, "r", encoding="utf-8", errors="replace") as f:
        coverage = check_finding_coverage(report_md, f.read())
    if not coverage.get("ok"):
        debug_path = args.output + ".rejected"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        coverage["rejected_output"] = debug_path
        print(json.dumps(coverage))
        sys.exit(1)

    # Quote grounding: every quoted passage in the report must trace to the
    # corpus or the gated inputs — quotes are never invented at synthesis time.
    quote_sources = [corpus_excerpt] if corpus_excerpt != "(not provided)" else []
    quote_sources += ["\n".join(role_outputs), json.dumps(red_team_insights)]
    quotes = check_report_quotes(report_md, quote_sources)
    if not quotes.get("ok"):
        debug_path = args.output + ".rejected"
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        quotes["rejected_output"] = debug_path
        print(json.dumps(quotes))
        sys.exit(1)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(json.dumps({
        "report_path": os.path.abspath(args.output),
        "verdict": verdict,
        "kill_likelihood": kill_score,
        "model": f"claude {args.model} (Claude Code subscription, local CLI)",
        "report_bytes": len(report_md.encode("utf-8")),
        "latency_ms": round(latency, 2),
        "timestamp": datetime.utcnow().isoformat(),
    }, indent=2))


if __name__ == "__main__":
    main()
