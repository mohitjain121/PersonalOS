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

## Provider auth watchdog

Standalone, NOT an agent skill — `scripts/check_provider_auth.py` runs on a Windows Scheduled Task (`HermesProviderAuthWatchdog`, every 30 min), independent of the Hermes agent loop. This exists because of a real 2026-07-06 to 2026-07-08 incident: the Nous Portal OAuth token went dead, and every Telegram message got a fast, generic fallback reply (`api_calls=0`) instead of a real response — silently, for the better part of three days, because nothing outside the broken agent loop was watching it. A check that depends on the agent to notice its own brokenness has the same failure mode as trusting unverified LLM output, so this is a deterministic script with no LLM involved, alerting straight to this project's own Builder OS Telegram topic via the Bot HTTP API.

Detection: `hermes auth status <provider>` for every provider in `model.provider`/`fallback_providers`, plus a scan of new `gateway.log` lines for `Primary provider auth failed` since the last run (catches a token that's present-but-invalid even if `auth status` doesn't reflect it yet). Alerts are deduped — fires on healthy→unhealthy and unhealthy→healthy transitions, plus a reminder every 4 hours if still broken.

Re-register after moving the repo or updating Hermes's venv path:
```powershell
$py = "C:\Users\<you>\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
$script = "<repo>\builder-os\scripts\check_provider_auth.py"
$action = New-ScheduledTaskAction -Execute $py -Argument "`"$script`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName "HermesProviderAuthWatchdog" -Action $action -Trigger $trigger -Force
```
Verify wiring any time with `python builder-os/scripts/check_provider_auth.py --self-test` (sends a real Telegram message regardless of health state).

## Structure

```
builder-os/
├── skills/builder-advisor/
│   ├── SKILL.md                 # all three workflows: scheduled scan, reactive Q&A, Work Order dispatch
│   └── scripts/
│       ├── save_discovery.py    # Supabase persistence for discoveries, via shared/db.py
│       └── save_work_order.py   # Supabase persistence for Work Orders, via shared/db.py
├── scripts/
│   └── check_provider_auth.py   # standalone provider-auth watchdog (Windows Scheduled Task, not agent-invoked)
└── supabase/
    └── schema.sql                # builder_discoveries + builder_work_orders tables
```
