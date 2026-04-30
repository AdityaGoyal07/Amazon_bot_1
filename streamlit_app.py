"""
streamlit_app.py — Amazon India Smartphone Bot (Full Redesign)

Run:
    streamlit run streamlit_app.py

Requires a .env file in the same directory:
    OPENAI_API_KEY=sk-...
    ANTHROPIC_API_KEY=sk-ant-...   (optional fallback)
"""

import asyncio
import json
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# ── Load .env ──────────────────────────────────────────────────────────────────
load_dotenv()
OPENAI_KEY    = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Windows fix ────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📱 Smartphone Bot — Amazon India",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════
#  GLOBAL CSS
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
    --bg:      #070b14;
    --bg2:     #0d1424;
    --bg3:     #111827;
    --border:  #1e2d45;
    --border2: #253550;
    --accent:  #3b82f6;
    --accent2: #60a5fa;
    --green:   #10b981;
    --green2:  #34d399;
    --gold:    #f59e0b;
    --purple:  #8b5cf6;
    --text:    #e2e8f0;
    --text2:   #94a3b8;
    --text3:   #64748b;
    --mono:    'JetBrains Mono', monospace;
    --sans:    'Space Grotesk', sans-serif;
}
html, body, [class*="css"] {
    font-family: var(--sans) !important;
    background: var(--bg) !important;
    color: var(--text) !important;
}
[data-testid="stSidebar"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--border) !important;
    min-width: 220px !important; max-width: 220px !important;
}
[data-testid="stSidebar"] * { color: var(--text2) !important; }
[data-testid="stSidebar"] hr { border-color: var(--border) !important; opacity: 1; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }

.badge {
    display: inline-flex; align-items: center;
    font-size: 0.72rem; font-weight: 600;
    padding: 3px 10px; border-radius: 20px; margin: 3px 3px 0 0;
}
.badge-green { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.badge-blue  { background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
.badge-gold  { background: rgba(245,158,11,0.15); color: #fcd34d; border: 1px solid rgba(245,158,11,0.3); }
.badge-gray  { background: rgba(148,163,184,0.1); color: #94a3b8; border: 1px solid #1e2d45; }
.badge-purple{ background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }

.best-card {
    background: linear-gradient(135deg,#0a2218 0%,#061810 60%,#091f16 100%);
    border: 1.5px solid #10b981; border-radius: 16px;
    padding: 28px 32px; position: relative; overflow: hidden; margin-bottom: 8px;
}
.best-card::before {
    content:''; position:absolute; top:0; right:0;
    width:200px; height:200px;
    background: radial-gradient(circle,rgba(16,185,129,0.12) 0%,transparent 70%);
    pointer-events:none;
}
.best-card .bc-label { font-size:0.68rem; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:#34d399; margin-bottom:8px; }
.best-card .bc-name  { font-size:1.3rem; font-weight:700; color:#fff; margin-bottom:6px; line-height:1.35; }
.best-card .bc-price { font-size:2rem; font-weight:800; color:#34d399; font-family:var(--mono); letter-spacing:-0.02em; }
.best-card .bc-reason{ color:#9bb8aa; font-size:0.88rem; margin-top:14px; line-height:1.65; }

.alt-card {
    background: #111827; border: 1px solid #253550; border-radius:12px;
    padding:20px; height:100%;
}
.alt-card .ac-medal  { font-size:1.8rem; margin-bottom:10px; }
.alt-card .ac-name   { font-size:0.88rem; font-weight:600; color:#e2e8f0; line-height:1.4; }
.alt-card .ac-price  { font-size:1.4rem; font-weight:800; color:#60a5fa; font-family:var(--mono); margin:6px 0; }
.alt-card .ac-reason { font-size:0.79rem; color:#64748b; line-height:1.5; margin-top:6px; }

.seller-card {
    background: linear-gradient(135deg,#130a24 0%,#0e0619 100%);
    border: 1.5px solid #8b5cf6; border-radius:14px; padding:22px 26px;
    position:relative; overflow:hidden;
}
.seller-card::before {
    content:''; position:absolute; top:-20px; right:-20px;
    width:140px; height:140px;
    background: radial-gradient(circle,rgba(139,92,246,0.18) 0%,transparent 70%);
}
.seller-card .sc-label { font-size:0.68rem; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:#a78bfa; margin-bottom:6px; }
.seller-card .sc-name  { font-size:1.05rem; font-weight:600; color:#ddd6fe; line-height:1.4; }
.seller-card .sc-price { font-size:1.8rem; font-weight:800; color:#c4b5fd; font-family:var(--mono); margin:6px 0; }
.seller-card .sc-meta  { font-size:0.82rem; color:#9070b8; margin-top:6px; }

.amz-btn {
    display:inline-flex; align-items:center; gap:6px;
    background:#f59e0b; color:#000 !important;
    font-weight:700; font-size:0.78rem;
    padding:7px 16px; border-radius:7px;
    text-decoration:none !important; margin-top:14px;
}
.amz-btn:hover { background:#fbbf24; }

.form-section {
    background: var(--bg2); border:1px solid var(--border);
    border-radius:14px; padding:22px 24px 18px; margin-bottom:16px;
}
.form-section .fs-title {
    font-size:0.7rem; font-weight:700; letter-spacing:0.1em;
    text-transform:uppercase; color:var(--text3);
    margin-bottom:16px; padding-bottom:10px; border-bottom:1px solid var(--border);
}

.stat-box {
    background:var(--bg3); border:1px solid var(--border);
    border-radius:10px; padding:16px 20px; text-align:center;
}
.stat-box .sb-val   { font-size:1.8rem; font-weight:800; color:#60a5fa; font-family:var(--mono); }
.stat-box .sb-label { font-size:0.75rem; color:var(--text3); margin-top:3px; }

.step-card {
    background:var(--bg2); border:1px solid var(--border);
    border-radius:12px; padding:22px; height:100%;
}
.step-card .step-num {
    width:32px; height:32px; border-radius:8px;
    background:rgba(59,130,246,0.15); border:1px solid rgba(59,130,246,0.3);
    color:#60a5fa; font-weight:700; font-size:0.9rem;
    display:flex; align-items:center; justify-content:center; margin-bottom:12px;
}
.step-card .step-title { font-weight:700; color:var(--text); margin-bottom:6px; }
.step-card .step-desc  { font-size:0.83rem; color:var(--text3); line-height:1.55; }

.about-block {
    background:var(--bg2); border:1px solid var(--border);
    border-radius:12px; padding:24px; margin-bottom:14px;
}
.about-block h4 { color:#60a5fa; margin:0 0 10px 0; font-size:1rem; }
.about-block p, .about-block li { font-size:0.88rem; color:#94a3b8; line-height:1.65; }
.about-block pre { margin:10px 0; }
.about-block code {
    background:#0d1424; border:1px solid #1e2d45; border-radius:4px;
    padding:2px 6px; font-size:0.82rem; color:#60a5fa;
}

.env-ok   { background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25); border-radius:8px; padding:10px 14px; font-size:0.79rem; color:#34d399; margin-bottom:8px; }
.env-warn { background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.25); border-radius:8px; padding:10px 14px; font-size:0.79rem; color:#fcd34d; margin-bottom:8px; }

.stTabs [data-baseweb="tab-list"] {
    gap:4px; background:var(--bg3) !important;
    border-radius:10px; padding:4px; border:1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    border-radius:7px !important; padding:8px 18px !important;
    font-weight:600 !important; font-size:0.84rem !important;
    color:var(--text3) !important; background:transparent !important;
}
.stTabs [aria-selected="true"] {
    background:rgba(59,130,246,0.2) !important; color:#60a5fa !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top:20px !important; }

.stButton > button { font-family:var(--sans) !important; font-weight:600 !important; border-radius:8px !important; }
.stDataFrame { border-radius:10px !important; overflow:hidden !important; }
#MainMenu { visibility:hidden; }
footer    { visibility:hidden; }
header    { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  CONSTANTS & HELPERS
# ══════════════════════════════════════════════════════════════════

MEDAL = {1:"🥇", 2:"🥈", 3:"🥉"}
BRAND_FLAG = {
    "samsung":"🇰🇷","apple":"🍎","oneplus":"1️⃣","google":"🔍","nothing":"⭕",
    "motorola":"〽️","poco":"⚡","redmi":"🔴","realme":"🟢","vivo":"🟦",
    "oppo":"🔵","iqoo":"🎮","nokia":"📡","infinix":"♾️","tecno":"🌐",
}
ALL_BRANDS = [
    "Any Brand","Samsung","Apple","OnePlus","Google","Nothing",
    "Motorola","Poco","Redmi","Realme","Vivo","Oppo","iQOO","Nokia",
]

def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def _apply_extra_filters(phones: list, req: dict) -> list:
    import re
    out = []
    for p in phones:
        n = p["name"].lower()
        if req.get("require_5g") and "5g" not in n:
            continue
        if req.get("brand") and req["brand"].lower() not in n:
            continue
        ram_m = re.search(r"(\d+)\s*gb\s*ram", n)
        if req.get("min_ram", 0) > 0 and ram_m and int(ram_m.group(1)) < req["min_ram"]:
            continue
        out.append(p)
    return out

def _fix_alternatives(rec: dict, all_phones: list) -> dict:
    """Ensure alternatives are unique and different from best pick."""
    best_name = (rec.get("best_phone") or "").lower().strip()
    alts = rec.get("alternatives", [])
    used  = {best_name}
    fixed = []
    for alt in alts:
        key = (alt.get("name") or "").lower().strip()
        if key and key not in used:
            fixed.append(alt)
            used.add(key)
    # Fill from ranked pool
    for i, phone in enumerate(all_phones):
        if len(fixed) >= 2:
            break
        key = phone["name"].lower().strip()
        if key not in used:
            fixed.append({
                "name":   phone["name"],
                "price":  phone["price"],
                "reason": (
                    f"Ranked #{i+1} overall — {phone.get('rating',0):.1f}★ rating "
                    f"across {phone.get('reviews',0):,} reviews. "
                    f"Score: {phone.get('score',0):.3f}."
                ),
            })
            used.add(key)
    rec["alternatives"] = fixed[:2]
    return rec

def _reorder_by_ai_pick(phones: list, rec: dict) -> list:
    """
    Reorder the phone list so the AI best pick is always #1,
    its alternatives are #2 and #3, and the rest follow by score.
    """
    best_name = (rec.get("best_phone") or "").lower().strip()
    alt_names = [
        (a.get("name") or "").lower().strip()
        for a in rec.get("alternatives", [])
    ]

    pinned_best = []
    pinned_alts = []
    rest        = []

    for p in phones:
        key = p["name"].lower().strip()
        if key == best_name:
            pinned_best.append(p)
        elif key in alt_names:
            pinned_alts.append(p)
        else:
            rest.append(p)

    # Sort alternatives to match the order in rec["alternatives"]
    pinned_alts.sort(key=lambda p: alt_names.index(p["name"].lower().strip())
                     if p["name"].lower().strip() in alt_names else 99)

    return pinned_best + pinned_alts + rest


def _detect_best_seller(phones: list, exclude_name: str = "") -> dict | None:
    """Phone with most reviews, excluding the AI best pick if it dominates."""
    if not phones:
        return None
    candidates = phones[:min(10, len(phones))]
    # prefer a phone that isn't the AI pick for a distinct recommendation
    others = [p for p in candidates if p["name"].lower().strip() != exclude_name.lower().strip()]
    pool = others if others else candidates
    return max(pool, key=lambda p: p.get("reviews", 0))

def _amz_btn(url: str) -> str:
    if not url:
        return ""
    return f'<a href="{url}" target="_blank" class="amz-btn">🛒 View on Amazon</a>'

def _badge(text: str, style: str = "gray") -> str:
    return f'<span class="badge badge-{style}">{text}</span>'

def _init_state():
    for k, v in {
        "page": "home", "searching": False, "search_done": False,
        "all_phones": [], "filtered_phones": [], "recommendation": {},
        "search_params": {},
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ══════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="padding:20px 4px 10px">
        <div style="font-size:1.6rem">📱</div>
        <div style="font-size:1rem;font-weight:700;color:#e2e8f0">Smartphone Bot</div>
        <div style="font-size:0.7rem;color:#475569;margin-top:2px">Amazon India Intelligence</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    for pid, icon, label in [
        ("home","🏠","Home"), ("bot","🤖","Run Bot"),
        ("results","📊","Results"), ("about","ℹ️","About"),
    ]:
        if st.button(f"{icon}  {label}", key=f"nav_{pid}",
                     use_container_width=True,
                     type="primary" if st.session_state["page"]==pid else "secondary"):
            st.session_state["page"] = pid
            st.rerun()

    st.markdown("---")
    # API key status
    st.markdown('<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#475569;margin-bottom:8px">API Status</div>', unsafe_allow_html=True)
    if OPENAI_KEY:
        st.markdown('<div class="env-ok">✅ OpenAI key loaded</div>', unsafe_allow_html=True)
    elif ANTHROPIC_KEY:
        st.markdown('<div class="env-ok">✅ Anthropic key loaded</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="env-warn">⚠️ No .env key found<br>Using rule-based fallback</div>', unsafe_allow_html=True)

    if st.session_state.get("search_done"):
        st.markdown("---")
        rec = st.session_state["recommendation"]
        fp  = st.session_state["filtered_phones"]
        ap  = st.session_state["all_phones"]
        st.markdown('<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#475569;margin-bottom:8px">Last Run</div>', unsafe_allow_html=True)
        bp = rec.get("best_phone","—")
        st.markdown(f'<div style="font-size:0.77rem;color:#475569;line-height:1.9">🏆 {bp[:32]}…<br>💰 ₹{rec.get("price",0):,}<br>📊 {len(fp)} matched / {len(ap)} pool</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  PAGE: HOME
# ══════════════════════════════════════════════════════════════════
if st.session_state["page"] == "home":
    st.markdown("""
    <div style="padding:50px 0 30px;text-align:center">
        <div style="font-size:3.2rem;font-weight:800;color:#fff;letter-spacing:-0.03em;margin-bottom:12px">
            Find Your Perfect <span style="color:#60a5fa">Smartphone</span>
        </div>
        <div style="font-size:1rem;color:#64748b;max-width:540px;margin:0 auto 30px;line-height:1.7">
            Live Amazon India scraping · AI-powered ranking · Intelligent recommendations —
            all automated for the Indian market.
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    for col,icon,title,desc in [
        (c1,"🌐","Live Scraping","Playwright scrapes Amazon India in real-time with anti-bot stealth."),
        (c2,"🔍","Smart Filtering","Removes accessories, fakes, and out-of-stock listings automatically."),
        (c3,"🏆","AI Ranking","GPT-4o-mini or Claude ranks by value, rating & brand quality."),
        (c4,"🔥","Best Seller","Highlights the crowd favourite separately from the AI pick."),
    ]:
        with col:
            st.markdown(f'<div class="step-card"><div class="step-num">{icon}</div><div class="step-title">{title}</div><div class="step-desc">{desc}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    ap  = st.session_state.get("all_phones",[])
    fp  = st.session_state.get("filtered_phones",[])
    rec = st.session_state.get("recommendation",{})

    s1,s2,s3,s4,s5 = st.columns(5)
    for col,val,label in [
        (s1, len(ap) if ap else "—", "Base Pool"),
        (s2, len(fp) if fp else "—", "Matched Filters"),
        (s3, f"₹{rec.get('price',0):,}" if rec.get('price') else "—", "AI Best Price"),
        (s4, sum(1 for p in ap if p.get("has_5g")) if ap else "—", "5G Phones"),
        (s5, f"{sum(p.get('reviews',0) for p in ap)//max(len(ap),1):,}" if ap else "—", "Avg Reviews"),
    ]:
        with col:
            st.markdown(f'<div class="stat-box"><div class="sb-val">{val}</div><div class="sb-label">{label}</div></div>', unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    _,cta,_ = st.columns([1,2,1])
    with cta:
        if st.button("🤖  Launch the Bot →", type="primary", use_container_width=True):
            st.session_state["page"] = "bot"
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  PAGE: RUN BOT
# ══════════════════════════════════════════════════════════════════
elif st.session_state["page"] == "bot":

    # ── SEARCHING: hide form, show live progress ──────────────────────────────
    if st.session_state["searching"]:
        st.markdown("## ⏳ Bot Running…")
        st.markdown('<div style="color:#64748b;font-size:0.87rem;margin-bottom:24px">Scraping Amazon India live. This takes 60–120 seconds. Do not close this tab.</div>', unsafe_allow_html=True)

        prog    = st.progress(0, text="Initialising…")
        status  = st.empty()
        log_exp = st.expander("🔧 Live Logs", expanded=True)
        log_box = log_exp.empty()
        logs: list[str] = []

        def _log(msg: str, pct: int, detail: str = ""):
            ts = datetime.now().strftime("%H:%M:%S")
            logs.append(f"[{ts}] {detail or msg}")
            log_box.code("\n".join(logs[-50:]), language=None)
            prog.progress(pct, text=msg)
            status.info(f"⏳ {msg}")

        sp = st.session_state["search_params"]
        budget       = sp["budget"]
        min_rating   = sp["min_rating"]
        min_reviews  = sp["min_reviews"]
        max_pages    = sp["max_pages"]
        headless     = sp["headless"]
        require_5g   = sp["require_5g"]
        brand_filter = sp["brand_filter"]
        min_ram      = sp["min_ram"]
        dry_run      = sp["dry_run"]
        query        = sp.get("query") or f"smartphones under {budget}"

        try:
            _log("Loading project modules…", 5, "Importing scraper / processor / recommender")
            from scraper     import scrape_amazon
            from processor   import process, phones_to_dicts
            from recommender import get_recommendation

            if dry_run:
                _log("🔁 Dry run — loading cached data…", 20)
                cache = Path("data/dry_run.json")
                raw_items = json.loads(cache.read_text()) if cache.exists() else []
            else:
                _log(f"🌐 Launching browser — '{query}' ({max_pages} pages)…", 15,
                     f"headless={headless}")
                raw_items = _run_async(
                    scrape_amazon(query=query, max_pages=max_pages, headless=headless)
                )

            _log(f"✅ Got {len(raw_items)} raw listings", 38)
            if not raw_items:
                st.error("❌ Scraping returned no results. Try more pages or disable brand/5G filter.")
                st.session_state["searching"] = False
                st.rerun()

            # Stage 1: base filter (budget+rating+reviews — NO brand/5G/RAM)
            _log("🔍 Stage 1 — base filtering…", 48,
                 f"Budget=₹{budget:,} | Rating≥{min_rating} | Reviews≥{min_reviews}")
            phones = process(raw_items, budget=budget, min_rating=min_rating, min_reviews=min_reviews)
            all_phones = phones_to_dicts(phones)
            _log(f"✅ Stage 1 pool: {len(all_phones)} phones", 56)

            # Stage 2: extra filters (5G / brand / RAM)
            extra = {"require_5g": require_5g, "brand": brand_filter, "min_ram": min_ram}
            filtered_phones = _apply_extra_filters(all_phones, extra)
            _log(f"✅ Stage 2 filtered: {len(filtered_phones)} phones", 64,
                 f"5G={require_5g} | brand={brand_filter} | RAM≥{min_ram}GB")

            if not all_phones:
                st.warning("⚠️ No phones passed base filters. Try lowering Min Rating / Min Reviews.")
                st.session_state["searching"] = False
                st.rerun()

            # AI always receives the fuller pool for variety
            ai_pool = all_phones if len(filtered_phones) < 3 else filtered_phones
            _log(f"🤖 Getting AI recommendation from pool of {len(ai_pool)}…", 75)
            rec = get_recommendation(
                ai_pool, budget,
                openai_api_key=OPENAI_KEY or None,
                anthropic_api_key=ANTHROPIC_KEY or None,
            )
            # Fix duplicate alternatives
            rec = _fix_alternatives(rec, all_phones)
            _log(f"✅ Best: {rec.get('best_phone','')[:45]}", 92)

            # Reorder: AI best pick → alternatives → rest (both pools)
            all_phones      = _reorder_by_ai_pick(all_phones, rec)
            disp_pool       = filtered_phones if filtered_phones else all_phones
            filtered_phones = _reorder_by_ai_pick(disp_pool, rec)

            st.session_state["all_phones"]      = all_phones
            st.session_state["filtered_phones"] = filtered_phones
            st.session_state["recommendation"]  = rec
            st.session_state["search_done"]     = True
            st.session_state["searching"]       = False

            prog.progress(100, text="Done!")
            status.success(f"✅ {len(filtered_phones) or len(all_phones)} phones found — best pick: {rec.get('best_phone','')[:50]}")
            time.sleep(1.2)
            st.session_state["page"] = "results"
            st.rerun()

        except ImportError as exc:
            st.error(f"❌ Missing module: {exc}\nEnsure scraper.py / processor.py / recommender.py are in the same folder.")
            st.session_state["searching"] = False
        except Exception as exc:
            st.error(f"❌ Pipeline error: {exc}")
            st.exception(exc)
            st.session_state["searching"] = False

    # ── FORM: search config ───────────────────────────────────────────────────
    else:
        st.markdown("## 🤖 Configure & Run Bot")
        st.markdown('<div style="color:#64748b;font-size:0.87rem;margin-bottom:28px">Set your search parameters below. The form hides once the bot launches and you\'ll see live logs instead.</div>', unsafe_allow_html=True)

        # ── Budget & Query ─────────────────────────────────────────────────────
        st.markdown('<div class="form-section"><div class="fs-title">💰 Budget & Search Query</div></div>', unsafe_allow_html=True)
        with st.container():
            cb1, cb2 = st.columns([3,2])
            with cb1:
                budget = st.slider("Max Budget (INR)", 5_000, 1_50_000, 30_000, 1_000, format="₹%d")
                st.markdown(f'{_badge(f"₹{budget:,} budget","gold")}', unsafe_allow_html=True)
            with cb2:
                custom_query = st.text_input("Custom Search Query (optional)", placeholder=f"smartphones under {budget}")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Quality Filters ────────────────────────────────────────────────────
        st.markdown('<div class="form-section"><div class="fs-title">⭐ Quality Filters</div></div>', unsafe_allow_html=True)
        with st.container():
            qc1,qc2,qc3 = st.columns(3)
            with qc1:
                min_rating = st.slider("Min Star Rating", 1.0, 5.0, 3.8, 0.1)
                st.markdown(f'{_badge(f"⭐ ≥ {min_rating}","gray")}', unsafe_allow_html=True)
            with qc2:
                min_reviews = st.number_input("Min Reviews Count", 0, 100000, 50, 10)
                st.markdown(f'{_badge(f"📝 ≥ {min_reviews} reviews","gray")}', unsafe_allow_html=True)
            with qc3:
                max_pages = st.select_slider("Pages to Scrape", options=[1,2,3,4,5], value=3)
                st.markdown(f'{_badge(f"📄 {max_pages} pages","gray")}', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Optional Feature Filters ───────────────────────────────────────────
        st.markdown('<div class="form-section"><div class="fs-title">🔧 Optional Feature Filters</div></div>', unsafe_allow_html=True)
        with st.container():
            fc1,fc2,fc3 = st.columns(3)
            with fc1:
                require_5g = st.toggle("📶 5G Phones Only", value=False,
                                       help="OFF = show all phones (4G + 5G). ON = 5G only.")
                st.markdown(
                    f'{_badge("📶 5G + 4G shown","gray") if not require_5g else _badge("📶 5G only","green")}',
                    unsafe_allow_html=True,
                )
            with fc2:
                min_ram = st.select_slider("🧠 Min RAM (GB)", options=[0,2,4,6,8,12,16], value=0,
                                           help="0 = no RAM filter")
                st.markdown(
                    f'{_badge("No RAM filter","gray") if min_ram==0 else _badge(f"{min_ram}GB+ RAM","blue")}',
                    unsafe_allow_html=True,
                )
            with fc3:
                brand_choice = st.selectbox("🏷️ Brand", ALL_BRANDS)
                brand_filter = None if brand_choice=="Any Brand" else brand_choice.lower()
                st.markdown(
                    f'{_badge("All brands","gray") if not brand_filter else _badge(brand_choice,"blue")}',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Advanced ───────────────────────────────────────────────────────────
        with st.expander("⚙️ Advanced Settings"):
            adv1,adv2 = st.columns(2)
            with adv1:
                headless = not st.toggle("🖥️ Show Browser Window", False)
                dry_run  = st.toggle("🔁 Dry Run (cached data)", False)
            with adv2:
                st.markdown('<div style="font-size:0.82rem;color:#64748b;line-height:1.7;padding-top:8px"><b style="color:#94a3b8">Headless:</b> invisible browser (faster).<br><b style="color:#94a3b8">Dry Run:</b> skip scraping, use data/dry_run.json.</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Active filter summary
        active = [f"₹{budget:,}",f"⭐≥{min_rating}",f"📝≥{min_reviews}",f"{max_pages}p"]
        if require_5g:   active.append("📶5G")
        if min_ram>0:    active.append(f"🧠{min_ram}GB")
        if brand_filter: active.append(f"🏷️{brand_choice}")
        st.markdown("**Active:** " + " ".join(f'<span class="badge badge-gray">{a}</span>' for a in active), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if not OPENAI_KEY and not ANTHROPIC_KEY:
            st.warning("⚠️ No API key in .env — rule-based fallback will be used. Create a `.env` file with `OPENAI_API_KEY=sk-...`")

        col_run, col_clr = st.columns([2,1])
        with col_run:
            run_clicked = st.button("🚀  Launch Search", type="primary", use_container_width=True)
        with col_clr:
            if st.button("🗑️  Clear Results", use_container_width=True):
                for k in ["all_phones","filtered_phones","recommendation"]:
                    st.session_state[k] = []
                st.session_state["recommendation"] = {}
                st.session_state["search_done"] = False
                st.toast("Cleared", icon="🗑️"); st.rerun()

        if run_clicked:
            st.session_state["search_params"] = {
                "budget": budget, "min_rating": min_rating, "min_reviews": min_reviews,
                "max_pages": max_pages, "headless": headless, "require_5g": require_5g,
                "brand_filter": brand_filter, "min_ram": min_ram,
                "dry_run": dry_run, "query": custom_query.strip() or None,
            }
            st.session_state["searching"] = True
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  PAGE: RESULTS
# ══════════════════════════════════════════════════════════════════
elif st.session_state["page"] == "results":
    if not st.session_state.get("search_done"):
        st.info("No results yet. Run the bot first.")
        if st.button("🤖 Go to Run Bot"):
            st.session_state["page"] = "bot"; st.rerun()
    else:
        all_phones      = st.session_state["all_phones"]
        filtered_phones = st.session_state["filtered_phones"]
        rec             = st.session_state["recommendation"]
        sp              = st.session_state["search_params"]
        budget          = sp.get("budget", 30_000)

        display   = filtered_phones if filtered_phones else all_phones
        best_name = rec.get("best_phone", "")
        best_seller = _detect_best_seller(display, exclude_name=best_name)

        # Header
        ch, cr = st.columns([5,1])
        with ch:
            st.markdown(f"## 📊 Results — ₹{budget:,}")
            st.markdown(f'<div style="font-size:0.84rem;color:#64748b">'
                        f'{len(all_phones)} phones in base pool · {len(display)} matched your filters'
                        f'</div>', unsafe_allow_html=True)
        with cr:
            if st.button("🔄 Search Again", use_container_width=True):
                st.session_state["page"] = "bot"; st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Quick stats
        qs1,qs2,qs3,qs4 = st.columns(4)
        for col,val,label in [
            (qs1, len(display), "Phones Found"),
            (qs2, sum(1 for p in display if p.get("has_5g")), "5G Phones"),
            (qs3, f"₹{min((p.get('price',0) for p in display),default=0):,}", "Cheapest"),
            (qs4, f"{sum(p.get('rating',0) for p in display)/max(len(display),1):.1f}⭐", "Avg Rating"),
        ]:
            with col:
                st.markdown(f'<div class="stat-box"><div class="sb-val">{val}</div><div class="sb-label">{label}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs([
            "🏆  Best Pick & Alternatives",
            "📋  All Phones Table",
            "🔥  Best Seller",
            "💾  Export",
        ])

        # ── TAB 1: BEST PICK ──────────────────────────────────────────────────
        with tab1:
            bp_price  = rec.get("price", 0)
            bp_reason = rec.get("reason","")
            bp_data   = next((p for p in all_phones if p["name"]==best_name), {})
            bp_url    = bp_data.get("url","")

            badges = []
            if bp_data.get("has_5g"):  badges.append(("📶 5G Ready","green"))
            if bp_data.get("rating"):  badges.append((f"⭐ {bp_data['rating']:.1f}","gold"))
            if bp_data.get("reviews"): badges.append((f"📝 {bp_data['reviews']:,} reviews","gray"))
            br = BRAND_FLAG.get(bp_data.get("brand",""),"📱")
            badges.append((f"{br} {(bp_data.get('brand') or 'Unknown').capitalize()}","gray"))
            if bp_data.get("score"):   badges.append((f"Score {bp_data['score']:.3f}","blue"))
            badge_html = "".join(f'<span class="badge badge-{s}">{t}</span>' for t,s in badges)

            st.markdown(f"""
            <div class="best-card">
                <div class="bc-label">🥇 AI Best Pick</div>
                <div class="bc-name">{best_name}</div>
                <div class="bc-price">₹{bp_price:,}</div>
                <div style="margin-top:12px">{badge_html}</div>
                <div class="bc-reason">{bp_reason}</div>
                {_amz_btn(bp_url)}
            </div>
            """, unsafe_allow_html=True)

            alts = rec.get("alternatives",[])
            if alts:
                st.markdown("<br>**🥈 AI Alternatives**", unsafe_allow_html=False)
                acols = st.columns(max(len(alts),1))
                for i,(col,alt) in enumerate(zip(acols,alts)):
                    with col:
                        ad   = next((p for p in all_phones if p["name"]==alt.get("name","")),{})
                        aurl = ad.get("url","")
                        a5g  = "📶" if ad.get("has_5g") else ""
                        arat = f"⭐{ad.get('rating',0):.1f}" if ad.get("rating") else ""
                        st.markdown(f"""
                        <div class="alt-card">
                            <div class="ac-medal">{"🥈" if i==0 else "🥉"}</div>
                            <div class="ac-name">{alt.get("name","")}</div>
                            <div class="ac-price">₹{alt.get("price",0):,}</div>
                            <div style="margin:4px 0">
                                {_badge(f"{a5g} {arat}".strip(),"gray")}
                            </div>
                            <div class="ac-reason">{alt.get("reason","")}</div>
                            {_amz_btn(aurl)}
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No distinct alternatives found — try removing brand/5G filters or increasing pages.")

        # ── TAB 2: ALL PHONES TABLE ───────────────────────────────────────────
        with tab2:
            tc1,tc2 = st.columns([3,1])
            with tc1:
                st.markdown(f"**{len(display)} phones matched your filters** (from {len(all_phones)} in base pool)")
            with tc2:
                show_all = st.toggle("Show base pool", value=False,
                                     help="Toggle to see all phones before brand/5G/RAM filters")

            pool = all_phones if show_all else display

            # caption explaining the ordering
            st.caption(
                "📌 Table is ordered by AI recommendation — best pick first, "
                "then alternatives, then remaining phones by score."
            )

            if not pool:
                st.warning("No phones. Try relaxing your filters in Run Bot.")
            else:
                alt_names_lower = [
                    (a.get("name") or "").lower().strip()
                    for a in rec.get("alternatives", [])
                ]

                rows = []
                for i, p in enumerate(pool, 1):
                    pkey = p["name"].lower().strip()
                    is_best   = pkey == best_name.lower().strip()
                    is_alt    = pkey in alt_names_lower
                    is_seller = best_seller and p["name"] == best_seller["name"] and not is_best

                    # Rank label — pin emoji for AI-chosen top 3
                    if is_best:
                        rank_label = "🥇 #1  📌"
                    elif is_alt:
                        alt_idx = alt_names_lower.index(pkey)
                        rank_label = f"{'🥈' if alt_idx==0 else '🥉'} #{i}  📌"
                    else:
                        rank_label = f"{MEDAL.get(i, str(i))} #{i}"

                    # Tag column
                    tag = ""
                    if is_best:                 tag = "⭐ AI Pick"
                    elif is_alt:                tag = "🤖 AI Alt"
                    elif is_seller:             tag = "🔥 Best Seller"

                    rows.append({
                        "Rank":    rank_label,
                        "Name":    p["name"],
                        "Price":   p.get("price", 0),
                        "Rating":  p.get("rating") or 0.0,
                        "Reviews": p.get("reviews", 0),
                        "5G":      p.get("has_5g", False),
                        "Brand":   (p.get("brand") or "?").capitalize(),
                        "Score":   round(p.get("score", 0), 4),
                        "Tag":     tag,
                        "In Pool": p in display,
                    })

                df = pd.DataFrame(rows)
                cols_show = ["Rank","Name","Price","Rating","Reviews","5G","Brand","Score","Tag"]
                if show_all: cols_show.append("In Pool")

                max_score = float(df["Score"].max()) if len(df)>0 else 1.0

                st.dataframe(
                    df[cols_show],
                    use_container_width=True,
                    height=min(60+40*len(rows), 660),
                    column_config={
                        "Rank":    st.column_config.TextColumn("Rank", width=75),
                        "Name":    st.column_config.TextColumn("Phone Name", width=290),
                        "Price":   st.column_config.NumberColumn("Price ₹", format="₹%d", width=110),
                        "Rating":  st.column_config.NumberColumn("Rating", format="%.1f ⭐", width=90),
                        "Reviews": st.column_config.NumberColumn("Reviews", format="%d", width=100),
                        "5G":      st.column_config.CheckboxColumn("5G", width=55),
                        "Brand":   st.column_config.TextColumn("Brand", width=100),
                        "Score":   st.column_config.ProgressColumn("Score", format="%.4f",
                                       min_value=0, max_value=max_score, width=140),
                        "Tag":     st.column_config.TextColumn("Highlight", width=110),
                        "In Pool": st.column_config.CheckboxColumn("Passes Filter", width=110),
                    },
                    hide_index=True,
                )

                st.markdown("<br>**🔎 Expandable Detail Cards**")
                for i,p in enumerate(pool[:20],1):
                    tag = ""
                    if p["name"]==best_name: tag=" ⭐ **AI Best Pick**"
                    elif best_seller and p["name"]==best_seller["name"]: tag=" 🔥 **Best Seller**"
                    with st.expander(f"{MEDAL.get(i,str(i))} **{p['name'][:60]}** — ₹{p.get('price',0):,}{tag}"):
                        m1,m2,m3,m4 = st.columns(4)
                        m1.metric("Price",   f"₹{p.get('price',0):,}")
                        m2.metric("Rating",  f"⭐ {p.get('rating',0):.1f}")
                        m3.metric("Reviews", f"{p.get('reviews',0):,}")
                        m4.metric("Score",   f"{p.get('score',0):.4f}")
                        d1,d2 = st.columns(2)
                        with d1:
                            bf = BRAND_FLAG.get(p.get("brand",""),"📱")
                            st.markdown(f"**Brand:** {bf} {(p.get('brand') or '?').capitalize()}")
                            st.markdown(f"**5G:** {'✅ Yes' if p.get('has_5g') else '❌ No'}")
                            st.markdown(f"**In Stock:** {'✅' if p.get('in_stock') else '❌'}")
                        with d2:
                            if p.get("url"):
                                st.markdown(f"[🛒 Open on Amazon]({p['url']})")

        # ── TAB 3: BEST SELLER ────────────────────────────────────────────────
        with tab3:
            if best_seller:
                bs = best_seller
                is_same = bs["name"]==best_name
                if is_same:
                    st.info("ℹ️ The crowd favourite matches the AI pick this run. Increase pages scraped to discover more variety.", icon="ℹ️")
                sf = BRAND_FLAG.get(bs.get("brand",""),"📱")
                st.markdown(f"""
                <div class="seller-card">
                    <div class="sc-label">🔥 Crowd Favourite / Best Seller</div>
                    <div class="sc-name">{bs["name"]}</div>
                    <div class="sc-price">₹{bs.get("price",0):,}</div>
                    <div class="sc-meta">
                        {sf} {(bs.get("brand") or "Unknown").capitalize()} &nbsp;·&nbsp;
                        ⭐ {bs.get("rating") or "N/A"} &nbsp;·&nbsp;
                        📝 <b>{bs.get("reviews",0):,} reviews</b> &nbsp;·&nbsp;
                        Score {bs.get("score",0):.4f}
                    </div>
                    {_amz_btn(bs.get("url",""))}
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("""
                <div class="about-block">
                    <h4>Why this phone?</h4>
                    <p>Identified by the highest review count among the top 5 ranked phones.
                    Many reviews mean real buyers have owned it long enough to form opinions —
                    it's the battle-tested, proven choice alongside the AI's analytical pick.</p>
                </div>
                """, unsafe_allow_html=True)

                if not is_same and bp_data:
                    st.markdown("#### 🆚 AI Pick vs Crowd Favourite")
                    vl, vr = st.columns(2)
                    for vcol, ph, label in [(vl, bp_data,"🥇 AI Best Pick"),(vr, bs,"🔥 Crowd Favourite")]:
                        with vcol:
                            st.markdown(f"**{label}**")
                            a,b = st.columns(2)
                            a.metric("Price",   f"₹{ph.get('price',0):,}")
                            b.metric("Rating",  f"⭐ {ph.get('rating',0):.1f}")
                            c,d = st.columns(2)
                            c.metric("Reviews", f"{ph.get('reviews',0):,}")
                            d.metric("Score",   f"{ph.get('score',0):.4f}")
            else:
                st.info("Not enough phones for a best seller comparison. Increase pages scraped.")

        # ── TAB 4: EXPORT ─────────────────────────────────────────────────────
        with tab4:
            st.markdown("#### 💾 Download Results")
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            e1,e2,e3 = st.columns(3)
            with e1:
                st.download_button("📥 All Phones JSON", json.dumps(all_phones,indent=2,ensure_ascii=False),
                    f"phones_{budget}_{ts}.json","application/json", use_container_width=True)
                st.caption(f"{len(all_phones)} phones")
            with e2:
                st.download_button("📥 All Phones CSV", pd.DataFrame(all_phones).to_csv(index=False),
                    f"phones_{budget}_{ts}.csv","text/csv", use_container_width=True)
                st.caption("Spreadsheet-ready")
            with e3:
                st.download_button("📥 Recommendation JSON", json.dumps(rec,indent=2,ensure_ascii=False),
                    f"rec_{budget}_{ts}.json","application/json", use_container_width=True)
                st.caption("AI pick + alternatives")
            st.markdown("<br>**👁️ JSON Preview**")
            pv1,pv2 = st.tabs(["Recommendation","Top 5 Phones"])
            with pv1: st.json(rec)
            with pv2: st.json(all_phones[:5])


# ══════════════════════════════════════════════════════════════════
#  PAGE: ABOUT
# ══════════════════════════════════════════════════════════════════
elif st.session_state["page"] == "about":
    st.markdown("## ℹ️ About & Setup")
    ab1,ab2 = st.columns(2)
    with ab1:
        st.markdown("""
        <div class="about-block">
            <h4>🔑 API Key Setup — .env file</h4>
            <p>Create a file named <code>.env</code> in the same folder:</p>
            <pre style="background:#0d1424;border:1px solid #1e2d45;border-radius:6px;padding:12px;font-size:0.82rem;color:#60a5fa">OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...  # optional</pre>
            <p>Never put API keys in the UI — they would appear in browser history and logs.
            The sidebar shows a green badge when keys load correctly from .env.</p>
        </div>
        <div class="about-block">
            <h4>📁 Required Files</h4>
            <ul>
                <li><code>streamlit_app.py</code> — this UI</li>
                <li><code>scraper.py</code> — Playwright Amazon scraper</li>
                <li><code>processor.py</code> — filtering + ranking engine</li>
                <li><code>recommender.py</code> — AI recommendation layer</li>
                <li><code>.env</code> — API keys (never commit to git)</li>
            </ul>
            <b style="color:#94a3b8">Removed (no longer needed):</b>
            <ul>
                <li><s>api.py</s> — replaced by Streamlit</li>
                <li><s>client.py</s> — replaced by Streamlit</li>
                <li><s>scheduler.py</s> — use system cron if needed</li>
                <li><s>main.py</s> — replaced by Streamlit</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with ab2:
        st.markdown("""
        <div class="about-block">
            <h4>🚀 Installation</h4>
            <pre style="background:#0d1424;border:1px solid #1e2d45;border-radius:6px;padding:12px;font-size:0.82rem;color:#60a5fa">pip install -r requirements.txt
playwright install chromium
streamlit run streamlit_app.py</pre>
        </div>
        <div class="about-block">
            <h4>🔍 Why Few Results?</h4>
            <p>Results go through two filter stages:</p>
            <ul>
                <li><b>Stage 1 (Base):</b> Budget + Min Rating + Min Reviews</li>
                <li><b>Stage 2 (Extra):</b> 5G / Brand / Min RAM</li>
            </ul>
            <p>If Stage 2 leaves &lt;3 phones, the AI still uses the Stage 1 pool
            for recommendations so alternatives are always different phones.</p>
            <p>In the <b>All Phones Table</b> tab, toggle <b>"Show base pool"</b>
            to see all Stage 1 phones before extra filters.</p>
        </div>
        <div class="about-block">
            <h4>🧮 Scoring Formula</h4>
            <p><code>score = (rating × log₁₀(reviews+1)) × brand_mult × value_mult + kw_bonus</code></p>
            <ul>
                <li>Apple 1.3× · Google/Samsung 1.2× · OnePlus 1.15× · iQOO 1.1×</li>
                <li>+5% for phones under 70% of budget</li>
                <li>+0.05 each: 5G, AMOLED, Snapdragon, Dimensity…</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
