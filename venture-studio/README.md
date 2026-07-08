# venture-studio

Hermes-powered personal venture studio. Drop an idea on Telegram — a MECE committee of specialist analysts and an adversarial Claude red team research it, then you get a structured verdict and a downloadable PDF report.

## Architecture

One shared evidence corpus → six specialist analysts with mutually-exclusive mandates (`demand`, `market`, `competition`, `feasibility`, `economics`, `external`; one free OpenRouter model each with a fallback chain; `demand`/`economics` each get a second opinion from a different model) → a sequential adversarial red team (Claude Sonnet via the locally-authenticated `claude` CLI, on the subscription — not an API key) → up to one bounded gap-closure iteration if the red team flags absent/single-source evidence → the final report written by Claude Sonnet, not the orchestrator model → PDF → Supabase persistence → Telegram delivery → the idea joins a recency watchlist so the verdict stays falsifiable over time.

Every stage is gated by mechanical, non-LLM integrity checks (`scripts/verify_research_data.py`): a byte-floor + structure check on the raw corpus, an entity-grounding check (corpus sections that never mention the idea are flagged as noise), a quote-grounding check (every "verbatim" quote in a role output or the final report must trace back to the corpus, or the gate fails), a finding-coverage check (the report can't drop or soften a fatal/high red-team finding), and the red-team's kill-likelihood score mechanically caps the verdict (≥70 blocks STRONG). None of this depends on a model "remembering" to be honest — the pipeline is built so a lazy or hallucinating run gets rejected before it reaches you.

**Evidence sources**, gathered per idea:
- Dimension-seeded web search + full-page extraction (not snippets)
- Real Reddit threads (full post + comments, via Agent Reach's OpenCLI browser bridge) — not web-indexed snippets
- An engagement-ranked, 30-day recency pass across Reddit/X/YouTube-with-transcripts/HN/GitHub/Polymarket/jobs, and TikTok/Instagram for consumer ideas (via `last30days-skill`)
- Competitor dossiers for the top 2–3 named incumbents (sentiment, hiring signals, GitHub activity, funding/pricing pages)
- An India-focus supplement (this is the default geography) — woven into every dimension of the report, not a separate section, with thin evidence stated honestly rather than extrapolated from global numbers

See `skills/idea-validator/SKILL.md` for the full step-by-step procedure and `skills/idea-validator/references/debugging-and-verification.md` for known failure modes and their fixes.

## Stack

- **Hermes** — agent orchestrator, Telegram gateway, scheduler. The orchestrator's own model is deliberately weak/free (it only runs scripts and moves files) — every quality-critical judgment (red team, report synthesis) runs on the `claude` CLI against Mohit's subscription instead.
- **OpenRouter** — free-tier models for the six specialist roles (`VENTURE_STUDIO_OPENROUTER_KEY`, not `OPENROUTER_API_KEY` — see `scripts/multi_model_research.py`'s docstring for why that distinction matters on this machine).
- **Agent Reach + last30days-skill** — real social/recency evidence (see the root `README.md`'s Shared services section for how these are installed).
- **Supabase** — single source of truth (`ideas`, `research_runs`, `evidence`, `competitors`, `experiments`, `idea_relations`, `market_signals`, `idea_ratings`, `agent_contributions`, `synthesis_reports`, plus the `active_ideas`/`digest_candidates` views).
- **Edge headless PDF generation** (`scripts/generate_pdf_fallback.py`) — WeasyPrint (`templates/generate_pdf.py`) is confirmed broken on this machine (missing native GTK/Pango libraries) and is not the working path; do not try it first.

## Setup

### 1. Supabase
1. Create a project at supabase.com.
2. SQL Editor → paste `supabase/schema.sql` → Run.
3. Settings → API → copy Project URL + service_role key.

### 2. Hermes `.env`
Add (note the app-specific key name — see the docstring in `multi_model_research.py`):
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_service_role_key
VENTURE_STUDIO_OPENROUTER_KEY=your_openrouter_key
```

### 3. Register the skill with Hermes
Add `venture-studio/skills` to `skills.external_dirs` in Hermes's `config.yaml`.

### 4. Telegram forum topic
Create a "Venture Studio" topic in the community supergroup, and register it in `telegram.extra.group_topics` with `skill: idea-validator`.

### 5. Evidence sources
Set up Agent Reach and last30days-skill per the root `README.md` — the idea-validator SKILL.md assumes both are available and degrades honestly (with a disclosed caveat in the report) if either isn't.

## Usage

**Drop an idea on Telegram:**
```
Idea: An AI-powered GST reconciliation tool for Indian CAs that integrates with Tally
```

Hermes will acknowledge immediately, persist the raw idea to Supabase before research starts (so it's never lost), build the evidence corpus, run the full committee + red team, synthesize the report, generate the PDF, persist everything, and send you a TL;DR + PDF on Telegram — then add the idea to a recency watchlist so a future shift in the evidence (a competitor stumbling, a regulation changing) can be flagged against the original verdict.

## Project Structure

```
venture-studio/
├── supabase/
│   └── schema.sql                        # ideas, research_runs, evidence, competitors, experiments,
│                                          # idea_relations, market_signals, idea_ratings,
│                                          # agent_contributions, synthesis_reports + views
├── skills/idea-validator/
│   ├── SKILL.md                          # the full procedure — read this first
│   ├── references/
│   │   └── debugging-and-verification.md  # known failure modes and fixes, self-documented by past runs
│   ├── templates/
│   │   └── generate_pdf.py               # WeasyPrint path — confirmed broken on this machine, not the working path
│   └── scripts/
│       ├── save_idea.py                  # Supabase persistence (save-idea, save-run, save-synthesis, save-competitor, update-status)
│       ├── multi_model_research.py       # the six MECE specialist role prompts + fallback chains
│       ├── red_team.py                   # adversarial review via claude -p (subscription, not API)
│       ├── write_report.py               # final report synthesis via claude -p, with mechanical rail enforcement
│       ├── verify_research_data.py       # all integrity gates: raw-data, synthesis, entity/quote grounding, finding coverage
│       ├── generate_pdf_fallback.py      # the actual working PDF generator (Edge headless)
│       └── trim_red_team_json.py         # repair tool for a red_team.json with a trailing duplicate JSON blob
└── scripts/
    └── weekly_digest.py                  # digest of unacted validated ideas
```

(`skills/idea-validator/tmp/` — per-run corpus/role-output working files — is gitignored; `reports/` output lives under Hermes's own directory, not this repo.)

## PDF Reports

Reports are saved to `~/.hermes/venture-studio/reports/` and auto-sent as Telegram file attachments via Hermes's `[[as_document]]` directive. Filename format: `YYYYMMDD-{idea-title}-{idea-id[:8]}.pdf`.
