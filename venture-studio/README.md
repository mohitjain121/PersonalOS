# venture-studio

Hermes-powered personal venture studio. Drop ideas on Telegram — Hermes researches, validates, persists to Supabase, and sends you a downloadable PDF report.

## Sprint Status
- [x] **Sprint 1** — Idea capture, web research, Supabase persistence, PDF reports, weekly digest
- [ ] Sprint 2 — Structured evidence, idea lifecycle, rich corpus search
- [ ] Sprint 3 — Cross-idea reasoning, market monitoring, personalized scoring
- [ ] Sprint 4 — Multi-agent studio (Researcher, Devil's Advocate, BizModel, TechFeasibility, GTM, Experiment Designer)

---

## Stack
- **Hermes** — agent orchestrator, Telegram gateway, scheduler
- **Supabase** — single source of truth (ideas, research, competitors, evidence)
- **fpdf2** — PDF report generation (no system dependencies)
- **Python** — helper scripts called via Hermes `execute_code`

---

## Setup

### 1. Clone and place
```bash
git clone <your-repo> ~/projects/venture-studio
```

### 2. Install Python dependencies
```bash
pip install supabase requests fpdf2
```

### 3. Supabase
1. Create project at supabase.com
2. SQL Editor → paste `supabase/schema.sql` → Run
3. Settings → API → copy Project URL + service_role key

### 4. Hermes .env
```bash
nano ~/.hermes/.env
```
Add:
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_service_role_key
```

### 5. Register skill with Hermes
Add to `~/.hermes/config.yaml`:
```yaml
skills:
  external_dirs:
    - ~/projects/venture-studio/skills
```
Then:
```bash
hermes skills reload
hermes chat -q "list your skills"
# Should show: idea-validator
```

### 6. Telegram gateway
```bash
hermes setup --telegram
```
Create a bot via @BotFather → paste the token when Hermes asks.

### 7. Nous Portal (web search)
```bash
hermes setup --portal
```
Required for the research tracks in the idea-validator skill.

### 8. Weekly digest cron
In a Hermes session:
```
/schedule add "weekly-digest" "0 3 * * 0" "Run python ~/projects/venture-studio/scripts/weekly_digest.py and send the full output to me on Telegram"
```
(3:00 UTC = 9:00 IST Sundays)

---

## Usage

**Drop an idea on Telegram:**
```
Idea: An AI-powered GST reconciliation tool for Indian CAs that integrates with Tally
```

Hermes will:
1. Acknowledge immediately
2. Save raw idea to Supabase (never lost)
3. Research in parallel: market, competitors, forums, TAM, regulatory
4. Synthesize full report
5. Generate PDF
6. Update Supabase with status + pdf_path
7. Send Telegram TL;DR + PDF as downloadable file

**Weekly digest (automatic every Sunday 9am IST):**
Top 3 unacted validated ideas with a forcing question.

---

## Project Structure

```
venture-studio/
├── supabase/
│   └── schema.sql                           # Sprint 1–4 schema
├── skills/
│   └── idea-validator/
│       ├── SKILL.md                         # Hermes skill workflow
│       ├── templates/
│       │   └── validation-report.md         # Synthesis template
│       └── scripts/
│           ├── save_idea.py                 # Supabase persistence
│           └── generate_pdf.py             # PDF report generation
├── scripts/
│   └── weekly_digest.py                     # Sunday digest
└── .hermes/
    └── CONTEXT.md                           # Workspace context
```

---

## PDF Reports
Reports are saved to `~/.hermes/venture-studio/reports/` and auto-sent as Telegram file attachments via Hermes's `[[as_document]]` directive.

Filename format: `YYYYMMDD-HHMMSS-{idea-title}-{idea-id[:8]}.pdf`

---

## Sprint 2 Preview
Sprint 2 adds structured evidence rows, competitor detail, idea lifecycle commands (`/kill-idea`, `/rate-idea`), and full-text search across your corpus. Schema already deployed.
