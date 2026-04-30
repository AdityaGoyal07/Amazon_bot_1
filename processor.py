"""
processor.py — Data Cleaning, Filtering & Ranking Engine
"""

import logging
import re
from typing import Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# ── Brand heuristics (score bonus) ────────────────────────────────────────────
BRAND_SCORES: dict[str, float] = {
    "samsung":  1.2,
    "apple":    1.3,
    "oneplus":  1.15,
    "google":   1.2,
    "nothing":  1.1,
    "motorola": 1.05,
    "poco":     1.05,
    "redmi":    1.0,
    "realme":   0.95,
    "vivo":     0.9,
    "oppo":     0.9,
    "iqoo":     1.1,
    "nokia":    0.85,
    "infinix":  0.8,
    "tecno":    0.75,
}

# ── Desired keywords for quality signals ──────────────────────────────────────
QUALITY_KEYWORDS = ["5g", "amoled", "oled", "snapdragon", "dimensity", "mediatek"]
PENALISE_KEYWORDS = ["refurbished", "renewed", "case", "cover", "charger", "screen guard"]


@dataclass
class Phone:
    name:       str
    price:      int
    rating:     float
    reviews:    int
    in_stock:   bool
    url:        str
    brand:      str       = field(default="unknown")
    score:      float     = field(default=0.0)
    has_5g:     bool      = field(default=False)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_brand(name: str) -> str:
    lower = name.lower()
    for brand in BRAND_SCORES:
        if brand in lower:
            return brand
    return "unknown"


def _is_accessory(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in PENALISE_KEYWORDS)


def _has_5g(name: str) -> bool:
    return "5g" in name.lower()


def _compute_score(phone: Phone, budget: int) -> float:
    """
    Composite score formula:
      base  = rating * log10(reviews + 1)
      brand = brand multiplier
      price = value-for-money bonus (cheaper within budget = slight bonus)
      kw    = quality keyword bonuses
    """
    import math

    if phone.reviews < 10:      # too few reviews — unreliable
        return 0.0

    rating  = phone.rating or 0.0
    reviews = max(phone.reviews, 1)

    base = rating * math.log10(reviews + 1)

    brand_mult = BRAND_SCORES.get(phone.brand, 0.85)

    # Value bonus: cheaper phones within budget get a mild boost
    price_ratio = phone.price / budget if budget else 1.0
    value_mult  = 1.05 if price_ratio < 0.7 else 1.0

    # Quality keyword bonus
    lower = phone.name.lower()
    kw_bonus = sum(0.05 for kw in QUALITY_KEYWORDS if kw in lower)

    return round(base * brand_mult * value_mult + kw_bonus, 4)


# ── Public API ────────────────────────────────────────────────────────────────

def clean_and_filter(
    raw_items: list[dict],
    budget: int,
    min_rating: float = 3.8,
    min_reviews: int = 50,
) -> list[Phone]:
    """
    Cleans raw scraped dicts, removes accessories/invalid items,
    applies budget + quality filters, returns Phone objects.
    """
    phones: list[Phone] = []
    seen_names: set[str] = set()

    for item in raw_items:
        name    = (item.get("name") or "").strip()
        price   = item.get("price")
        rating  = item.get("rating")
        reviews = item.get("reviews", 0)
        in_stock = item.get("in_stock", False)
        url     = item.get("url", "")

        # ── Basic validity ────────────────────────────────────────────────────
        if not name or not price:
            continue
        if _is_accessory(name):
            logger.debug(f"Skipped accessory: {name!r}")
            continue
        if not in_stock:
            continue
        if price > budget:
            continue
        if (rating or 0) < min_rating:
            continue
        if reviews < min_reviews:
            continue

        # ── Deduplicate (first-seen wins) ─────────────────────────────────────
        key = name[:60].lower()
        if key in seen_names:
            continue
        seen_names.add(key)

        brand = _detect_brand(name)

        phones.append(Phone(
            name     = name,
            price    = price,
            rating   = rating,
            reviews  = reviews,
            in_stock = in_stock,
            url      = url,
            brand    = brand,
            has_5g   = _has_5g(name),
        ))

    logger.info(f"🔍 After filtering: {len(phones)} phones (from {len(raw_items)} raw).")
    return phones


def rank_phones(phones: list[Phone], budget: int) -> list[Phone]:
    """Compute scores and return phones sorted best → worst."""
    for phone in phones:
        phone.score = _compute_score(phone, budget)

    ranked = sorted(phones, key=lambda p: p.score, reverse=True)
    logger.info(f"🏆 Ranking complete. Top phone: {ranked[0].name if ranked else 'N/A'}")
    return ranked


def process(
    raw_items: list[dict],
    budget: int,
    min_rating: float = 3.8,
    min_reviews: int = 50,
) -> list[Phone]:
    """Full pipeline: clean → filter → rank."""
    phones = clean_and_filter(raw_items, budget, min_rating, min_reviews)
    if not phones:
        logger.warning("No phones passed filtering. Consider relaxing min_rating/min_reviews.")
        return []
    return rank_phones(phones, budget)


def phones_to_dicts(phones: list[Phone]) -> list[dict]:
    return [p.to_dict() for p in phones]


def summary_table(phones: list[Phone], top_n: int = 5) -> str:
    """Pretty-print top N phones as a text table."""
    lines = [
        f"\n{'Rank':<5} {'Name':<55} {'Price':>8} {'Rating':>7} {'Reviews':>10} {'Score':>7}",
        "-" * 100,
    ]
    for i, p in enumerate(phones[:top_n], 1):
        lines.append(
            f"{i:<5} {p.name[:54]:<55} ₹{p.price:>7,} {p.rating or 0:>7.1f} {p.reviews:>10,} {p.score:>7.3f}"
        )
    return "\n".join(lines)
