"""
Finance Wallpaper Generator
============================
Fetches live market data via yfinance and writes a styled index.html
that auto-refreshes every 5 minutes.  Run this script once; it loops
forever, regenerating the HTML every 300 seconds.

Requirements:
    pip install yfinance requests

Usage:
    python finance_wallpaper.py

Output:
    finance_dashboard.html  (point Lively Wallpaper at this file)
"""

import yfinance as yf
import json
import time
import os
import datetime
import traceback

# ── Configuration ─────────────────────────────────────────────────────────────

OUTPUT_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finance_dashboard.html")
REFRESH_SECS  = 300          # Python re-fetches every 5 minutes
PAGE_RELOAD   = REFRESH_SECS # JS reloads the page at the same cadence

TICKERS = {
    "us": [
        {"symbol": "^GSPC",  "label": "S&P 500"},
        {"symbol": "^IXIC",  "label": "NASDAQ"},
        {"symbol": "AAPL",   "label": "Apple"},
    ],
    "india": [
        {"symbol": "^NSEI",        "label": "NIFTY 50"},
        {"symbol": "^BSESN",       "label": "SENSEX"},
        {"symbol": "RELIANCE.NS",  "label": "Reliance"},
    ],
    "commodities": [
        {"symbol": "CL=F",  "label": "Crude Oil (WTI)"},
        {"symbol": "GC=F",  "label": "Gold"},
        {"symbol": "SI=F",  "label": "Silver"},
    ],
}

NEWS_TICKER    = "SPY"
MAX_NEWS       = 15
MAX_NEWS_SHOWN = 10   # headline ticker cycles through this many

# ── Data Fetching ──────────────────────────────────────────────────────────────

def safe_round(val, decimals=2):
    try:
        return round(float(val), decimals)
    except Exception:
        return None


def fetch_quote(symbol: str) -> dict:
    """Return price, change, pct_change for a single symbol."""
    try:
        tk   = yf.Ticker(symbol)
        info = tk.fast_info
        price    = safe_round(info.last_price)
        prev     = safe_round(info.previous_close)
        if price is None or prev is None:
            return {"price": None, "change": None, "pct": None}
        change   = safe_round(price - prev)
        pct      = safe_round((change / prev) * 100) if prev else None
        return {"price": price, "change": change, "pct": pct}
    except Exception:
        return {"price": None, "change": None, "pct": None}


def fetch_all_quotes() -> dict:
    result = {}
    for group, items in TICKERS.items():
        result[group] = []
        for item in items:
            q = fetch_quote(item["symbol"])
            result[group].append({**item, **q})
    return result


def fetch_news() -> list[dict]:
    try:
        tk    = yf.Ticker(NEWS_TICKER)
        raw   = tk.news or []
        items = []
        for n in raw[:MAX_NEWS]:
            ct = n.get("content", {})
            title = ct.get("title") or n.get("title") or ""
            if not title:
                continue
            provider = ""
            prov_obj = ct.get("provider") or {}
            if isinstance(prov_obj, dict):
                provider = prov_obj.get("displayName", "")
            pub_date = ct.get("pubDate") or ""
            if pub_date:
                try:
                    dt = datetime.datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    pub_date = dt.strftime("%b %d, %H:%M UTC")
                except Exception:
                    pub_date = pub_date[:16]
            items.append({"title": title, "provider": provider, "date": pub_date})
        return items[:MAX_NEWS_SHOWN]
    except Exception:
        return []


# ── HTML Generation ────────────────────────────────────────────────────────────

def fmt_price(val, symbol=""):
    """Format a number with commas; add ₹ for Indian, $ for others."""
    if val is None:
        return "—"
    # Indian tickers
    if ".NS" in symbol or symbol in ("^NSEI", "^BSESN"):
        return f"₹{val:,.2f}"
    return f"{val:,.2f}"


def fmt_change(change, pct):
    if change is None or pct is None:
        return "—", "neutral"
    direction = "up" if change >= 0 else "down"
    sign      = "+" if change >= 0 else ""
    return f"{sign}{change:,.2f} ({sign}{pct:.2f}%)", direction


def card_html(item: dict) -> str:
    label  = item["label"]
    symbol = item["symbol"]
    price  = item["price"]
    change_str, direction = fmt_change(item["change"], item["pct"])
    arrow  = "▲" if direction == "up" else ("▼" if direction == "down" else "")
    cls    = direction  # "up" | "down" | "neutral"

    return f"""
        <div class="card">
          <div class="card-label">{label}</div>
          <div class="card-symbol">{symbol}</div>
          <div class="card-price">{fmt_price(price, symbol)}</div>
          <div class="card-change {cls}">{arrow} {change_str}</div>
        </div>"""


def section_html(title: str, items: list) -> str:
    cards = "\n".join(card_html(i) for i in items)
    return f"""
      <div class="section">
        <div class="section-title">{title}</div>
        <div class="cards">{cards}</div>
      </div>"""


def news_ticker_html(headlines: list) -> str:
    if not headlines:
        return ""
    items_html = "".join(
        f'<span class="ticker-item"><span class="ticker-source">'
        f'{h["provider"] or "Reuters"}</span> {h["title"]}'
        f'<span class="ticker-sep">◆</span></span>'
        for h in headlines
    )
    # Duplicate for seamless loop
    return f"""
    <div class="news-ticker-bar">
      <div class="ticker-label">LIVE</div>
      <div class="ticker-track">
        <div class="ticker-inner" id="tickerInner">
          {items_html}{items_html}
        </div>
      </div>
    </div>"""


def build_html(quotes: dict, news: list) -> str:
    now      = datetime.datetime.utcnow().strftime("%A, %d %b %Y  %H:%M UTC")
    us_sec   = section_html("🇺🇸 &nbsp;US MARKETS", quotes["us"])
    in_sec   = section_html("🇮🇳 &nbsp;INDIAN MARKETS", quotes["india"])
    com_sec  = section_html("⛽ &nbsp;COMMODITIES", quotes["commodities"])
    news_bar = news_ticker_html(news)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Finance Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap" rel="stylesheet"/>
  <style>
    /* ── Reset & Base ─────────────────────────────────────────────── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:          #050810;
      --bg2:         #080d18;
      --panel:       rgba(10, 15, 28, 0.82);
      --border:      rgba(255,255,255,0.06);
      --border-glow: rgba(0,200,255,0.18);
      --accent:      #00c8ff;
      --accent2:     #7b5cfa;
      --up:          #00ff9d;
      --down:        #ff3d5a;
      --muted:       #4a5568;
      --text:        #e2e8f0;
      --text-dim:    #718096;
      --font-mono:   'JetBrains Mono', monospace;
      --font-sans:   'Space Grotesk', sans-serif;
    }}

    html, body {{
      width: 100vw; height: 100vh;
      overflow: hidden;
      background: var(--bg);
      color: var(--text);
      font-family: var(--font-sans);
    }}

    /* ── Background ───────────────────────────────────────────────── */
    body::before {{
      content: '';
      position: fixed; inset: 0; z-index: 0;
      background:
        radial-gradient(ellipse 80% 60% at 15% 20%, rgba(0,200,255,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 85% 75%, rgba(123,92,250,0.09) 0%, transparent 55%),
        radial-gradient(ellipse 40% 30% at 50% 50%, rgba(0,255,157,0.03) 0%, transparent 70%),
        linear-gradient(180deg, #050810 0%, #030609 100%);
    }}

    /* Subtle grid overlay */
    body::after {{
      content: '';
      position: fixed; inset: 0; z-index: 0;
      background-image:
        linear-gradient(rgba(0,200,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,200,255,0.03) 1px, transparent 1px);
      background-size: 60px 60px;
      pointer-events: none;
    }}

    /* ── Layout ───────────────────────────────────────────────────── */
    .wrapper {{
      position: relative; z-index: 1;
      width: 100vw; height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr auto;
      grid-template-columns: 1fr;
      gap: 0;
    }}

    /* ── Header ───────────────────────────────────────────────────── */
    .header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 18px 40px 14px;
      border-bottom: 1px solid var(--border);
      background: rgba(5,8,16,0.6);
      backdrop-filter: blur(12px);
    }}

    .header-brand {{
      display: flex;
      align-items: baseline;
      gap: 12px;
    }}

    .brand-name {{
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--accent);
      text-shadow: 0 0 20px rgba(0,200,255,0.5);
    }}

    .brand-sub {{
      font-size: 0.65rem;
      font-weight: 400;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--muted);
    }}

    .header-time {{
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--text-dim);
      letter-spacing: 0.08em;
    }}

    .header-time span {{
      color: var(--accent);
      font-weight: 500;
    }}

    /* ── Live dot ─────────────────────────────────────────────────── */
    .live-dot {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-family: var(--font-mono);
      font-size: 0.62rem;
      letter-spacing: 0.14em;
      color: var(--up);
      text-transform: uppercase;
    }}
    .live-dot::before {{
      content: '';
      width: 7px; height: 7px;
      border-radius: 50%;
      background: var(--up);
      box-shadow: 0 0 8px var(--up);
      animation: pulse 2s ease-in-out infinite;
    }}
    @keyframes pulse {{
      0%,100% {{ opacity:1; transform:scale(1); }}
      50%      {{ opacity:0.5; transform:scale(0.8); }}
    }}

    /* ── Main content: left panel / center / right panel ─────────── */
    .content {{
      display: grid;
      grid-template-columns: 340px 1fr 340px;
      gap: 0;
      overflow: hidden;
    }}

    /* ── Side panels ──────────────────────────────────────────────── */
    .panel {{
      padding: 28px 24px;
      display: flex;
      flex-direction: column;
      gap: 28px;
      overflow-y: auto;
      scrollbar-width: none;
    }}
    .panel::-webkit-scrollbar {{ display: none; }}

    .panel-left  {{
      border-right: 1px solid var(--border);
      background: linear-gradient(180deg, rgba(0,200,255,0.04) 0%, transparent 100%);
    }}
    .panel-right {{
      border-left: 1px solid var(--border);
      background: linear-gradient(180deg, rgba(123,92,250,0.04) 0%, transparent 100%);
    }}

    /* ── Center area ──────────────────────────────────────────────── */
    .center {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0;
      padding: 20px;
    }}

    .center-logo {{
      font-size: clamp(3rem, 7vw, 6rem);
      font-weight: 700;
      letter-spacing: -0.03em;
      text-align: center;
      line-height: 1;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 60%, var(--up) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      filter: drop-shadow(0 0 40px rgba(0,200,255,0.25));
      animation: shimmer 6s ease-in-out infinite;
    }}

    @keyframes shimmer {{
      0%,100% {{ filter: drop-shadow(0 0 30px rgba(0,200,255,0.2)); }}
      50%      {{ filter: drop-shadow(0 0 60px rgba(123,92,250,0.4)); }}
    }}

    .center-tagline {{
      font-size: 0.65rem;
      letter-spacing: 0.35em;
      text-transform: uppercase;
      color: var(--text-dim);
      margin-top: 10px;
    }}

    .center-clock {{
      font-family: var(--font-mono);
      font-size: clamp(1.8rem, 4vw, 3rem);
      font-weight: 300;
      color: var(--text);
      letter-spacing: 0.08em;
      margin-top: 28px;
      text-shadow: 0 0 30px rgba(0,200,255,0.15);
    }}

    .center-date {{
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--text-dim);
      letter-spacing: 0.14em;
      margin-top: 6px;
      text-transform: uppercase;
    }}

    /* ── Sections & Cards ─────────────────────────────────────────── */
    .section {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    .section-title {{
      font-size: 0.6rem;
      font-weight: 600;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--text-dim);
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }}

    .cards {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      display: grid;
      grid-template-columns: 1fr auto;
      grid-template-rows: auto auto;
      gap: 2px 12px;
      transition: border-color 0.3s, box-shadow 0.3s;
      position: relative;
      overflow: hidden;
    }}

    .card::before {{
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(135deg, rgba(255,255,255,0.02) 0%, transparent 60%);
      pointer-events: none;
    }}

    .card:hover {{
      border-color: var(--border-glow);
      box-shadow: 0 0 20px rgba(0,200,255,0.05);
    }}

    .card-label {{
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--text);
      grid-column: 1;
      grid-row: 1;
    }}

    .card-symbol {{
      font-family: var(--font-mono);
      font-size: 0.58rem;
      color: var(--text-dim);
      letter-spacing: 0.06em;
      grid-column: 1;
      grid-row: 2;
    }}

    .card-price {{
      font-family: var(--font-mono);
      font-size: 0.92rem;
      font-weight: 500;
      color: var(--text);
      grid-column: 2;
      grid-row: 1;
      text-align: right;
      white-space: nowrap;
    }}

    .card-change {{
      font-family: var(--font-mono);
      font-size: 0.68rem;
      font-weight: 500;
      text-align: right;
      grid-column: 2;
      grid-row: 2;
      white-space: nowrap;
    }}

    .card-change.up      {{ color: var(--up);   text-shadow: 0 0 10px rgba(0,255,157,0.4); }}
    .card-change.down    {{ color: var(--down);  text-shadow: 0 0 10px rgba(255,61,90,0.4); }}
    .card-change.neutral {{ color: var(--muted); }}

    /* ── News panel (right) ───────────────────────────────────────── */
    .news-list {{
      display: flex;
      flex-direction: column;
      gap: 0;
    }}

    .news-item {{
      padding: 11px 0;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 4px;
      animation: fadeIn 0.4s ease;
    }}

    @keyframes fadeIn {{
      from {{ opacity:0; transform: translateY(4px); }}
      to   {{ opacity:1; transform: translateY(0); }}
    }}

    .news-title {{
      font-size: 0.72rem;
      font-weight: 500;
      color: var(--text);
      line-height: 1.45;
    }}

    .news-meta {{
      display: flex;
      gap: 8px;
      align-items: center;
    }}

    .news-source {{
      font-family: var(--font-mono);
      font-size: 0.55rem;
      font-weight: 500;
      letter-spacing: 0.1em;
      color: var(--accent2);
      text-transform: uppercase;
    }}

    .news-date {{
      font-family: var(--font-mono);
      font-size: 0.55rem;
      color: var(--muted);
    }}

    /* ── News ticker bar (bottom) ─────────────────────────────────── */
    .news-ticker-bar {{
      border-top: 1px solid var(--border);
      background: rgba(5,8,16,0.85);
      backdrop-filter: blur(10px);
      display: flex;
      align-items: center;
      height: 34px;
      overflow: hidden;
    }}

    .ticker-label {{
      flex-shrink: 0;
      padding: 0 14px;
      font-family: var(--font-mono);
      font-size: 0.58rem;
      font-weight: 700;
      letter-spacing: 0.18em;
      color: #050810;
      background: var(--accent);
      height: 100%;
      display: flex;
      align-items: center;
    }}

    .ticker-track {{
      flex: 1;
      overflow: hidden;
      height: 100%;
    }}

    .ticker-inner {{
      display: flex;
      align-items: center;
      height: 100%;
      white-space: nowrap;
      animation: scroll-ticker linear infinite;
      animation-duration: 60s;
    }}

    @keyframes scroll-ticker {{
      0%   {{ transform: translateX(0); }}
      100% {{ transform: translateX(-50%); }}
    }}

    .ticker-item {{
      font-family: var(--font-mono);
      font-size: 0.65rem;
      color: var(--text-dim);
      padding: 0 28px;
    }}

    .ticker-source {{
      color: var(--up);
      font-weight: 600;
      margin-right: 8px;
    }}

    .ticker-sep {{
      color: var(--accent2);
      margin-left: 28px;
      opacity: 0.5;
    }}

    /* ── Scrollbar for news panel ─────────────────────────────────── */
    .panel-right::-webkit-scrollbar {{ display: none; }}

    /* ── Refresh countdown ────────────────────────────────────────── */
    .refresh-bar {{
      position: fixed;
      bottom: 34px;
      left: 50%;
      transform: translateX(-50%);
      width: 160px;
      height: 2px;
      background: rgba(255,255,255,0.05);
      border-radius: 2px;
      overflow: hidden;
    }}

    .refresh-bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--accent2));
      border-radius: 2px;
      animation: deplete {PAGE_RELOAD}s linear forwards;
    }}

    @keyframes deplete {{
      from {{ width: 100%; }}
      to   {{ width: 0%; }}
    }}
  </style>
</head>
<body>
<div class="wrapper">

  <!-- ── Header ─────────────────────────────────────────── -->
  <header class="header">
    <div class="header-brand">
      <div class="brand-name">FinDesk</div>
      <div class="brand-sub">Live Market Dashboard</div>
    </div>
    <div class="live-dot">Live</div>
    <div class="header-time">
      Last updated &nbsp;<span>{now}</span>
    </div>
  </header>

  <!-- ── Main ───────────────────────────────────────────── -->
  <main class="content">

    <!-- Left panel: US + Commodities -->
    <div class="panel panel-left">
      {us_sec}
      {com_sec}
    </div>

    <!-- Center: branding + clock -->
    <div class="center">
      <div class="center-logo">MARKETS</div>
      <div class="center-tagline">Real-time · Global · Intelligent</div>
      <div class="center-clock" id="liveClock">--:--:--</div>
      <div class="center-date"  id="liveDate">---</div>
    </div>

    <!-- Right panel: India + News -->
    <div class="panel panel-right">
      {in_sec}
      <div class="section">
        <div class="section-title">📰 &nbsp;Market News</div>
        <div class="news-list">
          {"".join(
              f'<div class="news-item">'
              f'<div class="news-title">{h["title"]}</div>'
              f'<div class="news-meta">'
              f'<span class="news-source">{h["provider"] or "Reuters"}</span>'
              f'<span class="news-date">{h["date"]}</span>'
              f'</div></div>'
              for h in news
          )}
        </div>
      </div>
    </div>

  </main>

  <!-- ── News ticker ─────────────────────────────────────── -->
  {news_bar}

</div>

<!-- Refresh progress bar -->
<div class="refresh-bar"><div class="refresh-bar-fill"></div></div>

<script>
  // ── Live clock ──────────────────────────────────────────
  function updateClock() {{
    const now = new Date();
    document.getElementById('liveClock').textContent =
      now.toUTCString().slice(17, 25);
    document.getElementById('liveDate').textContent =
      now.toUTCString().slice(0, 16).toUpperCase();
  }}
  updateClock();
  setInterval(updateClock, 1000);

  // ── Auto-reload after Python updates the file ───────────
  setTimeout(() => location.reload(), {PAGE_RELOAD * 1000});
</script>
</body>
</html>"""


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    print(f"[FinDesk] Starting — output → {OUTPUT_FILE}")
    print(f"[FinDesk] Refreshing every {REFRESH_SECS}s.  Press Ctrl+C to stop.\n")

    while True:
        try:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Fetching quotes…", end=" ", flush=True)
            quotes = fetch_all_quotes()
            print("done.  Fetching news…", end=" ", flush=True)
            news   = fetch_news()
            print(f"done ({len(news)} headlines).")

            html = build_html(quotes, news)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ HTML written → {OUTPUT_FILE}")

        except Exception:
            print("\n[FinDesk] ⚠ Error during refresh:")
            traceback.print_exc()

        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sleeping {REFRESH_SECS}s…\n")
        time.sleep(REFRESH_SECS)


if __name__ == "__main__":
    main()
