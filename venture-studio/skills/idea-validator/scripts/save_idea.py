"""
save_idea.py — Supabase persistence for venture-studio

Called by Hermes via execute_code after each research run.

Usage:
    python save_idea.py save-idea --text "..." --title "..." --domain "fintech"
    python save_idea.py save-run --idea-id <uuid> --synthesis "..." --pdf-path "..."
    python save_idea.py update-status --idea-id <uuid> --status validated --verdict strong
    python save_idea.py save-competitor --idea-id <uuid> --name "..." --url "..." ...
    python save_idea.py get-digest       (returns digest_candidates for weekly digest)
"""

import os
import sys
import json
import argparse
from datetime import datetime

try:
    from supabase import create_client, Client
except ImportError:
    print(json.dumps({"error": "supabase-py not installed. Run: pip install supabase"}))
    sys.exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print(json.dumps({"error": "SUPABASE_URL and SUPABASE_KEY must be set in ~/.hermes/.env"}))
    sys.exit(1)

db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def save_idea(text: str, title: str = None, domain: str = None, source: str = "telegram") -> dict:
    """Insert a new idea, return the created row."""
    payload = {
        "raw_text": text,
        "source": source,
        "status": "researching",
    }
    if title:
        payload["title"] = title
    if domain:
        payload["domain"] = domain

    res = db.table("ideas").insert(payload).execute()
    return res.data[0] if res.data else {"error": "Insert failed", "details": str(res)}


def save_research_run(
    idea_id: str,
    web_results: dict = None,
    synthesis: str = None,
    pdf_path: str = None,
    status: str = "complete",
) -> dict:
    """Insert a research run, return the created row."""
    payload = {
        "idea_id": idea_id,
        "status": status,
        "sprint_level": 1,
    }
    if web_results:
        payload["web_results"] = web_results
    if synthesis:
        payload["synthesis"] = synthesis
    if pdf_path:
        payload["pdf_path"] = pdf_path

    res = db.table("research_runs").insert(payload).execute()
    return res.data[0] if res.data else {"error": "Insert failed"}


def save_synthesis_report(
    idea_id: str,
    run_id: str,
    verdict: str,
    summary: str,
    report_md: str,
    report_json: dict = None,
) -> dict:
    """Insert a synthesis report."""
    payload = {
        "idea_id": idea_id,
        "run_id": run_id,
        "final_verdict": verdict,
        "summary": summary,
        "report_md": report_md,
        "sprint_level": 1,
    }
    if report_json:
        payload["report_json"] = report_json

    res = db.table("synthesis_reports").insert(payload).execute()
    return res.data[0] if res.data else {"error": "Insert failed"}


def save_competitor(
    idea_id: str,
    name: str,
    url: str = None,
    description: str = None,
    funding: str = None,
    stage: str = None,
    geo_focus: str = None,
    threat_level: str = "medium",
) -> dict:
    """Insert a competitor entry."""
    payload = {
        "idea_id": idea_id,
        "name": name,
        "threat_level": threat_level,
    }
    for k, v in [("url", url), ("description", description), ("funding", funding),
                 ("stage", stage), ("geo_focus", geo_focus)]:
        if v:
            payload[k] = v

    res = db.table("competitors").insert(payload).execute()
    return res.data[0] if res.data else {"error": "Insert failed"}


def update_idea_status(idea_id: str, status: str, verdict: str = None, title: str = None) -> dict:
    """Update an idea's status and optional verdict."""
    payload = {"status": status}
    if verdict:
        payload["verdict"] = verdict
    if title:
        payload["title"] = title

    res = db.table("ideas").update(payload).eq("id", idea_id).execute()
    return res.data[0] if res.data else {"error": "Update failed"}


def get_digest_candidates() -> list:
    """Fetch top ideas for weekly digest."""
    res = db.table("digest_candidates").select("*").limit(10).execute()
    return res.data or []


def get_idea(idea_id: str) -> dict:
    """Fetch a single idea by ID."""
    res = db.table("ideas").select("*").eq("id", idea_id).single().execute()
    return res.data or {"error": "Not found"}


def main():
    parser = argparse.ArgumentParser(description="venture-studio Supabase operations")
    subparsers = parser.add_subparsers(dest="command")

    # save-idea
    p_idea = subparsers.add_parser("save-idea")
    p_idea.add_argument("--text", required=True)
    p_idea.add_argument("--title")
    p_idea.add_argument("--domain")
    p_idea.add_argument("--source", default="telegram")

    # save-run
    p_run = subparsers.add_parser("save-run")
    p_run.add_argument("--idea-id", required=True)
    p_run.add_argument("--synthesis")
    p_run.add_argument("--pdf-path")
    p_run.add_argument("--web-results")  # JSON string
    p_run.add_argument("--status", default="complete")

    # save-synthesis
    p_synth = subparsers.add_parser("save-synthesis")
    p_synth.add_argument("--idea-id", required=True)
    p_synth.add_argument("--run-id", required=True)
    p_synth.add_argument("--verdict", required=True)
    p_synth.add_argument("--summary", required=True)
    p_synth.add_argument("--report-md", required=True)

    # save-competitor
    p_comp = subparsers.add_parser("save-competitor")
    p_comp.add_argument("--idea-id", required=True)
    p_comp.add_argument("--name", required=True)
    p_comp.add_argument("--url")
    p_comp.add_argument("--description")
    p_comp.add_argument("--funding")
    p_comp.add_argument("--stage")
    p_comp.add_argument("--geo-focus")
    p_comp.add_argument("--threat-level", default="medium")

    # update-status
    p_status = subparsers.add_parser("update-status")
    p_status.add_argument("--idea-id", required=True)
    p_status.add_argument("--status", required=True)
    p_status.add_argument("--verdict")
    p_status.add_argument("--title")

    # get-digest
    subparsers.add_parser("get-digest")

    # get-idea
    p_get = subparsers.add_parser("get-idea")
    p_get.add_argument("--idea-id", required=True)

    args = parser.parse_args()

    try:
        if args.command == "save-idea":
            result = save_idea(args.text, args.title, args.domain, args.source)

        elif args.command == "save-run":
            web_results = json.loads(args.web_results) if args.web_results else None

            # Handle both direct synthesis content and file paths
            synthesis_content = args.synthesis
            if args.synthesis and os.path.isfile(args.synthesis):
                with open(args.synthesis, 'r', encoding='utf-8') as f:
                    synthesis_content = f.read()

            result = save_research_run(
                args.idea_id, web_results, synthesis_content, args.pdf_path, args.status
            )

        elif args.command == "save-synthesis":
            # Handle both direct markdown content and file paths
            report_md_content = args.report_md
            if os.path.isfile(args.report_md):
                with open(args.report_md, 'r', encoding='utf-8') as f:
                    report_md_content = f.read()

            result = save_synthesis_report(
                args.idea_id, args.run_id, args.verdict, args.summary, report_md_content
            )

        elif args.command == "save-competitor":
            result = save_competitor(
                args.idea_id, args.name, args.url, args.description,
                args.funding, args.stage, args.geo_focus, args.threat_level
            )

        elif args.command == "update-status":
            result = update_idea_status(args.idea_id, args.status, args.verdict, args.title)

        elif args.command == "get-digest":
            result = get_digest_candidates()

        elif args.command == "get-idea":
            result = get_idea(args.idea_id)

        else:
            parser.print_help()
            sys.exit(1)

        print(json.dumps(result, default=str, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
