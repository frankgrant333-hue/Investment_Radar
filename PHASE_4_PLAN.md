# Phase 4.1 Plan — Read-Only Streamlit Dashboard

*This is the plan document the README promised. Read it once end-to-end
before any code gets written. It's intentionally chatty because you're
new to Python — every choice is explained, not just stated.*

---

## 1. What we're actually building (in one paragraph)

A small web page that runs on **your own computer** (not the public
internet). When you open it, it reads `ideas.csv`, goes out to Yahoo
Finance to download fresh fundamentals and price history for every
ticker on the list, computes two scores per ticker (Value Score and
Technical Score), and shows everything as a sortable table. You'll be
able to click a column header to sort, and that's it for 4.1. No
filtering, no detail pages, no "buy this now" highlight — those come in
4.2 and 4.3. The goal of 4.1 is just: *prove the pipeline works
end-to-end on at least one ticker.*

---

## 2. The data flow, drawn out

```
   ideas.csv  ─┐
               │
               ▼
        +──────────────+        +──────────────+
        │  load_data   │ ─────► │   yfinance   │  (internet call)
        │   (pandas)   │ ◄───── │ fundamentals │
        +──────────────+        +──────────────+
               │
               ▼
        +──────────────+
        │   scoring    │  (pure math, no internet)
        │  value+tech  │
        +──────────────+
               │
               ▼
        +──────────────+
        │  Streamlit   │  ──► your browser at http://localhost:8501
        │   web page   │
        +──────────────+
```

Each box becomes one Python file. We'll build them in that order.

---

## 3. Tools we'll use, and why

| Tool | What it is | Why we picked it |
|---|---|---|
| **Python 3.11+** | The programming language. | Free, mature, huge ecosystem for finance. You already have it if the trade bot runs. |
| **pandas** | A library for working with tables of data. Think "Excel inside Python". | The CSV becomes a pandas DataFrame; scoring is just adding columns. |
| **yfinance** | Free, unofficial Python wrapper around Yahoo Finance data. | Gives us price history + fundamentals without an API key. Reliable enough for personal use. Not for production trading. |
| **Streamlit** | A library that turns a Python script into a web page. You write Python, you get a UI. | Zero front-end knowledge required. One command (`streamlit run app.py`) and a browser tab pops open. |
| **venv** | Python's built-in tool for isolating project dependencies. | Keeps Investment Radar's library versions from clashing with the trade bot's. Strongly recommended even for hobby projects. |

**Beginner note on libraries:** A "library" in Python is just a folder
of pre-written code you can use. You install them with `pip install
<name>`. They live inside your virtual environment (the `venv` folder),
not globally on your computer, which is why the venv matters — you can
delete it and start over without breaking anything else.

---

## 4. The folder layout after Phase 4.1 is done

```
Investment_Radar/
├── README.md                ← already exists
├── ideas.csv                ← already exists (you fill it)
├── ideas_example.csv        ← already exists (reference only)
├── themes/themes.md         ← already exists
├── PHASE_4_PLAN.md          ← this file
│
├── requirements.txt         ← NEW: list of libraries we need
├── .gitignore               ← NEW: tells git to ignore the venv folder
├── venv/                    ← NEW: created by you, not committed
│
└── radar/                   ← NEW: all the Python code lives in here
    ├── __init__.py          ← empty file, makes Python treat radar/ as a package
    ├── load_data.py         ← reads ideas.csv, returns a DataFrame
    ├── fundamentals.py      ← fetches Value-Score inputs from yfinance
    ├── technicals.py        ← fetches Tech-Score inputs from yfinance
    ├── scoring.py           ← the math: turns raw numbers into 0-100 scores
    └── app.py               ← the Streamlit page (the "main" file)
```

Why split into so many files? Because each file has **one job**. If the
Value Score formula needs to change in six months, you'll open
`scoring.py`, not hunt through a 400-line `app.py`. This is called
*separation of concerns* — boring rule, big payoff.

---

## 5. The Value Score — what goes in, how we score it

### 5a. How to read any score (this applies to Section 6 too)

Every score in the dashboard sits on a 0-to-100 scale. Higher is
better. Think of it like a school grade — the band tells you what to
feel about the number at a glance.

| Score | Grade | What it means in plain English |
|---|---|---|
| **85 – 100** | **A — Excellent** | Top-tier on this dimension. Rare. Worth a second look. |
| **70 – 84**  | **B — Strong** | Comfortably better than what you'd want to see. |
| **50 – 69**  | **C — Average** | Acceptable, nothing exciting. Neither a green nor red flag. |
| **25 – 49**  | **D — Weak** | Yellow flag. Investigate before adding to a real position. |
| **0 – 24**   | **F — Poor** | Red flag on this dimension. Probably skip, or have a *very* good reason. |
| **N/A** | — | Couldn't be computed (e.g., ETFs don't have Return on Equity). |

Same bands apply to every individual sub-score, the averaged Value
Score, the averaged Technical Score, and the final Composite. So a
Value Score of 78 means "fundamentals are *Strong* on average." In
4.2/4.3 we'll likely color-code these in the dashboard; for 4.1 it's
just the number plus the grade letter in the table.

### 5b. The five fundamental sub-scores

For each metric we set a **ceiling** (the value that earns a 100) and a
**floor** (the value that earns a 0). Anything in between scales
proportionally — so a metric exactly halfway between floor and ceiling
gets a 50.

| Metric | What it measures | A "good" company typically… | Score = 100 at | Score = 0 at |
|---|---|---|---|---|
| `debt_to_equity` | How leveraged the company is. Lower = safer. | …keeps this under 0.5 | ≤ 0.25 | ≥ 2.0 |
| `current_ratio` | Can short-term assets cover short-term bills? | …has this above 1.5 | ≥ 2.5 | ≤ 1.0 |
| `net_cash` (cash − debt, as % of market cap) | Cushion vs. underwater? | …has positive net cash | ≥ +25% | ≤ −25% |
| `roe` (Return on Equity, %) | How well management turns shareholder money into profit. | …earns above 15% | ≥ 25% | ≤ 0% |
| `fcf_yield` (Free Cash Flow ÷ Market Cap, %) | Cash minted relative to price. | …yields above 5% | ≥ 10% | ≤ 0% |

**`value_score` = simple average of the 5 sub-scores.**

### 5c. Worked example — making it concrete

Imagine NVDA comes back from yfinance with these raw numbers. Here's
how each one becomes a sub-score:

| Raw number | Where it sits | Sub-score | Grade |
|---|---|---|---|
| debt_to_equity = 0.30 | Just above the 0.25 ceiling | **≈ 93** | A |
| current_ratio = 4.10 | Way above the 2.5 ceiling | **100** | A |
| net_cash = +8% of market cap | Between −25% (0) and +25% (100) | **66** | C |
| roe = 95% | Far above the 25% ceiling | **100** | A |
| fcf_yield = 2% | Between 0% (0) and 10% (100) | **20** | F |

Average = (93 + 100 + 66 + 100 + 20) / 5 = **76 — B (Strong).**

In English: *NVDA is in great financial shape on almost every
dimension, but cash-generation-relative-to-price is poor — which makes
sense because the stock is expensive.* That's the kind of one-line read
the dashboard is designed to give you for every ticker on the list.

### 5d. Edge cases (the "hold your hand" part)

- **ETFs** don't report these per-fund. Their `value_score` cell will
  say `N/A` and they'll be marked with `asset_type = etf`.
- **Crypto** has none of these either. Same `N/A` treatment.
- **Missing data** (e.g., yfinance returns no debt-to-equity for a
  micro-cap): that one sub-score is skipped, the average is taken over
  the remaining ones. We never invent numbers to fill gaps.

Why these thresholds and not others? They're standard rules of thumb
from quality-investing literature (Buffett-style screens, Joel
Greenblatt's *Little Book*, etc.). They're not magic — in 4.3 we can
revisit them. The point is to start with defensible defaults so you
can see the dashboard react sensibly to your tickers.

---

## 6. The Technical Score — same idea, but for price action

**Same 0-100 scale and same A-F grade bands as Section 5a.** A
Technical Score of 82 reads as "*Strong* on price action — in a
healthy uptrend with reasonable volatility."

We'll reuse the trade bot's logic so you don't have to re-learn
anything. Four sub-scores, averaged.

| Metric | Meaning | Sub-score = 100 when… | Sub-score = 0 when… |
|---|---|---|---|
| `stage_2` (boolean) | Price > 30-week moving average AND the MA is sloping up. (Weinstein's Stage Analysis.) | True | False |
| `dist_from_20d_high` (%) | How far below the 20-day high are we? Smaller = more momentum. | within 0-2% of high | > 20% below high |
| `rs_vs_spy` (%) | Has this ticker outperformed SPY over the last 90 days? | beat SPY by ≥ 20% | trailed SPY by ≥ 20% |
| `atr_pct` (%) | Average True Range as a % of price. We want the "sweet spot" — not dead, not insane. | between 2% and 5% | < 0.5% or > 10% |

**`tech_score` = simple average of the 4 sub-scores.**

Crypto note: crypto trades 24/7 and has fatter tails. We'll still run
the same formulas — the technicals are price-only, so they work for any
asset. Just expect higher ATR readings.

---

## 7. The Composite Score

`composite_score = 0.5 × value_score + 0.5 × tech_score`

For ETFs/crypto (where value_score is N/A), composite falls back to
just the tech_score. That's a deliberate, transparent rule — not a
secret weighting.

In 4.3 we'll add the "Quality + Momentum" highlight column, which is
simply: *both* scores ≥ 70. That's the academic sweet spot the README
mentions. Not coding it in 4.1 — keeping 4.1 narrow.

---

## 8. Milestones inside Phase 4.1 *(revised 2026-05-22 — dashboard-first)*

**Daily workflow goal:** open Terminal once, type `streamlit run radar/app.py`, switch to your browser. Everything you do after that — adding tickers, reading scores, looking at charts — happens in the browser. The terminal just runs the server quietly in the background. Same model as the trade bot.

The build order below reflects that: the dashboard appears at step C, not step F. Earlier steps build the plumbing it needs.

### Milestone 4.1.a — Project skeleton + dependencies ✓ DONE

- `requirements.txt`, `.gitignore`, `radar/__init__.py` created.
- Virtual environment built and `pandas` / `yfinance` / `streamlit` installed.

### Milestone 4.1.b — `load_data.py` ✓ DONE

- `load_ideas()` function: reads `ideas.csv`, validates schema, returns a DataFrame.
- Verified against four cases: empty CSV, populated CSV, missing file, bad schema.

### Milestone 4.1.c — Dashboard MVP (the part you actually use)

- `radar/app.py` — the Streamlit app.
- **Left sidebar:** a form to add a new ticker. Type symbol, name, theme, etc. Click "Add to radar". A new row gets appended to `ideas.csv` behind the scenes. No more editing the CSV by hand.
- **Main panel:** the table of every ticker on your radar. Sortable by clicking column headers.
- No fundamentals, no scores, no charts yet — those are the next three milestones. This step proves the daily workflow works.
- **You should see:** one terminal command (`streamlit run radar/app.py`) opens a browser tab. You add NVDA via the sidebar form. The table refreshes and shows the new row.

### Milestone 4.1.d — Add `fundamentals.py` and a Value Score column

- New file `radar/fundamentals.py` fetches the five Value inputs from yfinance for each ticker.
- `radar/scoring.py` turns those raw numbers into a 0–100 Value Score using the rules from Section 5.
- The dashboard table gains a **Value Score** column and a **Value Grade** column (A / B / C / D / F).
- ETFs and crypto show `N/A` for value score — by design.
- **You should see:** every stock ticker in your table now has a numeric Value Score with a grade.

### Milestone 4.1.e — Add `technicals.py` and a Tech Score column

- New file `radar/technicals.py` pulls price history (and SPY for relative-strength comparison) from yfinance.
- Same 0–100 Tech Score logic from Section 6, plumbed into the table.
- **You should see:** every ticker (including crypto and ETFs, since technicals are price-only) now has a numeric Tech Score and grade.

### Milestone 4.1.f — Composite score + a small price chart per ticker

- A **Composite Score** column = average of Value + Tech (or just Tech, when value is N/A).
- Table sorted by Composite Score descending by default.
- Click any ticker row to expand a small 90-day price chart underneath. (Streamlit gives us this almost for free with `st.line_chart`.)
- Caching layer: yfinance calls are cached for 30 minutes so refreshing the page is instant and we don't hammer Yahoo.
- **You should see:** a ranked table of every ticker on your radar, scored, gradeable, with a click-to-expand chart. This is the deliverable of Phase 4.1.

---

## 9. Your daily workflow (once 4.1.c lands)

Once the dashboard exists, this is *all* you do day to day:

```
cd ~/Investment_Radar
source venv/bin/activate          # turns ON the virtual environment
streamlit run radar/app.py        # launches the dashboard
```

Your browser opens to `http://localhost:8501`. From there:

- **Add a ticker** — sidebar form on the left.
- **Browse / sort** — click column headers in the main table.
- **Refresh** — just reload the browser tab.
- **Stop the server** — switch back to Terminal, press `Ctrl+C`. Then `deactivate`, then close Terminal.

You only touch the terminal to start and stop the server. The actual work happens in the browser. Optionally we can later add a tiny launcher script so even starting the server is one double-click.

---

## 10. Errors you'll probably hit, and what they mean

| Error message contains… | What's happening | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'streamlit'` | Library isn't installed in the active environment. | Make sure the venv is activated (your prompt should start with `(venv)`), then re-run `pip install -r requirements.txt`. |
| `KeyError: 'symbol'` | The CSV is missing a required column. | Open `ideas.csv`, check the header row matches the schema in the README. |
| yfinance prints `No data found, symbol may be delisted` | The ticker is wrong, or Yahoo changed how it's spelled (crypto is `BTC-USD`, not `BTC`). | Fix the symbol in `ideas.csv`. |
| Streamlit page is blank / hangs | yfinance is rate-limiting you (too many requests). | Wait 5 minutes, or reduce the watchlist size. The 30-minute cache prevents this once it's primed. |

We'll add to this table as real errors come up.

---

## 11. What's intentionally NOT in 4.1

To keep this phase finishable in a few short sessions, these are out
of scope and saved for later:

- Filtering by sector / theme / score — **4.2**.
- Per-ticker detail page with a price chart — **4.2**.
- "Quality + Momentum" highlight column — **4.3**.
- Scheduled daily refresh + saved snapshot history — **4.4**.
- Any kind of order placement, alerts, or notifications — **never**
  (per the README, this tool places no orders).

If we feel tempted to build any of these mid-4.1, the answer is "write
it down, finish 4.1 first." Scope discipline is how the trade bot
shipped, and it's how this ships too.

---

## 12. Mini glossary (for future-you, six months from now)

- **DataFrame** — a pandas table. Like a sheet in Excel: rows, columns,
  with names. You'll see `df` everywhere; it's just the variable name
  convention.
- **venv (virtual environment)** — an isolated Python install for one
  project. Activate it before working; deactivate when done.
- **yfinance** — the library that talks to Yahoo Finance. Unofficial,
  so occasionally Yahoo breaks it for a day. Don't panic.
- **Streamlit** — a Python library that hosts a tiny web server on
  your laptop and renders your script as a web page. You don't write
  HTML or JavaScript.
- **localhost:8501** — `localhost` = your own computer. `8501` = the
  port number Streamlit uses by default. Only you can reach it.
- **Stage 2** — a stock in a confirmed uptrend per Stan Weinstein's
  framework: price above a rising 30-week moving average.
- **ATR (Average True Range)** — average daily price range. A
  volatility measure. We want stocks that move enough to be interesting
  but not so much you can't sleep at night.
- **RS (Relative Strength)** — performance of this ticker vs. the
  S&P 500 over the same window. > 0 means it beat the index.

---

## Ready signal

When you've read this through and the plan makes sense, say so and
we'll start on **Milestone 4.1.a** — the skeleton + venv setup. That
first milestone is mostly clicking buttons and pasting commands; the
real code starts at 4.1.b.

If anything in this plan reads "huh?", flag it now. Cheaper to fix the
plan than the code.
