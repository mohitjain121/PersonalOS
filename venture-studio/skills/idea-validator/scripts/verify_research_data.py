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
"""

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


def main():
    parser = argparse.ArgumentParser(description="Research data integrity checks for idea-validator")
    subparsers = parser.add_subparsers(dest="command")

    p_raw = subparsers.add_parser("check-raw-data")
    p_raw.add_argument("--file", required=True)
    p_raw.add_argument("--min-bytes", type=int, default=DEFAULT_MIN_BYTES)

    p_synth = subparsers.add_parser("check-synthesis-output")
    p_synth.add_argument("--file", help="Path to a file containing multi_model_research.py's JSON stdout")
    p_synth.add_argument("--json", dest="json_str", help="multi_model_research.py's JSON stdout, passed directly")

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
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
