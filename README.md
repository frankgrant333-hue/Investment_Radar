# 📡 Investment Radar

A personal investment-idea capture, scoring, and ranking tool.
Type in a ticker, the Radar auto-fills the metadata from Yahoo
Finance, computes fundamental + technical scores, and ranks every
idea on your watchlist by a composite score with an A–F grade.

Built with Python + Streamlit + pandas + yfinance.

This project is intentionally separate from the trade bot
(`~/Tradebot_Restore`). The trade bot is for **automated
paper-trading** of short-term swing setups. The Radar is for
**manual brokerage decisions** in your personal account — both
short-term and long-term — where you want to track ideas you hear
from podcasts, YouTube channels, friends, and research, then rank
them by a combination of value and technical signals.

## What it does

- **Capture** — sidebar form to add tickers. Type a symbol; the
  Radar pulls the name, sector, industry, and description from
  Yahoo. You only supply your own theme tag ("AI", "Nuclear",
  etc.) and optional notes.
- **Score** — for stocks, a Value Score (5 fundamental metrics:
  debt/equity, current ratio, net cash %, ROE, FCF yield) and a
  Tech Score (4 signals: Weinstein Stage 2, 20-day-high proximity,
  relative strength vs SPY, ATR sweet spot). ETFs and crypto get
  Tech Score only. A Composite Score blends the two, with A–F
  grades on the 0–100 scale.
- **Rank** — the table sorts by Composite Score descending. A ⭐
  column marks "Quality + Momentum" picks (both scores ≥ 70).
- **Filter** — narrow by sector, theme, or asset type.
- **Detail** — click any ticker for a full breakdown: description,
  every sub-score with its raw value and grade, 1-year price chart,
  quick stats.
- **History** — daily snapshots let you look back at "what did my
  radar say on June 1?"

## Running it

### On your Mac (full interactive)

```bash
cd ~/Investment_Radar
source venv/bin/activate
streamlit run radar/app.py --server.port 9000
```

Then open http://localhost:9000 in your browser.

### On Streamlit Community Cloud (phone-friendly, read-only)

The hosted version reads the same `ideas.csv` from this repo and
computes the same scores. It's automatically read-only — adding,
editing, saving, and taking snapshots are Mac-only actions. To
update the phone view, edit locally and push to GitHub.

## Project layout

```
Investment_Radar/
├── radar/
│   ├── app.py              # Streamlit dashboard (the UI)
│   ├── load_data.py        # Reads ideas.csv → DataFrame
│   ├── lookup.py           # Yahoo lookup + crypto alias map
│   ├── fundamentals.py     # Value-metric fetcher
│   ├── technicals.py       # Price-history + tech-metric fetcher
│   ├── scoring.py          # All the math — 0-100 scores + A-F grades
│   ├── snapshots.py        # Daily-snapshot CSV read/write
│   └── daily_snapshot.py   # Headless CLI for scheduled snapshots
├── launchd/                # macOS launchd plist for daily auto-snapshot
├── snapshots/              # Dated CSV snapshots
├── ideas.csv               # Your watchlist (schema: 10 columns)
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Not investment advice

This tool is a personal thinking aid, not a recommendation engine.
The scoring thresholds are standard "rules of thumb" from
quality-investing literature, not proven predictors. Always do
your own research before committing capital.
