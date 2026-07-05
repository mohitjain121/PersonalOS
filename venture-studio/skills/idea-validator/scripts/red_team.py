"""
red_team.py — Sequential adversarial review over the specialist role outputs

This is a STAGE, not another researcher: it runs AFTER the MECE roles
(demand, market, competition, feasibility, economics, external) and reads their outputs,
cross-examining theses instead of researching raw data. Cross-examination is
the error-correction mechanism that replaced same-prompt-voting redundancy
when the ensemble moved to role decomposition (2026-07-04).

It calls Claude (Sonnet) headlessly through the locally-authenticated Claude
Code CLI (`claude -p`) — i.e. on Mohit's Claude subscription. No API key is
needed or used; ANTHROPIC_API_KEY is deliberately stripped from the child
environment so the CLI cannot silently bill an API account instead.

The red team also carries the collectively-exhaustive backstop for the whole
framework: its `unowned_considerations` field must name any material
consideration NONE of the analysts covered. It accepts any number of --inputs
(e.g. second-opinion runs of the same role by a different model — disagreement
between them is signal the red team should exploit).

Usage:
    python red_team.py \
        --idea "Title: one-line description" \
        --inputs demand.json market.json competition.json feasibility.json economics.json external.json \
        [--corpus corpus.txt] [--timeout 300]

Output:
    Same JSON envelope shape as multi_model_research.py (analysis_type
    "red_team"), so verify_research_data.py check-synthesis-output gates it
    identically.
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from datetime import datetime

# How much of the raw corpus to show the red team for evidence-quality attacks.
# The five role outputs are the primary input; the corpus excerpt lets it
# check claims against what the evidence actually says.
MAX_CORPUS_EXCERPT_CHARS = 20000

RED_TEAM_PROMPT = """You are the Red Team on a research committee evaluating this decision:
{idea}

The specialist analysts have filed their analyses (JSON below, one per dimension). Your mandate is
adversarial review — you create information by attacking, not by researching:

1. hidden_assumptions — the load-bearing assumptions each analysis silently depends on. For each:
   which dimension owns it, how severe if wrong, and the CHEAPEST concrete test that could falsify it
   (a landing page, 10 cold DMs, a poll — never "build a prototype").
2. contradictions — places where two analyses cannot both be right (e.g. feasibility's cost drivers
   vs economics' margin claims; demand's urgency vs competition's whitespace).
3. evidence_quality_attacks — claims resting on weak, absent, or SEO-report-mill evidence.
4. unowned_considerations — anything material that NONE of the analysts covered. This is your
   catch-all duty: the decomposition is only exhaustive because you fill its gaps.
5. kill_likelihood — 0-100, with the top reasons this fails.
6. verdict_pressure_test — the strongest argument AGAINST the emerging positive case, and what
   evidence would change your mind.

Be specific and adversarial. Do not soften. Do not restate the analyses back.
Return ONLY valid JSON (no markdown fences, no prose before or after) with this exact structure:
{
    "hidden_assumptions": [
        {"assumption": "...", "owning_dimension": "demand|market|competition|feasibility|economics|external",
         "severity": "low|medium|high|fatal", "falsification_test": "...", "test_cost": "..."}
    ],
    "contradictions": [{"between": "dimension A vs dimension B", "detail": "..."}],
    "evidence_quality_attacks": [{"claim": "...", "dimension": "...", "weakness": "..."}],
    "unowned_considerations": ["..."],
    "kill_likelihood": {"score_pct": 0, "top_kill_reasons": ["..."]},
    "verdict_pressure_test": "...",
    "confidence_score": 0.0
}

=== SPECIALIST ANALYSES ===
{role_outputs}

=== RAW EVIDENCE CORPUS EXCERPT (for evidence-quality checks) ===
{corpus_excerpt}
"""


def extract_json(text: str) -> dict:
    """Extract the first JSON object from possibly-noisy CLI output."""
    text = text.strip()
    if text.startswith("```"):
        # strip a fenced block if the model ignored instructions
        first_nl = text.find("\n")
        text = text[first_nl + 1:] if first_nl != -1 else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in output")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj


def main():
    parser = argparse.ArgumentParser(description="Adversarial review of specialist role outputs")
    parser.add_argument("--idea", required=True, help="Title: one-line description of the decision")
    parser.add_argument("--inputs", required=True, nargs="+",
                        help="Paths to the five role-output JSON files")
    parser.add_argument("--corpus", default=None, help="Optional path to the raw evidence corpus")
    parser.add_argument("--timeout", type=int, default=300)
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

    corpus_excerpt = "(not provided)"
    if args.corpus and os.path.exists(args.corpus):
        with open(args.corpus, "r", encoding="utf-8", errors="replace") as f:
            corpus_excerpt = f.read()[:MAX_CORPUS_EXCERPT_CHARS]

    # .replace(), never .format(): role outputs and corpus text contain braces.
    prompt = (RED_TEAM_PROMPT
              .replace("{idea}", args.idea)
              .replace("{role_outputs}", "\n\n".join(role_outputs))
              .replace("{corpus_excerpt}", corpus_excerpt))

    claude = shutil.which("claude")
    if not claude:
        print(json.dumps({"error": (
            "claude CLI not found on PATH — the red team runs on the locally-"
            "authenticated Claude Code subscription and cannot proceed without it. "
            "Stop and tell Mohit; do not substitute a weaker model for the red team."
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

    try:
        parsed = extract_json(proc.stdout)
    except (ValueError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"Red team returned unparseable output: {e}",
                          "raw_head": proc.stdout[:500]}))
        sys.exit(1)

    result = {
        "analysis_type": "red_team",
        "model_count": 1,
        "models_used": [f"claude {args.model} (Claude Code subscription, local CLI)"],
        "timestamp": datetime.utcnow().isoformat(),
        "consolidated_insights": parsed,
        "raw_model_responses": [{
            "model": f"claude {args.model} (claude -p)",
            "response": parsed,
            "latency_ms": round(latency, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
