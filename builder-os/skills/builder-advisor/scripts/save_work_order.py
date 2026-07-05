"""
save_work_order.py — Supabase persistence for builder-os Work Orders

Called by Hermes via execute_code during Builder OS's Branch C (draft/dispatch)
workflow. See docs/adr/0001-personal-ai-os-philosophy.md for why this uses
shared/db.py instead of its own client setup, and the approved Builder OS
Engineering Control Plane design for the Work Order lifecycle.

Usage:
    python save_work_order.py create --title "..." --objective "..." --work-type feature --acceptance-criteria "..."
    python save_work_order.py update-status --id <uuid> --status queued
    python save_work_order.py update-session --id <uuid> --worker-session-id <id>
    python save_work_order.py complete --id <uuid> --status done --result-summary "..." --commit-sha <sha>
    python save_work_order.py get --id <uuid>
    python save_work_order.py list --status draft
    python save_work_order.py delete --id <uuid>
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from shared.db import get_client

db = get_client()

VALID_STATUSES = ["draft", "queued", "in_progress", "needs_input", "review", "done", "failed", "rejected"]
TERMINAL_STATUSES = {"done", "rejected"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_work_order(
    title: str, objective: str, work_type: str, acceptance_criteria: str,
    application: str = None, priority: str = "normal", context: str = None,
    architectural_constraints: str = None, dependencies: str = None,
) -> dict:
    """Insert a new Work Order as a draft, return the created row."""
    payload = {
        "title": title,
        "objective": objective,
        "work_type": work_type,
        "acceptance_criteria": acceptance_criteria,
        "priority": priority,
        "status": "draft",
    }
    for key, value in [
        ("application", application), ("context", context),
        ("architectural_constraints", architectural_constraints),
        ("dependencies", dependencies),
    ]:
        if value:
            payload[key] = value

    res = db.table("builder_work_orders").insert(payload).execute()
    return res.data[0] if res.data else {"error": "Insert failed", "details": str(res)}


def update_status(work_order_id: str, status: str) -> dict:
    """Transition a Work Order's status."""
    if status not in VALID_STATUSES:
        return {"error": f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}"}

    current_res = db.table("builder_work_orders").select("status").eq("id", work_order_id).execute()
    if current_res.data:
        current_status = current_res.data[0]["status"]
        if current_status in TERMINAL_STATUSES:
            raise ValueError(
                f"Cannot update status: Work Order {work_order_id} is already in terminal status '{current_status}'"
            )

    payload = {"status": status, "updated_at": _now()}
    res = db.table("builder_work_orders").update(payload).eq("id", work_order_id).execute()
    return res.data[0] if res.data else {"error": "Update failed"}


def update_session(work_order_id: str, worker_session_id: str) -> dict:
    """Record the worker's session id, for --resume during the clarification loop."""
    payload = {"worker_session_id": worker_session_id, "updated_at": _now()}
    res = db.table("builder_work_orders").update(payload).eq("id", work_order_id).execute()
    return res.data[0] if res.data else {"error": "Update failed"}


def complete_work_order(work_order_id: str, status: str, result_summary: str, commit_sha: str = None) -> dict:
    """Record the final outcome of a dispatched Work Order."""
    if status not in ("done", "failed", "review", "rejected"):
        return {"error": f"complete expects a terminal-ish status (done/failed/review/rejected), got '{status}'"}
    payload = {"status": status, "result_summary": result_summary, "updated_at": _now()}
    if commit_sha:
        payload["commit_sha"] = commit_sha
    res = db.table("builder_work_orders").update(payload).eq("id", work_order_id).execute()
    return res.data[0] if res.data else {"error": "Update failed"}


def get_work_order(work_order_id: str) -> dict:
    res = db.table("builder_work_orders").select("*").eq("id", work_order_id).single().execute()
    return res.data or {"error": "Not found"}


def list_work_orders(status: str = None, limit: int = 20) -> list:
    query = db.table("builder_work_orders").select("*").order("created_at", desc=True).limit(limit)
    if status:
        query = query.eq("status", status)
    res = query.execute()
    return res.data or []


def delete_work_order(work_order_id: str) -> dict:
    """Permanently remove a Work Order row (for clearing throwaway/test rows)."""
    res = db.table("builder_work_orders").delete().eq("id", work_order_id).execute()
    return {"deleted": True, "id": work_order_id} if res.data else {"error": "Not found"}


def main():
    parser = argparse.ArgumentParser(description="builder-os Work Order operations")
    subparsers = parser.add_subparsers(dest="command")

    p_create = subparsers.add_parser("create")
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--objective", required=True)
    p_create.add_argument("--work-type", required=True,
                          choices=["feature", "bug", "research", "refactor", "architecture", "documentation"])
    p_create.add_argument("--acceptance-criteria", required=True)
    p_create.add_argument("--application")
    p_create.add_argument("--priority", default="normal", choices=["low", "normal", "high"])
    p_create.add_argument("--context")
    p_create.add_argument("--architectural-constraints")
    p_create.add_argument("--dependencies")
    p_create.add_argument("--dry-run", action="store_true",
                          help="Print the would-be-inserted payload without writing to Supabase")

    p_status = subparsers.add_parser("update-status")
    p_status.add_argument("--id", required=True, dest="work_order_id")
    p_status.add_argument("--status", required=True, choices=VALID_STATUSES)

    p_session = subparsers.add_parser("update-session")
    p_session.add_argument("--id", required=True, dest="work_order_id")
    p_session.add_argument("--worker-session-id", required=True)

    p_complete = subparsers.add_parser("complete")
    p_complete.add_argument("--id", required=True, dest="work_order_id")
    p_complete.add_argument("--status", required=True, choices=["done", "failed", "review", "rejected"])
    p_complete.add_argument("--result-summary", required=True)
    p_complete.add_argument("--commit-sha")

    p_get = subparsers.add_parser("get")
    p_get.add_argument("--id", required=True, dest="work_order_id")

    p_list = subparsers.add_parser("list")
    p_list.add_argument("--status", choices=VALID_STATUSES)
    p_list.add_argument("--limit", type=int, default=20)

    p_delete = subparsers.add_parser("delete")
    p_delete.add_argument("--id", required=True, dest="work_order_id")

    args = parser.parse_args()

    try:
        if args.command == "create":
            if args.dry_run:
                payload = {
                    "title": args.title,
                    "objective": args.objective,
                    "work_type": args.work_type,
                    "acceptance_criteria": args.acceptance_criteria,
                    "priority": args.priority,
                    "status": "draft",
                }
                for key in ["application", "context", "architectural_constraints", "dependencies"]:
                    value = getattr(args, key)
                    if value:
                        payload[key] = value
                result = {"dry_run": True, "would_insert": payload}
            else:
                result = create_work_order(
                args.title, args.objective, args.work_type, args.acceptance_criteria,
                args.application, args.priority, args.context,
                args.architectural_constraints, args.dependencies,
            )
        elif args.command == "update-status":
            result = update_status(args.work_order_id, args.status)
        elif args.command == "update-session":
            result = update_session(args.work_order_id, args.worker_session_id)
        elif args.command == "complete":
            result = complete_work_order(args.work_order_id, args.status, args.result_summary, args.commit_sha)
        elif args.command == "get":
            result = get_work_order(args.work_order_id)
        elif args.command == "list":
            result = list_work_orders(args.status, args.limit)
        elif args.command == "delete":
            result = delete_work_order(args.work_order_id)
        else:
            parser.print_help()
            sys.exit(1)

        print(json.dumps(result, default=str, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
