"""
radar/fundamentals.py
=====================

Ask Yahoo Finance for the five raw numbers `scoring.py` needs to
compute a Value Score for one ticker.

Why this is a separate file from `scoring.py`:
  - Network calls are slow and fail in interesting ways.
  - Math is fast and deterministic.
Keeping them apart means we can test the scoring with hand-typed
numbers (no internet required) and swap data sources later without
touching the scoring rules.

This file never raises. Anything that goes wrong (no internet, bad
ticker, missing field on Yahoo's side) results in a None for that
metric — and `scoring.value_score()` averages over whatever metrics
DID come back.
"""

from typing import Optional
import yfinance as yf


# --- 1. Helpers ------------------------------------------------------

def _safe_float(value) -> Optional[float]:
    """
    Yahoo's `info` dict gives us strings, ints, floats, None — and
    occasionally weird sentinels. This funnels everything to either
    a real float or None.

    Why this matters: doing arithmetic on a None or a string causes
    a TypeError that crashes the dashboard. One safe converter at
    the boundary keeps the rest of the code clean.
    """
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    # NaN check — yfinance occasionally returns float('nan') for
    # missing fields. NaN is technically a float but useless for us.
    if out != out:   # the one and only way to detect NaN without imports
        return None
    return out


def _fetch_info(symbol: str) -> dict:
    """
    Single yfinance call wrapped in try/except. Returns {} on any
    failure so the calling code can just do `info.get("debtToEquity")`
    without worrying about whether the network was up.
    """
    try:
        return yf.Ticker(symbol).info or {}
    except Exception:
        return {}


# --- 2. The public function the dashboard imports -------------------

def fetch_fundamentals(symbol: str, asset_type: str) -> dict:
    """
    Pull the five raw inputs that `scoring.value_score()` consumes.

    Parameters
    ----------
    symbol : str
        The yfinance-recognised ticker (e.g. "NVDA", "BTC-USD").
        We use whatever `lookup.py` stored at add-time, so this is
        already canonical.
    asset_type : str
        "stock", "etf", or "crypto" — from the ideas.csv row. ETFs
        and crypto don't report these per-fund/per-coin, so we skip
        the network call entirely and return an all-None dict.

    Returns
    -------
    dict with these keys (any may be None):
        debt_to_equity   — ratio (0.30 means 30% debt-to-equity)
        current_ratio    — ratio (4.10 means current assets are 4.1x liabilities)
        net_cash_pct     — percent (8.0 means net cash = 8% of market cap)
        roe              — percent (95.0 means 95% return on equity)
        fcf_yield        — percent (2.0 means free cash flow yield = 2%)

    Never raises. On any failure: every value in the dict is None.
    """

    empty = {
        "debt_to_equity": None,
        "current_ratio":  None,
        "net_cash_pct":   None,
        "roe":            None,
        "fcf_yield":      None,
    }

    # ETFs and crypto are N/A by design (Section 5d of the plan).
    if asset_type in ("etf", "crypto"):
        return empty

    info = _fetch_info(symbol)
    if not info:
        return empty

    # --- Yahoo unit conversions --------------------------------
    #
    # `debtToEquity`: Yahoo reports as a percentage (30 = 0.30
    # ratio). Our thresholds in scoring.py expect the ratio.
    de_raw = _safe_float(info.get("debtToEquity"))
    debt_to_equity = de_raw / 100.0 if de_raw is not None else None

    # `currentRatio`: already a ratio. No conversion.
    current_ratio = _safe_float(info.get("currentRatio"))

    # `returnOnEquity`: Yahoo reports as a decimal (0.95 = 95%).
    # Our thresholds expect a percent.
    roe_raw = _safe_float(info.get("returnOnEquity"))
    roe = roe_raw * 100.0 if roe_raw is not None else None

    # --- Net cash and FCF yield need market cap ---------------
    #
    # net_cash      = totalCash - totalDebt          (dollars)
    # net_cash_pct  = net_cash / marketCap * 100     (percent)
    # fcf_yield     = freeCashflow / marketCap * 100 (percent)
    #
    # If marketCap is missing or zero we can't compute either of
    # these — leave them None.
    market_cap = _safe_float(info.get("marketCap"))
    total_cash = _safe_float(info.get("totalCash"))
    total_debt = _safe_float(info.get("totalDebt"))
    fcf        = _safe_float(info.get("freeCashflow"))

    if market_cap and market_cap > 0:
        if total_cash is not None and total_debt is not None:
            net_cash_pct = (total_cash - total_debt) / market_cap * 100.0
        else:
            net_cash_pct = None
        if fcf is not None:
            fcf_yield = fcf / market_cap * 100.0
        else:
            fcf_yield = None
    else:
        net_cash_pct = None
        fcf_yield = None

    return {
        "debt_to_equity": debt_to_equity,
        "current_ratio":  current_ratio,
        "net_cash_pct":   net_cash_pct,
        "roe":            roe,
        "fcf_yield":      fcf_yield,
    }


# --- 3. Run-this-file-directly: quick smoke test --------------------

if __name__ == "__main__":
    # Usage: python -m radar.fundamentals NVDA AAPL SPY BTC-USD
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m radar.fundamentals <SYMBOL> [SYMBOL …]")
        print("  Tip: pass ETF/crypto tickers (SPY, BTC-USD) to see "
              "the all-None case.")
        raise SystemExit(1)

    # Pretend everything is a stock for the CLI test — the real
    # dashboard passes the actual asset_type from ideas.csv.
    from radar.scoring import value_score, grade_letter

    for symbol in sys.argv[1:]:
        funds = fetch_fundamentals(symbol, asset_type="stock")
        score = value_score(funds)
        print(f"\n--- {symbol} ---")
        for k, v in funds.items():
            shown = "None" if v is None else f"{v:.3f}"
            print(f"  {k:16s} = {shown}")
        if score is None:
            print(f"  -> Value Score: N/A  (no metrics returned)")
        else:
            print(f"  -> Value Score: {score:.1f}  Grade: {grade_letter(score)}")
