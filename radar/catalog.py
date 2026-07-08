"""
radar/catalog.py
================

Job: load catalog.csv — the master menu of tickers organized by
sector and sub-sector — so the dashboard can show it as a browsable,
click-to-add catalog.

catalog.csv is YOURS to edit. Open it in Excel or Numbers, add a row
with symbol/name/asset_type/sector/sub_sector, save — the catalog
section in the dashboard picks it up on the next refresh.
"""

import pandas as pd
from pathlib import Path

# catalog.csv sits in the project root, next to ideas.csv.
CATALOG_PATH = Path(__file__).parent.parent / "catalog.csv"


def load_catalog() -> pd.DataFrame:
    """
    Read catalog.csv and return a clean DataFrame.
    Returns an EMPTY DataFrame (not an error) if the file is missing —
    the dashboard simply hides the catalog section in that case.
    """
    if not CATALOG_PATH.exists():
        return pd.DataFrame(
            columns=["symbol", "name", "asset_type", "sector", "sub_sector"]
        )

    df = pd.read_csv(CATALOG_PATH, dtype=str)
    for col in df.columns:
        df[col] = df[col].fillna("").str.strip()
    return df
