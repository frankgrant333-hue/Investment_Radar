"""
radar/load_data.py
==================

Job: open the ideas.csv file you maintain by hand, hand it back as a
clean pandas DataFrame, and complain loudly (with a useful message) if
the file is missing or has the wrong columns.

This is intentionally the smallest possible "first real Python file."
Read it top to bottom — every block has a comment explaining the
*idea*, not just the syntax.
"""

# --- 1. Imports -------------------------------------------------------
#
# `import` makes another library's code available inside this file.
# Convention: pandas is *always* renamed to `pd` for brevity. You'll
# see `pd.something` constantly in this project and in every pandas
# tutorial online.
import pandas as pd

# `Path` is Python's modern way to talk about file paths. Better than
# raw strings ("/Users/frank/...") because it knows how to join
# folders together, check existence, etc. across Mac / Linux / Windows.
from pathlib import Path


# --- 2. Constants -----------------------------------------------------
#
# By convention in Python, ALL_CAPS names mean "this is a constant —
# don't reassign it." These are the columns the README promises will
# exist in ideas.csv. If any are missing, we fail with a clear message
# instead of getting weird errors deep inside the dashboard later.

REQUIRED_COLUMNS = [
    "symbol",
    "name",
    "asset_type",
    "sector",
    "theme",
    "description",
    "date_added",
]

# Where ideas.csv lives.
#
# We check two places, in this order:
#   1. iCloud Drive (~/Library/Mobile Documents/com~apple~CloudDocs/Investment_Radar/
#      ideas.csv). If the file exists here, the dashboard reads and writes
#      this copy. iCloud auto-syncs it to your iPhone's Files app, so you
#      can view your tickers from anywhere on mobile.
#   2. The project folder next to this radar/ package. This is the
#      fallback if iCloud isn't set up — keeps the dashboard working out
#      of the box.
#
# To switch FROM local TO iCloud-synced: move ideas.csv into the iCloud
# folder above. The dashboard will pick up the new location automatically.

_ICLOUD_CSV_PATH = (
    Path.home()
    / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
    / "Investment_Radar" / "ideas.csv"
)
_LOCAL_CSV_PATH = Path(__file__).parent.parent / "ideas.csv"

# Prefer iCloud if it exists; otherwise stay local.
DEFAULT_CSV_PATH = _ICLOUD_CSV_PATH if _ICLOUD_CSV_PATH.exists() else _LOCAL_CSV_PATH


# --- Write helper -----------------------------------------------------
#
# When Frank saves changes on his Mac, we want the local repo copy
# AND the iCloud copy to stay in sync — so Streamlit Cloud (which
# only sees the local repo copy) doesn't fall behind, AND the iOS
# Files-app view of ideas.csv also stays fresh.
#
# On Streamlit Cloud (Linux), the iCloud path won't exist and we
# only ever write to local. That's a no-op because writes on Cloud
# aren't expected anyway (the hosted app is read-only).

def write_ideas(df) -> list[Path]:
    """
    Persist ideas.csv to every relevant location.

    Returns
    -------
    list of Paths that were successfully written to.
    """
    written = []
    # Always write the local repo copy — that's what the hosted phone
    # view reads. If we skipped this on Mac, the phone view would
    # fall behind every save.
    df.to_csv(_LOCAL_CSV_PATH, index=False)
    written.append(_LOCAL_CSV_PATH)

    # Mirror to iCloud if that folder is configured. Failures here
    # are non-fatal (e.g. iCloud offline, permission issue) — the
    # local write already succeeded.
    if _ICLOUD_CSV_PATH.parent.exists():
        try:
            df.to_csv(_ICLOUD_CSV_PATH, index=False)
            written.append(_ICLOUD_CSV_PATH)
        except OSError:
            pass

    return written


# --- 3. The one function this module exposes --------------------------

def load_ideas(csv_path: Path = DEFAULT_CSV_PATH) -> pd.DataFrame:
    """
    Read ideas.csv and return it as a pandas DataFrame.

    Why wrap this in a function instead of just running the code at the
    top of the file? So the rest of the project (app.py, scoring.py,
    future tests) can `import` this one function and call it, instead
    of re-implementing CSV reading in five places.

    Parameters
    ----------
    csv_path : Path
        Where to find ideas.csv. Defaults to the file sitting next to
        the radar/ folder.

    Returns
    -------
    pd.DataFrame
        One row per ticker, with the columns from the README schema.

    Raises
    ------
    FileNotFoundError
        If ideas.csv doesn't exist at the given path.
    ValueError
        If ideas.csv is missing one of the required columns.
    """

    # 3a. Does the file even exist?
    #     Better to ask now and give a friendly message than to let
    #     pandas error out with something more cryptic.
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Couldn't find ideas.csv at: {csv_path}\n"
            "Make sure you're running this from inside the "
            "Investment_Radar folder, and that ideas.csv exists there."
        )

    # 3b. Read the CSV. pandas does the heavy lifting in one call.
    #     `dtype=str` tells pandas: "read every cell as plain text,
    #     don't try to guess types yet." We'll convert specific columns
    #     to numbers later when we need them. This avoids surprises
    #     like a ticker "BRK.B" being parsed as a number.
    df = pd.read_csv(csv_path, dtype=str)

    # 3c. Check that all the required columns are present.
    #     A list comprehension: "for each col in REQUIRED_COLUMNS,
    #     keep it only if it's NOT in df.columns." The result is the
    #     list of missing column names — empty if all are present.
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"ideas.csv is missing required columns: {missing}\n"
            f"Required columns are: {REQUIRED_COLUMNS}\n"
            f"Found columns are:    {list(df.columns)}"
        )

    # 3d. Trim accidental whitespace from every text cell. Common when
    #     humans edit CSVs in Excel — a stray space before a ticker
    #     would later cause "NVDA " to not match "NVDA".
    #
    #     For each column: replace NaN (empty cells) with empty string
    #     first, then strip whitespace. `.fillna("")` is the safe
    #     handling for blank optional fields like `notes`.
    for col in df.columns:
        df[col] = df[col].fillna("").str.strip()

    return df


# --- 4. Run-this-file-directly block ----------------------------------
#
# `if __name__ == "__main__":` is Python's idiom for:
# "only run the code below if this file is being executed directly,
# NOT if it's being imported by another file."
#
# So when you run `python -m radar.load_data` in the terminal, this
# fires. When app.py later does `from radar.load_data import load_ideas`,
# this block is skipped — exactly what we want.

if __name__ == "__main__":
    # try / except = "attempt this code; if a specific error happens,
    # catch it and react gracefully instead of crashing with a stack
    # trace." Friendlier for a beginner running their first script.
    try:
        ideas = load_ideas()
    except FileNotFoundError as err:
        print("File-not-found error:")
        print(err)
        raise SystemExit(1)
    except ValueError as err:
        print("Schema error in ideas.csv:")
        print(err)
        raise SystemExit(1)

    # `len(df)` = number of rows. An empty CSV (just the header row)
    # is a totally valid state at this stage — we just say so.
    if len(ideas) == 0:
        print("ideas.csv loaded successfully — but it has no ticker rows yet.")
        print(f"Columns present: {list(ideas.columns)}")
        print("Add one or more rows to ideas.csv, save, then re-run this script.")
    else:
        print(f"Loaded {len(ideas)} ticker(s) from ideas.csv:\n")
        # `.to_string(index=False)` prints the table without the row
        # numbers on the left (cleaner terminal output than `print(df)`).
        print(ideas.to_string(index=False))
