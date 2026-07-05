# Idea Validator — Debugging & Verification Notes

Use these notes when `multi_model_research.py`, `red_team.py`, `verify_research_data.py`, or `run` persistence misbehaves.

## MECE role architecture (2026-07-04 redesign)

- `multi_model_research.py` takes `--role {demand|market|competition|feasibility|economics|external}`, not `--analysis-type`. One model per role; `ROLE_MODELS` defines the priority/fallback list per role, tried sequentially until one returns parseable JSON. `--models` overrides. (`arena` was split into `market` + `competition` on 2026-07-04 — attractiveness vs winnability are separate questions.)
- Second opinions: with no cap on model calls, the highest-variance roles (`demand`, `competition`) can be run twice with different `--models` and both outputs passed to `red_team.py --inputs` — it accepts any number of inputs, and disagreement between two runs of the same role is signal for the red team.
- All roles read the SAME shared corpus file — never build per-role data files; mutual exclusivity is in the prompts.
- A role failing all fallbacks = a missing decision dimension. The envelope's `failed_attempts` lists per-model causes.
- `red_team.py` runs AFTER the five roles, on their output files, via `claude -p --model sonnet` (locally-authenticated Claude Code CLI, subscription auth; `ANTHROPIC_API_KEY` is stripped from its child env so it can't silently bill the API). Timeout default 300s. If `claude` is not on PATH or unauthenticated, the red-team stage hard-stops.
- Envelope keys (`analysis_type`, `model_count`, `consolidated_insights`, ...) are kept compatible with `verify_research_data.py`; per-role substantive-field requirements live in `SUBSTANTIVE_FIELDS` there.

## Repaired `multi_model_research.py` behavior

### Prompt assembly
- Raw web search text commonly contains `{`, `}`, `[`, `]` from code snippets, JSON, or live data.
- Old behavior: `prompt.format(raw_data=...)` crashes with `KeyError`/`IndexError` on braces.
- Current behavior: explicit `prompt.replace("{raw_data}", raw_data[:MAX_RAW_DATA_CHARS])` (60K chars).
- Rule: when editing prompts, never switch back to `.format(raw_data=...)`; keep replacement form.

### Truncation and rate limits (fixed 2026-07-04)
- `max_tokens` is `MAX_COMPLETION_TOKENS` (8000). The old 2000 cap caused every model to truncate mid-JSON ("Unterminated string") because reasoning models burn 1–2K tokens on reasoning before emitting the answer.
- Responses with `finish_reason == "length"` are now discarded as errors instead of being parsed — a truncated response is never usable.
- 429s are retried `RETRY_429_ATTEMPTS` times with backoff inside each call; role invocations must run one at a time (the old simultaneous 5-way burst reliably 429'd 3 of 5 free-tier models).
- **OpenRouter free tier has an ACCOUNT-LEVEL daily request cap** (~50 requests/day if account balance is under $10; ~1000/day above). When EVERY model in a role's chain 429s — including slugs that worked earlier the same day — the daily cap is exhausted, not the individual models (observed 2026-07-04 after a day of testing). Failed attempts count against the cap too. Fixes: wait for the daily reset, or hold a one-time $10 balance on the OpenRouter account to raise the cap ~20x. A full 6-role validation run needs at least 6 successful calls of headroom before starting.
- Do not shrink these constants back; they encode the 2026-07-03 failure modes.
- `google/gemini-2.0-flash-exp:free` is a dead slug (hard 404 on OpenRouter) — do not re-add it.

### Reasoning-channel responses
- Some OpenRouter models return assistant content in `reasoning`, not `content`.
- Script now checks `content` first, then falls back to `reasoning`, then `response.get("text")`.
- If you patch response extraction, preserve this fallback.

### Model availability
- Confirmed responsive free slugs in this environment: `poolside/laguna-xs-2.1:free`, `google/gemma-4-26b-a4b-it:free`.
- Earlier failures in this environment were `429 Too Many Requests` after the first two models; this is a rate-limit/concurrency symptom, not every model being unavailable.
- The skill reports headline ensemble models; on tight rate limits, pass `--models` with the handful that actually answer.

## Empty-consolidation gate

`check-synthesis-output` fails when `consolidated_insights` is structurally present but carries no content (e.g. market with `market_size: null` and empty `growth_signals`/`tailwinds`/`headwinds`). `model_count` counts responses *received*, not responses *parsed* — a run where every model 429'd or truncated produces `model_count >= 1` with an all-empty consolidation, which used to pass. When this gate fails, check `raw_model_responses[*].error` for the per-model cause and re-run the track.

## Stdout JSON extraction

`verify_research_data.py check-synthesis-output` expects true JSON.
When piping raw `multi_model_research.py` stdout, leading error lines may precede the JSON envelope.

Easiest use path: write stdout to a file first, then point the verifier at that file. If you must parse stdout, extract the first JSON object carefully before calling the verifier.

## Persistence quirks

- `save_idea.py` does not implement `update-run`. To change `pdf_path` or `status`, create a new `save-run` row.
- Only `"complete"` is a known-good status for `save-run --status`; invented states will fail the DB check constraint.
- `save-synthesis` and `save-competitor` must use the `run-id` returned by the successful `save-run` call.

## Raw-data file paths

- Write raw search dumps with `write_file` and use its returned `resolved_path` verbatim.
- Do not hand-type `/tmp/...` or guessed temp paths: toolchain-specific sandboxes resolve bare `/tmp` differently between `write_file`, `terminal`, and `execute_code`.

## Acceptable partial-track fallback

If model JSON parsing truncates or fails for a track:
- You may transcode valid `raw_model_responses[*].response` entries into report sections manually
- Add a `Research Process Note` explaining why that track is partial
- Do NOT fabricate structured `consolidated_insights` when the ensemble did not produce them
