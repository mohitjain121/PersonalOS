# ADR 0001: Personal AI OS — Architecture Philosophy

**Status:** Accepted (2026-07-02)

## Context

This repository is the foundation of a long-running Personal AI Operating System, not a standalone Venture Studio. Hermes is the runtime/kernel; this repo holds Applications (Venture Studio today; more planned) and, over time, shared modules those applications actually need.

An earlier draft of this decision proposed a `Provider`/`Evidence` abstraction layer for external research, a subprocess-CLI wrapper around Agent Reach, Postgres schema namespacing per app, and a restructure into an `apps/` directory. All four were rejected after review:

- The `Provider` abstraction had exactly one implementation (Agent Reach) — speculative generality with no second use case to shape the interface.
- The CLI-shim added a second layer of process-spawning latency on top of what Agent Reach's own SKILL.md-driven direct invocation already does, at the exact moment a live latency complaint had just been diagnosed and fixed — and replaced an LLM's robust, self-correcting shell-command usage with a brittle stdout-parsing contract against another project's CLI output.
- Postgres schema namespacing (`CREATE SCHEMA venture`) has a concrete failure mode: Supabase's PostgREST API only exposes the `public` schema by default; additional schemas require explicit dashboard configuration easy to forget, causing silent query failures.
- Moving `venture-studio/` into an `apps/` wrapper was restructuring risk for zero present benefit, immediately after a session where a hardcoded/broken path had silently broken the live pipeline.

## Decision

**Build applications first. Extract shared modules only when multiple applications naturally need them, driven by observed duplication, not predicted duplication.**

Concretely:

1. **Hermes owns the runtime** — orchestration, planning, scheduling, tool execution, its own cross-session memory, Telegram transport (including per-topic routing and file delivery). This repository does not duplicate any of it.
2. **This repository owns application logic** — SKILL.md workflows/prompts, Supabase schemas and domain data, and shared helper modules extracted only from proven reuse.
3. **Applications are flat top-level folders** (`venture-studio/`, and future apps the same way) — no `apps/` wrapper unless repo growth later makes one a felt necessity, not a predicted one.
4. **Supabase uses table-prefix naming** (`venture_ideas`, future `investment_reports`, etc.) inside the default `public` schema — not Postgres schema namespacing — avoiding the PostgREST exposed-schema gotcha while still avoiding table-name collisions across apps.
5. **Agent Reach is used directly** by application SKILL.md files, per its own upstream design (the LLM agent reads routing instructions and runs shell commands itself) — no wrapper package. If a provider swap is ever genuinely needed, the cost at today's scale (1–2 apps) is editing a couple of SKILL.md files, which is cheaper than maintaining a parsing layer against another project's CLI output.
6. **The first (and, as of this ADR, only) shared module is `shared/db.py`** — a single Supabase client factory — because it is *already* duplicated today in `venture-studio/scripts/save_idea.py` and `venture-studio/scripts/weekly_digest.py`. This is observed reuse, not anticipated reuse.

Plausible future shared candidates — explicitly not built yet, to be extracted only if/when a second application actually needs them: multi-model synthesis (`multi_model_research.py` is already provider-agnostic and cheap to move later), PDF/document generation, user preferences. Telegram notification formatting is likely never needed as shared code, since Hermes's native `[[as_document]]` delivery already covers it.

## Consequences

- Every phase of future work must leave the repository fully working — no big-bang migrations.
- New applications are scaffolded by copying `venture-studio/`'s shape, not by depending on a not-yet-proven abstraction layer.
- Extraction into `shared/` happens after the second real caller exists, not before. This ADR is the record of that discipline; future extractions should cite the specific duplication that justified them.
