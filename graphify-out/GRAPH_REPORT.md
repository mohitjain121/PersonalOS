# Graph Report - hermes_agent  (2026-07-08)

## Corpus Check
- 38 files · ~41,337 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 270 nodes · 308 edges · 31 communities (23 shown, 8 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9dc227a7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Hermes Agent Personal OS
- Idea Persistence Layer
- check_provider_auth.py
- save_work_order.py
- save_discovery.py
- weekly_digest.py
- run_role
- MECE Research Committee
- generate_pdf_fallback.py
- Graphify Knowledge Graph Tool
- write_report.py
- red_team.py
- builder-os
- generate_pdf.py
- Venture Studio Supabase Schema
- Claude Code CLI for Work Order Dispatch
- PDF Report Generation
- Idea Validator — Debugging & Verification Notes
- write_report.py
- trim_red_team_json.py
- hermes_agent
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native AGENTS.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- extraction-spec.md
- Procedure
- Roadmap
- Pair Programmer Application

## God Nodes (most connected - your core abstractions)
1. `What You Must Do When Invoked` - 12 edges
2. `Idea Validator — Debugging & Verification Notes` - 11 edges
3. `Procedure` - 10 edges
4. `/graphify` - 10 edges
5. `main()` - 8 edges
6. `graphify reference: extra exports and benchmark` - 8 edges
7. `main()` - 8 edges
8. `main()` - 8 edges
9. `hermes_agent` - 7 edges
10. `venture-studio` - 7 edges

## Surprising Connections (you probably didn't know these)
- `ADR 0001: Personal AI OS Philosophy` --rationale_for--> `Shared Supabase Client Factory`  [EXTRACTED]
  docs/adr/0001-personal-ai-os-philosophy.md → shared/db.py
- `Save Work Order Script` --references--> `Shared Supabase Client Factory`  [EXTRACTED]
  builder-os/skills/builder-advisor/scripts/save_work_order.py → shared/db.py
- `Builder Advisor Skill` --references--> `Save Work Order Script`  [EXTRACTED]
  builder-os/skills/builder-advisor/SKILL.md → builder-os/skills/builder-advisor/scripts/save_work_order.py
- `Venture Studio Supabase Schema` --shares_data_with--> `Save Idea Script`  [EXTRACTED]
  venture-studio/supabase/schema.sql → venture-studio/skills/idea-validator/scripts/save_idea.py
- `Builder OS Supabase Schema` --shares_data_with--> `Save Work Order Script`  [EXTRACTED]
  builder-os/supabase/schema.sql → builder-os/skills/builder-advisor/scripts/save_work_order.py

## Import Cycles
- None detected.

## Communities (31 total, 8 thin omitted)

### Community 0 - "Hermes Agent Personal OS"
Cohesion: 0.33
Nodes (6): ADR 0001: Personal AI OS Philosophy, Builder OS Supabase Schema, Save Work Order Script, Builder Advisor Skill, Shared Supabase Client Factory, Work Order Dispatch & Verification Pattern

### Community 1 - "Idea Persistence Layer"
Cohesion: 0.17
Nodes (16): get_digest_candidates(), get_idea(), main(), save_idea.py — Supabase persistence for venture-studio  Called by Hermes via exe, Insert a competitor entry., Update an idea's status and optional verdict., Fetch top ideas for weekly digest., Fetch a single idea by ID. (+8 more)

### Community 2 - "check_provider_auth.py"
Cohesion: 0.27
Nodes (11): _auth_status(), _configured_providers(), _load_state(), main(), check_provider_auth.py — Standalone watchdog for Hermes's model-provider auth  N, Read only the bytes appended since the last run (cheap, no full-file     rescan), Returns {"provider": ..., "logged_in": bool, "detail": str}., _read_env_var() (+3 more)

### Community 3 - "save_work_order.py"
Cohesion: 0.21
Nodes (15): complete_work_order(), create_work_order(), delete_work_order(), get_work_order(), list_work_orders(), main(), _now(), save_work_order.py — Supabase persistence for builder-os Work Orders  Called by (+7 more)

### Community 4 - "save_discovery.py"
Cohesion: 0.12
Nodes (21): list_discoveries(), main(), save_discovery.py — Supabase persistence for builder-os  Called by Hermes via ex, Insert a new discovery, return the created row., Update a discovery's review status., List discoveries, optionally filtered by status, most recent first., save_discovery(), update_status() (+13 more)

### Community 5 - "weekly_digest.py"
Cohesion: 0.15
Nodes (12): 1. Supabase, 2. Hermes `.env`, 3. Register the skill with Hermes, 4. Telegram forum topic, 5. Evidence sources, Architecture, PDF Reports, Project Structure (+4 more)

### Community 6 - "run_role"
Cohesion: 0.31
Nodes (9): Any, call_openrouter(), _is_usable(), main(), multi_model_research.py — MECE specialist ensemble for decision research  Archit, Call a single model via OpenRouter, with 429 retry and truncation detection., A response is usable only if the model answered AND its JSON parsed., Run one specialist role: try each model in order until one returns     parseable (+1 more)

### Community 7 - "MECE Research Committee"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native AGENTS.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 8 - "generate_pdf_fallback.py"
Cohesion: 0.33
Nodes (8): main(), Offline PDF fallback using headless Edge HTML→PDF, with a final plain-text fallb, Render the report markdown to HTML; escape-and-<br> only if the     markdown pa, The generator renders its own <h1> title and verdict badge, so drop a     leadi, render_markdown(), render_with_headless_edge(), strip_duplicate_header(), write_html()

### Community 9 - "Graphify Knowledge Graph Tool"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 10 - "write_report.py"
Cohesion: 0.18
Nodes (20): check_entity_grounding(), check_finding_coverage(), check_quote_grounding(), check_raw_data(), check_report_quotes(), check_synthesis_output(), _extract_quotes_from_json(), _find_quotes() (+12 more)

### Community 11 - "red_team.py"
Cohesion: 0.50
Nodes (4): extract_json(), main(), red_team.py — Sequential adversarial review over the specialist role outputs  Th, Extract the first JSON object from possibly-noisy CLI output.

### Community 12 - "builder-os"
Cohesion: 0.33
Nodes (5): builder-os, Provider auth watchdog, Setup, Structure, Usage

### Community 13 - "generate_pdf.py"
Cohesion: 0.67
Nodes (3): generate_pdf(), main(), generate_pdf.py — Generates a formatted PDF validation report using WeasyPrint

### Community 16 - "PDF Report Generation"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 17 - "Idea Validator — Debugging & Verification Notes"
Cohesion: 0.12
Nodes (15): Acceptable partial-track fallback, Empty-consolidation gate, Idea Validator — Debugging & Verification Notes, MECE role architecture (2026-07-04 redesign), Model availability, Persistence quirks, Prompt assembly, Raw-data file paths (+7 more)

### Community 18 - "write_report.py"
Cohesion: 0.47
Nodes (5): extract_verdict(), main(), write_report.py — Final report synthesis by Claude on the local subscription  Th, Remove one whole-document ```-fence if the model ignored instructions., strip_outer_fence()

### Community 20 - "hermes_agent"
Cohesion: 0.25
Nodes (7): Architecture, hermes_agent, License, Planned, Setup, Shared services & tooling, What's here today

### Community 21 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 22 - "graphify reference: commit hook and native AGENTS.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native AGENTS.md integration, graphify reference: commit hook and native AGENTS.md integration

### Community 23 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 28 - "Procedure"
Cohesion: 0.10
Nodes (20): Venture Studio Application, Idea Validator, Pitfalls, Procedure, Step 0 — Parse the idea, Step 1 — Persist the raw idea to Supabase, Step 2 — MECE research committee (shared corpus → 6 specialists → red team), Step 2a — Build the shared evidence corpus (once per idea) (+12 more)

### Community 29 - "Roadmap"
Cohesion: 0.33
Nodes (5): Done, In progress, Next, Open / blocked, Roadmap

## Knowledge Gaps
- **101 isolated node(s):** `Architecture`, `What's here today`, `Shared services & tooling`, `Setup`, `Planned` (+96 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_client()` connect `save_discovery.py` to `Idea Persistence Layer`, `save_work_order.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **What connects `Architecture`, `What's here today`, `Shared services & tooling` to the rest of the system?**
  _150 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `save_discovery.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11956521739130435 - nodes in this community are weakly interconnected._
- **Should `MECE Research Committee` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
- **Should `Idea Validator — Debugging & Verification Notes` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._
- **Should `Procedure` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._