# builder-os

Hermes-powered "technical co-founder" for the Personal AI OS itself — not a coding agent itself (Claude Code owns implementation as a dispatched worker), not a chatbot. It continuously scans the external ecosystem (Hermes, Agent Reach, Hacker News, arXiv, blogs, GitHub) for what actually matters to this specific project, answers live architecture/technical questions grounded in this repo's own `README.md`, `docs/adr/`, and `ROADMAP.md`, and turns change requests into structured Work Orders dispatched to Claude Code — plan, approve, execute, verify.

See `docs/adr/0001-personal-ai-os-philosophy.md` for the full reasoning — in short: almost nothing here is new infrastructure. Blog/paper monitoring reuses Hermes's native `blogwatcher`/`arxiv` skills, GitHub/Reddit/Twitter/web reuse Agent Reach (already wired globally), and the genuinely new pieces are two Supabase tables (`builder_discoveries`, `builder_work_orders`), one Telegram topic, and the Work Order dispatch loop itself.

## Setup

1. Supabase: run `supabase/schema.sql` against the same project venture-studio uses (env vars already configured are reused — no new credentials needed).
2. Install `blogwatcher-cli` (see the `blogwatcher` skill for install methods) if you want blog monitoring in the scheduled scan — everything else in Branch A works without it.
3. Create a "🔧 Builder OS" forum topic in the existing Telegram supergroup, register it in Hermes's `telegram.extra.group_topics` config alongside Venture Studio's entry.
4. Register `builder-os/skills` in Hermes's `skills.external_dirs`.
5. Make sure the `claude` CLI is installed and authenticated in the environment Hermes's `terminal` tool runs in — Branch C dispatches to it via `claude -p`.
6. Schedule the discovery scan: `/schedule add "builder-os-scan" "<twice-weekly cron>" "run the builder-advisor scheduled discovery scan"`.

## Usage

**Scheduled discovery digest** (automatic, twice weekly): posts new, specifically-relevant findings to the "🔧 Builder OS" topic.

**Ask it anything technical**, directly in that topic — "should we adopt X", "what's blocking us", "what's our current architecture" — it reads the live repo state before answering.

**Request a change** — a feature, bug fix, refactor, or doc update, in plain language. Builder OS dispatches the classification/drafting itself to Claude Code (not its own judgment), posts the resulting Work Order for your confirmation, dispatches a plan from that same Claude session, relays the plan for a second, separate approval, then resumes it again to implement and commit. Builder OS itself never edits code — it only reads context, dispatches, and independently verifies the diff before marking a Work Order done. Everyday scanning and Q&A (Branches A/B) stay on Builder OS's own configured model; only Work Order dispatch (Branch C) runs through Claude Code, so it can use a Claude Pro/Max subscription login instead of separate API credits if one is available in the environment.

## Structure

```
builder-os/
├── skills/builder-advisor/
│   ├── SKILL.md                 # all three workflows: scheduled scan, reactive Q&A, Work Order dispatch
│   └── scripts/
│       ├── save_discovery.py    # Supabase persistence for discoveries, via shared/db.py
│       └── save_work_order.py   # Supabase persistence for Work Orders, via shared/db.py
└── supabase/
    └── schema.sql                # builder_discoveries + builder_work_orders tables
```
