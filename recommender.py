"""
recommender.py — AI-Powered Smartphone Recommendation Layer
Uses OpenAI Chat API (GPT-4o-mini by default) to interpret ranked phones
and return structured JSON recommendations.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ── Prompt template ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert smartphone reviewer and consumer-tech advisor,
specialising in the Indian smartphone market.
You have deep knowledge of chipsets, camera quality, software support, and brand reliability.
Always respond only with valid JSON — no markdown, no preamble."""

USER_PROMPT_TEMPLATE = """User criteria:
- Budget: ₹{budget}

Here are the top scraped & ranked phones from Amazon India:
{phone_data}

Tasks:
1. Pick the single best phone for this budget, considering real-world performance,
   value-for-money, software updates, and after-sales service.
2. Give a short (2–3 sentence), practical reason aimed at a first-time buyer.
3. Suggest 2 alternative phones from the list with brief reasons.

Respond ONLY with this JSON structure (no extra keys):
{{
  "best_phone": "<exact product name from the list>",
  "price": <integer price in INR>,
  "reason": "<2-3 sentence explanation>",
  "alternatives": [
    {{
      "name": "<exact product name>",
      "price": <integer>,
      "reason": "<1-2 sentence reason>"
    }},
    {{
      "name": "<exact product name>",
      "price": <integer>,
      "reason": "<1-2 sentence reason>"
    }}
  ]
}}"""


def _build_phone_summary(phones: list[dict], top_n: int = 10) -> str:
    """Format top N phones as a compact JSON array for the prompt."""
    subset = phones[:top_n]
    compact = [
        {
            "name":    p["name"],
            "price":   p["price"],
            "rating":  p["rating"],
            "reviews": p["reviews"],
            "score":   p["score"],
            "has_5g":  p.get("has_5g", False),
            "brand":   p.get("brand", "unknown"),
        }
        for p in subset
    ]
    return json.dumps(compact, indent=2, ensure_ascii=False)


def _call_openai(prompt: str, api_key: str, model: str = "gpt-4o-mini") -> str:
    """
    Call OpenAI Chat Completion API.
    Returns the raw text content of the assistant message.
    """
    try:
        import openai
    except ImportError:
        raise ImportError("openai package not installed. Run: pip install openai")

    client = openai.OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,
        max_tokens=800,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def _call_anthropic(prompt: str, api_key: str) -> str:
    """
    Alternative: Use Anthropic Claude API if OpenAI key not available.
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package not installed. Run: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def get_recommendation(
    phones: list[dict],
    budget: int,
    openai_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    top_n: int = 10,
) -> dict:
    """
    Main entry-point.  Returns recommendation dict:
      {best_phone, price, reason, alternatives}

    Priority: OpenAI → Anthropic → rule-based fallback.
    API keys can be passed directly or read from environment variables:
      OPENAI_API_KEY or ANTHROPIC_API_KEY
    """
    if not phones:
        return {"error": "No phones to recommend."}

    phone_summary = _build_phone_summary(phones, top_n)
    prompt = USER_PROMPT_TEMPLATE.format(budget=f"{budget:,}", phone_data=phone_summary)

    # ── Try OpenAI ─────────────────────────────────────────────────────────────
    oai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if oai_key:
        try:
            logger.info(f"🤖 Calling OpenAI {model} for recommendation …")
            raw = _call_openai(prompt, oai_key, model)
            result = json.loads(raw)
            logger.info("✅ OpenAI recommendation received.")
            return result
        except Exception as exc:
            logger.warning(f"OpenAI call failed: {exc} — trying Anthropic …")

    # ── Try Anthropic ──────────────────────────────────────────────────────────
    ant_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    if ant_key:
        try:
            logger.info("🤖 Calling Anthropic Claude for recommendation …")
            raw = _call_anthropic(prompt, ant_key)
            # Strip potential markdown code fences
            cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            result = json.loads(cleaned)
            logger.info("✅ Anthropic recommendation received.")
            return result
        except Exception as exc:
            logger.warning(f"Anthropic call failed: {exc} — using rule-based fallback.")

    # ── Rule-based fallback ────────────────────────────────────────────────────
    logger.info("🔁 No AI key available — using rule-based recommendation.")
    return _rule_based_recommendation(phones)


def _rule_based_recommendation(phones: list[dict]) -> dict:
    """Simple heuristic-only fallback when no AI key is configured."""
    if not phones:
        return {"error": "No phones available."}

    best = phones[0]
    alts = []
    for p in phones[1:]:
        if p["brand"] != best["brand"] and len(alts) < 2:
            alts.append({
                "name":   p["name"],
                "price":  p["price"],
                "reason": f"Rated {p['rating']}★ with {p['reviews']:,} reviews and a value score of {p['score']:.2f}.",
            })
    while len(alts) < 2 and len(phones) > len(alts) + 1:
        p = phones[len(alts) + 1]
        alts.append({
            "name":   p["name"],
            "price":  p["price"],
            "reason": f"Strong score of {p['score']:.2f} with {p['reviews']:,} reviews.",
        })

    return {
        "best_phone": best["name"],
        "price":      best["price"],
        "reason": (
            f"Highest composite score ({best['score']:.2f}) among filtered phones, "
            f"with a {best['rating']}★ average rating across {best['reviews']:,} reviews. "
            f"{'Supports 5G connectivity.' if best.get('has_5g') else ''}"
        ).strip(),
        "alternatives": alts,
    }
