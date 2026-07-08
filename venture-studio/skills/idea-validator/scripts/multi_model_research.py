"""
multi_model_research.py — MECE specialist ensemble for decision research

Architecture (redesigned 2026-07-04, replacing the original same-prompt-5-models
design whose consolidation added no information):

1. The calling agent builds ONE shared evidence corpus per decision (web
   searches seeded per dimension + extracted full pages), persisted via the
   write_file tool. Evidence is intentionally shared across roles — mutual
   exclusivity lives in the mandates, not the reading list.
2. Six specialist roles, each owning mutually-exclusive decision questions:
   demand, market, competition, feasibility, economics, external. One model
   per role (free-tier OpenRouter), with sequential fallback through
   ROLE_MODELS until a model returns parseable JSON. Under role decomposition
   a lost call is a lost DIMENSION (not lost redundancy), so
   retry-until-answered is mandatory. (market/competition were split from a
   single "arena" role 2026-07-04: attractiveness and winnability are distinct
   questions, and narrower mandates get deeper answers from weak models.)
3. Adversarial review runs AFTER the roles, in series, via red_team.py
   (Claude Sonnet through the locally-authenticated Claude Code CLI) —
   cross-examination replaces same-prompt voting as the error-correction
   mechanism.
4. Synthesis, founder fit, and the verdict belong to the orchestrating agent
   (SKILL.md Step 3), not this script.

Usage:
    python multi_model_research.py \
        --role demand \
        --raw-data-file "/path/to/evidence_corpus.txt" \
        [--models "slug1,slug2"]   # optional override of the role's model list

Requires VENTURE_STUDIO_OPENROUTER_KEY (not OPENROUTER_API_KEY) in the
environment. This script runs as a subprocess via the terminal/execute_code
tools, and Hermes's own OPENROUTER_API_KEY is a Hermes-managed provider
credential that is permanently stripped from every such subprocess by design
(see tools/env_passthrough.py, GHSA-rhgp-j443-p4rf) — no config change can
make it visible here. This script needs its own, separately-named key.

Output:
    JSON envelope, keys kept compatible with verify_research_data.py:
    {"analysis_type": <role>, "model_count": 1, "models_used": [...],
     "consolidated_insights": {<role JSON>}, "raw_model_responses": [...]}
"""

import os
import sys
import json
import argparse
import asyncio
from typing import Dict, Any, List, Tuple
from datetime import datetime

try:
    import httpx
except ImportError:
    print(json.dumps({"error": "httpx not installed. Run: pip install httpx"}))
    sys.exit(1)

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("VENTURE_STUDIO_OPENROUTER_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Raw research data budget per model call. Every model used here has a 128K
# context; 60K chars (~15K tokens) leaves ample room for prompt + completion.
# Do not shrink this back to a few KB — snippet-sized inputs were the quality
# ceiling behind the 2026-07-03 mediocre-report run.
MAX_RAW_DATA_CHARS = 60000

# Completion budget. Reasoning models can burn 1-2K tokens on reasoning before
# emitting JSON; the old 2000 cap caused systematic mid-JSON truncation.
MAX_COMPLETION_TOKENS = 8000

RETRY_429_ATTEMPTS = 2
RETRY_429_BACKOFF_SECONDS = 15

# Per-role model priority lists (all free tier). First slug is the preferred
# assignment for the role's cognitive profile; the rest are fallbacks, tried
# sequentially until one returns parseable JSON. poolside/laguna and
# google/gemma are the two slugs confirmed responsive in this environment
# (2026-07-04); the others 429 intermittently but succeed with retries.
ROLE_MODELS: Dict[str, List[str]] = {
    "demand": [
        "google/gemma-4-26b-a4b-it:free",          # faithful extraction from bulky forum text
        "meta-llama/llama-3.3-70b-instruct:free",
        "poolside/laguna-xs-2.1:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
    ],
    "market": [
        "meta-llama/llama-3.3-70b-instruct:free",  # broadest world knowledge of the free set
        "poolside/laguna-xs-2.1:free",
        "openai/gpt-oss-120b:free",
        "google/gemma-4-26b-a4b-it:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
    ],
    "competition": [
        "google/gemma-4-26b-a4b-it:free",          # reliable entity/structure extraction
        "meta-llama/llama-3.3-70b-instruct:free",
        "poolside/laguna-xs-2.1:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
    ],
    "feasibility": [
        "qwen/qwen-2.5-72b-instruct:free",         # strongest technical/code reasoning
        "poolside/laguna-xs-2.1:free",
        "openai/gpt-oss-120b:free",
        "google/gemma-4-26b-a4b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
    ],
    "economics": [
        "qwen/qwen-2.5-72b-instruct:free",         # structured quantitative reasoning
        "meta-llama/llama-3.3-70b-instruct:free",
        "openai/gpt-oss-120b:free",
        "poolside/laguna-xs-2.1:free",
        "google/gemma-4-26b-a4b-it:free",
    ],
    "external": [
        "poolside/laguna-xs-2.1:free",             # careful literal reading for regulatory text
        "google/gemma-4-26b-a4b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
    ],
}

# Role prompts. MECE is enforced through mandates and explicit non-goals; all
# roles read the same shared corpus. Plain string literals with a {raw_data}
# placeholder — assembled via .replace(), NEVER .format() (search text contains
# braces and .format() crashes prompt assembly).

_EVIDENCE_RULE = """Every claim must cite evidence from the corpus (a quote or a URL that appears in it).
If the corpus does not support a claim, write "no evidence found" for that field — never invent data.
Return ONLY valid JSON (no markdown, no explanations) with the exact structure shown."""

ROLE_PROMPTS: Dict[str, str] = {
    "demand": """You are the Demand Reality analyst on a research committee. You own exactly one question:
"Is the pain real, frequent, and urgent — and whose is it?"

You own: pain evidence, ideal customer profile, jobs-to-be-done, current workarounds and status-quo
behavior, user sentiment about existing alternatives (as experiences, not as businesses),
willingness-to-pay SIGNALS reported verbatim, and whether the proposed solution actually addresses
the job-to-be-done (solution-demand fit).
You do NOT cover (owned by other analysts): competitors as businesses/funding (Arena), pricing
strategy or unit economics (Economics — you only report what users say/do about paying),
buildability (Feasibility), regulation (External).

""" + _EVIDENCE_RULE + """
{
    "pain_points": [
        {"pain": "specific pain", "evidence_quote": "verbatim user quote or close paraphrase",
         "source": "URL or forum name from corpus", "frequency": "how often discussed",
         "intensity": "low|medium|high", "confidence": 0.0}
    ],
    "icp": {"who": "specific persona", "context": "when/where the pain bites", "urgency": "low|medium|high"},
    "jtbd": ["job the user is hiring a product to do"],
    "current_workarounds": ["what users do today, including 'do nothing'"],
    "alternative_experience": [
        {"alternative": "product/tool name", "user_sentiment": "what users say", "gaps": "what it fails at"}
    ],
    "wtp_signals": [{"signal": "observed paying behavior or stated willingness", "evidence": "quote/URL"}],
    "solution_demand_fit": {"assessment": "does the proposed solution address the JTBD?", "gaps": "mismatches"},
    "confidence_score": 0.0
}

Raw evidence corpus:
{raw_data}""",

    "market": """You are the Market analyst on a research committee. You own exactly one question:
"Is the space attractive — big enough, growing, and timely?"

You own: market size (label it Directional, and state the spread when sources disagree), growth,
industry structure (who holds power, distribution chokepoints), and why-now TAILWINDS ONLY —
forces working IN FAVOR of entering now (adoption curves, cost collapses, behavior shifts,
enabling infrastructure). The boundary rule: if a timing force helps, it is yours under why_now;
if it can hurt, delay, or kill, it belongs to External and must NOT appear in your output, even
hedged. Never write "X is a tailwind but also a risk" — hand the risk half to External by omission.
You do NOT cover: individual competitors, moats, or whitespace (Competition analyst), user
sentiment/quotes (Demand), pricing for THIS idea (Economics), regulation or any
too-early/too-late/cycle risk (External).

""" + _EVIDENCE_RULE + """
{
    "market_size": {"value": "TAM/SAM with units", "confidence": 0.0,
                    "label": "Directional - web-sourced", "source": "URL from corpus"},
    "market_size_spread": "if corpus sources disagree, state the range and why they diverge",
    "growth_signals": [{"signal": "specific indicator", "confidence": 0.0}],
    "industry_structure": "fragmented/consolidated, who holds power, distribution chokepoints",
    "why_now": ["tailwind that makes this timely"],
    "demand_drivers": ["macro force pushing spend into this category"],
    "confidence_score": 0.0
}

Raw evidence corpus:
{raw_data}""",

    "competition": """You are the Competition analyst on a research committee. You own exactly one question:
"Can a NEW ENTRANT win against who is already here?"

You own: competitors AS BUSINESSES (funding, positioning, stage, threat), funding flows into the
category, market saturation, available moats for a new entrant, whitespace, and likely incumbent
response. Competitor pricing is yours only as a landscape fact.
You do NOT cover: market size/growth (Market analyst), user sentiment about these products
(Demand), pricing strategy for THIS idea (Economics), regulation (External).

""" + _EVIDENCE_RULE + """
{
    "competitors": [
        {"name": "Name", "url": "https://...", "description": "what they do",
         "funding": "bootstrapped | $XM seed | Series A/B/C", "stage": "early|growth|mature",
         "geo_focus": "India|US|Global", "threat_level": "low|medium|high|direct", "confidence": 0.0}
    ],
    "market_saturation": "low|medium|high, with basis",
    "funding_flows": "where category capital is going, from corpus evidence",
    "moats_available": ["defensibility mechanism realistically available to a new entrant"],
    "whitespace": "the specific gap no listed competitor covers, or 'none found'",
    "incumbent_response_risk": "what the strongest incumbent does if this works",
    "confidence_score": 0.0
}

Raw evidence corpus:
{raw_data}""",

    "feasibility": """You are the Feasibility analyst on a research committee. You own exactly one question:
"Can this be built and operated — with what, by whom, how fast?"

You own: AI/tech capability limits relevant to the idea, data availability, infrastructure and
API dependencies, engineering effort and the skills required (a solo PM founder context — note
what must be hired/contracted), scalability and operational complexity, and cost-to-serve DRIVERS.
You produce cost/effort INPUTS only.
You do NOT cover: pricing or margins (Economics turns your cost drivers into margin judgments),
market demand (Demand), competitors (Arena), regulation (External).

""" + _EVIDENCE_RULE + """
{
    "capability_assessment": {"required_capabilities": ["capability"], "maturity": "proven|emerging|speculative",
                              "evidence": "quote/URL"},
    "data_requirements": {"needed": ["data asset"], "availability": "how obtainable"},
    "infrastructure": {"apis_and_services": ["dependency"], "build_vs_buy": "assessment"},
    "engineering_effort": {"mvp_estimate": "time with stated assumptions", "skills_required": ["skill"],
                           "solo_founder_gap": "what a solo non-engineer founder cannot do alone"},
    "scalability_risks": ["what breaks at 10x/100x usage"],
    "cost_to_serve_drivers": [{"driver": "e.g. inference tokens per session", "behavior": "how it scales"}],
    "confidence_score": 0.0
}

Raw evidence corpus:
{raw_data}""",

    "economics": """You are the Economics & Path-to-Market analyst on a research committee. You own exactly one question:
"Is there a credible, affordable route to revenue?"

You own: pricing thesis (converting willingness-to-pay evidence into a pricing/packaging view),
CAC by channel, LTV and retention/churn expectations, margin structure, sales motion,
distribution channels, partnerships, adoption frictions, and capital intensity.
You do NOT cover: raw user quotes (Demand reports the signals; you build the thesis on them),
competitor profiles (Arena; their pricing appears in the corpus as landscape fact you may use),
build effort (Feasibility supplies cost drivers), regulation (External).

""" + _EVIDENCE_RULE + """
{
    "pricing_thesis": {"model": "subscription|usage|transaction|ads|hybrid", "price_point": "with currency",
                       "basis": "evidence from corpus supporting this price"},
    "cac_by_channel": [{"channel": "channel", "expected_cac": "estimate with basis", "confidence": 0.0}],
    "ltv_retention": {"retention_expectation": "with basis", "churn_risks": ["risk"]},
    "margin_structure": "gross-margin view given the cost drivers visible in the corpus",
    "sales_motion": "self-serve|sales-led|plg|community",
    "distribution_channels": ["channel ranked by fit"],
    "partnerships": ["partnership that changes distribution economics"],
    "adoption_frictions": ["friction between a user hearing about this and paying"],
    "capital_intensity": "cash needed before default-alive, order of magnitude",
    "confidence_score": 0.0
}

Raw evidence corpus:
{raw_data}""",

    "external": """You are the External Constraints analyst on a research committee. You own exactly one question:
"What forces from OUTSIDE the market can kill or unlock this?"

You own: regulation and compliance, platform dependency risk (app stores, model providers,
payment rails), IP/licensing exposure, ethical/societal-backlash risk, and ALL timing/macro
HEADWINDS and shocks (too early, too late, cycle-dependent, regulatory tide, macro squeeze).
The boundary rule: Market owns timing forces working in the idea's FAVOR (its why_now); you own
every force that can hurt, delay, or kill. If the same fact cuts both ways (e.g. a new law
legitimizes the category AND restricts it), you own the restricting half — state it as risk and
do not soften it because it also has an upside; Market will claim the upside separately.
You do NOT cover: competitive forces inside the market (Competition owns competitors and
incumbent response), demand, feasibility, or economics.

""" + _EVIDENCE_RULE + """
{
    "regulatory": [
        {"body": "regulator/framework", "requirement": "specific obligation",
         "difficulty": "low|medium|high", "timeline": "time to comply", "evidence": "quote/URL"}
    ],
    "platform_dependencies": [{"platform": "dependency", "risk": "what they can do to you", "severity": "low|medium|high"}],
    "ip_licensing": "IP or licensing exposure, or 'none found'",
    "ethical_backlash_risk": "societal/press/brand risk assessment",
    "timing_macro_risks": ["too-early/too-late/cycle risk with basis"],
    "blockers": ["hard blocker if any"],
    "risk_level": "low|medium|high|fatal",
    "confidence_score": 0.0
}

Raw evidence corpus:
{raw_data}""",
}

ROLES = list(ROLE_PROMPTS.keys())


async def call_openrouter(
    model: str,
    prompt: str,
    raw_data: str,
    timeout: int = 120
) -> Dict[str, Any]:
    """Call a single model via OpenRouter, with 429 retry and truncation detection."""
    if not OPENROUTER_API_KEY:
        return {
            "error": "VENTURE_STUDIO_OPENROUTER_KEY not set in environment",
            "model": model
        }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/anthropics/hermes",
        "X-Title": "Hermes Venture Studio MECE Research"
    }

    # Explicit placeholder replacement instead of .format() so corpus text
    # containing '{'/'}' does not break prompt assembly.
    full_prompt = prompt.replace("{raw_data}", raw_data[:MAX_RAW_DATA_CHARS])

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a research analyst. Always return valid JSON only, no markdown formatting."
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": MAX_COMPLETION_TOKENS
    }

    start_time = datetime.utcnow()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(RETRY_429_ATTEMPTS + 1):
                response = await client.post(
                    OPENROUTER_BASE_URL,
                    headers=headers,
                    json=payload
                )
                if response.status_code == 429 and attempt < RETRY_429_ATTEMPTS:
                    await asyncio.sleep(RETRY_429_BACKOFF_SECONDS * (attempt + 1))
                    continue
                response.raise_for_status()
                break
            result = response.json()

            choice = result["choices"][0]

            # A completion cut off at max_tokens is mid-JSON garbage — hard error.
            if choice.get("finish_reason") == "length":
                return {
                    "model": model,
                    "error": (
                        f"Response truncated at max_tokens={MAX_COMPLETION_TOKENS} "
                        "(finish_reason=length); truncated JSON is unusable"
                    ),
                    "timestamp": datetime.utcnow().isoformat()
                }

            # Some models return the answer in `reasoning`, not `content`.
            content = choice["message"].get("content")
            if content is None:
                content = choice["message"].get("reasoning", "") or ""

            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            if not content:
                parsed_json = {"error": "Model returned empty content"}
            else:
                try:
                    parsed_json = json.loads(content)
                except (json.JSONDecodeError, TypeError) as e:
                    parsed_json = {"error": f"Model returned invalid JSON: {str(e)}", "raw_content": content}

            latency = (datetime.utcnow() - start_time).total_seconds() * 1000

            return {
                "model": model,
                "response": parsed_json,
                "latency_ms": round(latency, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "tokens_used": result.get("usage", {})
            }

    except Exception as e:
        return {
            "model": model,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


def _is_usable(resp: Dict[str, Any]) -> bool:
    """A response is usable only if the model answered AND its JSON parsed."""
    if "error" in resp:
        return False
    parsed = resp.get("response")
    return isinstance(parsed, dict) and "error" not in parsed


async def run_role(
    raw_data: str,
    role: str,
    models: List[str]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Run one specialist role: try each model in order until one returns
    parseable JSON. Returns (winning_response_or_None, failed_attempts).
    """
    prompt = ROLE_PROMPTS[role]
    failures = []
    for model in models:
        resp = await call_openrouter(model, prompt, raw_data)
        if _is_usable(resp):
            return resp, failures
        failures.append({
            "model": model,
            "error": resp.get("error") or resp.get("response", {}).get("error", "unknown"),
        })
        print(f"Role {role}: model {model} failed "
              f"({failures[-1]['error']}), trying next fallback", file=sys.stderr)
    return None, failures


def main():
    parser = argparse.ArgumentParser(description="MECE specialist research role")
    parser.add_argument("--role", required=True, choices=ROLES,
                        help="Which specialist mandate to run")
    parser.add_argument("--raw-data-file", required=True,
                        help="Path to the shared evidence corpus")
    parser.add_argument("--models", default=None,
                        help="Optional comma-separated override of the role's model list")

    args = parser.parse_args()

    if not os.path.exists(args.raw_data_file):
        print(json.dumps({"error": f"Raw data file not found: {args.raw_data_file}"}))
        sys.exit(1)

    with open(args.raw_data_file, 'r', encoding='utf-8') as f:
        raw_data = f.read()

    if not raw_data.strip():
        print(json.dumps({"error": "Raw data file is empty"}))
        sys.exit(1)

    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        models = ROLE_MODELS[args.role]

    if not models:
        print(json.dumps({"error": "No models specified"}))
        sys.exit(1)

    try:
        winner, failures = asyncio.run(run_role(raw_data, args.role, models))
    except Exception as e:
        print(json.dumps({"error": f"Role analysis failed: {str(e)}"}))
        sys.exit(1)

    if winner is None:
        print(json.dumps({
            "error": (
                f"Role '{args.role}' got no usable response from any of {models}. "
                "This dimension is MISSING from the decision — do not paper over it; "
                "report the gap. Per-model failures in 'failed_attempts'."
            ),
            "failed_attempts": failures,
        }))
        sys.exit(1)

    # Envelope keys kept compatible with verify_research_data.py.
    result = {
        "analysis_type": args.role,
        "model_count": 1,
        "models_used": [winner.get("model")],
        "timestamp": datetime.utcnow().isoformat(),
        "consolidated_insights": winner.get("response"),
        "raw_model_responses": [winner],
        "failed_attempts": failures,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
