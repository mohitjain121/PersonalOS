---
name: idea-validator
description: Autonomously validates a startup idea — builds a shared web-evidence corpus, runs a MECE committee of six specialist analysts (demand, market, competition, feasibility, economics, external) plus a Claude red-team review, then synthesizes a structured report, persists to Supabase, generates a PDF, and sends a TL;DR verdict via Telegram.
version: 1.0.0
metadata:
  hermes:
    tags: [startup, research, validation, venture-studio]
    category: venture-studio
    requires_toolsets: [web]
    required_environment_variables:
      - name: SUPABASE_URL
        prompt: "Supabase project URL (from Supabase dashboard → Settings → API)"
        help: https://supabase.com/dashboard/project/_/settings/api
      - name: SUPABASE_KEY
        prompt: "Supabase service role key (Settings → API → service_role)"
      - name: VENTURE_STUDIO_OPENROUTER_KEY
        prompt: "OpenRouter API key for multi-model research ensemble (must use this name, not OPENROUTER_API_KEY — that name is a Hermes-managed provider credential and is permanently stripped from terminal/execute_code subprocesses; see multi_model_research.py's module docstring)"
        help: https://openrouter.ai/keys
---

# Idea Validator

## When to Use
Load this skill when:
- A message from Telegram describes a startup idea, product concept, or business opportunity
- The user says "validate this", "what do you think about", "new idea:", "idea dump:"
- Any message resembling a problem statement + proposed solution

Trigger phrase examples:
- "Idea: an AI-powered invoice reconciliation tool for Indian SMEs"
- "What if there was a platform that..."
- "I've been thinking about building X for Y users"

Do NOT trigger for: questions about existing ideas already validated, status checks, or the weekly digest.

---

## Procedure

**Non-negotiable execution rules — read before starting:**
- **Never delegate, dispatch, or background this pipeline via `delegate_task` or any subagent/fan-out mechanism.** This happened for real (2026-07-08): given a detailed waste-management idea, the orchestrator called `delegate_task` with a hand-written "author a 50-page report" goal instead of running Steps 0-8 itself. The delegated subagent had none of this file's rules loaded, made zero web searches, invented an arbitrary output path (`C:\Users\mjain\...` instead of the real PDF convention in Step 4), and after its own generation attempts failed (WeasyPrint broken exactly as documented below, no pandoc/LibreOffice/wkhtmltopdf installed) it deleted its own output files and then fabricated a detailed "Task Complete" summary describing a report that never existed — which the parent agent relayed to Mohit as fact, plus its own invented detail on top ("~6,000 pages"). Separately confirmed: the idea was never even persisted to Supabase (Step 1 never ran), proving no part of this SKILL.md executed. **You, the calling agent, must run every step and every script invocation below yourself, in this session** — delegation throws away every gate this file defines (corpus integrity, quote/entity grounding, the red team, the verdict rails) because a delegated subagent starts from a blank slate with none of them.
- Every step below is mandatory and must actually run as a tool/script call. Reading a script's source to "understand" it is not the same as executing it — every `python .../scripts/*.py` command shown below must actually be invoked.
- Step 2 requires literally executing `multi_model_research.py` for each of the six roles, plus `red_team.py` after them. Summarizing raw web search results yourself instead of running these scripts is not a valid substitute, even though it's faster — it silently drops the specialist ensemble and the adversarial review that make the report reliable, and it will visibly regress report quality.
- Never write a new script to replace a provided one (e.g. do not invent your own PDF generator, your own Supabase writer, or your own report synthesizer). If a provided script fails, use its documented fallback (Step 4). Do not improvise a replacement pipeline.
- Persistence steps (1, 5, 6) are not optional under time pressure — the idea must be saved before research starts (Step 1) and the run/synthesis/status updates must be saved even if later steps have problems. Step 5 (save-run) must run before Step 6 (save-synthesis) — see Step 5's note on why.
- If you are genuinely blocked (a script errors with no documented fallback), say so explicitly to the user rather than silently substituting a lower-quality approach.
- **Never fabricate placeholder or guessed content in place of real data, at any step, for any reason.** This has actually happened (2026-07-03): real research (16 real web searches, ~21K chars) was lost to a path bug, and rather than stopping, one-line made-up stand-ins like `"AI character entertainment market research raw data placeholder."` were written in its place and fed to the model ensemble — and separately, when the model ensemble failed entirely (missing API key), a report was still generated and shipped to Mohit as if it were properly researched. Both were violations of this rule. If real data is missing, lost, or a script fails with no documented fallback: **stop that track, tell Mohit specifically what's missing and why, and do not proceed to write a report section, a synthesis, or a verdict based on fabricated or absent input.** A report that's honest about a gap is far better than one that hides it behind invented content.

### Step 0 — Parse the idea

Extract and structure from the raw input:
- **Core problem**: What pain is being solved?
- **Proposed solution**: What does the product do?
- **Target user**: Who specifically suffers from this problem?
- **Domain**: Classify as one of: fintech, saas, marketplace, ai, health, edtech, logistics, other
- **Geography**: Default to India unless stated otherwise

Tell the user you're starting research: *"Got it. Researching [extracted title] now — will ping you when the report's ready."*

---

### Step 1 — Persist the raw idea to Supabase

Run immediately after parsing — before research starts, so the idea is never lost even if research fails.

```bash
python ${HERMES_SKILL_DIR}/scripts/save_idea.py save-idea \
  --text "<RAW_IDEA_TEXT>" \
  --title "<EXTRACTED_TITLE>" \
  --domain "<DOMAIN>"
```

Capture the returned `idea_id` — you'll need it for all subsequent persistence calls.

---

### Step 2 — MECE research committee (shared corpus → 6 specialists → red team)

**Architecture:** One shared evidence corpus → six specialist analysts with mutually-exclusive mandates (one free model each, automatic fallback through the role's model list) → sequential red-team review by Claude Sonnet (via the locally-authenticated Claude Code CLI, on the subscription) → synthesis by you in Step 3.

The six roles and the single question each owns (mandates and boundaries are baked into the script's prompts):

| Role | Question |
|---|---|
| `demand` | Is the pain real, frequent, urgent — and whose? (pain, ICP, JTBD, workarounds, user sentiment on alternatives, WTP signals, solution–demand fit) |
| `market` | Is the space attractive? (TAM [Directional] + source spread, growth, industry structure, why-now **tailwinds only** — timing risks belong to `external`, demand drivers) |
| `competition` | Can a new entrant win? (competitors-as-businesses, funding flows, saturation, moats, whitespace, incumbent response) |
| `feasibility` | Can it be built and operated — with what, by whom, how fast? (capabilities, data, infra, effort + skills, scalability, cost-to-serve drivers) |
| `economics` | Is there a credible, affordable route to revenue? (pricing thesis, CAC, LTV/retention, margins, motion, channels, partnerships, frictions, capital intensity) |
| `external` | What outside forces can kill or unlock it? (regulation, platform dependency, IP/licensing, ethical backlash, **all timing/macro headwinds and shocks** — the risk half of any double-edged force) |

Founder fit and the verdict are yours in Step 3 — you have Mohit-context the ensemble doesn't. The red team is a **stage, not another researcher**: it must run AFTER the roles, on their outputs — never in parallel on raw data.

**Never use a bare path like `/tmp/...` to hand data between steps.** On this machine, that literal string resolves to a different real directory depending on which tool touches it — `execute_code`'s own sandbox, `terminal`'s bash-to-Windows argument translation, and the `write_file` tool all disagree with each other. This has actually caused real, exhaustive research data (16 real web searches, ~21K chars) to be silently lost — written by one tool to a location no other tool could ever find again. Do not write raw search results using code-internal file I/O (`pathlib`/`open()`) inside `execute_code` — that sandbox is not guaranteed to share a filesystem with anything that runs later.

#### Step 2a — Build the shared evidence corpus (once per idea)

Evidence is intentionally shared across all six roles — mutual exclusivity lives in their mandates, not their reading lists. Do not build per-role data files.

1. **Gather searches seeded per dimension** using the Hermes web toolset (adapt queries to the idea):
   - *demand*: `"<problem> reddit"`, `"<problem> site:reddit.com OR site:news.ycombinator.com"`, `"<problem> frustrating OR broken OR expensive OR painful"`, X/Twitter search if available
   - *market*: `"<problem domain> market size India 2025 2026"`, `"<solution type> industry growth trends"`, `"<domain> adoption drivers"`
   - *competition*: `"<solution type> startups India funding"`, `"alternatives to <existing player if known>"`, Product Hunt/Tracxn/YC batches
   - *feasibility*: `"<solution type> tech stack build"`, `"<core AI capability> API pricing rate limits"`, `"<solution type> engineering challenges scale"`
   - *economics*: `"<solution type> pricing"`, `"CAC benchmarks <domain>"`, `"<solution type> unit economics margins"`
   - *external*: `"<solution type> RBI regulation India"` / `"SEBI compliance"` / `"DPDP data privacy India"` (only if domain is fintech, health, edtech, lending, payments, insurance, or data-heavy), `"<solution type> app store platform dependency"`
2. **Pull real Reddit threads via Agent Reach — do not settle for web-indexed Reddit snippets.** A generic web search with `reddit` as a keyword only returns pages Google happened to index; it never surfaces the full post or its comments, which is where the actual user-sentiment evidence lives. Run `agent-reach doctor --json` once per idea run and check `reddit.status`:
   - If `ok` (`active_backend: OpenCLI`, requires Mohit's Brave browser open with the OpenCLI extension connected and logged into Reddit — see `shared-skills/agent-reach/references/social.md`):
     ```bash
     opencli reddit search "<demand query>" -f yaml
     opencli reddit read <POST_ID> -f yaml   # top 3-5 threads by relevance/score — full post + comments
     ```
     Do this for the *demand* queries above at minimum; also use it for *competition* (`"<competitor> reddit reviews"`, `"<competitor> vs <alternative>"`) and *external* (`"<domain> banned OR lawsuit OR regulation reddit"`) when a competitor or regulatory angle is already named. Append each thread's post text + comments under `=== PAGE: <reddit thread URL> ===`, same as extracted web pages.
   - If not `ok`, fall back to the web-search `site:reddit.com` queries above and note "Reddit: web-indexed snippets only (Agent Reach unavailable)" in the report's Research Process Note — do not silently degrade without saying so.
3. **Run a last30days engagement-ranked recency pass** — this is a different evidence class from searches and thread pulls: it quantifies *current* community consensus (upvotes, views, comment volume, cross-platform clusters) over the trailing 30 days, which is exactly what static web pages and old threads can't show. The engine lives at `C:/Users/mjain/OneDrive/Documents/hermes_agent/last30days-skill/skills/last30days/scripts/last30days.py` and **requires Python 3.12+ — invoke with `python3.14`, NOT bare `python`** (the Hermes venv python is 3.11 and the engine will refuse to run):
   ```bash
   python3.14 <engine path> "<idea topic phrase>" --days 30 --emit=md --output "<corpus dir>/last30days_<slug>.md" \
     --subreddits "<comma-separated subreddits already discovered in steps 1-2>"
   ```
   You are the planner: resolve entities BEFORE calling the engine (pass `--subreddits` from communities found in the searches; add `--polymarket-keywords` when the domain has regulatory/event risk, `--github-repo` when a competitor is open-source; for consumer/B2C ideas add `--tiktok-hashtags`/`--ig-creators` — TikTok and Instagram are live via ScrapeCreators but credit-metered, so keep the default depth and skip them for B2B/infra ideas where consumer social signal is noise). A bare keyword call without resolution flags returns noisy matches — the engine will warn you. Append the emitted markdown into the corpus under a `=== PAGE: last30days:<topic> ===` header. Treat its "Freshness" note as evidence: "recent evidence is thin" is itself a demand-side data point. If the engine is missing or errors, skip and note "no recency pass" in the Research Process Note — do not block the run on it.
4. **Extract full page content for the top 5–8 substantive URLs per dimension group — search snippets alone are not research.** A snippet is a 1–2 line SEO description; a report synthesized from snippets can never be better than a Google results page (this was the quality ceiling behind the 2026-07-03 mediocre report). Append each page's content under a `=== PAGE: <url> ===` header after the search-results sections. Prefer primary-ish sources (company statements, app-analytics firms like Business of Apps/Sensor Tower, actual forum threads, regulator pages) over SEO report-mill pages. If a page fails to extract, pick the next URL down.
5. **Build competitor dossiers for the top 2–3 named competitors.** Once the searches and social pulls have surfaced who the real competitors are, give each a targeted evidence section — the generic corpus describes the *category*; dossiers describe the *incumbents you'd actually fight*. Per competitor, gather what applies:
   - **User sentiment**: `opencli reddit search "<competitor> review OR sucks OR alternative"` → `opencli reddit read` the top 1–2 threads (real complaints about incumbents are whitespace evidence)
   - **Scaling signal**: include the competitor's name in the last30days call's topic or run `--hiring-signals` — who is hiring is who is scaling
   - **If open-source**: `gh repo view <org/repo>` for stars/activity/release cadence
   - **Business facts**: extract 1–2 pages on funding/pricing (Crunchbase-reported news pages, their own pricing page)
   Append each under `=== COMPETITOR DOSSIER: <name> ===`. These sections feed the `competition` role's threat assessment and the red team's evidence-quality attacks; without them, competitor claims rest on whatever one blog said (the SpicyChat "100M users from a single app-review blog" failure, 2026-07-04).
6. **India focus supplement (mandatory when geography includes India — the default).** The pipeline runs globally as-is; this adds an India lens at the end of corpus building, NOT a separate research channel. Run 3–5 India-seeded searches (`"<idea/domain> India market"`, `"<solution type> India startups funding"`, `"<domain> India regulation DPDP RBI"` as applicable, `"<competitor> India"`), prefer Indian startup/business media for extraction (Inc42, YourStory, Entrackr, Economic Times tech), and check Indian subreddits (r/india, r/StartupIndia, r/IndiaInvestments) via the same agent-reach flow as item 2. Append under `=== INDIA FOCUS ===` headers. If India evidence is genuinely thin, that thinness is itself a finding — do not pad; the report will state it honestly.
7. **Persist everything as ONE corpus file using the `write_file` tool itself** (not a script running inside `execute_code`) — this is the one mechanism in this toolchain engineered to resolve the same real path regardless of which tool reads it back. **Capture the exact `resolved_path` string `write_file` returns** — never re-type or guess a path like `/tmp/corpus.txt` yourself.
8. **Run the integrity gates on the corpus (both):**
   ```bash
   python ${HERMES_SKILL_DIR}/scripts/verify_research_data.py check-raw-data --file "<CORPUS_RESOLVED_PATH>" --min-bytes 25000
   python ${HERMES_SKILL_DIR}/scripts/verify_research_data.py check-entity-grounding --file "<CORPUS_RESOLVED_PATH>" --terms "<COMMA_SEPARATED_ENTITY_TERMS>"
   ```
   For `--terms`, pass the idea's proper nouns and problem keywords from Step 0 (e.g. `"AI companion,character.ai,interactive drama"`). The entity gate fails when >40% of corpus bytes never mention the idea (off-topic keyword noise); on a `warning` about specific dead sections, delete those sections from the corpus and re-run both gates — dead sections dilute every role's reading budget.
   This exits non-zero if the file is missing, too small, or doesn't look like a real search dump (this is exactly how the fabricated placeholders from the 2026-07-03 incident would have been caught). The floor also catches a corpus that skipped page extraction. Only if extraction is broken across the board may you fall back to snippets-only — then run the gate with the default `--min-bytes` instead and note "snippet-only research" in a `Research Process Note` section of the report. **If the gate fails, do not proceed and do not fabricate a fix** — re-gather, or stop and say so per the fabrication rule above.

#### Step 2b — Run the six specialist roles (sequentially, one at a time)

For each role in `demand`, `market`, `competition`, `feasibility`, `economics`, `external`:
```bash
python ${HERMES_SKILL_DIR}/scripts/multi_model_research.py --role <role> --raw-data-file "<CORPUS_RESOLVED_PATH>" > "<role>.json"
```
(Write each stdout to a file in the same directory as the corpus so Step 2c can read them back. **Redirect stdout only — never use `2>&1`**: the script's fallback-progress messages go to stderr, and merging them into the file corrupts the JSON envelope and fails the gate with "Output is not valid JSON".) Then gate each — both checks:
```bash
python ${HERMES_SKILL_DIR}/scripts/verify_research_data.py check-synthesis-output --file "<role>.json"
python ${HERMES_SKILL_DIR}/scripts/verify_research_data.py check-quote-grounding --file "<role>.json" --corpus "<CORPUS_RESOLVED_PATH>"
```
The quote gate fails if any "verbatim" quote in the role output cannot be traced to the corpus — that quote was invented, and it must not reach the red team or the report. On failure: re-run that role once; if it fails again, use the role's output only after stripping the ungrounded quotes, and note it in the report's Research Process Note.

- The script tries the role's model list in order until one returns parseable JSON (`--models` can override the list). Run roles **one at a time** — parallel invocations burst the free-tier rate limits.
- **Second opinions for the two verdict-driving roles (mandatory):** after `demand` and `economics` are gated, run each a second time with a different model, so single-model hallucination in those dimensions can't pass unchallenged. Read `models_used` from the first output's envelope, then rerun with `--models` set to the role's chain **minus that model** (e.g. if demand's first run answered via `google/gemma-4-26b-a4b-it:free`, rerun with `--models "meta-llama/llama-3.3-70b-instruct:free,qwen/qwen-2.5-72b-instruct:free,nousresearch/hermes-3-llama-3.1-405b:free"`). Write to `demand_2.json` / `economics_2.json` and gate both exactly like the primaries (both checks). If the second opinion fails through its whole chain (rate caps), proceed without it and note "no second opinion for <role>" in the report's Open Questions — the primary is still gated evidence; do not block the run.
  **If dispatched via a background process, WAIT for it to actually finish (poll or block) before moving to Step 2c — do not let it run past Step 2c into the background.** A real incident (2026-07-08): second-opinion calls were still retrying through 429s in the background when Step 7 delivered the final report; their late completion notifications then caused the agent to re-run the entire pipeline a second time (duplicate Supabase rows, a duplicate PDF sent to Telegram 49 minutes later). Second opinions must resolve — success, or a confirmed failure through the whole chain — before Step 2c starts.
- **A role call can take several minutes worst-case** (each 429'd fallback model adds retry backoff). Invoke the terminal with an extended timeout (600s) for these calls rather than the 180s default — a timeout kill mid-chain wastes the models that already answered.
- A role that fails through all its fallbacks is a **missing dimension of the decision**, not a cosmetic gap. Hard stop for that role: tell Mohit which dimension is missing and why, per the fabrication rule. Do not write that report section from nothing.

#### Step 2c — Red team (mandatory, only after ALL roles are gated)

```bash
python ${HERMES_SKILL_DIR}/scripts/red_team.py --idea "<TITLE>: <ONE_LINE_DESCRIPTION>" \
  --inputs "<demand.json>" "<demand_2.json>" "<market.json>" "<competition.json>" "<feasibility.json>" "<economics.json>" "<economics_2.json>" "<external.json>" \
  --corpus "<CORPUS_RESOLVED_PATH>" > "red_team.json"
python ${HERMES_SKILL_DIR}/scripts/verify_research_data.py check-synthesis-output --file "red_team.json"
```

Include the `demand_2.json`/`economics_2.json` second opinions when they exist — where the two runs of the same role disagree (different pain severity, different margin math), that disagreement is exactly what the red team should exploit; where they agree independently, that claim is stronger. Omit them only if the second-opinion runs were skipped.

- **Runs Claude Sonnet through the locally-authenticated `claude` CLI** (Mohit's Claude subscription — no API key involved). If `claude` is missing or unauthenticated this is a **hard stop**: tell Mohit. Do not substitute a weaker model as red team — adversarial review by a weak model is worse than none because it launders bad theses as "reviewed".
- **If `red_team.json` fails `check-synthesis-output` with `Extra data`**, the file likely contains a duplicate JSON tail from a `claude -p` retry/reasoning trace. Repair it before re-running synthesis:
  ```bash
  python C:\Users\mjain\OneDrive\Documents\hermes_agent\venture-studio\skills\idea-validator\scripts\trim_red_team_json.py "C:\...\red_team.json"
  ```
  This overwrites the file with the first complete JSON object only. Re-run the gate; do not hand-edit.
- Use the red team's output in Step 3: its `falsification_test` entries are the source for the **Lowest-Cost Validation Experiment** section; its `unowned_considerations` go into **Open Questions**; its `kill_likelihood` constrains the verdict (see Step 3 synthesis rules).

#### Step 2d — Gap closure (EXACTLY one iteration, then stop)

Real research answers its own objections. After the red team is gated, check its `evidence_quality_attacks`: does any attack say evidence for a claim is **absent or single-source** (not merely weak)? If none do, skip this step entirely.

If yes, close the gaps — once:
1. For each such attack (cap at the 4 most severe), run 1–2 **targeted** searches/pulls for exactly the missing evidence (e.g. attack says "SpicyChat's 100M users rests on one app-review blog" → search for a second independent source for that number; attack says "no India pricing evidence" → targeted India pricing search). Use whichever tool fits: web search + extraction, agent-reach thread pull, last30days with tightened flags.
2. Append findings — including honest negative results ("no independent confirmation found") — under `=== GAP CLOSURE: <attack summary> ===` headers, re-persist the corpus, re-run BOTH corpus gates.
3. Re-run **only the roles whose dimension was attacked** (same commands, same two gates per role). Unattacked roles' outputs stand.
4. Re-run the red team once on the updated inputs, re-gate it. The second red-team output is final.

**Hard bound: this loop runs at most once per idea, ever.** If the second red team still attacks evidence quality, those attacks go into the report as-is (Open Questions / Research Process Note) — that is an honest finding about the evidence landscape, not a defect to iterate away. Never loop back from Step 2d to Step 2d.

---

### Step 3 — Synthesize the report

**Do NOT write the report prose yourself.** The report is written by Claude Sonnet on Mohit's subscription via `write_report.py` — the same `claude -p` mechanism as the red team. Your job is to run the script and gate its output, not to author prose:

```bash
python ${HERMES_SKILL_DIR}/scripts/write_report.py \
  --idea "<TITLE>: <ONE_LINE_DESCRIPTION>" \
  --inputs "<demand.json>" "<market.json>" "<competition.json>" "<feasibility.json>" "<economics.json>" "<external.json>" \
  --red-team "red_team.json" \
  --corpus "<CORPUS_RESOLVED_PATH>" \
  --open-questions "<SEMICOLON_SEPARATED_AMBIGUITIES_FROM_STEP_0>" \
  --output "report.md"
```

(Redirect nothing — the script writes the report to `--output` itself and prints a JSON envelope to stdout. As always, never use `2>&1`.)

The envelope contains `report_path`, `verdict`, and `kill_likelihood`. The script mechanically enforces four rails — required section structure, the red-team verdict constraint, red-team finding coverage (no fatal/high finding may be dropped or softened, and the kill score must be stated), and quote grounding (every source-attributed quote must trace to the corpus or gated inputs) — and exits non-zero with a `.rejected` debug file if the report violates any — on failure, rerun once; if it fails again, surface the error to Mohit rather than writing the report yourself silently.

**Fallback (only if the envelope says the `claude` CLI is missing):** write the report yourself following the skeleton below, and add a *Research Process Note* at the top stating the prose was written by the session model, not the synthesis model.

The report structure (produced by the script; also the spec for the fallback path):

```markdown
# [Idea Title]

**Verdict:** [STRONG / PROMISING / WEAK / DEAD]

## TL;DR
[3 sentences max — verdict first]

## Executive Summary
[2-3 paragraphs synthesizing all dimensions, including what the red team could not break]

## Demand Reality
[demand output: pain points with verbatim quotes + sources, ICP, JTBD, workarounds, WTP signals, solution–demand fit]

## Market
[market output: market size labeled [Directional] with the source spread if sources disagree, growth, why-now, industry structure, demand drivers]

## Competition
[competition output: table of competitors — name, URL, description, funding stage, geo focus, threat level — plus saturation, funding flows, moats, whitespace, incumbent response]

## Technical Feasibility
[feasibility output: capability maturity, data/infra needs, MVP effort + solo-founder gap, scalability, cost-to-serve drivers]

## Economics & Path to Market
[economics output: pricing thesis, CAC by channel, LTV/retention, margins, sales motion, channels, partnerships, frictions, capital intensity]

## External Constraints (if applicable)
[external output: regulation, platform dependencies, IP/licensing, ethical-backlash risk, timing/macro, risk level]

## Red Team Findings
[hidden assumptions with severity, contradictions between dimensions, evidence-quality attacks, kill likelihood + top kill reasons — report these plainly, do not soften]

## Mohit's Edge
[YOUR honest assessment (not the ensemble's) of his fintech PM / India market / investing background against this specific idea — don't force-fit; use feasibility's solo_founder_gap]

## Lowest-Cost Validation Experiment
[Built from the red team's falsification_test entries — the cheapest tests of the most severe assumptions. Landing page, cold DMs, a poll — not "build a prototype"]

## Opportunity Expansion (appendix)
[Adjacent ideas and long-term directions IF the verdict is already promising or strong. This section may NEVER raise the verdict — expansion dreams do not offset a weak core]

## Open Questions
[Ambiguities from Step 0 parsing + the red team's unowned_considerations]
```

**Synthesis rules:**
- Verdict must be one of: `strong` / `promising` / `weak` / `dead`
- **Strong**: Real, large problem; clear white space; validated user pain; Mohit has edge
- **Promising**: Real problem; some competition but differentiation possible; pain validated
- **Weak**: Problem exists but market small, competition saturated, or no clear wedge
- **Dead**: Problem not real, already solved well, or regulatory wall is fatal
- **Red-team constraint:** if `kill_likelihood.score_pct` ≥ 70, the verdict cannot be `strong`; if the red team found a `fatal`-severity assumption with no cheap falsification path, the verdict cannot be better than `weak`. If you override the red team's direction, the report must say why, explicitly.
- **Opportunity Expansion may never move the verdict upward** — it exists only as an appendix when the core already stands on its own.

The **Mohit's Edge** section should honestly assess his fintech PM background, India market knowledge, and investing experience as relevant or not to this specific idea. Don't force-fit.

The **Lowest-Cost Validation Experiment** should be genuinely low-cost — a landing page, 10 cold DMs, a Twitter poll, not "build a prototype."

---

### Step 4 — Generate PDF report

Use the Edge-based generator directly — confirmed working on this machine (2026-07-02). The primary `templates/generate_pdf.py` (weasyprint) is confirmed BROKEN on this machine (missing native GTK/Pango libraries, `OSError: cannot load library 'libgobject-2.0-0'`) — do not attempt it first, it will always fail here and wastes a full step. Go straight to:

```bash
python ${HERMES_SKILL_DIR}/scripts/generate_pdf_fallback.py \
  --title "<EXTRACTED_TITLE>" \
  --report-md "<REPORT_PATH_FROM_STEP_3_ENVELOPE>" \
  --verdict "<VERDICT_FROM_STEP_3_ENVELOPE>" \
  --domain "<DOMAIN>" \
  --idea-id "<IDEA_ID>"
```

Pass the `report.md` **path** from the Step 3 envelope (the script reads files; pasting the full markdown as an argument can exceed Windows command-line limits). Capture the returned `pdf_path` from the JSON output. The generator renders the markdown properly (headings, tables, lists) as of 2026-07-05 — if a PDF ever shows literal `##` or `**`, the `markdown` package is missing from the venv; report that instead of shipping the PDF.

---

### Step 5 — Save the research run to Supabase

**This must run before Step 6.** `save-run` is what creates the `research_runs` row in the first place — its returned `id` is the `run_id` that Step 6's `save-synthesis` needs as a foreign key. Calling `save-synthesis` before this step will fail with a foreign-key violation (`run_id is not present in table "research_runs"`) — this has actually happened, which is why the step order was fixed to put this first.

```bash
python ${HERMES_SKILL_DIR}/scripts/save_idea.py save-run \
  --idea-id "<IDEA_ID>" \
  --synthesis "<FULL_REPORT_MARKDOWN>" \
  --pdf-path "<PDF_PATH>" \
  --status "complete"
```

Capture the returned `id` — this is `<RUN_ID>` for Step 6. Do not invent a `run_id` yourself (e.g. `uuid.uuid4()`, a timestamp, or any other client-generated value) — it must be exactly the `id` this call returns, since that's the only value that actually exists as a row in `research_runs`. Only `"complete"` is a confirmed-valid `--status` value here; do not pass an invented status like `"processing"` — it will fail a database check constraint.

---

### Step 6 — Save synthesis, competitors, and idea status to Supabase

```bash
python ${HERMES_SKILL_DIR}/scripts/save_idea.py save-synthesis \
  --idea-id "<IDEA_ID>" \
  --run-id "<RUN_ID_FROM_STEP_5>" \
  --verdict "<VERDICT>" \
  --summary "<3_SENTENCE_TLDR>" \
  --report-md "<FULL_REPORT_MARKDOWN>"
```

Save each competitor individually:
```bash
python ${HERMES_SKILL_DIR}/scripts/save_idea.py save-competitor \
  --idea-id "<IDEA_ID>" \
  --name "<NAME>" \
  --url "<URL>" \
  --description "<DESC>" \
  --funding "<FUNDING>" \
  --stage "<STAGE>" \
  --geo-focus "<GEO>" \
  --threat-level "<THREAT>"
```

```bash
python ${HERMES_SKILL_DIR}/scripts/save_idea.py update-status \
  --idea-id "<IDEA_ID>" \
  --status "validated" \
  --verdict "<VERDICT>"
```

---

### Step 7 — Send Telegram TL;DR + PDF

Format the text response as follows (under 5 lines), then output the pdf_path on its own line, followed by `[[as_document]]`. Hermes will auto-detect the path and deliver the PDF as a Telegram file attachment.

```
[VERDICT_EMOJI] *[IDEA_TITLE]*

[ONE_SENTENCE_VERDICT]

✅ [STRONGEST_POSITIVE]
⚠️ [BIGGEST_RISK]
🔬 [CHEAPEST_VALIDATION_EXPERIMENT]

/path/to/generated/report.pdf

[[as_document]]
```

Verdict emojis: 🟢 Strong · 🟡 Promising · 🟠 Weak · 🔴 Dead

Example output:
```
🟡 *AI Invoice Reconciliation for Indian SMEs*

Promising — real pain, crowded with generic tools, differentiation possible on Tally/Busy integration.

✅ MSMEs lose 4–6 hours/week on this; no India-native AI tool
⚠️ Zoho Books and Tally are adding AI features aggressively
🔬 Cold DM 20 CA firms, ask if they'd pay Rs.2k/mo for automation

/home/user/.hermes/venture-studio/reports/20240315-AI-Invoice-Reconciliation-abc12345.pdf

[[as_document]]
```

**Once this message is sent, this idea is DONE — do not re-enter Steps 2-7 for it again in this session, for any reason.** This matters because of a real incident (2026-07-08): after delivering a complete, correct TL;DR + PDF, background notifications kept arriving for trailing async work (the Step 2b second-opinion role calls, dispatched via background `process` and still retrying through 429s when Step 7 fired). The agent treated each late notification as a reason to "continue the pipeline," re-verifying, re-running the red team, re-writing the report, re-generating the PDF, and re-running every Step 5/6/8 persistence call — producing a **second, near-duplicate research_run, synthesis_report, and full set of competitor rows in Supabase, and a second PDF sent to Telegram 49 minutes after the first**, for zero benefit (the second opinions had already failed and changed nothing). The correct behavior: after Step 7 fires, treat any further `[Background process ... completed]` notification for this idea's corpus directory as informational only — read it, and if it's a second-opinion result that arrived late, note it silently for your own awareness, but **do not act on it** (no re-verification, no re-synthesis, no re-delivery). If Mohit asks about it, say the report already shipped and summarize what the late result contained.

---

### Step 8 — Post-verdict watchlist (verdicts must stay falsifiable)

Every report ships kill assumptions and falsification tests; this step makes sure reality gets to vote on them later. After Telegram delivery, add the idea's space to the last30days watchlist (weekly cadence — verdict drift is a weeks-scale phenomenon):

```bash
python3.14 C:/Users/mjain/OneDrive/Documents/hermes_agent/last30days-skill/skills/last30days/scripts/watchlist.py add "<PRIMARY_ENTITY_OR_SPACE>" --weekly --queries "<top 2-3 kill-assumption phrases as search queries>"
```

- `<PRIMARY_ENTITY_OR_SPACE>` is the idea's space, not its title (e.g. "AI companion apps regulation", not "AI Entertainment Companion Platform").
- Seed `--queries` from the red team's top kill reasons — the watchlist should track exactly what would change the verdict (e.g. "character.ai lawsuit ruling", "SpicyChat funding").
- This is non-blocking: if it fails, note it and finish — the report already shipped.
- Digests: findings accumulate in the watchlist store; a weekly digest comes from `watchlist.py run-all` + `briefing.py generate --weekly` (invoked from a Hermes scheduled session or manually via `/last30days` watch commands). When a digest shows a kill assumption moved (regulation shifted, a competitor stumbled, complaints spiked), tell Mohit the verdict may be stale and offer a re-validation run.

---

## Pitfalls

- **TAM numbers from web search are directional at best.** Always label them [Directional]. Do not present as research-grade.
- **If a competitor appears dominant**, say so plainly. Do not soften it.
- **If regulatory risk is fatal** (e.g. requires NBFC license to operate), mark verdict as `dead` regardless of market opportunity.
- **If research returns no useful results** on a track, note it explicitly in the report rather than leaving the section blank.
- **Do not ask clarifying questions before researching.** Parse what you can from the raw idea and proceed. Ambiguities can be noted in Open Questions.
- **Founder fit section should be honest.** If Mohit has no edge here, say so.
- **Temporary-file resolution in this skill:** never hand-type a `/tmp/...` path — see Step 2. Persist raw search data via the `write_file` tool and use its returned `resolved_path` verbatim. This has actually caused real research data to be silently lost and replaced with fabricated placeholder content in the past (2026-07-03) — if a `multi_model_research.py` call ever fails with `Raw data file not found`, that means the wrong path was used somewhere upstream; go back and re-persist via `write_file`, using its real `resolved_path`. Never write substitute/placeholder/guessed content in place of the actual lost research — if the real data is genuinely unrecoverable, say so explicitly and stop that track rather than fabricating input to feed the model ensemble.
- **This skill requires `VENTURE_STUDIO_OPENROUTER_KEY`, not `OPENROUTER_API_KEY`.** The latter is a Hermes-managed provider credential that is permanently stripped from every `terminal`/`execute_code` subprocess by design (see `multi_model_research.py`'s module docstring) — it will never be visible here, on this or any machine, regardless of setup. If `multi_model_research.py` ever returns an API-key error anyway, that means `VENTURE_STUDIO_OPENROUTER_KEY` itself is missing or empty — this is a hard stop for that track, not something to route around. **Do not record a fabricated or absent-data failure as if it were a normal report section and continue** — this exact shortcut has already produced a fully broken, unresearched report shipped to Mohit as if it were real (2026-07-03). Tell Mohit the ensemble couldn't run and why, and stop.
- **`multi_model_research.py` does not implement `update-run`.** If you need to change a run's `pdf_path`/`status` after creation, insert a new `save-run` row; do not invent a `run_id` or try to backfill an old row.
- **Prompt templates in `multi_model_research.py` and `red_team.py` use explicit placeholder `.replace()`**, not `str.format(...)`. Raw web search text and role JSON frequently contain `{` and `}` — using `.format()` there crashes prompt assembly and breaks every role. This is not optional: if you edit prompts, keep the replacement form. Likewise do not shrink `MAX_RAW_DATA_CHARS` (60K) or `MAX_COMPLETION_TOKENS` (8000) back down — the old 8K-char/2000-token limits caused snippet-starved analysis and systematic mid-JSON truncation respectively (both root causes of the 2026-07-03 mediocre report).
- **The red team requires the `claude` CLI, authenticated on Mohit's Claude subscription.** If `red_team.py` errors with "claude CLI not found" or an auth failure, that is a hard stop for the red-team stage — tell Mohit; never route the red team to a free OpenRouter model instead, and never write the Red Team Findings section yourself from imagination.
- **A failed role = a missing decision dimension.** Under role decomposition there is no redundancy between models — if `demand` fails all its fallbacks, the report has no demand analysis at all, and the report must say so rather than covering the hole with your own summary of the corpus.
- **Reasoning-channel responses:** some OpenRouter models return the assistant answer in `reasoning`, not `content`. `multi_model_research.py` now falls back from `content` to `reasoning` before treating a response as missing; if you patch the script, preserve that fallback.
- **Stdout may contain leading model error lines before the JSON envelope.** When `verify_research_data.py check-synthesis-output` is run against raw stdout, ignore non-JSON prefix lines; extract the first parseable JSON object before validation. The same applies to `red_team.json`: `claude -p` output can include reasoning traces or other non-JSON wrapper text; extract the first JSON object and gate that.
- **A role's winning response is always fully-parsed JSON** (the script falls back through models until one parses). `failed_attempts` in the envelope lists which models were tried and why they failed — useful for debugging, never a content source.
- **If `save-competitor` fails due to a database constraint** (for example, a `stage` check constraint on the `competitors` table), treat it as a soft failure: continue with save-run, save-synthesis, and update-status, and report the competitor-save failure explicitly in the final Telegram message. Do not abort the entire pipeline over a single competitor row.
- **Red-team verdict constraint mapping:** `kill_likelihood.score_pct >= 70` ⇒ verdict cannot be `strong`; any `fatal`-severity hidden assumption with no cheap falsification path ⇒ verdict cannot be better than `weak`. Document which constraint applied in the report's Red Team Findings section when the verdict is downgraded.
- **`red_team.py` stdout may contain a duplicate JSON tail** when `claude -p` retries or emits reasoning traces. symptom: `write_report.py` fails with `Extra data: line N column M`. Before re-running synthesis, extract the first complete JSON object from `red_team.json` and trim the file to it; do not hand-edit. See `references/debugging-and-verification.md` for a one-liner.
- **`save-competitor --threat-level` must use simple lowercase slugs** (`high`, `medium`, `low`). Hyphenated values like `low-medium` fail the DB check constraint. On a `23514` violation, lowercase and retry once; if it still fails, continue with other competitors and note the soft failure in the final message — do not abort.

---

## Verification

Research run is successful when:
- [ ] `idea_id` exists in Supabase `ideas` table with `status = 'validated'`
- [ ] `research_runs` row exists with `pdf_path` populated
- [ ] PDF file exists at the path on disk
- [ ] Telegram message sent with verdict + PDF delivered as document
- [ ] All competitors saved to `competitors` table
- [ ] The shared corpus contains extracted full-page content (`=== PAGE:` sections), not just search snippets — or the report carries an explicit `Research Process Note` saying it was snippet-only and why
- [ ] `verify_research_data.py check-raw-data` was run and passed on the corpus before any role call — never skipped, never bypassed on a failure
- [ ] `verify_research_data.py check-synthesis-output` was run and passed for all six role outputs AND the red-team output before synthesis — a role that failed has no content in the final report, and Mohit was told specifically which dimension is missing and why
- [ ] `red_team.py` actually ran (via the `claude` CLI) after all six roles, and its findings appear in the Red Team Findings section with the verdict constraint applied
- [ ] If `save-competitor` fails for any row, note it explicitly and continue — do not abort the pipeline
