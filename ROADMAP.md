# Roadmap

Whole-OS milestone tracker, read/updated by Builder OS and by hand. Reflects current reality, not aspiration — see `docs/adr/` for the decisions behind these choices.

## Done

- **Venture Studio** (`venture-studio/`) — idea-validator skill, redesigned 2026-07-04 from the original same-prompt ensemble into a MECE committee: shared evidence corpus → six specialist roles (`demand`, `market`, `competition`, `feasibility`, `economics`, `external`) → sequential Claude Sonnet red team (local `claude -p`, subscription) → Sonnet-written report → PDF → Supabase → Telegram. A 2026-07-08 quality upgrade added: mechanical quote/entity-grounding and finding-coverage gates, an 80K-char red-team/report corpus window, one bounded gap-closure iteration, competitor dossiers, an India evidence lens woven through every dimension, second-opinion runs for `demand`/`economics`, a market/external mandate-overlap fix, and a post-verdict last30days watchlist.
- **Real social evidence wired into the corpus**: Agent Reach (Reddit full-thread pulls via OpenCLI/Brave, throwaway account) and last30days-skill (engagement-ranked 30-day recency across Reddit/X/YouTube-with-transcripts/HN/GitHub/Polymarket/jobs, plus TikTok/Instagram via a ScrapeCreators key). X/Twitter live via both OpenCLI and `twitter-cli` (throwaway-account cookies).
- **Graphify** knowledge graph integrated (`shared-skills/graphify/`, committed graph in `graphify-out/`) — auto-rebuilds on every commit via a git hook; doc/media semantic passes run on the local `claude` CLI (subscription, Haiku), $0 marginal cost.
- **PDF generation fixed** (2026-07-05) — the working path (`generate_pdf_fallback.py`, Edge headless) now actually renders markdown instead of dumping raw `##`/`**`; WeasyPrint (`templates/generate_pdf.py`) remains confirmed broken on this machine and is documented as such, not attempted first.
- **Builder OS** (`builder-os/`) — technical co-founder app: reactive architecture Q&A, and Work Order dispatch (draft → confirm → dispatch to Claude Code → plan approval → execute → independent verify) proven end-to-end 2026-07-03 (two real Work Orders shipped). Extended 2026-07-08 with a standalone, non-agent **provider-auth watchdog** (`scripts/check_provider_auth.py`, Windows Scheduled Task) after a real 3-day silent Nous Portal auth outage.
- **pair-programmer** (`pair-programmer/`) — live conversational coding collaborator reachable from Telegram, for changes that don't need Builder OS's Work Order ceremony.
- **`shared/db.py`** — Supabase client factory, extracted from real duplication in `save_idea.py`/`weekly_digest.py` (ADR 0001).
- **Telegram community structure** — one bot, one private supergroup, forum topics per Application.
- Repo pushed public: github.com/mohitjain121/PersonalOS.
- Two real incidents found and fixed the same day (2026-07-08): the orchestrator bypassing the entire idea-validator pipeline via `delegate_task` (fabricated a fake "Task Complete" report), and the pipeline re-running itself end-to-end a second time after delivery off a stale background second-opinion notification (duplicate Supabase rows, a duplicate PDF sent to Telegram) — both now blocked in SKILL.md, and the resulting Supabase duplicates cleaned up.

## In progress

- Builder OS's **scheduled discovery scan** (Branch A) — the scan logic and Supabase persistence work (`builder_discoveries` has real rows from a prior run), but the twice-weekly cron job itself has not been scheduled yet.
- First fully clean, single-pass production validation run since the 2026-07-08 fixes (double-execution + delegate_task bypass) — every fix has been unit-verified individually; the next real idea submitted end-to-end is the integration proof.

## Open / blocked

- **OpenRouter free-tier daily cap** (~50 requests/day under a $10 account balance) remains the main fragility in the six-role committee + second-opinion calls — a one-time $10 top-up (raises the cap to ~1000/day) is still the cheapest fix and hasn't been done yet.
- Twitter/X evidence depends on a throwaway account's cookies staying valid in `~/.config/last30days/.env` and as `TWITTER_AUTH_TOKEN`/`TWITTER_CT0` env vars — no expiry monitoring yet (unlike the Nous auth watchdog).
- Facebook/Instagram channels report `ok` via Agent Reach's doctor but were never individually live-tested (only Reddit/X were).
- `gh auth login` not yet run in the context Hermes's terminal tool uses by default — GitHub channel works ad-hoc but isn't durably authenticated.
- LinkedIn, Xiaoyuzhou (podcast), Xueqiu (stocks) channels — not configured, no current app needs them.
- `blogwatcher-cli` not yet installed — Builder OS's blog-monitoring source is inert until this is done.

## Next

- Schedule Builder OS's discovery scan cron and do a live verification run of Branch A end-to-end.
- Build the last30days watchlist → Telegram briefing flywheel: surface trending pains *into* the validator instead of only validating ideas Mohit brings.
- Pick and build Application #4 once the above settles — per ADR 0001, only extract further shared modules (e.g. `shared/synthesis.py` from `multi_model_research.py`) when a second real app needs them, not before.
