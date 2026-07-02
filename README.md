# hermes_agent

Mohit's personal Hermes-powered "Applications" layer — specialized subagents (Telegram-driven) built on top of the [Hermes](https://hermes-agent.nousresearch.com) agent runtime.

## Architecture

Hermes itself is the runtime/kernel (planner, scheduler, memory, tool registry, permissions — all native to Hermes, not part of this repo). This repo holds the **Applications** built on top of it, plus the setup for shared services they depend on.

Each Application is a Telegram forum **topic** inside one community group, bound to its own Hermes skill and, where relevant, its own Supabase tables for persistence — configured via `skills.external_dirs` and `telegram.extra.group_topics` in Hermes's own `config.yaml` (not part of this repo; machine-specific).

## What's here today

- **`venture-studio/`** — the `idea-validator` skill. Drop a startup idea in the Venture Studio topic; Hermes researches it (4-track multi-model ensemble via OpenRouter), persists to Supabase, generates a PDF report, and replies with a TL;DR + PDF.
- **`shared-skills/agent-reach/`** — our own in-house fork of Agent Reach's routing skill (SKILL.md + reference docs), available to every Application. We own and edit this file directly; it does not sync from the `agent-reach/` clone.

## Shared services

- **[Agent Reach](https://github.com/Panniantong/agent-reach)** — the underlying CLI package (per-platform scraping/routing code for Reddit, Twitter/X, YouTube, GitHub, and more — `channels/`, `backends/`, `cli.py`, `doctor.py`). Deliberately **not** forked — it's actively maintained upstream against adversarial platform changes we don't want to take on ourselves. Not vendored in this repo (see setup below) — cloned and pip-installed separately, updated via `git pull` in that clone. Only the routing *instructions* the agent reads (`shared-skills/agent-reach/`) are ours to customize.
- **Supabase** — persistence layer, one shared project, one table namespace per Application.
- **Telegram** — delivery/interaction layer, one bot, one community group, one topic per Application.

## Setup

1. Clone this repo.
2. Clone and install the Agent Reach CLI package alongside it:
   ```bash
   git clone https://github.com/Panniantong/agent-reach.git
   pip install -e agent-reach
   agent-reach install --env=auto
   ```
3. Register skill folders in Hermes's `skills.external_dirs` config: each Application's skill folder, plus `shared-skills` (our in-house Agent Reach routing skill — not `agent-reach/agent_reach`, that's the external clone's own copy, unused now).
4. Set up Supabase (see `venture-studio/README.md` for schema + env vars) and Telegram forum topics per Application.

## Planned

More Applications, one at a time, following the same pattern: its own Hermes skill, its own Telegram topic, its own Supabase tables where it needs persistence. Nothing beyond `venture-studio/` is built yet — anything else is future work, not a commitment.

## License

MIT — see [LICENSE](LICENSE).
