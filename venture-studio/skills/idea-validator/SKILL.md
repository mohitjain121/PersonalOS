---
name: idea-validator
description: Autonomously validates a startup idea — researches market, competitors, forum signals, regulatory flags, then synthesizes a structured report, persists to Supabase, generates a PDF, and sends a TL;DR verdict via Telegram.
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
      - name: OPENROUTER_API_KEY
        prompt: "OpenRouter API key for multi-model research ensemble"
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
- Every step below is mandatory and must actually run as a tool/script call. Reading a script's source to "understand" it is not the same as executing it — every `python .../scripts/*.py` command shown below must actually be invoked.
- Step 2 requires literally executing `multi_model_research.py` for each track. Summarizing raw web search results yourself instead of running this script is not a valid substitute, even though it's faster — it silently drops the 5-model ensemble that makes the report reliable, and it will visibly regress report quality.
- Never write a new script to replace a provided one (e.g. do not invent your own PDF generator, your own Supabase writer, or your own report synthesizer). If a provided script fails, use its documented fallback (Step 5). Do not improvise a replacement pipeline.
- Persistence steps (1, 4, 6) are not optional under time pressure — the idea must be saved before research starts (Step 1) and the synthesis/status updates must be saved even if later steps have problems.
- If you are genuinely blocked (a script errors with no documented fallback), say so explicitly to the user rather than silently substituting a lower-quality approach.

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

### Step 2 — Multi-model research ensemble

**Architecture:** Raw web data → 4-5 LLMs in parallel → consolidation → high-confidence signals

For each research track below:
1. Gather raw web search data using Hermes web toolset
2. Save raw data to temporary file
3. Pass to `multi_model_research.py` with appropriate analysis type
4. Script calls 5 models in parallel via OpenRouter (GPT-4o, Claude Sonnet 4, Gemini 2.0 Flash, DeepSeek, Qwen)
5. Consolidates outputs with weighted voting and confidence scoring

Run all four tracks (spawn subagents if available for speed; otherwise run sequentially).

#### Track A — Market Analysis

**Web search queries:**
- `"<problem domain> market India 2024 2025"`
- `"<solution type> industry growth India"`
- `"<target user> pain points <domain>"`

Save raw search results to file, then:
```bash
python ${HERMES_SKILL_DIR}/scripts/multi_model_research.py   --raw-data-file "/tmp/market_search_results.txt"   --analysis-type "market"
```

Output: consolidated market size (labeled [Directional]), growth signals with confidence scores, tailwinds/headwinds, customer segments.

#### Track B — Competitor Intelligence

**Web search queries:**
- `"<solution type> startups India"`
- `"<solution type> companies funding"`
- `"alternatives to <existing player if known>"`
- Check Product Hunt, Tracxn, YC batches

Save raw search results, then:
```bash
python ${HERMES_SKILL_DIR}/scripts/multi_model_research.py   --raw-data-file "/tmp/competitor_search_results.txt"   --analysis-type "competitor"
```

Output: deduplicated competitor list with name, URL, description, funding stage, geo focus, threat level (models vote on saturation level).

#### Track C — User Signal Mining

**Web search queries:**
- `"<problem> reddit"`
- `"<problem> site:reddit.com OR site:indiahacks.com OR site:news.ycombinator.com"`
- `"<problem> frustrating OR broken OR expensive OR painful"`
- Enable X/Twitter search if available for real-time sentiment

Save raw results, then:
```bash
python ${HERMES_SKILL_DIR}/scripts/multi_model_research.py   --raw-data-file "/tmp/user_signal_search_results.txt"   --analysis-type "user_signal"
```

Output: pain points with direct user quotes, workarounds, willingness-to-pay signals, frequency mentions (consolidated from multiple model interpretations).

#### Track D — Regulatory Scan (India)

Only if domain is fintech, health, edtech, lending, payments, insurance, or data-heavy.

**Web search queries:**
- `"<solution type> RBI regulation India"`
- `"<solution type> SEBI compliance India"` (if investments/securities)
- `"<solution type> DPDP data privacy India"`
- `"fintech startup license India <specific activity>"`

Save raw results, then:
```bash
python ${HERMES_SKILL_DIR}/scripts/multi_model_research.py   --raw-data-file "/tmp/regulatory_search_results.txt"   --analysis-type "regulatory"
```

Output: regulatory bodies, compliance requirements with difficulty/timeline, blockers, consensus risk level (low/medium/high/fatal).

---

### Step 3 — Synthesize the report

Using all research gathered from the four `multi_model_research.py` track outputs, write the full report as markdown following this structure (there is no separate template file — this skeleton is the spec):

```markdown
# [Idea Title]

**Verdict:** [STRONG / PROMISING / WEAK / DEAD]

## TL;DR
[3 sentences max — verdict first]

## Executive Summary
[2-3 paragraphs synthesizing all four tracks]

## Market Analysis
[Track A output: market size labeled [Directional], growth signals, tailwinds/headwinds, customer segments]

## Competitive Landscape
[Track B output: table of competitors — name, URL, description, funding stage, geo focus, threat level]

## User Signal
[Track C output: pain points with direct quotes, workarounds, willingness-to-pay signals, frequency]

## Regulatory (if applicable)
[Track D output: bodies, requirements, difficulty/timeline, blockers, risk level]

## Mohit's Edge
[Honest assessment of his fintech PM / India market / investing background as relevant or not — don't force-fit]

## Lowest-Cost Validation Experiment
[Genuinely low-cost: landing page, cold DMs, a poll — not "build a prototype"]

## Open Questions
[Ambiguities noted during Step 0 parsing]
```

**Synthesis rules:**
- Verdict must be one of: `strong` / `promising` / `weak` / `dead`
- **Strong**: Real, large problem; clear white space; validated user pain; Mohit has edge
- **Promising**: Real problem; some competition but differentiation possible; pain validated
- **Weak**: Problem exists but market small, competition saturated, or no clear wedge
- **Dead**: Problem not real, already solved well, or regulatory wall is fatal

The **Mohit's Edge** section should honestly assess his fintech PM background, India market knowledge, and investing experience as relevant or not to this specific idea. Don't force-fit.

The **Lowest-Cost Validation Experiment** should be genuinely low-cost — a landing page, 10 cold DMs, a Twitter poll, not "build a prototype."

---

### Step 4 — Save synthesis to Supabase

```bash
python ${HERMES_SKILL_DIR}/scripts/save_idea.py save-synthesis \
  --idea-id "<IDEA_ID>" \
  --run-id "<RUN_ID>" \
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

---

### Step 5 — Generate PDF report

Use the Edge-based generator directly — confirmed working on this machine (2026-07-02). The primary `templates/generate_pdf.py` (weasyprint) is confirmed BROKEN on this machine (missing native GTK/Pango libraries, `OSError: cannot load library 'libgobject-2.0-0'`) — do not attempt it first, it will always fail here and wastes a full step. Go straight to:

```bash
python ${HERMES_SKILL_DIR}/scripts/generate_pdf_fallback.py \
  --title "<EXTRACTED_TITLE>" \
  --report-md "<FULL_REPORT_MARKDOWN>" \
  --verdict "<VERDICT>" \
  --domain "<DOMAIN>" \
  --idea-id "<IDEA_ID>"
```

Capture the returned `pdf_path` from the JSON output.

---

### Step 6 — Update idea status + save run to Supabase

```bash
python ${HERMES_SKILL_DIR}/scripts/save_idea.py update-status \
  --idea-id "<IDEA_ID>" \
  --status "validated" \
  --verdict "<VERDICT>"
```

```bash
python ${HERMES_SKILL_DIR}/scripts/save_idea.py save-run \
  --idea-id "<IDEA_ID>" \
  --pdf-path "<PDF_PATH>" \
  --status "complete"
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

---

## Pitfalls

- **TAM numbers from web search are directional at best.** Always label them [Directional]. Do not present as research-grade.
- **If a competitor appears dominant**, say so plainly. Do not soften it.
- **If regulatory risk is fatal** (e.g. requires NBFC license to operate), mark verdict as `dead` regardless of market opportunity.
- **If research returns no useful results** on a track, note it explicitly in the report rather than leaving the section blank.
- **Do not ask clarifying questions before researching.** Parse what you can from the raw idea and proceed. Ambiguities can be noted in Open Questions.
- **Founder fit section should be honest.** If Mohit has no edge here, say so.

---

## Verification

Research run is successful when:
- [ ] `idea_id` exists in Supabase `ideas` table with `status = 'validated'`
- [ ] `research_runs` row exists with `pdf_path` populated
- [ ] PDF file exists at the path on disk
- [ ] Telegram message sent with verdict + PDF delivered as document
- [ ] All competitors saved to `competitors` table
