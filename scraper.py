"""
scraper.py — Amazon India Smartphone Scraper (Selector-Resilient Build)
Uses multiple fallback selectors since Amazon frequently changes its HTML.
Also navigates DIRECTLY to search URL instead of typing in search box.
"""

import asyncio
import random
import logging
import re
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

NAME_SELECTORS = [
    "h2 span.a-text-normal",
    "h2 a span",
    "h2 span",
    ".a-size-medium.a-color-base.a-text-normal",
    ".a-size-base-plus.a-color-base.a-text-normal",
    "span[class*='a-text-normal']",
]

PRICE_SELECTORS = [
    "span.a-price:not(.a-text-strike) span.a-price-whole",
    ".a-price .a-price-whole",
    "span.a-price[data-a-color='base'] .a-price-whole",
    ".a-price-whole",
]

RATING_SELECTORS = [
    "span.a-icon-alt",
    "i.a-icon-star span.a-icon-alt",
    "i[class*='a-star'] span.a-icon-alt",
    "span[aria-label*='out of 5']",
]

REVIEW_SELECTORS = [
    "span.a-size-base.s-underline-text",
    "span.a-size-base.s-link-centralized-style",
    "a[aria-label*='ratings']",
    "a[aria-label*='reviews']",
    "span[aria-label*='ratings']",
    "span[aria-label*='reviews']",
    "a.a-link-normal span.a-size-base",
    "div.a-row.a-size-small span:nth-child(2)",
    "span.a-size-base",
]

LINK_SELECTORS = [
    "h2 a.a-link-normal",
    "h2 a",
    "a[href*='/dp/']",
]


async def _human_delay(lo=0.8, hi=2.5):
    await asyncio.sleep(random.uniform(lo, hi))


async def _scroll_page(page: Page, steps=6):
    for _ in range(steps):
        await page.mouse.wheel(0, random.randint(300, 700))
        await asyncio.sleep(random.uniform(0.3, 0.7))
    await page.mouse.wheel(0, -200)
    await asyncio.sleep(0.4)


async def _try_get_text(element, selectors: list) -> Optional[str]:
    for sel in selectors:
        try:
            el = await element.query_selector(sel)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    return text
        except Exception:
            continue
    return None


async def _try_get_attr(element, selectors: list, attr: str) -> Optional[str]:
    for sel in selectors:
        try:
            el = await element.query_selector(sel)
            if el:
                val = await el.get_attribute(attr)
                if val:
                    return val.strip()
        except Exception:
            continue
    return None


def _parse_price(raw: Optional[str]) -> Optional[int]:
    if not raw:
        return None
    try:
        return int(re.sub(r"[^\d]", "", raw))
    except (ValueError, TypeError):
        return None


def _parse_rating(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    m = re.search(r"(\d+\.?\d*)\s*out of", raw)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+\.\d+)", raw)
    return float(m.group(1)) if m else None


def _parse_reviews(raw: Optional[str]) -> int:
    if not raw:
        return 0
    nums = re.sub(r"[^\d]", "", raw)
    return int(nums) if nums else 0


async def _get_valid_cards(page: Page) -> list:
    """Get cards that have a non-empty data-asin attribute."""
    all_cards = await page.query_selector_all('div[data-asin]')
    valid = []
    for card in all_cards:
        asin = await card.get_attribute("data-asin")
        if asin and len(asin) > 3:
            valid.append(card)
    return valid


async def _diagnose(page: Page):
    """Called when 0 items extracted — logs debug info."""
    logger.warning("  🔎 Running page diagnosis …")
    body = (await page.content()).lower()
    if "captcha" in body or "robot check" in body:
        logger.error("  ❌ CAPTCHA detected! Try headless: false and run manually.")
        return
    cards = await _get_valid_cards(page)
    logger.info(f"  Cards with data-asin: {len(cards)}")
    price_els = await page.query_selector_all("span.a-price-whole")
    logger.info(f"  span.a-price-whole elements: {len(price_els)}")
    h2_els = await page.query_selector_all("h2")
    logger.info(f"  h2 elements: {len(h2_els)}")
    logger.info(f"  Page title: {await page.title()}")
    if cards:
        snippet = await cards[0].inner_html()
        logger.debug(f"  First card HTML:\n{snippet[:1000]}")


async def _extract_items(page: Page) -> list[dict]:
    items = []
    cards = await _get_valid_cards(page)
    logger.info(f"  Found {len(cards)} valid data-asin cards.")

    if not cards:
        await _diagnose(page)
        return []

    for i, card in enumerate(cards):
        try:
            # Skip sponsored
            sp = await card.query_selector(
                "span.s-label-popover-default, "
                ".puis-sponsored-label-text, "
                "[data-component-type='s-status-badge-component']"
            )
            if sp:
                continue

            # Name
            name = await _try_get_text(card, NAME_SELECTORS)
            if not name or len(name) < 5:
                continue

            # Price — try selectors first
            price_raw = await _try_get_text(card, PRICE_SELECTORS)
            price = _parse_price(price_raw)

            # Price fallback: scan all text for ₹ pattern
            if not price:
                try:
                    full_text = await card.inner_text()
                    m = re.search(r"[₹\u20b9]\s*([\d,]+)", full_text)
                    if m:
                        price = _parse_price(m.group(1))
                except Exception:
                    pass

            # Rating
            rating_raw = (
                await _try_get_attr(card, RATING_SELECTORS, "alt") or
                await _try_get_attr(card, ["span[aria-label*='out of 5']"], "aria-label") or
                await _try_get_text(card, RATING_SELECTORS)
            )
            rating = _parse_rating(rating_raw)

            # Reviews — try text first, then aria-label, then card text scan
            reviews_raw = await _try_get_text(card, REVIEW_SELECTORS)
            if not reviews_raw or not re.search(r"\d", reviews_raw):
                reviews_raw = await _try_get_attr(card, REVIEW_SELECTORS, "aria-label")
            if not reviews_raw or not re.search(r"\d", reviews_raw):
                try:
                    card_text = await card.inner_text()
                    m = re.search(r"\(([\d,]+)\)", card_text)
                    if m:
                        reviews_raw = m.group(1)
                except Exception:
                    pass
            if reviews_raw and not re.search(r"\d", reviews_raw):
                reviews_raw = None
            reviews = _parse_reviews(reviews_raw)

            # URL
            href = await _try_get_attr(card, LINK_SELECTORS, "href") or ""
            url = f"https://www.amazon.in{href}" if href.startswith("/") else href

            in_stock = price is not None

            items.append({
                "name":     name,
                "price":    price,
                "rating":   rating,
                "reviews":  reviews,
                "in_stock": in_stock,
                "url":      url,
            })
            logger.debug(f"  [{i}] {name[:45]} | ₹{price} | ⭐{rating} | {reviews} reviews")

        except Exception as exc:
            logger.debug(f"  Card {i} error: {exc}")
            continue

    logger.info(f"  Extracted {len(items)} items.")
    if not items:
        await _diagnose(page)
    return items


async def scrape_amazon(
    query: str,
    max_pages: int = 3,
    headless: bool = True,
    retries: int = 3,
) -> list[dict]:
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"🚀 Attempt {attempt}/{retries} — '{query}'")
            results = await _run_scrape(query, max_pages, headless)
            logger.info(f"✅ Done — {len(results)} products collected.")
            return results
        except Exception as exc:
            logger.error(f"Attempt {attempt} failed: {exc}")
            if attempt < retries:
                wait = random.uniform(8, 20)
                logger.info(f"  Retrying in {wait:.1f}s …")
                await asyncio.sleep(wait)
    logger.error("All attempts exhausted.")
    return []


async def _run_scrape(query: str, max_pages: int, headless: bool) -> list[dict]:
    all_items: list[dict] = []

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--lang=en-IN",
            ],
        )

        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1366, "height": 768},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            extra_http_headers={
                "Accept-Language": "en-IN,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        # Stealth patches
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en'] });
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()

        # ── Go directly to search results URL (more reliable than typing) ──
        encoded = query.replace(" ", "+")
        url = f"https://www.amazon.in/s?k={encoded}&i=electronics&rh=n%3A1389432031"
        logger.info(f"  → {url}")

        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await _human_delay(2.5, 4.5)

        body_lower = (await page.content()).lower()
        if "captcha" in body_lower or "robot check" in body_lower:
            raise RuntimeError("CAPTCHA on first page!")

        logger.info(f"  Title: {await page.title()}")

        # ── Paginate ──────────────────────────────────────────────────────
        for page_num in range(1, max_pages + 1):
            logger.info(f"  📄 Page {page_num} …")

            try:
                await page.wait_for_selector(
                    'div[data-asin]:not([data-asin=""])',
                    timeout=12_000,
                )
            except Exception:
                logger.warning(f"  Timeout waiting for cards on page {page_num}.")

            await _scroll_page(page, steps=random.randint(5, 8))
            await _human_delay(1.0, 2.0)

            page_items = await _extract_items(page)
            all_items.extend(page_items)
            logger.info(f"     page {page_num}: {len(page_items)} items | total: {len(all_items)}")

            if page_num >= max_pages:
                break

            next_btn = await page.query_selector(
                'a.s-pagination-next, '
                'a[aria-label="Go to next page"], '
                'li.a-last a, '
                '.s-pagination-item.s-pagination-next'
            )
            if not next_btn:
                logger.info("  No next-page button found — done.")
                break

            await _human_delay(1.5, 3.0)
            await next_btn.click()
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
            await _human_delay(2.0, 3.5)

        await browser.close()

    return all_items
