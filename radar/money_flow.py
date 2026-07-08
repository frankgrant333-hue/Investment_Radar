"""
radar/money_flow.py
===================

Job: figure out which sectors "big money" is rotating INTO right now.

How it works (plain English):
    Every sector of the US market has an official ETF that tracks it —
    XLK is Technology, XLE is Energy, and so on. Each trading day,
    (closing price x shares traded) tells you how many DOLLARS moved
    through that sector. We call that "dollar volume".

    To spot money FLOWING (not just sitting), we compare recent dollar
    volume against the period just before it:

        flow = (dollar volume, last N days) / (dollar volume, prior N days) - 1

    A flow of +0.25 means 25% MORE money traded in that sector lately
    than in the previous stretch — money is accelerating in. Negative
    means money is drying up.

    We compute this for three windows — 5, 15, and 30 trading days —
    so you can see the fast pulse and the slower rotation at once.
"""

import pandas as pd
import yfinance as yf

# The 11 GICS sectors and their SPDR sector ETFs.
SECTOR_ETFS = {
    "XLK":  "Technology",
    "XLC":  "Communication",
    "XLY":  "Consumer Discret.",
    "XLP":  "Consumer Staples",
    "XLE":  "Energy",
    "XLF":  "Financials",
    "XLV":  "Healthcare",
    "XLI":  "Industrials",
    "XLB":  "Materials",
    "XLRE": "Real Estate",
    "XLU":  "Utilities",
}

WINDOWS = (5, 15, 30)  # trading days


def compute_sector_flow() -> pd.DataFrame | None:
    """
    Fetch ~4 months of history for all 11 sector ETFs and compute the
    flow ratio for each window.

    Returns
    -------
    DataFrame indexed by sector name with one column per window
    (e.g. "5d", "15d", "30d"), values are flow ratios (0.25 = +25%).
    Returns None if the download failed (no network, Yahoo hiccup) —
    the caller decides how to degrade gracefully.
    """
    try:
        # One batched download is much faster than 11 separate calls.
        # 4 months ≈ 85 trading days — enough for 30d + prior 30d.
        raw = yf.download(
            list(SECTOR_ETFS.keys()),
            period="4mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception:
        return None

    if raw is None or len(raw) == 0:
        return None

    rows = {}
    for etf, sector in SECTOR_ETFS.items():
        try:
            close = raw[etf]["Close"].dropna()
            volume = raw[etf]["Volume"].dropna()
        except (KeyError, TypeError):
            continue  # this ETF failed — skip it, keep the rest

        dollar_vol = (close * volume).dropna()
        if len(dollar_vol) < 2 * max(WINDOWS):
            continue  # not enough history to compare fairly

        row = {}
        for w in WINDOWS:
            recent = dollar_vol.iloc[-w:].sum()          # last N days
            prior = dollar_vol.iloc[-2 * w:-w].sum()     # N days before that
            row[f"{w}d"] = (recent / prior) - 1 if prior > 0 else 0.0
        rows[sector] = row

    if not rows:
        return None
    return pd.DataFrame.from_dict(rows, orient="index")


def top_sectors(flow_df: pd.DataFrame, window: str, n: int = 3) -> list[tuple[str, float]]:
    """
    Rank sectors by flow for one window and return the top `n`
    as (sector name, flow ratio) pairs, best first.
    """
    ranked = flow_df[window].sort_values(ascending=False).head(n)
    return list(ranked.items())
