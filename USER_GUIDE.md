# 📡 Investment Radar — User Guide

A plain-English walkthrough of everything the Radar does, what
each number means, and how to use it day-to-day.

Written for Frank — no coding required to *use* the Radar, though a
couple of terminal commands are needed to start it up.

---

## 1. What the Radar is for

A single place to capture every investment idea you hear about
(from podcasts, YouTube, friends, articles), automatically fill in
the boring metadata, score each one on two dimensions, and rank
them all in a table you can scan in under a minute.

Two goals:
1. **Fill your knowledge gaps.** You never have to know what
   sector NVDA is in — the Radar pulls that from Yahoo Finance.
2. **Rank ideas honestly.** Every ticker gets a numeric score, so
   you can compare AMD vs. NVDA vs. TSLA without leaning on gut
   feel or hype.

The Radar is a **thinking aid**, not a recommendation engine. It
tells you what the numbers say. You still decide what to buy.

---

## 2. Starting the dashboard (on your Mac)

Every time you want to work with the Radar, follow these steps.
This takes about 30 seconds after the first time.

### Step by step

1. **Open Terminal.** Press `Command + Space` to open Spotlight,
   type `Terminal`, hit Enter.

2. **Move into the project folder.** Type this exactly and press
   Enter:
   ```
   cd ~/Investment_Radar
   ```

3. **Turn on the virtual environment.** This makes sure Python
   uses the exact set of libraries the Radar was built with.
   ```
   source venv/bin/activate
   ```
   You should see `(venv)` appear at the start of your prompt.
   That's how you know it worked.

4. **Launch the dashboard.**
   ```
   streamlit run radar/app.py --server.port 9000
   ```
   Your default browser (Chrome) will open a new tab at
   `http://localhost:9000`. First load takes about 15–30 seconds
   because the Radar fetches fresh data from Yahoo for every
   ticker.

5. **When you're done**, come back to the Terminal window and
   press `Control + C` (that's the letter C, not "command"). That
   stops the server. Then close Terminal.

### If something goes wrong

- **"venv/bin/activate: No such file"** → you're not in the right
  folder. Run `cd ~/Investment_Radar` again.
- **"Streamlit: command not found"** → you forgot Step 3. The
  virtual environment isn't on. Re-run `source venv/bin/activate`.
- **Browser shows "This site can't be reached"** → wait a few more
  seconds; Streamlit is still booting.

---

## 3. Adding a new ticker (Mac dashboard only)

You can only add tickers from your Mac dashboard, not the phone
view. The sidebar on the left is where the "add" form lives.

### Two-step add

1. **Type the symbol** in the "Ticker symbol" box. Case doesn't
   matter. For US stocks use the plain symbol (`NVDA`, `AAPL`).
   For crypto, the short form works — the Radar knows that `BTC`
   means Bitcoin, `ETH` means Ethereum, etc.
2. **Click "🔍 Look up info".** The Radar hits Yahoo Finance and
   pulls the full company name, sector, industry, asset type, and
   a one-sentence description.
3. **If Yahoo found it**, you see a preview under the button. Fill
   in the **Theme** field — this is *your* investment thesis tag,
   like `AI`, `Nuclear Energy`, `Semiconductors`, `Dividend
   Play`. You can put multiple, separated by commas. Optionally
   add a **Source** (where you heard about it) and **Notes**.
4. **Click "✓ Add to radar"** and the ticker appears in your
   table below.

### Deleting or editing tickers

- **Delete a row:** hover over it in the table, click the trash
  icon that appears on the left of the row, then click **💾 Save
  changes** below the table.
- **Edit theme, source, or notes:** click any cell in those
  columns, type, then click **💾 Save changes**.
- **Edit things Yahoo got wrong** (like NVDA's sector being
  mislabeled): flip on **🔓 Edit metadata mode** above the table.
  The name, sector, sub_sector, asset_type, and description
  columns become editable. Fix what you need, click **💾 Save
  changes**, then flip Edit mode back off so you don't accidentally
  overwrite something later.

---

## 4. Reading the main table

From left to right, the columns are:

| Column | What it means |
|---|---|
| **⭐** | Star appears when BOTH Value Score AND Tech Score are ≥ 70. "Quality + Momentum" pick — the academic sweet spot. |
| **current_price** | Most recent daily closing price from Yahoo (not live intraday). Refreshes when you click 🔄 Refresh fundamentals. |
| **past_30d_price** | Closing price 30 trading days ago (about 6 calendar weeks back). Eyeball it against current_price to see recent trajectory. |
| **symbol** | The ticker as Yahoo recognizes it. `BTC-USD` for Bitcoin, `NVDA` for NVIDIA, etc. |
| **composite_score** | The headline number: 0–100. Higher is better. |
| **composite_grade** | Letter grade (with color) for the composite. See §6 for what the letters mean. |
| **value_score** | 0–100 score from 5 fundamentals: debt-to-equity, current ratio, net cash %, ROE, FCF yield. Higher = stronger business. |
| **value_grade** | Letter grade for value. |
| **tech_score** | 0–100 score from 4 price-action signals: Stage 2 uptrend, distance from 20-day high, relative strength vs SPY, ATR sweet spot. Higher = healthier chart. |
| **tech_grade** | Letter grade for tech. |
| **name** | Full company name from Yahoo. |
| **asset_type** | `stock`, `etf`, or `crypto`. |
| **sector / sub_sector** | Yahoo's classification. Sector is the broad bucket ("Technology"), sub_sector is the industry ("Semiconductors"). |
| **theme** | *Your* thesis tag, like "AI" or "Nuclear." Comma-separate multiple. |
| **source** | Where you heard about it. |
| **notes** | Anything else worth remembering. |
| **description** | One-sentence company summary from Yahoo. |
| **date_added** | When you added this ticker. Auto-set. |

### Sorting

- By default, the table is **sorted by composite_score, highest
  first.** The best-ranked idea is always at the top.
- **Click any column header** to re-sort by that column. Click
  again to reverse.
- **Group by sector** (a toggle above the table) clusters all
  tickers in the same sector together, then sub-sectors within
  that, then composite score within that. Useful for comparing
  "which of my Tech Semiconductor stocks is scoring best?"

### Filtering

Click the **🔍 Filter the radar** expander above the table to
narrow what's shown.

- **Sector** — pick one or more (e.g., only show Technology and
  Financial Services).
- **Theme** — pick one or more (e.g., only show tickers tagged
  "AI").
- **Asset type** — stocks only, ETFs only, crypto only, or any
  combination.
- **⭐ Show only Quality + Momentum picks** — checkbox that
  keeps only the ⭐ rows.

Filters affect the table AND the per-ticker charts below. They
don't change your `ideas.csv` file — clearing all selections shows
everything again.

---

## 5. How Value Score works (the fundamentals side)

Five metrics, each scored 0–100. The Value Score is the simple
average of the five sub-scores. Any sub-score that couldn't be
computed (missing data) is dropped from the average, not zeroed.

| Metric | What it measures | Score = 100 at | Score = 0 at |
|---|---|---|---|
| **Debt / Equity** | How leveraged the business is | ≤ 0.25 | ≥ 2.0 |
| **Current Ratio** | Short-term assets vs. short-term bills | ≥ 2.5 | ≤ 1.0 |
| **Net Cash % of MC** | (Cash − Debt) / Market Cap × 100 | ≥ +25% | ≤ −25% |
| **ROE %** | Return on equity | ≥ 25% | ≤ 0% |
| **FCF Yield %** | Free cash flow / Market cap | ≥ 10% | ≤ 0% |

Values between the two extremes scale linearly. A debt-to-equity
of 1.1 (halfway between 0.25 and 2.0) scores about 50.

**Value Score is stocks-only.** ETFs and crypto have no
fundamentals of the sort we're measuring, so they show **N/A** in
the value_score column — by design, not a bug.

---

## 6. How Tech Score works (the price-action side)

Four metrics, each scored 0–100. Tech Score is the simple average.

| Metric | What it measures | Score = 100 when… | Score = 0 when… |
|---|---|---|---|
| **Stage 2 trend** | Price above 30-week moving average AND the MA sloping up | Both true | Either is false |
| **% below 20-day high** | How far below the last 20 days' high are we? | Within 0–2% of high | > 20% below high |
| **RS vs SPY (90-day)** | Ticker's 90-day return minus SPY's | Beat SPY by ≥ 20 pts | Trailed SPY by ≥ 20 pts |
| **ATR %** | Average True Range as % of price — volatility sweet spot | Between 2% and 5% | Below 0.5% or above 10% |

The ATR metric is a *band*, not a slope — too little volatility
means dead money, too much means casino. The 2–5% band is where
swing setups typically live.

**Tech Score works for all asset types** — stocks, ETFs, AND
crypto — because it's derived only from price history.

---

## 7. How Composite Score works

`composite_score = 0.5 × value_score + 0.5 × tech_score`

Simple 50/50 blend. Two special cases:
- **If Value Score is N/A** (ETFs, crypto, or missing data), the
  composite is just the Tech Score. Not zero-weighted — we use
  whatever signal we DO have.
- **If both are N/A**, composite is N/A.

This is the number the table sorts by. It's also the number the
star (⭐) uses to decide "quality + momentum" — both value AND
tech must be ≥ 70 for the star to appear.

---

## 8. How to read the grade letters

Every 0–100 score maps to an A–F letter with a colored circle:

| Score range | Grade | Meaning |
|---|---|---|
| 85–100 | 🟢 **A — Excellent** | Top-tier. Rare. Investigate why. |
| 70–84 | 🟢 **B — Strong** | Comfortably better than baseline. |
| 50–69 | 🟡 **C — Average** | Neither a green nor red flag. |
| 25–49 | 🟠 **D — Weak** | Yellow flag. Investigate before sizing. |
| 0–24 | 🔴 **F — Poor** | Red flag on this dimension. |
| — | ⚫ **N/A** | Couldn't be computed (e.g., ETF value score). |

Same bands apply to every score in the app — sub-scores, Value,
Tech, Composite. So a Value Score of 78 reads as *"Strong on
fundamentals."* A Composite of 44 reads as *"Weak overall — think
twice."*

---

## 9. Clicking any ticker for the full breakdown

Below the table, each ticker gets its own expander (a
collapsible section). Click any of them to see:

- **Full description** from Yahoo.
- **Value Score breakdown** — the raw numbers Yahoo reported
  (debt/equity, ROE, etc.) alongside each metric's sub-score.
- **Tech Score breakdown** — the raw numbers (Stage 2 boolean,
  ATR%, etc.) alongside each metric's sub-score.
- **1-year price chart.**
- **Quick stats:** latest close, price 90 days ago, 90-day change %.

This is where you go when a ticker's headline score surprises
you. If NVDA has a Composite B but you thought it should be A,
the breakdown shows you which sub-scores dragged it down.

---

## 10. Refresh fundamentals

The **🔄 Refresh fundamentals** button clears the internal
30-minute cache and re-pulls every ticker from Yahoo. Use it:
- After a company's earnings release (fundamentals change).
- If a number looks wrong and you want a fresh read.
- Otherwise, let the cache do its work — every re-load of the page
  within 30 minutes is nearly instant.

---

## 11. Snapshots (looking back in time)

Click **📸 Snapshot today** to save the current state of the
Radar to a dated CSV in the `snapshots/` folder next to your
project. Every ticker's scores and prices get frozen for that
day. Same-day clicks overwrite (you get the latest read of the
day, not duplicates).

Below the per-ticker expanders, a **📅 Past snapshots** section
lets you pick any past date and see what your Radar looked like
then.

Snapshots let you answer *"Had NVDA been trending up in the weeks
before I bought it?"* — a question you can't ask the live view.

### Automated daily snapshots (optional)

A macOS launchd job (a scheduled task) can auto-snapshot every
morning at 8 AM so you don't have to remember. See the
`launchd/` folder — the `.plist` file inside has install
instructions in the comments.

---

## 12. Filters, deletions, and edits — the save flow

Any change you make in the table (edit a cell, delete a row)
stays in the browser only until you click **💾 Save changes**.
Refreshing the page before saving throws away the edits.

Once you click Save, the changes get written to `ideas.csv` in
your Investment_Radar folder AND (if you set it up) your iCloud
Drive copy. Both stay in sync automatically.

---

## 13. The phone view (Streamlit Cloud)

Once you've published your Radar to Streamlit Community Cloud (a
one-time setup — see `PHONE_ACCESS_SETUP.md`), you can visit
your dashboard from any phone or browser at
`frank-investment-radar.streamlit.app`.

**The phone view is read-only.** You'll see:
- Same table, same scores, same charts.
- Sidebar says "📱 Phone view — read only" instead of the add
  form.
- No Save, no Snapshot, no Edit toggle.

**To update the phone view with new tickers or edits:**
1. Add/edit as usual on your Mac dashboard, click Save.
2. Open **GitHub Desktop** — you'll see `ideas.csv` and
   `latest_metrics.csv` in the Changes panel.
3. Type a short commit message ("Add MU" or whatever), click
   **Commit to main**, then **Push origin** at the top.
4. Wait about a minute. Streamlit Cloud auto-detects the new
   commit and rebuilds. Refresh your phone browser — new data
   is there.

### Why scores work on Mac but not directly on phone

Yahoo Finance's fundamentals endpoint is rate-limited from cloud
servers (they block datacenter IPs). Your Mac's home IP is fine.
So the Mac dashboard fetches fresh fundamentals, and it also
writes them to `latest_metrics.csv`. The phone view reads the CSV
instead of calling Yahoo. **Result: your phone always shows the
scores your Mac last saw** — which is exactly what you want.

---

## 14. Sync workflow — one-line summary

| Change on Mac | To reach phone |
|---|---|
| Added a ticker, saved | Push `ideas.csv` + `latest_metrics.csv` via GitHub Desktop |
| Edited a theme, saved | Same |
| Deleted a row, saved | Same |
| Clicked Refresh fundamentals | Same (metrics changed) |
| Took a snapshot | Optional — push `snapshots/*.csv` if you want past snapshots visible on phone |

Basic rule: **any time you save on Mac, do a GitHub Desktop
commit + push before you leave the house.** Then the phone view
is fresh.

---

## 15. Where things live

```
~/Investment_Radar/
├── radar/                     # The Python code
│   ├── app.py                 # The dashboard
│   ├── load_data.py           # Reads ideas.csv
│   ├── lookup.py              # Yahoo ticker lookup
│   ├── fundamentals.py        # Value-metric fetcher
│   ├── technicals.py          # Price history + tech metric fetcher
│   ├── scoring.py             # All the math
│   ├── latest_metrics.py      # Mac→Cloud metric sync
│   ├── snapshots.py           # Daily snapshot CSVs
│   └── daily_snapshot.py      # Headless CLI for scheduled runs
├── launchd/                   # macOS auto-schedule plist
├── snapshots/                 # Dated CSV snapshots (auto-created)
├── ideas.csv                  # YOUR WATCHLIST — the one file you edit
├── latest_metrics.csv         # Auto-written scores for phone view
├── requirements.txt           # Python dependencies
├── venv/                      # The isolated Python setup (git-ignored)
├── PHASE_4_PLAN.md            # The build history
├── PHONE_ACCESS_SETUP.md      # One-time hosting setup guide
├── USER_GUIDE.md              # This file
└── README.md                  # High-level project blurb
```

The only file you ever edit by hand is `ideas.csv` (and only
through the dashboard's Save button — don't open it in Numbers
while Streamlit is running).

---

## 16. If something breaks

- **Dashboard shows the wrong price for a crypto ticker** (e.g.
  BTC showing $8 instead of $67,000) — Yahoo probably matched
  your symbol to a trust product. Delete the row and re-add
  using `BTC-USD` explicitly, or edit the row's symbol via
  the Edit mode toggle.
- **Value Score shows N/A for a stock** — Yahoo may have stopped
  reporting a metric. Click 🔄 Refresh fundamentals; if it's
  persistent, the company probably went private / delisted /
  had a corporate action.
- **Phone view is showing old data** — you forgot to push. Open
  GitHub Desktop, commit + push. Wait 60 seconds, refresh phone.
- **Streamlit dashboard won't open** — double-check the Terminal
  says `(venv)` and the command is `streamlit run radar/app.py
  --server.port 9000`.

---

## 17. Not investment advice

The Radar's numbers are a decision-support tool, not a
recommendation. The scoring thresholds come from standard
quality-investing literature (Buffett-style screens, Weinstein
Stage Analysis, etc.), but past behavior is not future returns.
Always do your own research before committing capital.
