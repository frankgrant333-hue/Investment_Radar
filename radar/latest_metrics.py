"""
radar/latest_metrics.py
=======================

The "Mac→Cloud bridge." Yahoo's `.info` endpoint (which powers our
Value Score) is rate-limited from datacenter IPs. That means on
Streamlit Community Cloud, `fetch_fundamentals()` silently returns
all-None for every ticker — and Value Score becomes N/A everywhere.

Fix: on Frank's Mac (residential IP, Yahoo lets us in), we write
every ticker's raw metrics to `latest_metrics.csv`. When Frank
pushes to GitHub, that file rides along with `ideas.csv`. On the
hosted phone view, we DON'T call Yahoo at all — we read the CSV and
run the pure-math scoring functions on the stored raw values.

Result: phone view shows real Value Scores, computed on Frank's Mac
whenever he last saved from the dashboard.

Design notes:
  - We store RAW metrics (debt_to_equity, ROE, etc.), not derived
    sub-scores. Scoring is deterministic — deriving is cheap and
    lets us tune thresholds without regenerating this file.
  - `computed_at` timestamp so the phone view can say "last scored 2h ago".
  - File lives in the project root next to `ideas.csv`. It's
    committed to git along with everything else.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd


# Same folder as ideas.csv (project root). This file rides in git,
# not iCloud — the whole point is to sync from Mac → GitHub → Cloud.
LATEST_METRICS_PATH = Path(__file__).parent.parent / "latest_metrics.csv"


# The exact columns we serialize. Order matters for stable diffs
# in git — a stable column order means small commits when only a
# few tickers change.
METRICS_COLUMNS = [
    "symbol",
    "computed_at",
    # Prices (already display strings, e.g. "$130.55" or "N/A")
    "current_price",
    "past_30d_price",
    # 5 raw Value metrics — any may be blank if Yahoo returned None
    "debt_to_equity",
    "current_ratio",
    "net_cash_pct",
    "roe",
    "fcf_yield",
    # 4 raw Tech metrics — any may be blank if not enough history
    "stage_2",             # bool as "True"/"False"/"" (missing)
    "dist_from_20d_high",
    "rs_vs_spy",
    "atr_pct",
]


def write_latest_metrics(rows: list[dict]) -> Path:
    """
    Persist per-symbol raw metrics for the hosted phone view to
    consume. `rows` is a list of dicts, one per ticker on the
    radar. Missing values (Yahoo returned None) should be None or
    absent from the dict — pandas will handle them as NaN.

    We overwrite the file every time — no history is kept here.
    Historical snapshots are `radar/snapshots.py`'s job.
    """
    # Ensure every row has a `computed_at` timestamp — makes the
    # phone view able to display "scored 15 min ago".
    now_iso = datetime.now().isoformat(timespec="seconds")
    for row in rows:
        row.setdefault("computed_at", now_iso)

    df = pd.DataFrame(rows)
    # Only keep columns we know about — extra keys silently dropped.
    keep = [c for c in METRICS_COLUMNS if c in df.columns]
    df = df[keep]
    df.to_csv(LATEST_METRICS_PATH, index=False)
    return LATEST_METRICS_PATH


def read_latest_metrics() -> pd.DataFrame:
    """
    Load the cached metrics into a DataFrame. Returns an empty
    DataFrame if the file doesn't exist yet (e.g. fresh clone on
    Streamlit Cloud before the first sync).
    """
    if not LATEST_METRICS_PATH.exists():
        return pd.DataFrame(columns=METRICS_COLUMNS)
    # dtype=str so numeric values keep whatever precision they had
    # when written. We'll parse to float per-column at use-time.
    return pd.read_csv(LATEST_METRICS_PATH, dtype=str).fillna("")


# --- Helpers the app.py cloud-enrichment path uses --------------

def _parse_optional_float(cell: str) -> Optional[float]:
    """Turn a CSV cell (possibly blank) into a float or None."""
    if cell is None or str(cell).strip() == "":
        return None
    try:
        return float(cell)
    except (TypeError, ValueError):
        return None


def _parse_optional_bool(cell: str) -> Optional[bool]:
    """Turn a CSV cell of 'True'/'False'/'' into bool or None."""
    if cell is None:
        return None
    s = str(cell).strip().lower()
    if s in ("true", "1"):
        return True
    if s in ("false", "0"):
        return False
    return None


def metrics_for_symbol(df: pd.DataFrame, symbol: str) -> Optional[dict]:
    """
    Look up one ticker's raw metrics from the DataFrame returned
    by `read_latest_metrics()`. Returns a dict of numeric values
    (with `None` for missing) suitable for feeding directly into
    `scoring.value_score()` / `scoring.tech_score()`.
    """
    if df.empty:
        return None
    hits = df[df["symbol"] == symbol]
    if hits.empty:
        return None
    row = hits.iloc[0]
    return {
        # Prices come back as display strings — leave them alone;
        # the app will just render them as-is.
        "current_price":     row.get("current_price", ""),
        "past_30d_price":    row.get("past_30d_price", ""),
        "computed_at":       row.get("computed_at", ""),
        # Value metrics
        "debt_to_equity":    _parse_optional_float(row.get("debt_to_equity")),
        "current_ratio":     _parse_optional_float(row.get("current_ratio")),
        "net_cash_pct":      _parse_optional_float(row.get("net_cash_pct")),
        "roe":               _parse_optional_float(row.get("roe")),
        "fcf_yield":         _parse_optional_float(row.get("fcf_yield")),
        # Tech metrics
        "stage_2":            _parse_optional_bool(row.get("stage_2")),
        "dist_from_20d_high": _parse_optional_float(row.get("dist_from_20d_high")),
        "rs_vs_spy":          _parse_optional_float(row.get("rs_vs_spy")),
        "atr_pct":            _parse_optional_float(row.get("atr_pct")),
    }
