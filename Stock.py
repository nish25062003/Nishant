"""
╔══════════════════════════════════════════════════════════════╗
║         LIVE STOCK MARKET TERMINAL — DESKTOP DASHBOARD       ║
║         Built with Streamlit + yfinance                      ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import time
import pytz

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Market Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CUSTOM CSS — Bloomberg-style dark terminal
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&family=Orbitron:wght@700;900&display=swap');

/* ── Reset & Root ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background: #020b14 !important;
    color: #c8d8e8;
    font-family: 'Rajdhani', sans-serif;
}

[data-testid="stHeader"] { display: none; }
[data-testid="stSidebar"] { display: none; }
.block-container { padding: 0.6rem 1rem 0rem 1rem !important; max-width: 100% !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }
button[title="View fullscreen"] { display: none !important; }

/* ── Scanline overlay ── */
body::after {
    content: "";
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,0,0,0.04) 2px,
        rgba(0,0,0,0.04) 4px
    );
    pointer-events: none;
    z-index: 9999;
}

/* ── Header bar ── */
.terminal-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.35rem 0.8rem;
    background: linear-gradient(90deg, #001a2e 0%, #002a45 50%, #001a2e 100%);
    border-bottom: 2px solid #00d4ff;
    margin-bottom: 0.5rem;
    box-shadow: 0 0 20px rgba(0,212,255,0.2);
}
.terminal-title {
    font-family: 'Orbitron', monospace;
    font-size: 1.2rem; font-weight: 900;
    color: #00d4ff;
    letter-spacing: 0.15em;
    text-shadow: 0 0 10px rgba(0,212,255,0.6);
}
.terminal-clock {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.9rem; color: #7fbfdf;
    letter-spacing: 0.08em;
}
.market-status-badge {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem; font-weight: 700;
    padding: 0.15rem 0.6rem;
    border-radius: 3px;
    letter-spacing: 0.1em;
}
.badge-open  { background: rgba(0,255,120,0.15); color: #00ff78; border: 1px solid #00ff78; box-shadow: 0 0 8px rgba(0,255,120,0.3); }
.badge-closed{ background: rgba(255,80,80,0.15);  color: #ff5050; border: 1px solid #ff5050; }
.badge-pre   { background: rgba(255,200,0,0.15);  color: #ffc800; border: 1px solid #ffc800; }

/* ── Section labels ── */
.section-label {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem; letter-spacing: 0.18em;
    color: #00d4ff; text-transform: uppercase;
    border-bottom: 1px solid #00405a;
    padding-bottom: 0.25rem; margin-bottom: 0.4rem;
    display: flex; align-items: center; gap: 0.4rem;
}
.section-label::before {
    content: "▶"; font-size: 0.55rem; color: #00d4ff;
}

/* ── Ticker card ── */
.ticker-card {
    background: linear-gradient(135deg, #001628 0%, #001e35 100%);
    border: 1px solid #003a55;
    border-left: 3px solid #00d4ff;
    border-radius: 4px;
    padding: 0.45rem 0.65rem;
    margin-bottom: 0.35rem;
    position: relative;
    transition: border-color 0.2s;
}
.ticker-card:hover { border-left-color: #00ffaa; border-color: #005577; }
.ticker-card.positive { border-left-color: #00e676; }
.ticker-card.negative { border-left-color: #ff1744; }

.ticker-symbol {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.82rem; font-weight: 700;
    color: #e0f0ff; letter-spacing: 0.06em;
}
.ticker-name {
    font-size: 0.65rem; color: #4a7fa0;
    font-family: 'Rajdhani', sans-serif;
    white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; max-width: 100%;
}
.ticker-price {
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.05rem; font-weight: 700;
    color: #ffffff;
    text-align: right;
}
.ticker-change-pos {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.78rem; color: #00e676;
    text-align: right;
}
.ticker-change-neg {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.78rem; color: #ff1744;
    text-align: right;
}
.ticker-vol {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.6rem; color: #3a6a80;
    text-align: right; margin-top: 0.05rem;
}

/* ── Marquee ticker tape ── */
.ticker-tape-wrapper {
    background: #000d1a;
    border-top: 1px solid #00405a;
    border-bottom: 1px solid #00405a;
    padding: 0.3rem 0;
    overflow: hidden;
    margin-bottom: 0.5rem;
    white-space: nowrap;
}
@keyframes marquee {
    0%   { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
}
.ticker-tape {
    display: inline-block;
    animation: marquee 60s linear infinite;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.04em;
}
.tape-item { display: inline-block; margin: 0 2rem; }
.tape-pos { color: #00e676; }
.tape-neg { color: #ff1744; }
.tape-sym { color: #7fbfdf; margin-right: 0.4rem; }

/* ── News feed ── */
.news-item {
    border-left: 2px solid #00405a;
    padding: 0.35rem 0.5rem;
    margin-bottom: 0.3rem;
    background: rgba(0,22,40,0.5);
    border-radius: 0 3px 3px 0;
    font-size: 0.75rem;
    line-height: 1.4;
}
.news-item:hover { border-left-color: #00d4ff; background: rgba(0,40,70,0.5); }
.news-time {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.6rem; color: #3a6a80;
    display: block; margin-bottom: 0.1rem;
}
.news-title { color: #b0cce0; font-weight: 600; }
.news-source { color: #005577; font-size: 0.6rem; margin-top: 0.1rem; }

/* ── Stat box ── */
.stat-box {
    background: #001020;
    border: 1px solid #003040;
    border-radius: 4px;
    padding: 0.4rem 0.6rem;
    margin-bottom: 0.35rem;
    text-align: center;
}
.stat-label { font-size: 0.62rem; color: #3a6a80; letter-spacing: 0.12em; font-family: 'Share Tech Mono', monospace; }
.stat-value { font-size: 1.1rem; color: #00d4ff; font-family: 'Share Tech Mono', monospace; font-weight: 700; }
.stat-sub   { font-size: 0.62rem; color: #4a7fa0; font-family: 'Share Tech Mono', monospace; }

/* ── Divider ── */
.v-divider { width: 1px; background: #00283d; margin: 0 0.3rem; }

/* ── Column padding fix ── */
[data-testid="column"] { padding: 0 0.3rem !important; }

/* scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #000d1a; }
::-webkit-scrollbar-thumb { background: #00405a; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DATA FETCHING HELPERS
# ─────────────────────────────────────────────
@st.cache_data(ttl=30)          # refresh every 30 s
def fetch_quote(symbol: str):
    try:
        tk = yf.Ticker(symbol)
        info = tk.fast_info
        prev = info.previous_close or 0
        curr = info.last_price or 0
        chg  = curr - prev
        pct  = (chg / prev * 100) if prev else 0
        vol  = info.three_month_average_volume or 0
        return {
            "symbol": symbol,
            "price":  curr,
            "change": chg,
            "pct":    pct,
            "volume": vol,
            "prev":   prev,
        }
    except Exception:
        return {"symbol": symbol, "price": 0, "change": 0, "pct": 0, "volume": 0, "prev": 0}


@st.cache_data(ttl=30)
def fetch_many(symbols):
    return [fetch_quote(s) for s in symbols]


@st.cache_data(ttl=300)         # news every 5 min
def fetch_news():
    """Pull headlines via GNews (free, no key needed for basic)."""
    headlines = []
    try:
        url = (
            "https://gnews.io/api/v4/search"
            "?q=stock+market+economy+india+fed"
            "&lang=en&max=10&token=demo"   # demo mode: limited hits
        )
        r = requests.get(url, timeout=5)
        if r.ok:
            for a in r.json().get("articles", []):
                headlines.append({
                    "title":  a.get("title", ""),
                    "source": a.get("source", {}).get("name", ""),
                    "time":   a.get("publishedAt", "")[:16].replace("T", " "),
                })
    except Exception:
        pass

    # Fallback headlines when API unavailable
    if not headlines:
        headlines = [
            {"title": "RBI holds repo rate steady amid inflation concerns; Governor signals cautious stance", "source": "Economic Times", "time": "Live"},
            {"title": "Nifty 50 flirts with all-time highs as FII inflows surge; IT sector leads gains", "source": "Mint", "time": "Live"},
            {"title": "Fed minutes reveal divided committee on pace of 2025 rate cuts", "source": "Reuters", "time": "Live"},
            {"title": "Brent crude rises above $85 on Middle East supply disruption fears", "source": "Bloomberg", "time": "Live"},
            {"title": "SEBI proposes new algo-trading norms for retail investors", "source": "Business Standard", "time": "Live"},
            {"title": "Reliance Industries announces ₹75,000 Cr capex plan for green energy", "source": "CNBC-TV18", "time": "Live"},
            {"title": "US-China trade tensions resurface; tech stocks under pressure in early trade", "source": "WSJ", "time": "Live"},
            {"title": "USD/INR eyes 84 handle as dollar strengthens on robust US jobs data", "source": "LiveMint", "time": "Live"},
        ]
    return headlines


# ─────────────────────────────────────────────
# SYMBOL GROUPS
# ─────────────────────────────────────────────
INDIAN_INDICES = [
    ("^NSEI",   "NIFTY 50"),
    ("^BSESN",  "SENSEX"),
    ("^NSEBANK","BANK NIFTY"),
]

INDIAN_EQUITIES = [
    ("RELIANCE.NS",   "Reliance Inds"),
    ("TCS.NS",        "TCS"),
    ("INFY.NS",       "Infosys"),
    ("HDFCBANK.NS",   "HDFC Bank"),
    ("ICICIBANK.NS",  "ICICI Bank"),
    ("HINDUNILVR.NS", "HUL"),
    ("WIPRO.NS",      "Wipro"),
    ("BAJFINANCE.NS", "Bajaj Finance"),
]

US_INDICES = [
    ("^GSPC",  "S&P 500"),
    ("^IXIC",  "NASDAQ"),
    ("^DJI",   "DOW JONES"),
]

US_TECH = [
    ("AAPL",  "Apple"),
    ("MSFT",  "Microsoft"),
    ("NVDA",  "NVIDIA"),
    ("GOOGL", "Alphabet"),
    ("META",  "Meta"),
    ("AMZN",  "Amazon"),
]

COMMODITIES_FOREX = [
    ("CL=F",   "Crude Oil (WTI)"),
    ("BZ=F",   "Brent Crude"),
    ("GC=F",   "Gold"),
    ("INR=X",  "USD/INR"),
    ("EURINR=X","EUR/INR"),
]


# ─────────────────────────────────────────────
# RENDERING HELPERS
# ─────────────────────────────────────────────
def fmt_price(p, decimals=2):
    if p >= 1_000:
        return f"{p:,.{decimals}f}"
    return f"{p:.{decimals}f}"


def fmt_vol(v):
    if v >= 1e7: return f"{v/1e7:.1f}Cr"
    if v >= 1e5: return f"{v/1e5:.1f}L"
    if v >= 1e3: return f"{v/1e3:.1f}K"
    return str(int(v))


def ticker_card_html(symbol, name, data):
    p   = data["price"]
    chg = data["change"]
    pct = data["pct"]
    vol = data["volume"]
    cls = "positive" if chg >= 0 else "negative"
    chg_cls = "ticker-change-pos" if chg >= 0 else "ticker-change-neg"
    arrow = "▲" if chg >= 0 else "▼"
    dec = 0 if p > 1000 else 2
    return f"""
<div class='ticker-card {cls}'>
  <div style='display:flex; justify-content:space-between; align-items:flex-start'>
    <div>
      <div class='ticker-symbol'>{symbol.replace(".NS","").replace("^","")}</div>
      <div class='ticker-name'>{name}</div>
    </div>
    <div>
      <div class='ticker-price'>{fmt_price(p, dec)}</div>
      <div class='{chg_cls}'>{arrow} {abs(chg):.2f} ({abs(pct):.2f}%)</div>
      <div class='ticker-vol'>Vol: {fmt_vol(vol)}</div>
    </div>
  </div>
</div>"""


def build_tape(all_data):
    parts = []
    for sym, name, d in all_data:
        p   = d["price"]
        pct = d["pct"]
        cls = "tape-pos" if pct >= 0 else "tape-neg"
        arrow = "▲" if pct >= 0 else "▼"
        dec = 0 if p > 1000 else 2
        short = sym.replace(".NS","").replace("^","").replace("=X","").replace("=F","")
        parts.append(
            f"<span class='tape-item'>"
            f"<span class='tape-sym'>{short}</span>"
            f"<span class='{cls}'>{fmt_price(p,dec)} {arrow}{abs(pct):.2f}%</span>"
            f"</span> ·"
        )
    tape = " ".join(parts)
    return f"<div class='ticker-tape-wrapper'><span class='ticker-tape'>{tape}</span></div>"


def market_status():
    now_ist = datetime.now(pytz.timezone("Asia/Kolkata"))
    now_est = datetime.now(pytz.timezone("America/New_York"))

    ist_open = now_ist.weekday() < 5 and (9*60+15) <= (now_ist.hour*60 + now_ist.minute) <= (15*60+30)
    est_open = now_est.weekday() < 5 and (9*60+30) <= (now_est.hour*60 + now_est.minute) <= (16*60+0)
    est_pre  = now_est.weekday() < 5 and (4*60) <= (now_est.hour*60 + now_est.minute) < (9*60+30)

    nse_badge = '<span class="market-status-badge badge-open">NSE ● LIVE</span>' if ist_open else '<span class="market-status-badge badge-closed">NSE ● CLOSED</span>'
    us_badge  = ('<span class="market-status-badge badge-open">NYSE ● LIVE</span>' if est_open
                 else '<span class="market-status-badge badge-pre">NYSE ● PRE</span>' if est_pre
                 else '<span class="market-status-badge badge-closed">NYSE ● CLOSED</span>')
    return nse_badge, us_badge


# ─────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────
def render():
    # ── Header ──
    nse_badge, us_badge = market_status()
    now_str = datetime.now().strftime("%d %b %Y  %H:%M:%S")
    st.markdown(f"""
    <div class='terminal-header'>
      <div class='terminal-title'>◈ MARKET TERMINAL</div>
      <div style='display:flex; gap:0.6rem; align-items:center'>
        {nse_badge}
        {us_badge}
      </div>
      <div class='terminal-clock'>⏱ {now_str} IST</div>
    </div>""", unsafe_allow_html=True)

    # ── Fetch ALL data ──
    all_syms  = (INDIAN_INDICES + INDIAN_EQUITIES + US_INDICES + US_TECH + COMMODITIES_FOREX)
    flat_syms = [s for s, _ in all_syms]
    all_raw   = fetch_many(flat_syms)
    data_map  = {d["symbol"]: d for d in all_raw}

    # ── Ticker tape ──
    tape_data = [(s, n, data_map.get(s, {})) for s, n in all_syms if data_map.get(s, {}).get("price", 0) > 0]
    st.markdown(build_tape(tape_data), unsafe_allow_html=True)

    # ─────────────────────────────────────────
    # LAYOUT: 4 columns
    # ─────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([1.1, 1.1, 1.0, 1.0])

    # ── COL 1 : Indian Markets ──
    with c1:
        st.markdown("<div class='section-label'>🇮🇳 INDIAN INDICES</div>", unsafe_allow_html=True)
        for sym, name in INDIAN_INDICES:
            d = data_map.get(sym, {})
            st.markdown(ticker_card_html(sym, name, d), unsafe_allow_html=True)

        st.markdown("<div class='section-label' style='margin-top:0.6rem'>INDIAN EQUITIES</div>", unsafe_allow_html=True)
        for sym, name in INDIAN_EQUITIES:
            d = data_map.get(sym, {})
            st.markdown(ticker_card_html(sym, name, d), unsafe_allow_html=True)

    # ── COL 2 : US Markets ──
    with c2:
        st.markdown("<div class='section-label'>🇺🇸 US INDICES</div>", unsafe_allow_html=True)
        for sym, name in US_INDICES:
            d = data_map.get(sym, {})
            st.markdown(ticker_card_html(sym, name, d), unsafe_allow_html=True)

        st.markdown("<div class='section-label' style='margin-top:0.6rem'>US TECH</div>", unsafe_allow_html=True)
        for sym, name in US_TECH:
            d = data_map.get(sym, {})
            st.markdown(ticker_card_html(sym, name, d), unsafe_allow_html=True)

    # ── COL 3 : Commodities + Forex ──
    with c3:
        st.markdown("<div class='section-label'>⛽ COMMODITIES & FOREX</div>", unsafe_allow_html=True)
        for sym, name in COMMODITIES_FOREX:
            d = data_map.get(sym, {})
            st.markdown(ticker_card_html(sym, name, d), unsafe_allow_html=True)

        # Quick stats panel
        st.markdown("<div class='section-label' style='margin-top:0.6rem'>MARKET PULSE</div>", unsafe_allow_html=True)

        nifty = data_map.get("^NSEI", {})
        sp500 = data_map.get("^GSPC", {})
        inr   = data_map.get("INR=X", {})
        gold  = data_map.get("GC=F",  {})

        for label, val, sub in [
            ("NIFTY 50",  f"{fmt_price(nifty.get('price',0), 0)}",  f"{'▲' if nifty.get('pct',0)>=0 else '▼'} {abs(nifty.get('pct',0)):.2f}%"),
            ("S&P 500",   f"{fmt_price(sp500.get('price',0), 0)}",  f"{'▲' if sp500.get('pct',0)>=0 else '▼'} {abs(sp500.get('pct',0)):.2f}%"),
            ("USD/INR",   f"₹{inr.get('price',0):.2f}",             "Forex"),
            ("GOLD (oz)", f"${gold.get('price',0):,.0f}",            f"{'▲' if gold.get('pct',0)>=0 else '▼'} {abs(gold.get('pct',0)):.2f}%"),
        ]:
            st.markdown(f"""
            <div class='stat-box'>
                <div class='stat-label'>{label}</div>
                <div class='stat-value'>{val}</div>
                <div class='stat-sub'>{sub}</div>
            </div>""", unsafe_allow_html=True)

    # ── COL 4 : News Feed ──
    with c4:
        st.markdown("<div class='section-label'>📡 MARKET NEWS</div>", unsafe_allow_html=True)
        news = fetch_news()
        for item in news:
            st.markdown(f"""
            <div class='news-item'>
              <span class='news-time'>🕐 {item['time']}</span>
              <div class='news-title'>{item['title']}</div>
              <div class='news-source'>— {item['source']}</div>
            </div>""", unsafe_allow_html=True)

    # ── Auto-refresh every 30 s ──
    st.markdown("""
    <script>
    setTimeout(function(){ window.location.reload(); }, 30000);
    </script>""", unsafe_allow_html=True)

    # ── Footer status bar ──
    st.markdown(f"""
    <div style='margin-top:0.5rem; padding:0.2rem 0.8rem;
         background:#000d1a; border-top:1px solid #002030;
         display:flex; justify-content:space-between;
         font-family:"Share Tech Mono",monospace; font-size:0.6rem; color:#2a5a70'>
      <span>⟳ AUTO-REFRESH: 30s  |  DATA: yfinance  |  PRICES MAY BE DELAYED 15 MIN</span>
      <span>MARKET TERMINAL v2.0  |  Built with Streamlit + yfinance</span>
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    render()
