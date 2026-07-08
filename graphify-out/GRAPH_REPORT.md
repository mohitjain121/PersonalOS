# Graph Report - hermes_agent  (2026-07-08)

## Corpus Check
- 36 files · ~37,801 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 218 nodes · 270 edges · 22 communities (17 shown, 5 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f90f9354`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Hermes Agent Personal OS
- Idea Persistence Layer
- save_work_order.py
- save_discovery.py
- weekly_digest.py
- run_role
- MECE Research Committee
- generate_pdf_fallback.py
- Graphify Knowledge Graph Tool
- write_report.py
- red_team.py
- generate_pdf.py
- Venture Studio Supabase Schema
- PDF Report Generation
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native AGENTS.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- extraction-spec.md
- Procedure

## God Nodes (most connected - your core abstractions)
1. `What You Must Do When Invoked` - 12 edges
2. `Procedure` - 10 edges
3. `/graphify` - 10 edges
4. `main()` - 8 edges
5. `graphify reference: extra exports and benchmark` - 8 edges
6. `main()` - 8 edges
7. `main()` - 8 edges
8. `Hermes Agent Personal OS` - 8 edges
9. `_normalize()` - 7 edges
10. `run_role()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `ADR 0001: Personal AI OS Philosophy` --rationale_for--> `Shared Supabase Client Factory`  [EXTRACTED]
  docs/adr/0001-personal-ai-os-philosophy.md → shared/db.py
- `Hermes Agent Personal OS` --references--> `Pair Programmer Application`  [INFERRED]
  README.md → pair-programmer/README.md
- `Pair Programmer Skill` --references--> `Hermes Agent Personal OS`  [INFERRED]
  pair-programmer/skills/pair-programmer/SKILL.md → README.md
- `ADR 0001: Personal AI OS Philosophy` --rationale_for--> `Venture Studio Application`  [EXTRACTED]
  docs/adr/0001-personal-ai-os-philosophy.md → venture-studio/README.md
- `Venture Studio Application` --references--> `Agent Reach System`  [EXTRACTED]
  venture-studio/.hermes/CONTEXT.md → ROADMAP.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared Services across All Applications** — hermes_runtime, supabase_service, telegram_service, agent_reach_service, shared_db_py [EXTRACTED 1.00]

## Communities (22 total, 5 thin omitted)

### Community 0 - "Hermes Agent Personal OS"
Cohesion: 0.10
Nodes (27): ADR 0001: Personal AI OS Philosophy, Agent Reach System, Agent Reach External Service, Builder OS Application, Builder OS Application, Builder OS Supabase Schema, Save Work Order Script, Builder Advisor Skill (+19 more)

### Community 1 - "Idea Persistence Layer"
Cohesion: 0.17
Nodes (16): get_digest_candidates(), get_idea(), main(), save_idea.py — Supabase persistence for venture-studio  Called by Hermes via exe, Insert a competitor entry., Update an idea's status and optional verdict., Fetch top ideas for weekly digest., Fetch a single idea by ID. (+8 more)

### Community 3 - "save_work_order.py"
Cohesion: 0.21
Nodes (15): complete_work_order(), create_work_order(), delete_work_order(), get_work_order(), list_work_orders(), main(), _now(), save_work_order.py — Supabase persistence for builder-os Work Orders  Called by (+7 more)

### Community 4 - "save_discovery.py"
Cohesion: 0.21
Nodes (11): list_discoveries(), main(), save_discovery.py — Supabase persistence for builder-os  Called by Hermes via ex, Insert a new discovery, return the created row., Update a discovery's review status., List discoveries, optionally filtered by status, most recent first., save_discovery(), update_status() (+3 more)

### Community 5 - "weekly_digest.py"
Cohesion: 0.27
Nodes (10): format_markdown(), format_telegram(), get_digest_candidates(), get_ideas_this_week(), get_total_idea_count(), main(), weekly_digest.py — Surfaces top unacted validated ideas for the weekly digest  T, Format digest as clean markdown. (+2 more)

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
Cohesion: 0.13
Nodes (25): check_entity_grounding(), check_finding_coverage(), check_quote_grounding(), check_raw_data(), check_report_quotes(), check_synthesis_output(), _extract_quotes_from_json(), _find_quotes() (+17 more)

### Community 11 - "red_team.py"
Cohesion: 0.50
Nodes (4): extract_json(), main(), red_team.py — Sequential adversarial review over the specialist role outputs  Th, Extract the first JSON object from possibly-noisy CLI output.

### Community 13 - "generate_pdf.py"
Cohesion: 0.67
Nodes (3): generate_pdf(), main(), generate_pdf.py — Generates a formatted PDF validation report using WeasyPrint

### Community 16 - "PDF Report Generation"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

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
Cohesion: 0.14
Nodes (14): Procedure, Step 0 — Parse the idea, Step 1 — Persist the raw idea to Supabase, Step 2 — MECE research committee (shared corpus → 6 specialists → red team), Step 2a — Build the shared evidence corpus (once per idea), Step 2b — Run the six specialist roles (sequentially, one at a time), Step 2c — Red team (mandatory, only after ALL roles are gated), Step 2d — Gap closure (EXACTLY one iteration, then stop) (+6 more)

## Knowledge Gaps
- **64 isolated node(s):** `When to Use`, `Step 0 — Parse the idea`, `Step 1 — Persist the raw idea to Supabase`, `Step 2a — Build the shared evidence corpus (once per idea)`, `Step 2b — Run the six specialist roles (sequentially, one at a time)` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_client()` connect `save_discovery.py` to `Idea Persistence Layer`, `save_work_order.py`, `weekly_digest.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `Idea Validator` connect `Hermes Agent Personal OS` to `Procedure`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `Procedure` connect `Procedure` to `Hermes Agent Personal OS`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **What connects `When to Use`, `Step 0 — Parse the idea`, `Step 1 — Persist the raw idea to Supabase` to the rest of the system?**
  _109 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Hermes Agent Personal OS` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._
- **Should `MECE Research Committee` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
- **Should `write_report.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1339031339031339 - nodes in this community are weakly interconnected._