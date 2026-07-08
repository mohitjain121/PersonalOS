"""
verify_research_data.py — Mechanical integrity gate for idea-validator's research pipeline

Guards against two real failure modes that have actually happened (2026-07-03):
1. Raw search-data files silently lost and replaced with fabricated one-line
   placeholders (e.g. "AI character entertainment market research raw data
   placeholder.") that then got fed to the model ensemble as if real.
2. multi_model_research.py's synthesis failing entirely (e.g. missing API key)
   while the pipeline continued and shipped a report anyway.

This is a deliberately mechanical, non-LLM-judgment check — the whole point is
a trip-wire that doesn't depend on the agent noticing something is wrong.

Usage:
    python verify_research_data.py check-raw-data --file <path> [--min-bytes 1000]
    python verify_research_data.py check-synthesis-output --file <path>
    python verify_research_data.py check-synthesis-output --json '<raw stdout from multi_model_research.py>'
    python verify_research_data.py check-entity-grounding --file <corpus> --terms "term1,term2"
    python verify_research_data.py check-quote-grounding --file <role.json> --corpus <corpus>
    python verify_research_data.py check-report-quotes --report <report.md> --corpus <corpus> [--inputs a.json b.json ...]
    python verify_research_data.py check-finding-coverage --report <report.md> --red-team <red_team.json>
"""

import re
import sys
import json
import argparse
import os

# Real per-track search dumps from a genuine run were 2942-6511 bytes; the
# fabricated placeholders that replaced them were 65-147 bytes. 1000 cleanly
# separates the two based on that incident.
DEFAULT_MIN_BYTES = 1000

# Structural markers a real multi-query search dump has that a fabricated
# one-paragraph stand-in does not.
MARKERS = ["=== QUERY", "URL:"]
MIN_MARKER_COUNT = 2

# Per-track fields at least one of which must carry actual content for a
# consolidation to be usable. On 2026-07-03 a market consolidation with
# market_size=null and every list empty (all models 429'd or returned
# truncated JSON) passed the purely structural check and nearly fed an empty
# section into the report.
SUBSTANTIVE_FIELDS = {
    # MECE role architecture (2026-07-04 redesign; arena split into
    # market + competition later the same day)
    "demand": ("pain_points", "icp", "current_workarounds", "wtp_signals"),
    "market": ("market_size", "growth_signals", "why_now", "industry_structure"),
    "competition": ("competitors", "whitespace", "moats_available"),
    "arena": ("market_size", "competitors", "why_now", "whitespace"),  # legacy pre-split
    "feasibility": ("capability_assessment", "engineering_effort",
                    "cost_to_serve_drivers", "scalability_risks"),
    "economics": ("pricing_thesis", "cac_by_channel",
                  "distribution_channels", "adoption_frictions"),
    "external": ("regulatory", "platform_dependencies",
                 "timing_macro_risks", "risk_level"),
    "red_team": ("hidden_assumptions", "kill_likelihood", "verdict_pressure_test"),
    # Legacy same-prompt track types, kept so old artifacts still verify
    "market": ("market_size", "growth_signals", "tailwinds", "headwinds"),
    "competitor": ("competitors",),
    "user_signal": ("pain_points", "workarounds"),
    "regulatory": ("regulatory_bodies", "requirements"),
}


def check_raw_data(file_path: str, min_bytes: int) -> dict:
    if not os.path.exists(file_path):
        return {"ok": False, "error": f"File does not exist: {file_path}"}

    size = os.path.getsize(file_path)
    if size < min_bytes:
        return {
            "ok": False,
            "error": (
                f"File is only {size} bytes (minimum {min_bytes}) — this looks like "
                "a placeholder/stub, not real research data. Do not proceed to "
                "synthesis with this file; re-persist the actual search results via "
                "the write_file tool, or stop this track and say so explicitly."
            ),
            "bytes": size,
        }

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    marker_count = sum(content.count(m) for m in MARKERS)
    if marker_count < MIN_MARKER_COUNT:
        return {
            "ok": False,
            "error": (
                f"File is {size} bytes but contains no recognizable search-result "
                f"structure (fewer than {MIN_MARKER_COUNT} occurrences of "
                f"{MARKERS!r}) — this looks fabricated or hallucinated, not a real "
                "search dump. Do not proceed to synthesis with this file."
            ),
            "bytes": size,
            "markers_found": marker_count,
        }

    return {"ok": True, "bytes": size, "markers_found": marker_count}


def check_synthesis_output(raw_text: str) -> dict:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Output is not valid JSON: {e}"}

    if "error" in data:
        return {
            "ok": False,
            "error": (
                f"Synthesis script reported an error: {data['error']!r} — this is "
                "not usable synthesis. Do not write a report section from this "
                "output; stop this track and tell Mohit specifically what failed."
            ),
        }

    model_count = data.get("model_count", 0)
    if not model_count or model_count < 1:
        return {
            "ok": False,
            "error": (
                f"model_count is {model_count} — no models actually responded, "
                "this synthesis is not usable even though it didn't error."
            ),
        }

    insights = data.get("consolidated_insights")
    if not insights or not isinstance(insights, dict):
        return {
            "ok": False,
            "error": "consolidated_insights is missing or empty — nothing to report from.",
        }

    analysis_type = data.get("analysis_type")
    substantive = SUBSTANTIVE_FIELDS.get(analysis_type)
    if substantive and not any(insights.get(field) for field in substantive):
        return {
            "ok": False,
            "error": (
                f"consolidated_insights for {analysis_type!r} is structurally present "
                f"but carries no content — none of {list(substantive)} have any values. "
                "This happens when every model 429'd or returned truncated/invalid "
                "JSON: model_count counts responses received, not responses parsed. "
                "This consolidation is not usable; do not write a report section from "
                "it. Check raw_model_responses for per-model errors and re-run the "
                "track (or stop it and tell Mohit specifically what failed)."
            ),
        }

    return {
        "ok": True,
        "model_count": model_count,
        "analysis_type": data.get("analysis_type"),
        "models_used": data.get("models_used"),
    }


# ---------------------------------------------------------------------------
# Fuzzy-grounding core (items 1-3 of the 2026-07-08 quality upgrade).
# Deliberately mechanical: token shingles, no LLM judgment, stdlib only.
# ---------------------------------------------------------------------------

# Quotes shorter than this are too generic to ground reliably; per the
# last30days entity-grounding philosophy, failure modes must degrade toward
# "no penalty", so short quotes are simply not checked.
MIN_GROUNDABLE_QUOTE_CHARS = 25
SHINGLE_TOKENS = 8

# Curly quotes are directional, so pairing is unambiguous. Straight quotes are
# not: a closing '"' scanned in isolation looks identical to an opener, and a
# naive pattern captures the prose BETWEEN two short quoted phrases (found in
# testing 2026-07-08). Anchor straight-quote openers to a preceding
# space/start/punctuation and closers to a following space/punctuation.
_CURLY_QUOTE_RE = re.compile(r'“([^”]{%d,}?)”' % MIN_GROUNDABLE_QUOTE_CHARS)
_STRAIGHT_QUOTE_RE = re.compile(
    r'(?:(?<=\s)|(?<=^)|(?<=[(\[{:;—–-]))"([^"\n]{%d,}?)"(?=[\s.,;:!?)\]}]|$)'
    % MIN_GROUNDABLE_QUOTE_CHARS,
    re.MULTILINE,
)
_QUOTE_FIELD_HINTS = ("quote", "verbatim", "evidence_text")


def _find_quotes(text: str):
    for rx in (_CURLY_QUOTE_RE, _STRAIGHT_QUOTE_RE):
        for m in rx.finditer(text):
            yield m.group(1)


def _normalize(text: str) -> str:
    """Lowercase, strip non-alphanumerics to spaces, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text.lower())).strip()


def _shingle_grounded(quote: str, corpus_norm: str) -> bool:
    """A quote is grounded if any SHINGLE_TOKENS-token run of it appears
    verbatim in the normalized corpus. Ellipsized quotes are split and each
    fragment long enough to check must ground independently."""
    for fragment in re.split(r"\.\.\.|…", quote):
        tokens = _normalize(fragment).split()
        if len(tokens) < 4:
            continue  # too short to judge — degrade toward no penalty
        window = min(SHINGLE_TOKENS, len(tokens))
        hit = any(
            " ".join(tokens[i:i + window]) in corpus_norm
            for i in range(len(tokens) - window + 1)
        )
        if not hit:
            return False
    return True


def _walk_strings(node, path=""):
    """Yield (json_path, string_value) for every string in a JSON structure."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def _extract_quotes_from_json(insights) -> list:
    """Collect (path, quote_text) pairs: whole values of *quote*-named fields,
    plus any quotation-marked span inside any string value."""
    quotes = []
    for path, value in _walk_strings(insights):
        leaf = path.rsplit(".", 1)[-1].split("[")[0].lower()
        if any(h in leaf for h in _QUOTE_FIELD_HINTS) and len(value) >= MIN_GROUNDABLE_QUOTE_CHARS:
            quotes.append((path, value))
        for q in _find_quotes(value):
            quotes.append((path, q))
    return quotes


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def check_quote_grounding(role_json_text: str, corpus_texts: list) -> dict:
    try:
        data = json.loads(role_json_text)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Role output is not valid JSON: {e}"}
    insights = data.get("consolidated_insights", data)
    corpus_norm = _normalize(" ".join(corpus_texts))
    quotes = _extract_quotes_from_json(insights)
    ungrounded = [
        {"path": p, "quote": q[:160]}
        for p, q in quotes if not _shingle_grounded(q, corpus_norm)
    ]
    if ungrounded:
        return {
            "ok": False,
            "error": (
                f"{len(ungrounded)} of {len(quotes)} quoted strings in this role output "
                "do NOT appear in the evidence corpus — the model likely invented or "
                "paraphrased them into 'verbatim' quotes. A quote that cannot be traced "
                "to the corpus must not reach the report. Re-run the role, or strip the "
                "ungrounded quotes and re-gate; do not proceed with them in place."
            ),
            "ungrounded": ungrounded,
            "quotes_checked": len(quotes),
        }
    return {"ok": True, "quotes_checked": len(quotes)}


# A quoted passage in the report only *claims to be evidence* when it carries
# source attribution nearby (u/, r/, @handle, a link, or an em-dash citation).
# Unattributed quotes are rhetorical compression by the writer — checking them
# produced 7 false positives on a known-good report (2026-07-08 calibration).
# Fabricated evidence is dangerous precisely because it comes WITH attribution.
_ATTRIBUTION_RE = re.compile(r'(u/|r/[A-Za-z]|https?://|@\w)')
_ATTRIBUTION_WINDOW = 140


def check_report_quotes(report_text: str, corpus_texts: list) -> dict:
    corpus_norm = _normalize(" ".join(corpus_texts))
    quotes = []
    for rx in (_CURLY_QUOTE_RE, _STRAIGHT_QUOTE_RE):
        for m in rx.finditer(report_text):
            trailing = report_text[m.end():m.end() + _ATTRIBUTION_WINDOW]
            if _ATTRIBUTION_RE.search(trailing):
                quotes.append(m.group(1))
    ungrounded = [q[:160] for q in quotes if not _shingle_grounded(q, corpus_norm)]
    if ungrounded:
        return {
            "ok": False,
            "error": (
                f"{len(ungrounded)} of {len(quotes)} quoted passages in the report do "
                "not trace back to the corpus or the gated role/red-team outputs. "
                "Quotes must never be invented at synthesis time. Rerun write_report.py; "
                "if it recurs, surface the specific quotes to Mohit."
            ),
            "ungrounded": ungrounded,
            "quotes_checked": len(quotes),
        }
    return {"ok": True, "quotes_checked": len(quotes)}


def check_entity_grounding(corpus_text: str, terms: list) -> dict:
    """Per-section topical check. Conservative by design: individual dead
    sections are warnings; the gate only fails when a large share of the
    corpus never mentions the idea it is supposed to be evidence for."""
    terms_norm = [_normalize(t) for t in terms if _normalize(t)]
    # Head tokens too: 'AI companion app' should also match on 'companion'
    heads = {t.split()[0] for t in terms_norm if len(t.split()[0]) >= 4}
    probes = set(terms_norm) | heads
    if not probes:
        return {"ok": False, "error": "No usable --terms supplied for entity grounding."}

    sections, current, header = [], [], "(preamble)"
    for line in corpus_text.splitlines():
        if line.startswith("=== "):
            sections.append((header, "\n".join(current)))
            header, current = line.strip(), []
        else:
            current.append(line)
    sections.append((header, "\n".join(current)))

    dead, total_bytes, dead_bytes = [], 0, 0
    for header, body in sections:
        size = len(body.encode("utf-8", errors="replace"))
        if size < 200:
            continue  # trivial section — no penalty
        total_bytes += size
        body_norm = _normalize(body)
        if not any(p in body_norm for p in probes):
            dead.append({"section": header[:120], "bytes": size})
            dead_bytes += size

    dead_share = (dead_bytes / total_bytes) if total_bytes else 0.0
    result = {
        "ok": dead_share <= 0.40,
        "sections_checked": sum(1 for _, b in sections if len(b.encode("utf-8", errors="replace")) >= 200),
        "dead_sections": dead,
        "dead_share": round(dead_share, 3),
    }
    if not result["ok"]:
        result["error"] = (
            f"{round(dead_share * 100)}% of corpus bytes never mention the idea's "
            f"entity terms {terms!r} — the corpus is substantially off-topic "
            "(this is the r/NOTHINGHomescreens failure mode: keyword-matched noise). "
            "Remove the dead sections listed and re-gather focused evidence before "
            "running roles."
        )
    elif dead:
        result["warning"] = (
            f"{len(dead)} section(s) never mention the entity terms — review and "
            "remove them from the corpus before running roles (they dilute every "
            "role's reading budget): " + "; ".join(d["section"] for d in dead[:5])
        )
    return result


def check_finding_coverage(report_text: str, red_team_json_text: str) -> dict:
    """Every fatal/high hidden assumption and every top kill reason from the
    red team must be traceable in the report — softening or dropping findings
    at synthesis time is the failure this closes."""
    try:
        rt = json.loads(red_team_json_text)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Red team file is not valid JSON: {e}"}
    insights = rt.get("consolidated_insights", rt)
    report_norm = _normalize(report_text)
    report_tokens = set(report_norm.split())

    must_cover = []
    for a in insights.get("hidden_assumptions", []) or []:
        if isinstance(a, dict) and str(a.get("severity", "")).lower() in ("fatal", "high"):
            must_cover.append(("assumption[%s]" % a.get("severity"), a.get("assumption", "")))
    kill = insights.get("kill_likelihood") or {}
    for r in (kill.get("top_kill_reasons") or []):
        must_cover.append(("kill_reason", r if isinstance(r, str) else json.dumps(r)))

    missing = []
    for kind, text in must_cover:
        content_words = [w for w in _normalize(text).split() if len(w) >= 5]
        if not content_words:
            continue
        coverage = sum(1 for w in content_words if w in report_tokens) / len(content_words)
        if coverage < 0.40:
            missing.append({"kind": kind, "finding": text[:200], "coverage": round(coverage, 2)})

    score = kill.get("score_pct")
    score_missing = score is not None and str(score) not in report_text
    if missing or score_missing:
        return {
            "ok": False,
            "error": (
                "The report drops or heavily softens red-team findings that must appear "
                f"in it: {len(missing)} finding(s) under 40% content-word coverage"
                + (f"; kill-likelihood score {score} never stated" if score_missing else "")
                + ". The Red Team Findings section must report these plainly — regenerate."
            ),
            "missing": missing,
            "findings_checked": len(must_cover),
        }
    return {"ok": True, "findings_checked": len(must_cover)}


def main():
    parser = argparse.ArgumentParser(description="Research data integrity checks for idea-validator")
    subparsers = parser.add_subparsers(dest="command")

    p_raw = subparsers.add_parser("check-raw-data")
    p_raw.add_argument("--file", required=True)
    p_raw.add_argument("--min-bytes", type=int, default=DEFAULT_MIN_BYTES)

    p_synth = subparsers.add_parser("check-synthesis-output")
    p_synth.add_argument("--file", help="Path to a file containing multi_model_research.py's JSON stdout")
    p_synth.add_argument("--json", dest="json_str", help="multi_model_research.py's JSON stdout, passed directly")

    p_entity = subparsers.add_parser("check-entity-grounding")
    p_entity.add_argument("--file", required=True, help="Corpus file")
    p_entity.add_argument("--terms", required=True,
                          help="Comma-separated entity/problem terms from Step 0 parsing")

    p_quote = subparsers.add_parser("check-quote-grounding")
    p_quote.add_argument("--file", required=True, help="Gated role-output JSON file")
    p_quote.add_argument("--corpus", required=True, help="Corpus file the quotes must trace to")

    p_rq = subparsers.add_parser("check-report-quotes")
    p_rq.add_argument("--report", required=True, help="Final report markdown")
    p_rq.add_argument("--corpus", required=True, help="Corpus file")
    p_rq.add_argument("--inputs", nargs="*", default=[],
                      help="Gated role/red-team JSONs (quotes may trace to these too)")

    p_cov = subparsers.add_parser("check-finding-coverage")
    p_cov.add_argument("--report", required=True, help="Final report markdown")
    p_cov.add_argument("--red-team", required=True, help="Gated red_team.json")

    args = parser.parse_args()

    if args.command == "check-raw-data":
        result = check_raw_data(args.file, args.min_bytes)
    elif args.command == "check-synthesis-output":
        if args.json_str:
            raw_text = args.json_str
        elif args.file:
            if not os.path.exists(args.file):
                print(json.dumps({"ok": False, "error": f"File does not exist: {args.file}"}))
                sys.exit(1)
            with open(args.file, "r", encoding="utf-8", errors="replace") as f:
                raw_text = f.read()
        else:
            raw_text = sys.stdin.read()
        result = check_synthesis_output(raw_text)
    elif args.command == "check-entity-grounding":
        result = check_entity_grounding(_read(args.file),
                                        [t.strip() for t in args.terms.split(",")])
    elif args.command == "check-quote-grounding":
        result = check_quote_grounding(_read(args.file), [_read(args.corpus)])
    elif args.command == "check-report-quotes":
        sources = [_read(args.corpus)] + [_read(p) for p in args.inputs if os.path.exists(p)]
        result = check_report_quotes(_read(args.report), sources)
    elif args.command == "check-finding-coverage":
        result = check_finding_coverage(_read(args.report), _read(args.red_team))
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
