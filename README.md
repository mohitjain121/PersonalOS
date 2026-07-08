# hermes_agent

Mohit's personal Hermes-powered "Applications" layer — specialized subagents (Telegram-driven) built on top of the [Hermes](https://hermes-agent.nousresearch.com) agent runtime. This is the foundation of a long-running Personal AI Operating System, not a single app — see `docs/adr/0001-personal-ai-os-philosophy.md` for the architecture philosophy behind that.

## Architecture

Hermes itself is the runtime/kernel (planner, scheduler, memory, tool registry, permissions, Telegram transport — all native to Hermes, not part of this repo). This repo holds the **Applications** built on top of it, the **shared skills** every Application can use, and the **shared services**/tooling those Applications depend on — configured via `skills.external_dirs` and `telegram.extra.group_topics` in Hermes's own `config.yaml` (not part of this repo; machine-specific).

## What's here today

- **`venture-studio/`** — the `idea-validator` skill. Drop a startup idea in the Venture Studio topic; a MECE committee of six specialist analysts plus an adversarial Claude red team researches it (real Reddit threads, X, YouTube transcripts, engagement-ranked recency, competitor dossiers, an India evidence lens), persists to Supabase, generates a PDF report, and replies with a TL;DR + PDF. See `venture-studio/README.md`.
- **`builder-os/`** — a "technical co-founder" for this repo itself: reactive architecture Q&A grounded in this repo's own docs, a scheduled discovery scan of the external ecosystem, a Work Order dispatch loop (plan → approve → execute via Claude Code → verify), and a standalone provider-auth watchdog. See `builder-os/README.md`.
- **`pair-programmer/`** — a live, conversational coding collaborator reachable from Telegram, for changes that don't need Builder OS's Work Order ceremony. See `pair-programmer/README.md`.
- **`shared/db.py`** — the one shared module so far: a Supabase client factory, extracted from real duplication (ADR 0001 — extraction happens after the second real caller exists, not before).
- **`shared-skills/`** — first-party skill forks available to every Application:
  - `agent-reach/` — our own in-house fork of Agent Reach's routing skill (SKILL.md + reference docs). We own and edit this file directly; it does not sync from the external `agent-reach/` clone.
  - `graphify/` — a first-party copy of Graphify's Claude Code skill, registered for every Hermes session.
- **`graphify-out/`** — the committed knowledge graph of this repo (code + docs + SQL), rebuilt automatically on every commit via a git hook. Query it before grepping: `graphify query "<question>"`, `graphify path "A" "B"`, `graphify explain "<concept>"`.

## Shared services & tooling

- **Supabase** — persistence layer, one shared project, one table namespace per Application.
- **Telegram** — delivery/interaction layer, one bot, one community group, one topic per Application.
- **[Agent Reach](https://github.com/Panniantong/agent-reach)** — the underlying CLI package for per-platform research (Reddit, X/Twitter, YouTube, GitHub, and more). Deliberately **not** forked or vendored — cloned and pip-installed separately (`agent-reach/`, gitignored), updated via `git pull`. Only the routing *instructions* it reads (`shared-skills/agent-reach/`) are ours to customize. Reddit and X are live via the OpenCLI browser bridge (a throwaway/secondary account logged into Brave — real primary accounts are never used for gated-platform research, per Agent Reach's own ban-risk guidance) and via `twitter-cli`/OpenCLI credentials.
- **[last30days-skill](https://github.com/mvanhorn/last30days-skill)** — engagement-ranked, 30-day recency research across Reddit, X, YouTube (with transcripts), Hacker News, GitHub, Polymarket, jobs signal, and TikTok/Instagram (via a ScrapeCreators key). Cloned externally (`last30days-skill/`, gitignored, `git pull`-updated) and registered via `skills.external_dirs` — its SKILL.md is version-coupled to its engine and is never forked. The calling agent acts as the planner (resolves entities before invoking the engine); requires Python 3.12+ (`python3.14` on this machine, not the Hermes venv's 3.11).
- **[Graphify](https://github.com/Graphify-Labs/graphify)** — knowledge-graph CLI (`uv tool install "graphifyy[leiden]"`, pinned to Python 3.12 for the Leiden extra). Doc/media semantic extraction runs on the local `claude` CLI (subscription, Haiku) via `--backend claude-cli`, so graph rebuilds cost nothing beyond the CLI's own session usage.
- **Provider-auth watchdog** (`builder-os/scripts/check_provider_auth.py`) — a standalone, non-agent Windows Scheduled Task that alerts the Builder OS Telegram topic if Hermes's model provider (Nous Portal OAuth) goes dead. Exists because that exact failure silently broke every response for three days (2026-07-06 to 2026-07-08) before anyone noticed — see `builder-os/README.md`.

## Setup

1. Clone this repo.
2. Clone and install the Agent Reach CLI package alongside it:
   ```bash
   git clone https://github.com/Panniantong/agent-reach.git
   pip install -e agent-reach
   agent-reach install --env=auto
   ```
3. Clone last30days-skill alongside it (do not `pip install` it — it's invoked directly by path):
   ```bash
   git clone https://github.com/mvanhorn/last30days-skill.git
   ```
4. Install Graphify:
   ```bash
   uv tool install --python 3.12 "graphifyy[leiden]"
   graphify install --project --platform agents   # or copy into shared-skills/ as first-party
   graphify hook install                          # auto-rebuild the graph on every commit
   ```
5. Register skill folders in Hermes's `skills.external_dirs` config: each Application's `skills/` folder, `shared-skills/`, and `last30days-skill/skills/`.
6. Set up Supabase (see `venture-studio/README.md` for schema + env vars) and Telegram forum topics per Application (see each Application's README for its topic name and skill binding).
7. For Reddit/X research: log a throwaway/secondary account into Brave (with the OpenCLI extension installed) and, for X specifically, export `AUTH_TOKEN`/`CT0` cookies into `~/.config/last30days/.env` and as `TWITTER_AUTH_TOKEN`/`TWITTER_CT0` user env vars.
8. Register the provider-auth watchdog as a Windows Scheduled Task — see `builder-os/README.md` for the exact `Register-ScheduledTask` command.

## Planned

More Applications, one at a time, following the same pattern: its own Hermes skill, its own Telegram topic, its own Supabase tables where it needs persistence. Extraction into `shared/` happens only when a second real Application needs something already duplicated — not speculatively.

## License

MIT — see [LICENSE](LICENSE).
