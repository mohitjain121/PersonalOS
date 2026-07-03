"""
save_discovery.py — Supabase persistence for builder-os

Called by Hermes via execute_code during Builder OS's scheduled discovery
scan and reactive Q&A workflows. See docs/adr/0001-personal-ai-os-philosophy.md
for why this uses shared/db.py instead of its own client setup.

Usage:
    python save_discovery.py save-discovery --source hn --title "..." --url "..." --relevance-note "..."
    python save_discovery.py update-status --id <uuid> --status reviewed
    python save_discovery.py list --status new
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from shared.db import get_client

db = get_client()


def save_discovery(source: str, title: str, relevance_note: str, url: str = None, summary: str = None) -> dict:
    """Insert a new discovery, return the created row."""
    payload = {
        "source": source,
        "title": title,
        "relevance_note": relevance_note,
        "status": "new",
    }
    if url:
        payload["url"] = url
    if summary:
        payload["summary"] = summary

    res = db.table("builder_discoveries").insert(payload).execute()
    return res.data[0] if res.data else {"error": "Insert failed", "details": str(res)}


def update_status(discovery_id: str, status: str) -> dict:
    """Update a discovery's review status."""
    payload = {"status": status}
    if status in ("reviewed", "actioned", "dismissed"):
        payload["reviewed_at"] = datetime.now(timezone.utc).isoformat()

    res = db.table("builder_discoveries").update(payload).eq("id", discovery_id).execute()
    return res.data[0] if res.data else {"error": "Update failed"}


def list_discoveries(status: str = None, limit: int = 20) -> list:
    """List discoveries, optionally filtered by status, most recent first."""
    query = db.table("builder_discoveries").select("*").order("discovered_at", desc=True).limit(limit)
    if status:
        query = query.eq("status", status)
    res = query.execute()
    return res.data or []


def main():
    parser = argparse.ArgumentParser(description="builder-os Supabase operations")
    subparsers = parser.add_subparsers(dest="command")

    p_save = subparsers.add_parser("save-discovery")
    p_save.add_argument("--source", required=True,
                        choices=["hn", "github", "arxiv", "blog", "reddit", "twitter", "web", "hermes", "agent-reach"])
    p_save.add_argument("--title", required=True)
    p_save.add_argument("--relevance-note", required=True,
                        help="Why this matters for the Personal AI OS specifically — required, not optional")
    p_save.add_argument("--url")
    p_save.add_argument("--summary")
    p_save.add_argument("--dry-run", action="store_true",
                        help="Print the would-be-inserted payload without writing to Supabase")

    p_status = subparsers.add_parser("update-status")
    p_status.add_argument("--id", required=True, dest="discovery_id")
    p_status.add_argument("--status", required=True, choices=["new", "reviewed", "actioned", "dismissed"])

    p_list = subparsers.add_parser("list")
    p_list.add_argument("--status", choices=["new", "reviewed", "actioned", "dismissed"])
    p_list.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()

    try:
        if args.command == "save-discovery":
            if args.dry_run:
                payload = {
                    "source": args.source,
                    "title": args.title,
                    "relevance_note": args.relevance_note,
                    "status": "new",
                }
                if args.url:
                    payload["url"] = args.url
                if args.summary:
                    payload["summary"] = args.summary
                result = {"dry_run": True, "would_insert": payload}
            else:
                result = save_discovery(args.source, args.title, args.relevance_note, args.url, args.summary)
        elif args.command == "update-status":
            result = update_status(args.discovery_id, args.status)
        elif args.command == "list":
            result = list_discoveries(args.status, args.limit)
        else:
            parser.print_help()
            sys.exit(1)

        print(json.dumps(result, default=str, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
