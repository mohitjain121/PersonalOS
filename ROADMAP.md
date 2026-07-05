# Roadmap

Whole-OS milestone tracker, read/updated by Builder OS and by hand. Reflects current reality, not aspiration — see `docs/adr/` for the decisions behind these choices.

## Done

- **Venture Studio** (`venture-studio/`) — idea-validator skill: MECE research committee (shared web-evidence corpus → five specialist roles: demand/arena/feasibility/economics/external, one free model each with fallback chains → sequential Claude Sonnet red team via local `claude -p` on the subscription), Supabase persistence, PDF report generation (Edge-headless fallback, primary weasyprint path confirmed broken on this machine), Telegram delivery. Live in the "Venture Studio" forum topic. Redesigned 2026-07-04 from the original same-prompt 4-track ensemble.
- **Agent Reach** wired globally (`shared-skills/agent-reach/`, in-house routing-instructions fork; `agent-reach/` CLI package stays external, `git pull`-updated) — gives every Application read/search access to GitHub, YouTube, RSS, web, Exa search (zero-config), plus Reddit/Twitter/Bilibili/XiaoHongShu (via OpenCLI/Brave, login-gated).
- **`shared/db.py`** — Supabase client factory, extracted from real duplication in `save_idea.py`/`weekly_digest.py` (ADR 0001).
- **Telegram community structure** — one bot, one private supergroup, forum topics per Application.
- Repo pushed public: github.com/mohitjain121/PersonalOS.
- **Builder OS** (`builder-os/`) — technical co-founder app, live in the "🔧 Builder OS" forum topic: reactive architecture Q&A, and Work Order dispatch (draft → confirm → dispatch to Claude Code → plan approval → execute → independent verify) proven end-to-end 2026-07-03 (two real Work Orders shipped: `save_discovery.py --dry-run`, commit `76c2556`; `save_work_order.py` terminal-status guard, commit `ae344f2`).

## In progress

- Builder OS's **scheduled discovery scan** (Branch A) — the scan logic and Supabase persistence work (`builder_discoveries` has real rows from a prior run), but the twice-weekly cron job itself has not been scheduled yet.

## Open / blocked

- Reddit, Twitter, XiaoHongShu still need throwaway/secondary accounts logged into Brave (ban-risk platforms, per Agent Reach's own guidance) — blocks the "socials" part of research quality for any app, including Builder OS's Reddit/Twitter discovery scanning.
- `gh auth login` not yet run in the context Hermes's terminal tool uses by default — GitHub channel works ad-hoc but isn't durably authenticated.
- LinkedIn, Xiaoyuzhou (podcast), Xueqiu (stocks) channels — not configured, no current app needs them.
- `blogwatcher-cli` not yet installed — Builder OS's blog-monitoring source is inert until this is done.

## Next

- Schedule Builder OS's discovery scan cron and do a live verification run of Branch A end-to-end.
- Pick and build Application #3 once Builder OS is proven — per ADR 0001, only extract further shared modules (e.g. `shared/synthesis.py` from `multi_model_research.py`) when a second real app needs them, not before.
