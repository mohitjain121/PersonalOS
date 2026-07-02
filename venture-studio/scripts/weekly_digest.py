"""
weekly_digest.py — Surfaces top unacted validated ideas for the weekly digest

This runs as a Hermes scheduled task every Sunday at 9am IST.
Hermes can call this via execute_code, or you can set up the cron in Hermes config:

  hermes schedule add "weekly-digest" "0 3 * * 0" \
    "run weekly_digest.py and send the output to Telegram"
  (3am UTC = 9am IST on Sundays)

Usage:
    python weekly_digest.py
    python weekly_digest.py --top-n 3
    python weekly_digest.py --format telegram   (default)
    python weekly_digest.py --format markdown
"""

import os
import sys
import json
import argparse
from datetime import datetime

try:
    from supabase import create_client
except ImportError:
    print("supabase-py not installed. Run: pip install supabase")
    sys.exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("SUPABASE_URL and SUPABASE_KEY must be set in ~/.hermes/.env")
    sys.exit(1)

db = create_client(SUPABASE_URL, SUPABASE_KEY)

VERDICT_EMOJI = {
    "strong":     "🟢",
    "promising":  "🟡",
    "weak":       "🟠",
    "dead":       "🔴",
}

FORCING_QUESTIONS = [
    "What's stopping you from spending 2 hours on a landing page this week?",
    "Can you DM 5 potential users about this today?",
    "Is this dead, paused, or still alive? Time to decide.",
    "What's the one thing you'd need to learn to move this forward?",
    "Have you talked to anyone who has this problem in the last month?",
    "What would kill this idea? Have you checked if that's true?",
    "Rate your founder fit here 1–5. If it's below 3, kill it.",
]


def get_digest_candidates(top_n: int = 5) -> list:
    """Fetch top unacted validated ideas from the digest view."""
    res = (
        db.table("digest_candidates")
        .select("*")
        .limit(top_n)
        .execute()
    )
    return res.data or []


def get_total_idea_count() -> int:
    res = db.table("ideas").select("id", count="exact").execute()
    return res.count or 0


def get_ideas_this_week() -> int:
    from datetime import timedelta
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    res = (
        db.table("ideas")
        .select("id", count="exact")
        .gte("created_at", week_ago)
        .execute()
    )
    return res.count or 0


def format_telegram(candidates: list, top_n: int) -> str:
    """Format digest for Telegram delivery."""
    if not candidates:
        return (
            "📭 *Weekly Digest — No new ideas to surface*\n\n"
            "No validated ideas waiting for action. Drop an idea when inspiration hits."
        )

    today = datetime.now().strftime("%d %b %Y")
    total = get_total_idea_count()
    new_this_week = get_ideas_this_week()

    lines = [
        f"📋 *Venture Studio Weekly Digest — {today}*",
        f"_{new_this_week} new idea{'s' if new_this_week != 1 else ''} this week · {total} total in corpus_",
        "",
        f"*Top {min(top_n, len(candidates))} ideas waiting for your decision:*",
        "─────────────────────",
    ]

    import random
    forcing_q = random.choice(FORCING_QUESTIONS)

    for i, idea in enumerate(candidates[:top_n], 1):
        verdict = idea.get("verdict", "uncertain")
        emoji = VERDICT_EMOJI.get(verdict, "⚪")
        title = idea.get("title") or "Untitled Idea"
        domain = idea.get("domain") or "unknown"
        avg_rating = idea.get("avg_rating")
        new_signals = idea.get("new_signals", 0)
        days_ago = ""

        if idea.get("created_at"):
            try:
                created = datetime.fromisoformat(idea["created_at"].replace("Z", "+00:00"))
                delta = (datetime.now().astimezone() - created).days
                days_ago = f" · {delta}d old"
            except Exception:
                pass

        rating_str = f" · ⭐ {avg_rating:.1f}/5" if avg_rating else ""
        signal_str = f" · 🔔 {new_signals} new signals" if new_signals > 0 else ""

        lines.append(f"\n*{i}. {emoji} {title}*")
        lines.append(f"_{domain.capitalize()}{days_ago}{rating_str}{signal_str}_")

        if idea.get("pdf_path") and os.path.exists(str(idea.get("pdf_path", ""))):
            lines.append(f"📎 PDF report available")
        elif not idea.get("pdf_path"):
            lines.append(f"_(no report generated)_")

    lines.extend([
        "",
        "─────────────────────",
        f"💬 *This week's question:*",
        f"_{forcing_q}_",
        "",
        "_Reply with idea number to get more detail, or /validate to add a new idea._",
    ])

    return "\n".join(lines)


def format_markdown(candidates: list, top_n: int) -> str:
    """Format digest as clean markdown."""
    today = datetime.now().strftime("%d %b %Y")
    lines = [f"# Venture Studio Weekly Digest — {today}", ""]

    if not candidates:
        return "\n".join(lines + ["No validated ideas waiting for action."])

    for i, idea in enumerate(candidates[:top_n], 1):
        verdict = idea.get("verdict", "uncertain")
        emoji = VERDICT_EMOJI.get(verdict, "⚪")
        title = idea.get("title") or "Untitled"
        pdf_path = idea.get("pdf_path", "")
        lines.extend([
            f"## {i}. {emoji} {title}",
            f"- **Verdict:** {verdict.capitalize()}",
            f"- **Domain:** {idea.get('domain', 'unknown').capitalize()}",
            f"- **Competitors found:** {idea.get('competitor_count', 0)}",
        ])
        if pdf_path:
            lines.append(f"- PDF: `{pdf_path}`")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate weekly venture studio digest")
    parser.add_argument("--top-n", type=int, default=3, help="Number of ideas to surface")
    parser.add_argument("--format", choices=["telegram", "markdown"], default="telegram")
    args = parser.parse_args()

    candidates = get_digest_candidates(top_n=args.top_n + 5)  # fetch a few extra for ranking

    if args.format == "telegram":
        output = format_telegram(candidates, args.top_n)
    else:
        output = format_markdown(candidates, args.top_n)

    print(output)


if __name__ == "__main__":
    main()
