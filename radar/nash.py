"""
radar/nash.py — Tom Nash "Double Down" DCA rules (Phase 2)
==========================================================

One home for the Nash Dip Meter math, shared by the dashboard
(`app.py`) and the daily snapshot job. Same rules and the same
quality map as the Divergence Alert scanner:

  - 52-week high  = highest daily CLOSE in the trailing 252 trading
    days. The Radar fetches "1y" of history (~250-252 rows), so we
    take the high over UP TO 252 closes of what was fetched.
  - % off high    = (close / 52-week high - 1) * 100  — always <= 0.
  - Stock DIP     : 20%+ below its 52-week high -> DIP — ACCELERATE
  - Market TOO HOT: SPY up 20%+ over the trailing 30 CALENDAR days
    -> TOO HOT — SLOW DOWN, and it beats a stock-level DIP badge
    (headline precedence per Frank's rules).
  - Badge only shows for stocks in the quality map (scored names).
"""

from datetime import timedelta

# Luna's six-check fundamental scorecard, Oct 26, 2026. Keep in sync
# with quality_scores in the Divergence Alert's config.json.
QUALITY_SCORES = {
    "NVDA": 97, "PLTR": 94, "GOOGL": 70,
    "MU": 100, "SNDK": 98, "APP": 93, "ANET": 87,
    "AVGO": 83, "BE": 77, "VRT": 77, "ARM": 71,
}
QUALITY_PASS = 70

TRADING_DAYS_52WK = 252
_MIN_CLOSES = 60          # below this, a "52-week high" is meaningless


def pct_off_52wk_high(history):
    """% below the 52-week high, from already-fetched daily history.
    Returns None (-> rendered "N/A") on short or missing history."""
    if history is None or len(history) == 0 or "Close" not in history:
        return None
    closes = history["Close"].dropna().tail(TRADING_DAYS_52WK)
    if len(closes) < _MIN_CLOSES:
        return None
    high = float(closes.max())
    close = float(closes.iloc[-1])
    return (close / high - 1) * 100


def spy_too_hot(spy_history) -> bool:
    """True when SPY is up 20%+ over the trailing 30 calendar days."""
    if spy_history is None or len(spy_history) == 0:
        return False
    cutoff = spy_history.index[-1] - timedelta(days=30)
    past = spy_history.loc[:cutoff]
    if past.empty:
        return False
    chg = (float(spy_history["Close"].iloc[-1])
           / float(past["Close"].iloc[-1]) - 1) * 100
    return chg >= 20


def dca_state(pct_off, symbol: str, market_hot: bool) -> str:
    """DCA badge for one stock. Empty string = no badge (no score,
    or not enough history to measure the dip)."""
    if symbol not in QUALITY_SCORES or pct_off is None:
        return ""
    if market_hot:
        return "TOO HOT — SLOW DOWN"
    if pct_off <= -20:
        return "DIP — ACCELERATE"
    return "NORMAL"


def fmt_pct_off(pct) -> str:
    return "N/A" if pct is None else f"{pct:.1f}%"
