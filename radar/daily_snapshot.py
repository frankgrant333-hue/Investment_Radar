"""
radar/daily_snapshot.py
=======================

Headless equivalent of the dashboard's enrichment loop. Run this
once a day from a scheduler (macOS launchd, cron, etc.) and it will:

  1. Read ideas.csv
  2. Fetch fundamentals + price history for every ticker
  3. Compute Value / Tech / Composite scores + the Q+M flag
  4. Write the result to snapshots/YYYY-MM-DD.csv

No Streamlit involved — this is pure Python, safe to run from a
background job when the dashboard isn't open.

Run manually:
    cd ~/Investment_Radar
    source venv/bin/activate
    python -m radar.daily_snapshot

Run automatically: install the launchd plist (see ../launchd/) — full
instructions are in the README at the bottom of this milestone.
"""

import sys
from datetime import date

from radar.load_data import load_ideas
from radar.fundamentals import fetch_fundamentals
from radar.technicals import fetch_history, compute_technicals
from radar.scoring import (
    value_score, tech_score, composite_score, grade_letter,
)
from radar.snapshots import take_snapshot


def _format_price(close: float | None) -> str:
    return "N/A" if close is None else f"${close:,.2f}"


def enrich_and_snapshot() -> None:
    """Read ideas, score everything, write today's snapshot."""
    print(f"[{date.today().isoformat()}] Investment Radar daily snapshot")
    print("=" * 60)

    print("Loading ideas.csv…")
    ideas = load_ideas()
    if len(ideas) == 0:
        print("  ideas.csv is empty — nothing to snapshot. Exiting.")
        return
    print(f"  Loaded {len(ideas)} tickers.")

    print("\nFetching SPY benchmark history…")
    spy_history = fetch_history("SPY")
    if spy_history.empty:
        print("  ⚠ SPY history fetch failed — RS-vs-SPY scores will be N/A.")
    else:
        print(f"  Got {len(spy_history)} days of SPY data.")

    # Buffers — one entry per ticker, in row order.
    cur_prices, past_prices = [], []
    v_scores_d, v_grades_d = [], []
    t_scores_d, t_grades_d = [], []
    c_scores_d, c_grades_d = [], []
    qm_stars = []

    print("\nScoring each ticker:")
    for _, row in ideas.iterrows():
        symbol     = row["symbol"]
        asset_type = row["asset_type"]
        print(f"  - {symbol:8s}", end=" ")

        # ---- Value side ----
        funds = fetch_fundamentals(symbol, asset_type)
        v_s = value_score(funds)
        v_g = grade_letter(v_s)

        # ---- Tech side ----
        history = fetch_history(symbol)
        if history is None or history.empty:
            t_s = None
            cur_close, past_close = None, None
        else:
            metrics = compute_technicals(history, spy_history)
            t_s = tech_score(metrics)
            cur_close = float(history["Close"].iloc[-1])
            past_close = (
                float(history["Close"].iloc[-30])
                if len(history) >= 30 else None
            )
        t_g = grade_letter(t_s)

        # ---- Composite + Q+M ----
        c_s = composite_score(v_s, t_s)
        c_g = grade_letter(c_s)
        qm_hit = (
            v_s is not None and v_s >= 70 and
            t_s is not None and t_s >= 70
        )

        # ---- Buffer for the DataFrame ----
        cur_prices.append(_format_price(cur_close))
        past_prices.append(_format_price(past_close))
        v_scores_d.append("N/A" if v_s is None else f"{round(v_s)}")
        v_grades_d.append(v_g)
        t_scores_d.append("N/A" if t_s is None else f"{round(t_s)}")
        t_grades_d.append(t_g)
        c_scores_d.append("N/A" if c_s is None else f"{round(c_s)}")
        c_grades_d.append(c_g)
        qm_stars.append("⭐" if qm_hit else "")

        print(f"composite={c_scores_d[-1]:>3} ({c_g})  "
              f"v={v_scores_d[-1]:>3}/{v_g}  t={t_scores_d[-1]:>3}/{t_g}  "
              f"{qm_stars[-1]}")

    # Attach computed columns. Same names the dashboard uses.
    ideas["current_price"]   = cur_prices
    ideas["past_30d_price"]  = past_prices
    ideas["qm"]              = qm_stars
    ideas["composite_score"] = c_scores_d
    ideas["composite_grade"] = c_grades_d
    ideas["value_score"]     = v_scores_d
    ideas["value_grade"]     = v_grades_d
    ideas["tech_score"]      = t_scores_d
    ideas["tech_grade"]      = t_grades_d

    print()
    path = take_snapshot(ideas)
    print(f"✓ Snapshot written to {path}")


if __name__ == "__main__":
    try:
        enrich_and_snapshot()
    except Exception as e:
        # Print to stderr so launchd's ErrorPath catches it cleanly.
        print(f"FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
