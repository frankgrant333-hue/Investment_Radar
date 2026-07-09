"""
radar/technicals.py
===================

Pull a year of daily price history from Yahoo Finance for a single
ticker, and compute the four raw technical inputs that
`scoring.tech_score()` expects:

  - stage_2              (bool)   Is it in a Weinstein Stage 2 uptrend?
  - dist_from_20d_high   (float)  Percent below the 20-day high.
  - rs_vs_spy            (float)  90-day return minus SPY's 90-day return.
  - atr_pct              (float)  14-day Wilder ATR as a percent of price.

Unlike `fundamentals.py`, this module works for STOCKS, ETFs, AND
crypto — price action is universal. ETFs and crypto are no different
from stocks here; we don't need to special-case them.

Architecture note — why fetch and compute are separated:
    SPY's price history is the SAME for every ticker in your radar
    (we use it as the benchmark for relative strength). If compute
    fetched it internally, we'd hit Yahoo for SPY once per ticker.
    Splitting them lets `app.py` fetch SPY ONCE and pass it in.
"""

from typing import Optional
import pandas as pd
import yfinance as yf


# --- 1. The fetch function (app.py caches this) ---------------------

def fetch_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Pull daily OHLCV history from yfinance.

    Parameters
    ----------
    symbol : str
        Any yfinance-recognised ticker.
    period : str
        yfinance period string. "1y" gives ~252 trading days, which
        covers our longest window (150-day moving average) with
        headroom for the slope calculation.

    Returns
    -------
    pd.DataFrame with columns Open, High, Low, Close, Volume.
    Empty DataFrame on any failure — never raises.

    The DataFrame index is dates (newest at the bottom). Use
    `df.iloc[-1]` for "today", `df.iloc[-20:]` for "last 20 days".
    """
    try:
        df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception:
        return pd.DataFrame()


def fetch_histories_batch(symbols: list[str], period: str = "1y") -> dict:
    """
    Pull daily history for MANY tickers in ONE yfinance request.

    Why this exists: fetching 60 tickers one-by-one means 60 separate
    round-trips to Yahoo — slow everywhere, and on Streamlit Cloud's
    shared servers Yahoo starts throttling, which can stall the page
    for minutes. One batched request downloads everything at once.

    Returns
    -------
    dict of {symbol: DataFrame}. Symbols that failed are simply
    absent — callers should use .get(symbol) and handle None.
    Never raises.
    """
    if not symbols:
        return {}
    try:
        raw = yf.download(
            list(symbols),
            period=period,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception:
        return {}
    if raw is None or len(raw) == 0:
        return {}

    out = {}
    for s in symbols:
        try:
            # With multiple tickers, columns are grouped per ticker.
            df = raw[s] if len(symbols) > 1 else raw
            df = df.dropna(how="all")
            if not df.empty:
                out[s] = df
        except Exception:
            continue  # this one failed; keep the rest
    return out


# --- 2. The four raw-metric calculators -----------------------------
#
# Each takes a price-history DataFrame and returns either a number
# (or bool) or None if there isn't enough data to compute it.

def _calc_stage_2(history: pd.DataFrame) -> Optional[bool]:
    """
    Weinstein Stage 2 = price above the 30-week (150-day) moving
    average AND the moving average itself is sloping up.

    We approximate "sloping up" as: today's MA > MA from 10 trading
    days ago. That's the standard "is the trend established?" check
    — a single up-tick isn't enough, but a steady climb across two
    weeks is.

    Needs at least 160 trading days of data (150 for the MA + 10 for
    the slope). Younger stocks return None.
    """
    if len(history) < 160:
        return None

    ma150 = history["Close"].rolling(window=150).mean()
    today_ma = ma150.iloc[-1]
    ma_10_days_ago = ma150.iloc[-11]      # iloc[-1] is today, iloc[-11] is 10 days back
    today_close = history["Close"].iloc[-1]

    # Any NaN in those three numbers means we don't trust the result.
    if pd.isna(today_ma) or pd.isna(ma_10_days_ago) or pd.isna(today_close):
        return None

    price_above_ma = today_close > today_ma
    ma_sloping_up = today_ma > ma_10_days_ago
    return bool(price_above_ma and ma_sloping_up)


def _calc_dist_from_20d_high(history: pd.DataFrame) -> Optional[float]:
    """
    Percent below the 20-day high (using daily HIGHs, not closes —
    you want the actual peak the price touched, intraday spikes
    included).

    0 means we closed exactly at the 20-day high.
    Positive number means we closed BELOW it.
    """
    if len(history) < 20:
        return None
    high_20d = history["High"].iloc[-20:].max()
    today_close = history["Close"].iloc[-1]
    if pd.isna(high_20d) or pd.isna(today_close) or high_20d == 0:
        return None
    return float((high_20d - today_close) / high_20d * 100.0)


def _calc_rs_vs_spy(history: pd.DataFrame,
                    spy_history: pd.DataFrame) -> Optional[float]:
    """
    Relative strength = ticker's 90-day return minus SPY's 90-day
    return, expressed in percentage points.

      ticker up 30%, SPY up 10%  →  rs = +20  (beat SPY by 20 pts)
      ticker down 5%, SPY up 10% →  rs = -15  (lagged SPY by 15 pts)

    Needs 90 trading days on BOTH series. Either one short → None.
    """
    if len(history) < 90 or len(spy_history) < 90:
        return None
    t_now,  t_then  = history["Close"].iloc[-1],     history["Close"].iloc[-90]
    s_now,  s_then  = spy_history["Close"].iloc[-1], spy_history["Close"].iloc[-90]
    if pd.isna(t_now) or pd.isna(t_then) or pd.isna(s_now) or pd.isna(s_then):
        return None
    if t_then == 0 or s_then == 0:
        return None
    ticker_return = (t_now - t_then) / t_then * 100.0
    spy_return    = (s_now - s_then) / s_then * 100.0
    return float(ticker_return - spy_return)


def _calc_atr_pct(history: pd.DataFrame, period: int = 14) -> Optional[float]:
    """
    14-day Average True Range, expressed as a percent of today's
    closing price. We use Wilder's smoothing (the original 1978
    formula) so this matches the trade bot's ATR for the same ticker.

    Steps:
      1. True Range = max(H-L, |H - prev_C|, |L - prev_C|)
      2. Seed ATR = simple mean of the first 14 TR values
      3. Each subsequent ATR = (prev_ATR * 13 + today_TR) / 14
      4. ATR% = ATR / today_close * 100
    """
    if len(history) < period + 1:
        return None

    high  = history["High"]
    low   = history["Low"]
    close = history["Close"]
    prev_close = close.shift(1)

    # Three candidate ranges, pick the biggest per row.
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Drop the first row — it has NaN because prev_close is NaN.
    tr = tr.dropna()
    if len(tr) < period:
        return None

    # Wilder smoothing: SMA seed, then exponential-style update.
    atr = tr.iloc[:period].mean()
    for value in tr.iloc[period:]:
        atr = (atr * (period - 1) + value) / period

    today_close = close.iloc[-1]
    if pd.isna(today_close) or today_close == 0:
        return None
    return float(atr / today_close * 100.0)


# --- 3. The public orchestrator -------------------------------------

def compute_technicals(history: pd.DataFrame,
                       spy_history: pd.DataFrame) -> dict:
    """
    Run all four calculators on a pre-fetched price history.

    Parameters
    ----------
    history : pd.DataFrame
        The ticker's daily OHLCV (from `fetch_history`).
    spy_history : pd.DataFrame
        SPY's daily OHLCV (also from `fetch_history`). Passed in
        instead of fetched here so we only hit Yahoo for SPY once,
        not once per ticker.

    Returns
    -------
    dict with keys stage_2, dist_from_20d_high, rs_vs_spy, atr_pct.
    Any value may be None if there wasn't enough data. Empty history
    → all None.
    """
    empty = {
        "stage_2":             None,
        "dist_from_20d_high":  None,
        "rs_vs_spy":           None,
        "atr_pct":             None,
    }
    if history is None or history.empty:
        return empty

    return {
        "stage_2":            _calc_stage_2(history),
        "dist_from_20d_high": _calc_dist_from_20d_high(history),
        "rs_vs_spy":          _calc_rs_vs_spy(history, spy_history),
        "atr_pct":            _calc_atr_pct(history),
    }


# --- 4. Run-this-file-directly: quick smoke test --------------------

if __name__ == "__main__":
    # Usage: python -m radar.technicals NVDA AAPL BTC-USD
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m radar.technicals <SYMBOL> [SYMBOL …]")
        raise SystemExit(1)

    from radar.scoring import tech_score, grade_letter

    print("Fetching SPY (the benchmark) first…")
    spy = fetch_history("SPY")
    if spy.empty:
        print("  ⚠ Couldn't fetch SPY — RS scores will be N/A.")

    for sym in sys.argv[1:]:
        print(f"\n--- {sym} ---")
        hist = fetch_history(sym)
        if hist.empty:
            print(f"  ⚠ No price history returned.")
            continue
        tech = compute_technicals(hist, spy)
        for k, v in tech.items():
            shown = "None" if v is None else (str(v) if isinstance(v, bool) else f"{v:.3f}")
            print(f"  {k:22s} = {shown}")
        s = tech_score(tech)
        if s is None:
            print(f"  -> Tech Score: N/A")
        else:
            print(f"  -> Tech Score: {s:.1f}  Grade: {grade_letter(s)}")
