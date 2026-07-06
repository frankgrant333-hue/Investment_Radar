"""
radar/snapshots.py
==================

Daily score history. Each day you click "📸 Snapshot today" (or each
morning the launchd job fires), this writes a CSV with the current
state of your radar to `snapshots/YYYY-MM-DD.csv` — sitting right
next to your `ideas.csv` (in iCloud Drive if you've set that up).

Why we want this:
  - Recall: "What did NVDA's composite look like on June 1?"
  - Trend: A ticker whose composite has been climbing for weeks is
    a different bet than one that just spiked yesterday.
  - Honesty: It's harder to fool yourself about a thesis when there's
    a written record of what the Radar told you on the day.

The snapshot is a *summary*, not the raw fundamentals/technicals.
We store the headline numbers (scores, grades, prices) — enough to
reconstruct "where did this ticker stand?" without ballooning into
gigabytes of price history.
"""

from pathlib import Path
from datetime import date as _date
from typing import Optional
import pandas as pd

# We put snapshots next to ideas.csv so iCloud sync (if active)
# picks them up automatically. Import is deferred inside functions
# to avoid pulling in pandas at module-import time for callers that
# only need list_snapshots().


def _snapshots_dir() -> Path:
    """Where snapshots live — always next to the active ideas.csv."""
    from radar.load_data import DEFAULT_CSV_PATH
    return DEFAULT_CSV_PATH.parent / "snapshots"


# These are the columns we save in each daily snapshot. Anything in
# the in-memory DataFrame that's NOT in this list is silently
# dropped. Order is the on-disk order — easy to eyeball in Excel.
SNAPSHOT_COLUMNS = [
    "symbol", "name", "asset_type",
    "current_price", "past_30d_price",
    "qm",
    "composite_score", "composite_grade",
    "value_score", "value_grade",
    "tech_score", "tech_grade",
    "theme",
]


def take_snapshot(scored_df: pd.DataFrame,
                  when: Optional[_date] = None) -> Path:
    """
    Persist the current state of the radar to a dated CSV.

    Parameters
    ----------
    scored_df : pd.DataFrame
        The fully-enriched ideas DataFrame from app.py — i.e., one
        that has the score and price columns already attached.
    when : date, optional
        Which date to label this snapshot. Defaults to today.

    Returns
    -------
    Path of the written file. If a snapshot for that date already
    exists, it's OVERWRITTEN — that's deliberate: re-running on the
    same day should give you the most recent intraday read, not a
    sprawl of duplicates.
    """
    when = when or _date.today()
    snap_dir = _snapshots_dir()
    # mkdir(parents=True) makes the dir AND any missing parents.
    # exist_ok=True so it's safe to call when the dir already exists.
    snap_dir.mkdir(parents=True, exist_ok=True)
    path = snap_dir / f"{when.isoformat()}.csv"

    # Only write columns we actually have — some may be absent if
    # the caller passed a partially-enriched DataFrame.
    cols = [c for c in SNAPSHOT_COLUMNS if c in scored_df.columns]
    scored_df[cols].to_csv(path, index=False)
    return path


def list_snapshots() -> list[str]:
    """
    Return every snapshot date we've taken, sorted oldest-first.

    Returns ISO date strings ("2026-06-30") because that's what the
    file basenames are — and ISO strings sort correctly as strings,
    no date-parsing required.
    """
    snap_dir = _snapshots_dir()
    if not snap_dir.exists():
        return []
    return sorted(p.stem for p in snap_dir.glob("*.csv"))


def load_snapshot(date_str: str) -> pd.DataFrame:
    """
    Read one snapshot CSV by ISO date ("2026-06-30").

    Returns an empty DataFrame if the snapshot doesn't exist — same
    safe-default pattern as the other readers in this project.
    """
    snap_dir = _snapshots_dir()
    path = snap_dir / f"{date_str}.csv"
    if not path.exists():
        return pd.DataFrame()
    # dtype=str so prices stay as "$130.55" strings, not parsed back
    # into floats with weird rounding.
    return pd.read_csv(path, dtype=str).fillna("")
