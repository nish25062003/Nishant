"""
Nifty 50 Swing Trading Screener
================================
Screens for swing trading setups using:
  - Price above 20 DMA & 50 DMA
  - 20 DMA recently crossed above 50 DMA (Golden Cross)
  - RSI (14) between 50 and 65
  - Volume at least 1.5x the 10-day average volume

Requirements:
    pip install yfinance pandas ta
"""

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import ta

# ── Nifty 50 tickers (Yahoo Finance format: append .NS) ──────────────────────
NIFTY_50_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "INFOSYS.NS", "SBIN.NS", "HINDUNILVR.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "MARUTI.NS", "HCLTECH.NS", "SUNPHARMA.NS",
    "ASIANPAINT.NS", "BAJFINANCE.NS", "WIPRO.NS", "ULTRACEMCO.NS", "TITAN.NS",
    "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "M&M.NS",
    "TATASTEEL.NS", "ADANIENT.NS", "ADANIPORTS.NS", "JSWSTEEL.NS", "COALINDIA.NS",
    "BAJAJFINSV.NS", "DRREDDY.NS", "DIVISLAB.NS", "CIPLA.NS", "EICHERMOT.NS",
    "HEROMOTOCO.NS", "BPCL.NS", "TATACONSUM.NS", "APOLLOHOSP.NS", "HINDALCO.NS",
    "GRASIM.NS", "BAJAJ-AUTO.NS", "BRITANNIA.NS", "TECHM.NS", "INDUSINDBK.NS",
    "SBILIFE.NS", "HDFCLIFE.NS", "TATAMOTORS.NS", "UPL.NS", "LTF.NS",
]

# ── Screener Parameters ───────────────────────────────────────────────────────
SHORT_MA       = 20          # Short moving average window
LONG_MA        = 50          # Long moving average window
RSI_PERIOD     = 14          # RSI look-back period
RSI_LOW        = 50          # RSI lower bound
RSI_HIGH       = 65          # RSI upper bound
VOL_MA         = 10          # Volume average window
VOL_MULTIPLIER = 1.5         # Minimum volume vs. average
CROSS_LOOKBACK = 5           # Days to look back for golden cross
DATA_PERIOD    = "6mo"       # History to download


def fetch_data(ticker: str) -> pd.DataFrame | None:
    """Download OHLCV data for a ticker. Returns None on failure."""
    try:
        df = yf.download(ticker, period=DATA_PERIOD, interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < LONG_MA + 10:
            return None
        return df
    except Exception:
        return None


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to the DataFrame."""
    close = df["Close"].squeeze()
    volume = df["Volume"].squeeze()

    df["MA20"]       = close.rolling(SHORT_MA).mean()
    df["MA50"]       = close.rolling(LONG_MA).mean()
    df["RSI"]        = ta.momentum.RSIIndicator(close, window=RSI_PERIOD).rsi()
    df["Vol_MA10"]   = volume.rolling(VOL_MA).mean()
    df["Vol_Ratio"]  = volume / df["Vol_MA10"]
    return df


def golden_cross_recently(df: pd.DataFrame, lookback: int = CROSS_LOOKBACK) -> bool:
    """
    Returns True if 20 DMA crossed above 50 DMA within the last `lookback` bars.
    A cross is identified when MA20 > MA50 on the latest bar and
    MA20 <= MA50 at least once in the prior `lookback` bars.
    """
    if len(df) < lookback + 1:
        return False
    recent = df.iloc[-(lookback + 1):]
    currently_above = recent["MA20"].iloc[-1] > recent["MA50"].iloc[-1]
    was_below_recently = (recent["MA20"].iloc[:-1] <= recent["MA50"].iloc[:-1]).any()
    return bool(currently_above and was_below_recently)


def screen_ticker(ticker: str) -> dict | None:
    """Run screening logic for a single ticker. Returns result dict or None."""
    df = fetch_data(ticker)
    if df is None:
        return None

    df = compute_indicators(df)
    latest = df.iloc[-1]

    close      = float(latest["Close"].squeeze())
    ma20       = float(latest["MA20"])
    ma50       = float(latest["MA50"])
    rsi        = float(latest["RSI"])
    vol_ratio  = float(latest["Vol_Ratio"])

    # ── Screening filters ────────────────────────────────────────────────────
    above_ma20    = close > ma20
    above_ma50    = close > ma50
    rsi_in_range  = RSI_LOW <= rsi <= RSI_HIGH
    vol_spike     = vol_ratio >= VOL_MULTIPLIER
    cross         = golden_cross_recently(df)

    if above_ma20 and above_ma50 and rsi_in_range and vol_spike and cross:
        return {
            "Ticker":          ticker.replace(".NS", ""),
            "Close Price (₹)": round(close, 2),
            "MA20 (₹)":        round(ma20, 2),
            "MA50 (₹)":        round(ma50, 2),
            "RSI (14)":        round(rsi, 2),
            "Vol Multiplier":  round(vol_ratio, 2),
        }
    return None


def run_screener() -> pd.DataFrame:
    """Screen all Nifty 50 tickers and return matching results."""
    print(f"\n{'═' * 58}")
    print("   📈  NIFTY 50 SWING TRADING SCREENER")
    print(f"{'═' * 58}")
    print(f"  Criteria:")
    print(f"  • Price > MA{SHORT_MA} and MA{LONG_MA}")
    print(f"  • MA{SHORT_MA} crossed above MA{LONG_MA} in last {CROSS_LOOKBACK} sessions")
    print(f"  • RSI({RSI_PERIOD}) between {RSI_LOW} and {RSI_HIGH}")
    print(f"  • Volume ≥ {VOL_MULTIPLIER}x the {VOL_MA}-day average")
    print(f"{'─' * 58}")
    print(f"  Scanning {len(NIFTY_50_TICKERS)} tickers...\n")

    results = []
    for ticker in NIFTY_50_TICKERS:
        symbol = ticker.replace(".NS", "")
        result = screen_ticker(ticker)
        if result:
            print(f"  ✅  {symbol:<15}  — MATCH FOUND")
            results.append(result)
        else:
            print(f"  ⬜  {symbol:<15}  — No setup")

    print(f"\n{'═' * 58}")

    if not results:
        print("  No tickers matched all criteria today.")
        print(f"{'═' * 58}\n")
        return pd.DataFrame(columns=[
            "Ticker", "Close Price (₹)", "MA20 (₹)", "MA50 (₹)",
            "RSI (14)", "Vol Multiplier"
        ])

    df_results = pd.DataFrame(results).sort_values("RSI (14)").reset_index(drop=True)
    df_results.index += 1  # 1-based ranking

    print(f"\n  🎯  {len(df_results)} stock(s) matched the swing setup criteria:\n")
    print(df_results.to_string())
    print(f"\n{'═' * 58}\n")
    return df_results


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    matches = run_screener()

    # Optional: save results to CSV
    if not matches.empty:
        output_file = "swing_trading_setups.csv"
        matches.to_csv(output_file)
        print(f"  💾  Results saved to '{output_file}'\n")
