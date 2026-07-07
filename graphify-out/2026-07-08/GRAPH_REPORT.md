# Graph Report - .  (2026-07-08)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 154 nodes · 198 edges · 21 communities (14 shown, 7 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `27f994d3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Hermes Agent Personal OS
- Idea Persistence Layer
- Idea Validator Skill
- save_work_order.py
- save_discovery.py
- weekly_digest.py
- run_role
- MECE Research Committee
- generate_pdf_fallback.py
- Graphify Knowledge Graph Tool
- write_report.py
- red_team.py
- verify_research_data.py
- generate_pdf.py
- Venture Studio Supabase Schema
- Graphify Knowledge Graph Skill
- PDF Report Generation
- Multi-Model Research Ensemble
- Red Team Review Script
- Research Data Verification Script
- Report Writing Script

## God Nodes (most connected - your core abstractions)
1. `Idea Validator Skill` - 12 edges
2. `main()` - 8 edges
3. `main()` - 8 edges
4. `Hermes Agent Personal OS` - 8 edges
5. `MECE Research Committee` - 8 edges
6. `Graphify Knowledge Graph Tool` - 7 edges
7. `get_client()` - 6 edges
8. `run_role()` - 6 edges
9. `Supabase Persistence Layer` - 6 edges
10. `Venture Studio Application` - 6 edges

## Surprising Connections (you probably didn't know these)
- `ADR 0001: Personal AI OS Philosophy` --rationale_for--> `Shared Supabase Client Factory`  [EXTRACTED]
  docs/adr/0001-personal-ai-os-philosophy.md → shared/db.py
- `Hermes Agent Personal OS` --references--> `Pair Programmer Application`  [INFERRED]
  README.md → pair-programmer/README.md
- `Pair Programmer Skill` --references--> `Hermes Agent Personal OS`  [INFERRED]
  pair-programmer/skills/pair-programmer/SKILL.md → README.md
- `save_idea.py Script` --references--> `Supabase Persistence Layer`  [EXTRACTED]
  venture-studio/skills/idea-validator/SKILL.md → README.md
- `Venture Studio Application` --references--> `Supabase Persistence Layer`  [EXTRACTED]
  venture-studio/.hermes/CONTEXT.md → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared Services across All Applications** — hermes_runtime, supabase_service, telegram_service, agent_reach_service, shared_db_py [EXTRACTED 1.00]
- **Work Order Creation, Planning & Execution Workflow** — builder_os_skills_builder_advisor_skill, save_work_order_py, claude_code_cli, work_order_dispatch_pattern [EXTRACTED 1.00]
- **MECE Research Ensemble Architecture** — demand_role, market_role, competition_role, feasibility_role, economics_role, external_role [EXTRACTED 1.00]
- **Idea Validation Research Pipeline** — venture_studio_skills_idea_validator_skill, multi_model_research_py, red_team_py, write_report_py, save_idea_py, generate_pdf_py [EXTRACTED 1.00]
- **Graphify Knowledge Graph Extraction System** — graphify_tool, ast_extraction, semantic_extraction, graph_query_traversal [EXTRACTED 1.00]

## Communities (21 total, 7 thin omitted)

### Community 0 - "Hermes Agent Personal OS"
Cohesion: 0.16
Nodes (17): ADR 0001: Personal AI OS Philosophy, Agent Reach External Service, Builder OS Application, Builder OS Supabase Schema, Save Work Order Script, Builder Advisor Skill, Claude Code CLI for Work Order Dispatch, Hermes Agent Personal OS (+9 more)

### Community 1 - "Idea Persistence Layer"
Cohesion: 0.17
Nodes (16): get_digest_candidates(), get_idea(), main(), save_idea.py — Supabase persistence for venture-studio  Called by Hermes via exe, Insert a competitor entry., Update an idea's status and optional verdict., Fetch top ideas for weekly digest., Fetch a single idea by ID. (+8 more)

### Community 2 - "Idea Validator Skill"
Cohesion: 0.17
Nodes (16): Agent Reach System, Builder OS Application, Claude Code Platform, Claude Sonnet Model, generate_pdf.py Script, Idea Validation Workflow, PDF Report Generation, red_team.py Script (+8 more)

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
Cohesion: 0.22
Nodes (9): Competition Analysis Role, Demand Analysis Role, Economics and Monetization Role, External Constraints Role, Technical Feasibility Role, Market Analysis Role, MECE Research Committee, multi_model_research.py Script (+1 more)

### Community 8 - "generate_pdf_fallback.py"
Cohesion: 0.33
Nodes (8): main(), Offline PDF fallback using headless Edge HTML→PDF, with a final plain-text fallb, Render the report markdown to HTML; escape-and-<br> only if the     markdown pa, The generator renders its own <h1> title and verdict badge, so drop a     leadi, render_markdown(), render_with_headless_edge(), strip_duplicate_header(), write_html()

### Community 9 - "Graphify Knowledge Graph Tool"
Cohesion: 0.25
Nodes (8): Abstract Syntax Tree Extraction, Graph Query and Traversal, Graphify Knowledge Graph Tool, Incremental Graph Update, Model Context Protocol MCP Server, Post-Commit Hook Mechanism, Semantic Knowledge Extraction, Video and Audio Transcription

### Community 10 - "write_report.py"
Cohesion: 0.47
Nodes (5): extract_verdict(), main(), write_report.py — Final report synthesis by Claude on the local subscription  Th, Remove one whole-document ```-fence if the model ignored instructions., strip_outer_fence()

### Community 11 - "red_team.py"
Cohesion: 0.50
Nodes (4): extract_json(), main(), red_team.py — Sequential adversarial review over the specialist role outputs  Th, Extract the first JSON object from possibly-noisy CLI output.

### Community 12 - "verify_research_data.py"
Cohesion: 0.60
Nodes (4): check_raw_data(), check_synthesis_output(), main(), verify_research_data.py — Mechanical integrity gate for idea-validator's researc

### Community 13 - "generate_pdf.py"
Cohesion: 0.67
Nodes (3): generate_pdf(), main(), generate_pdf.py — Generates a formatted PDF validation report using WeasyPrint

## Knowledge Gaps
- **14 isolated node(s):** `Save Idea Script`, `Multi-Model Research Ensemble`, `Red Team Review Script`, `PDF Report Generation`, `Research Data Verification Script` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_client()` connect `save_discovery.py` to `Idea Persistence Layer`, `save_work_order.py`, `weekly_digest.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `Idea Validator Skill` connect `Idea Validator Skill` to `Hermes Agent Personal OS`, `MECE Research Committee`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `Supabase Persistence Layer` connect `Hermes Agent Personal OS` to `Idea Validator Skill`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Hermes Agent Personal OS` (e.g. with `Pair Programmer Application` and `Pair Programmer Skill`) actually correct?**
  _`Hermes Agent Personal OS` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `save_discovery.py — Supabase persistence for builder-os  Called by Hermes via ex`, `Insert a new discovery, return the created row.`, `Update a discovery's review status.` to the rest of the system?**
  _66 weakly-connected nodes found - possible documentation gaps or missing edges._