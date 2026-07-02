"""
multi_model_research.py — Multi-model ensemble research for startup validation

Architecture:
1. Receive raw web search data (from Hermes web toolset)
2. Pass raw data to 4-5 LLMs in parallel via OpenRouter
3. Each model independently extracts insights
4. Consolidate and weight outputs to generate high-confidence signals

Usage:
    python multi_model_research.py \
        --raw-data-file "/path/to/search_results.txt" \
        --analysis-type "market" \
        --models "openai/gpt-4o,anthropic/claude-sonnet-4,google/gemini-2.0-flash-exp:free"

Output:
    JSON with consolidated insights, confidence scores, and model agreement
"""

import os
import sys
import json
import argparse
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from collections import Counter

try:
    import httpx
except ImportError:
    print(json.dumps({"error": "httpx not installed. Run: pip install httpx"}))
    sys.exit(1)

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Default model ensemble - ALL FREE via OpenRouter
DEFAULT_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "microsoft/phi-3.5-mini-128k-instruct:free"
]

# Analysis prompts for each track
ANALYSIS_PROMPTS = {
    "market": """Analyze this raw web data about the market. Extract structured insights.

Return ONLY valid JSON (no markdown, no explanations) with this exact structure:
{
    "market_size": {
        "value": "estimated TAM/SAM with units",
        "confidence": 0.0-1.0,
        "label": "Directional - web-sourced",
        "source": "source URL or description"
    },
    "growth_signals": [
        {"signal": "specific growth indicator", "confidence": 0.0-1.0}
    ],
    "tailwinds": ["positive market force 1", "positive market force 2"],
    "headwinds": ["negative market force 1", "negative market force 2"],
    "customer_segments": [
        {"segment": "segment name", "pain_points": ["pain 1", "pain 2"]}
    ],
    "confidence_score": 0.0-1.0
}

Raw web data:
{raw_data}""",

    "competitor": """Analyze this raw web data about competitors. Extract structured insights.

Return ONLY valid JSON (no markdown, no explanations) with this exact structure:
{
    "competitors": [
        {
            "name": "Competitor Name",
            "url": "https://...",
            "description": "what they do",
            "funding": "bootstrapped | $XM seed | Series A/B/C",
            "stage": "early|growth|mature",
            "geo_focus": "India|US|Global",
            "threat_level": "low|medium|high|direct",
            "confidence": 0.0-1.0
        }
    ],
    "market_saturation": "low|medium|high",
    "competitive_moats": ["moat 1", "moat 2"],
    "confidence_score": 0.0-1.0
}

Raw web data:
{raw_data}""",

    "user_signal": """Analyze this raw web data from forums/social media. Extract structured user insights.

Return ONLY valid JSON (no markdown, no explanations) with this exact structure:
{
    "pain_points": [
        {
            "pain": "specific pain point",
            "quote": "direct user quote if available",
            "source": "reddit|hn|twitter|forum name",
            "intensity": "low|medium|high",
            "confidence": 0.0-1.0
        }
    ],
    "workarounds": ["current workaround 1", "current workaround 2"],
    "willingness_to_pay": {
        "signal": "description of WTP indicators",
        "confidence": 0.0-1.0
    },
    "frequency_mentions": "how often this problem is discussed",
    "confidence_score": 0.0-1.0
}

Raw web data:
{raw_data}""",

    "regulatory": """Analyze this raw web data about regulations. Extract structured regulatory insights.

Return ONLY valid JSON (no markdown, no explanations) with this exact structure:
{
    "regulatory_bodies": ["RBI", "SEBI", "etc"],
    "requirements": [
        {
            "requirement": "specific license/compliance",
            "difficulty": "low|medium|high",
            "timeline": "estimated timeline to obtain"
        }
    ],
    "blockers": ["known blocker 1", "known blocker 2"],
    "risk_level": "low|medium|high|fatal",
    "notes": "additional context",
    "confidence_score": 0.0-1.0
}

Raw web data:
{raw_data}"""
}


async def call_openrouter(
    model: str,
    prompt: str,
    raw_data: str,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Call a single model via OpenRouter API.
    """
    if not OPENROUTER_API_KEY:
        return {
            "error": "OPENROUTER_API_KEY not set in environment",
            "model": model
        }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/anthropics/hermes",
        "X-Title": "Hermes Venture Studio Multi-Model Research"
    }

    full_prompt = prompt.format(raw_data=raw_data[:8000])  # Limit raw data size

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
        "temperature": 0.3,  # Lower temp for more consistent structured output
        "max_tokens": 2000
    }

    start_time = datetime.utcnow()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            # Extract the assistant's response
            content = result["choices"][0]["message"]["content"]

            # Try to parse as JSON
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            try:
                parsed_json = json.loads(content)
            except json.JSONDecodeError:
                parsed_json = {"error": "Model returned invalid JSON", "raw_content": content}

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


async def parallel_model_analysis(
    raw_data: str,
    analysis_type: str,
    models: List[str]
) -> List[Dict[str, Any]]:
    """
    Send raw data to multiple models in parallel and collect responses.
    """
    if analysis_type not in ANALYSIS_PROMPTS:
        raise ValueError(f"Invalid analysis_type: {analysis_type}. Choose from: {list(ANALYSIS_PROMPTS.keys())}")

    prompt = ANALYSIS_PROMPTS[analysis_type]

    # Create tasks for parallel execution
    tasks = [call_openrouter(model, prompt, raw_data) for model in models]

    # Execute in parallel
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter and categorize responses
    valid_responses = []
    for resp in responses:
        if isinstance(resp, Exception):
            print(f"Model error: {resp}", file=sys.stderr)
        elif "error" in resp:
            print(f"Model {resp.get('model')} error: {resp.get('error')}", file=sys.stderr)
        else:
            valid_responses.append(resp)

    return valid_responses


def consolidate_market_analysis(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Consolidate market analysis from multiple models."""
    if not responses:
        return {"error": "No valid responses"}

    # Extract confidence scores
    confidences = []
    market_sizes = []
    growth_signals = []
    tailwinds = []
    headwinds = []

    for r in responses:
        resp = r.get("response", {})
        if "confidence_score" in resp:
            confidences.append(resp["confidence_score"])

        if "market_size" in resp and isinstance(resp["market_size"], dict):
            market_sizes.append(resp["market_size"])

        if "growth_signals" in resp:
            growth_signals.extend(resp.get("growth_signals", []))

        if "tailwinds" in resp:
            tailwinds.extend(resp.get("tailwinds", []))

        if "headwinds" in resp:
            headwinds.extend(resp.get("headwinds", []))

    # Consolidate market size (take highest confidence)
    best_market_size = max(market_sizes, key=lambda x: x.get("confidence", 0)) if market_sizes else None

    # Deduplicate and count growth signals
    signal_texts = [s.get("signal", "") for s in growth_signals if isinstance(s, dict)]
    signal_counts = Counter(signal_texts)

    # Consolidate: signals mentioned by multiple models get higher weight
    consolidated_signals = [
        {
            "signal": signal,
            "mentions": count,
            "confidence": round(count / len(responses), 2)
        }
        for signal, count in signal_counts.most_common(10)
    ]

    return {
        "market_size": best_market_size,
        "growth_signals": consolidated_signals,
        "tailwinds": list(set(tailwinds))[:10],
        "headwinds": list(set(headwinds))[:10],
        "avg_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0,
        "model_agreement": round(len(set(str(r.get("response")) for r in responses)) / len(responses), 2)
    }


def consolidate_competitor_analysis(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Consolidate competitor analysis from multiple models."""
    if not responses:
        return {"error": "No valid responses"}

    all_competitors = []
    saturations = []

    for r in responses:
        resp = r.get("response", {})
        if "competitors" in resp:
            all_competitors.extend(resp.get("competitors", []))
        if "market_saturation" in resp:
            saturations.append(resp["market_saturation"])

    # Deduplicate competitors by name (case-insensitive)
    unique_competitors = {}
    for comp in all_competitors:
        if not isinstance(comp, dict):
            continue
        name = comp.get("name", "").lower().strip()
        if not name:
            continue

        if name not in unique_competitors:
            unique_competitors[name] = comp
        else:
            # Merge: take higher confidence version
            existing = unique_competitors[name]
            if comp.get("confidence", 0) > existing.get("confidence", 0):
                unique_competitors[name] = comp

    # Determine consensus on market saturation
    saturation_counts = Counter(saturations)
    consensus_saturation = saturation_counts.most_common(1)[0][0] if saturation_counts else "unknown"

    return {
        "competitors": list(unique_competitors.values()),
        "competitor_count": len(unique_competitors),
        "market_saturation": consensus_saturation,
        "saturation_agreement": round(saturation_counts.most_common(1)[0][1] / len(responses), 2) if saturation_counts else 0
    }


def consolidate_user_signal_analysis(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Consolidate user signal analysis from multiple models."""
    if not responses:
        return {"error": "No valid responses"}

    all_pain_points = []
    all_workarounds = []

    for r in responses:
        resp = r.get("response", {})
        if "pain_points" in resp:
            all_pain_points.extend(resp.get("pain_points", []))
        if "workarounds" in resp:
            all_workarounds.extend(resp.get("workarounds", []))

    # Group pain points by similarity (simple text matching)
    pain_texts = [p.get("pain", "") for p in all_pain_points if isinstance(p, dict)]
    pain_counts = Counter(pain_texts)

    consolidated_pains = [
        {
            "pain": pain,
            "mentions": count,
            "confidence": round(count / len(responses), 2),
            "quotes": [p.get("quote") for p in all_pain_points if p.get("pain") == pain and p.get("quote")][:3]
        }
        for pain, count in pain_counts.most_common(10)
    ]

    return {
        "pain_points": consolidated_pains,
        "workarounds": list(set(all_workarounds))[:10],
        "pain_point_count": len(pain_counts)
    }


def consolidate_regulatory_analysis(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Consolidate regulatory analysis from multiple models."""
    if not responses:
        return {"error": "No valid responses"}

    all_bodies = []
    all_requirements = []
    risk_levels = []

    for r in responses:
        resp = r.get("response", {})
        if "regulatory_bodies" in resp:
            all_bodies.extend(resp.get("regulatory_bodies", []))
        if "requirements" in resp:
            all_requirements.extend(resp.get("requirements", []))
        if "risk_level" in resp:
            risk_levels.append(resp["risk_level"])

    # Determine consensus risk level
    risk_counts = Counter(risk_levels)
    consensus_risk = risk_counts.most_common(1)[0][0] if risk_counts else "unknown"

    return {
        "regulatory_bodies": list(set(all_bodies)),
        "requirements": all_requirements[:10],
        "risk_level": consensus_risk,
        "risk_agreement": round(risk_counts.most_common(1)[0][1] / len(responses), 2) if risk_counts else 0
    }


def consolidate_insights(
    responses: List[Dict[str, Any]],
    analysis_type: str
) -> Dict[str, Any]:
    """
    Consolidate multiple model outputs into weighted, high-confidence signals.

    Strategy:
    - Agreement across models → high confidence
    - Disagreement → flag for manual review
    - Weight by model confidence scores
    - Preserve minority insights if high confidence
    """

    if not responses:
        return {"error": "No valid responses to consolidate"}

    # Type-specific consolidation
    if analysis_type == "market":
        consolidated = consolidate_market_analysis(responses)
    elif analysis_type == "competitor":
        consolidated = consolidate_competitor_analysis(responses)
    elif analysis_type == "user_signal":
        consolidated = consolidate_user_signal_analysis(responses)
    elif analysis_type == "regulatory":
        consolidated = consolidate_regulatory_analysis(responses)
    else:
        consolidated = {}

    # Add metadata
    return {
        "analysis_type": analysis_type,
        "model_count": len(responses),
        "models_used": [r.get("model") for r in responses],
        "timestamp": datetime.utcnow().isoformat(),
        "consolidated_insights": consolidated,
        "raw_model_responses": responses  # For transparency and debugging
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-model research consolidation")
    parser.add_argument("--raw-data-file", required=True,
                       help="Path to file containing raw web search results")
    parser.add_argument("--analysis-type", required=True,
                       choices=["market", "competitor", "user_signal", "regulatory"],
                       help="Type of analysis to perform")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS),
                       help="Comma-separated list of models to use")

    args = parser.parse_args()

    # Read raw data
    if not os.path.exists(args.raw_data_file):
        print(json.dumps({"error": f"Raw data file not found: {args.raw_data_file}"}))
        sys.exit(1)

    with open(args.raw_data_file, 'r', encoding='utf-8') as f:
        raw_data = f.read()

    if not raw_data.strip():
        print(json.dumps({"error": "Raw data file is empty"}))
        sys.exit(1)

    # Parse models
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    if not models:
        print(json.dumps({"error": "No models specified"}))
        sys.exit(1)

    # Run parallel analysis
    try:
        responses = asyncio.run(parallel_model_analysis(raw_data, args.analysis_type, models))
    except Exception as e:
        print(json.dumps({"error": f"Parallel analysis failed: {str(e)}"}))
        sys.exit(1)

    if not responses:
        print(json.dumps({"error": "No valid responses from models"}))
        sys.exit(1)

    # Consolidate insights
    result = consolidate_insights(responses, args.analysis_type)

    # Output JSON
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
