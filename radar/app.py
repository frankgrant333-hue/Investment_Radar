"""
radar/app.py
============

The Investment Radar dashboard — the page you'll actually use.

How to run it (from a terminal inside ~/Investment_Radar, with venv on):

    streamlit run radar/app.py --server.port 9000

A browser tab opens at http://localhost:9000. From there:
  - Type a ticker in the sidebar and click "Look up info".
  - The Radar fetches the name, sector, industry, and a short
    description from Yahoo Finance.
  - You confirm your own theme tag and click "Add to radar".
  - The ticker shows up in the main table.
  - Press Ctrl+C in the terminal to stop the server when done.

Phase 4 COMPLETE. Capabilities live in this app:
    - Sidebar add-a-ticker flow with Yahoo auto-fill (Phase 4.1.c)
    - Value + Tech + Composite scoring with A-F grades (4.1.d-f)
    - Filter by sector / theme / asset_type (4.2a)
    - Per-ticker breakdown expanders with full sub-score tables (4.2b)
    - Edit-mode toggle to fix Yahoo misclassifications (4.2c)
    - Quality + Momentum star column + filter (4.3)
    - Daily snapshot button + past-snapshot viewer (4.4)
"""

# --- 0. Make the parent folder importable ----------------------------
#
# Why this block exists:
#   When you run `streamlit run radar/app.py`, Streamlit adds *this
#   file's folder* (radar/) to Python's import path — but NOT the
#   Investment_Radar parent folder. So `from radar.<...> import ...`
#   below would fail with "ModuleNotFoundError: No module named 'radar'"
#   because Python can't see a `radar` package one level up.
#
#   These three lines, executed BEFORE any `from radar.<...>` import,
#   teach Python where to look. Launch command stays simple — no
#   PYTHONPATH prefix required.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# --- 1. Imports -------------------------------------------------------
import platform
import streamlit as st
import pandas as pd
from datetime import date


# --- 1a. Hosted-mode detection ---------------------------------------
#
# We want the SAME app.py file to work both on Frank's Mac (fully
# interactive — add/edit/save/snapshot) AND on Streamlit Community
# Cloud (read-only phone view). The differences:
#   - Mac (Darwin) can write to disk → iCloud → phone. Full editing.
#   - Cloud (Linux) has an ephemeral disk → writes evaporate on redeploy.
#     Also, we don't want the phone version silently saving changes
#     that vanish when the container restarts. Read-only is honest.
#
# platform.system() returns "Darwin" on any Mac and "Linux" on
# Streamlit Cloud's containers. Zero configuration required.
IS_HOSTED = platform.system() != "Darwin"


# --- 1b. Color-coded grade display -----------------------------------
#
# Streamlit's data_editor doesn't support conditional-color cells the
# way Excel does. The next-best beginner-friendly thing: prefix each
# grade letter with a coloured circle emoji so you can spot A's and
# F's at a glance. Emoji render everywhere — on phone, on desktop, in
# a screenshot pasted into a text message.
_GRADE_EMOJI = {
    "A":   "🟢 A",
    "B":   "🟢 B",
    "C":   "🟡 C",
    "D":   "🟠 D",
    "F":   "🔴 F",
    "N/A": "⚫ N/A",
}
def _colored_grade(grade: str) -> str:
    """Turn a bare letter grade into 'colour letter' for display."""
    return _GRADE_EMOJI.get(grade, grade)

from radar.load_data import load_ideas, DEFAULT_CSV_PATH, write_ideas
from radar.lookup import lookup_ticker
from radar.fundamentals import fetch_fundamentals
from radar.technicals import fetch_history, compute_technicals, fetch_histories_batch
from radar.snapshots import take_snapshot, list_snapshots, load_snapshot
from radar.latest_metrics import (
    write_latest_metrics, read_latest_metrics, metrics_for_symbol,
)
from radar.scoring import (
    value_score, tech_score, composite_score, grade_letter,
    # Sub-scorers for the per-ticker breakdown tables.
    score_debt_to_equity, score_current_ratio, score_net_cash_pct,
    score_roe, score_fcf_yield,
    score_stage_2, score_dist_from_20d_high, score_rs_vs_spy, score_atr_pct,
)
from radar.money_flow import compute_sector_flow, top_sectors
from radar.catalog import load_catalog


# --- 1a. Cached fundamentals fetcher --------------------------------
#
# Yahoo's `.info` call is slow (1-3 seconds per ticker) and a little
# rate-limited. If we called it every time Streamlit reruns (which is
# basically every button-click) the dashboard would crawl.
#
# `@st.cache_data(ttl=1800)` is Streamlit's "remember the result of
# this function for 30 minutes" decorator. Keyed on the function
# arguments — so the cache treats each (symbol, asset_type) pair
# separately. Adding ONE new ticker fetches only that one; existing
# tickers come back from the cache instantly.
#
# When you want fresh numbers (e.g. after earnings), click the
# "🔄 Refresh fundamentals" button in section 5 — that calls
# `st.cache_data.clear()` which throws the whole cache out.

@st.cache_data(ttl=1800, show_spinner=False)
def cached_score_for(symbol: str, asset_type: str) -> tuple[float | None, str]:
    """
    Fetch fundamentals for one ticker, compute its Value Score and
    grade letter. Returns (score, grade). ETFs and crypto come back
    as (None, "N/A") instantly — no network call.

    Why we return a tuple of (score, grade) instead of just the score:
    grade_letter() is cheap, but cache hits skip the function body
    entirely. Bundling both into the cached return means BOTH stay in
    sync — no risk of cached score ≠ recomputed grade.
    """
    funds = fetch_fundamentals(symbol, asset_type)
    score = value_score(funds)
    return score, grade_letter(score)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_fundamentals(symbol: str, asset_type: str) -> dict:
    """
    Cached wrapper around fetch_fundamentals — used by the detail
    expanders to show the RAW value-metric numbers (not just the
    averaged Value Score). Same cache key as cached_score_for, so
    they share data — calling both for the same ticker only hits
    Yahoo once.
    """
    return fetch_fundamentals(symbol, asset_type)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_history(symbol: str):
    """
    Cached wrapper around technicals.fetch_history. Same 30-min TTL.
    Crucially: SPY is the benchmark used by EVERY tech-score
    calculation, so caching here means we only hit Yahoo for SPY
    once per page-load-with-cache-miss, not once per ticker.
    """
    return fetch_history(symbol)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_tech_score_for(symbol: str) -> tuple[float | None, str]:
    """
    Compute Tech Score for one ticker. Unlike Value Score, this works
    for stocks, ETFs, AND crypto — it's all derived from price action.

    Note we DON'T cache the score on (symbol, asset_type) — asset_type
    doesn't affect the calculation here, so it'd just bloat the cache.
    """
    history = cached_history(symbol)
    spy_history = cached_history("SPY")    # cache hit after first call
    metrics = compute_technicals(history, spy_history)
    score = tech_score(metrics)
    return score, grade_letter(score)


# --- 2. Page-level setup ---------------------------------------------
st.set_page_config(
    page_title="Investment Radar",
    page_icon="📡",
    layout="wide",
)

st.title("📡 Investment Radar")
st.caption(
    "Capture investment ideas, see them in one place, score them, "
    "track them over time. _Phase 4 complete — filter by sector or "
    "theme, expand any ticker for the full breakdown, ⭐ marks "
    "Quality + Momentum picks (Value ≥ 70 AND Tech ≥ 70), and "
    "snapshots let you look back at past readings._"
)


# --- 3. Helper: save a new row back to ideas.csv ---------------------
def append_ticker_to_csv(new_row: dict) -> None:
    """Load current ideas.csv, append the new row, write to all mirrors."""
    existing = load_ideas()
    new_df = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    column_order = [
        "symbol", "name", "asset_type", "sector", "sub_sector",
        "theme", "description", "source", "date_added", "notes",
    ]
    new_df = new_df[column_order]
    # write_ideas writes to BOTH the local repo copy and iCloud (if
    # iCloud sync is configured), so the phone view — which reads the
    # local repo copy from GitHub — never falls behind.
    write_ideas(new_df)


# --- 3b. Money-flow panel — where is big money rotating? -------------
#
# Watches the 11 SPDR sector ETFs. For each one: dollar volume
# (price x shares traded) over the last 5 / 15 / 30 trading days,
# compared to the SAME length of time just before. A big positive
# number = money accelerating INTO that sector. See money_flow.py
# for the full plain-English explanation.

@st.cache_data(ttl=1800)  # refresh at most every 30 minutes
def cached_sector_flow():
    return compute_sector_flow()


st.subheader("💰 Where the money is flowing")
_flow = cached_sector_flow()
if _flow is None:
    st.caption(
        "Couldn't reach Yahoo Finance for sector data right now — "
        "this panel will come back on the next refresh."
    )
else:
    _windows = [("5d", "Past 5 days"), ("15d", "Past 15 days"), ("30d", "Past 30 days")]
    _medals = ["🥇", "🥈", "🥉"]
    _flow_cols = st.columns(3)
    for _col, (_w, _label) in zip(_flow_cols, _windows):
        with _col:
            st.markdown(f"**{_label}**")
            for _medal, (_sector, _ratio) in zip(_medals, top_sectors(_flow, _w)):
                _arrow = "🔺" if _ratio > 0 else "🔻"
                st.markdown(f"{_medal} {_sector} &nbsp;{_arrow} {_ratio:+.0%}")
    st.caption(
        "Ranked by change in dollar volume (price × shares traded) in the "
        "11 sector ETFs vs. the equal-length period before. "
        "+25% = a quarter more money trading in that sector than before."
    )

st.divider()


# --- 3c. Ticker catalog — browse by sector, click to add -------------
#
# catalog.csv (project root — edit it in Excel any time) holds a master
# menu of well-known stocks, ETFs and cryptos organized by sector and
# sub-sector. On the Mac, clicking a ticker looks it up on Yahoo and
# adds it straight to your radar. On the phone view it's browse-only.

_catalog = load_catalog()
if len(_catalog) > 0:
    with st.expander("🗂️ Ticker catalog — browse by sector, click to add", expanded=False):

        # A little celebration note that survives the page rerun after adding.
        if "catalog_added" in st.session_state:
            st.success(f"✅ {st.session_state.pop('catalog_added')} added to your radar!")

        if IS_HOSTED:
            st.info("📱 Browse-only here — adding to the radar happens on your Mac.")

        _sectors = sorted(_catalog["sector"].unique())
        _chosen_sector = st.selectbox("Pick a sector", _sectors, key="catalog_sector")
        _sector_rows = _catalog[_catalog["sector"] == _chosen_sector]

        # Which symbols are already on the radar? (✅ = already there.)
        try:
            _on_radar = set(load_ideas()["symbol"].str.upper())
        except Exception:
            _on_radar = set()

        for _sub in sorted(_sector_rows["sub_sector"].unique()):
            _group = _sector_rows[_sector_rows["sub_sector"] == _sub]
            st.markdown(f"**{_sub}**")
            _btn_cols = st.columns(4)
            for _i, (_, _row) in enumerate(_group.iterrows()):
                with _btn_cols[_i % 4]:
                    _already = _row["symbol"].upper() in _on_radar
                    if IS_HOSTED:
                        _mark = "✅" if _already else "•"
                        st.markdown(f"{_mark} `{_row['symbol']}` {_row['name']}")
                    elif _already:
                        st.button(
                            f"✅ {_row['symbol']}",
                            key=f"cat_{_row['symbol']}",
                            help=f"{_row['name']} — already on your radar",
                            disabled=True,
                            use_container_width=True,
                        )
                    else:
                        if st.button(
                            f"➕ {_row['symbol']}",
                            key=f"cat_{_row['symbol']}",
                            help=f"Add {_row['name']} to your radar",
                            use_container_width=True,
                        ):
                            with st.spinner(f"Looking up {_row['symbol']} on Yahoo…"):
                                _data = lookup_ticker(_row["symbol"])
                            _new_row = {
                                "symbol": _data["symbol"] if _data.get("found") else _row["symbol"],
                                "name": (_data.get("name") or _row["name"]),
                                "asset_type": (_data.get("asset_type") or _row["asset_type"]),
                                "sector": (_data.get("sector") or _row["sector"]),
                                "sub_sector": (_data.get("sub_sector") or _row["sub_sector"]),
                                "theme": "",
                                "description": _data.get("description", ""),
                                "source": "catalog",
                                "date_added": date.today().isoformat(),
                                "notes": "",
                            }
                            append_ticker_to_csv(_new_row)
                            st.session_state["catalog_added"] = _new_row["symbol"]
                            st.rerun()

st.divider()


# --- 4. Sidebar — two-step add flow ----------------------------------
#
# Step 1: type a symbol → click "Look up info".
# Step 2: app fetches Yahoo data, shows a preview, you confirm theme
#         (+ optional source/notes) → click "Add to radar".
#
# We use st.session_state to remember the looked-up data across the
# Streamlit reruns that happen every time you click a button.

if IS_HOSTED:
    # Read-only phone view — the whole Add/Edit flow is Mac-only.
    st.sidebar.info(
        "📱 **Phone view — read only.**\n\n"
        "To add, edit, or delete tickers, use the dashboard on your "
        "Mac. Your Mac writes to `ideas.csv`; when you're ready to "
        "update this phone view, push the file to GitHub from your Mac."
    )
    st.sidebar.caption(
        "This page auto-refreshes when GitHub gets a new commit — "
        "usually within a minute of your push."
    )
else:
    st.sidebar.header("➕ Add a new ticker")
    st.sidebar.write(
        "Just type the symbol. The Radar pulls the name, sector and industry "
        "from Yahoo — you only confirm your own theme tag."
    )

    # Step 1: the symbol input + Look-up button -------------------------
    typed_symbol = st.sidebar.text_input(
        "Ticker symbol",
        placeholder="NVDA, BTC, SPY, CEG…",
        key="symbol_input",
    )
    lookup_clicked = st.sidebar.button(
        "🔍 Look up info",
        type="primary",
        use_container_width=True,
    )

    if lookup_clicked:
        if not typed_symbol.strip():
            st.sidebar.error("Type a ticker symbol first.")
        else:
            with st.spinner(f"Looking up {typed_symbol.upper()}…"):
                data = lookup_ticker(typed_symbol)
            if not data.get("found"):
                st.sidebar.error(
                    f"Yahoo didn't recognise **{typed_symbol.upper()}**.  \n"
                    "Double-check the spelling. For US stocks use the plain "
                    "ticker (NVDA, CEG). For crypto, the bare symbol works "
                    "(BTC, ETH). For non-US stocks you may need a suffix "
                    "(e.g. `RIO.L` for London-listed)."
                )
                st.session_state.pop("lookup_data", None)
            else:
                st.session_state["lookup_data"] = data

    # Step 2: preview + theme/notes + confirm -------------------------
    lookup_data = st.session_state.get("lookup_data")

    if lookup_data:
        st.sidebar.divider()
        st.sidebar.markdown(f"**Found:** `{lookup_data['symbol']}` — {lookup_data['name']}")
        st.sidebar.markdown(
            f"*Type:* `{lookup_data['asset_type']}`  \n"
            f"*Sector:* {lookup_data['sector'] or '_n/a_'}  \n"
            f"*Industry:* {lookup_data['sub_sector'] or '_n/a_'}"
        )
        if lookup_data["description"]:
            st.sidebar.caption(lookup_data["description"])

        # The theme/notes form lives inside an st.form so we don't fire
        # off the save on every keystroke — only when the submit clicks.
        with st.sidebar.form("confirm_form", clear_on_submit=True):
            theme = st.text_input(
                "Theme(s) * — your own thesis tag",
                placeholder="AI, Data Centers",
                help=(
                    "Your investment thesis bucket. Make these up — they're "
                    "YOUR categories. Comma-separate if a ticker fits multiple."
                ),
            )
            source = st.text_input(
                "Source (optional)",
                placeholder="Patrick Boyle podcast",
            )
            notes = st.text_area(
                "Notes (optional)",
                placeholder="Anything that didn't fit elsewhere.",
            )
            confirm = st.form_submit_button(
                "✓ Add to radar",
                type="primary",
                use_container_width=True,
            )

            if confirm:
                if not theme.strip():
                    st.sidebar.error(
                        "Please tag this with at least one theme — that's your own "
                        "judgment call and the only thing Yahoo can't tell us."
                    )
                else:
                    new_row = {
                        "symbol":      lookup_data["symbol"],
                        "name":        lookup_data["name"],
                        "asset_type":  lookup_data["asset_type"],
                        "sector":      lookup_data["sector"],
                        "sub_sector":  lookup_data["sub_sector"],
                        "theme":       theme.strip(),
                        "description": lookup_data["description"],
                        "source":      source.strip(),
                        "date_added":  date.today().isoformat(),
                        "notes":       notes.strip(),
                    }
                    try:
                        append_ticker_to_csv(new_row)
                        st.sidebar.success(
                            f"Added **{new_row['symbol']}** to your radar ✓"
                        )
                        # Clear lookup state so the form is ready for the next one.
                        st.session_state.pop("lookup_data", None)
                        st.rerun()
                    except Exception as err:
                        st.sidebar.error(f"Couldn't save: {err}")

        # A small "back out of this lookup" button OUTSIDE the form.
        if st.sidebar.button("← Cancel / look up a different ticker"):
            st.session_state.pop("lookup_data", None)
            st.rerun()


# --- 5. Main panel — the editable table -----------------------------
#
# `st.data_editor` is Streamlit's spreadsheet widget. Users can:
#   - click any unlocked cell to edit it in place,
#   - select a row and press Delete (or use the trash icon) to remove it,
#   - see their edits live, then commit them with the Save button below.
#
# We LOCK columns that came from Yahoo (symbol, name, sector, etc.) so a
# stray click can't corrupt them, and leave the personal-judgment fields
# (theme, source, notes) editable.

ideas = load_ideas()

# --- 5a. Enrich with Value Score + Grade columns -------------------
#
# These two columns are DERIVED from yfinance data, not stored in
# ideas.csv. We compute them at display time and strip them off
# again at save time (see column_order in the save block below).
#
# Why not store them? Because they'd be stale the moment a company's
# fundamentals change. Better to recompute on demand and cache for
# 30 minutes than to write rotting numbers into the CSV.
if len(ideas) > 0:
    v_scores, v_grades = [], []
    t_scores, t_grades = [], []
    c_scores, c_grades = [], []
    c_numeric = []   # hidden float column for sorting (strings sort wrong)
    cur_prices, past_prices = [], []   # display-only price columns
    qm_stars = []    # ⭐ when both value ≥ 70 AND tech ≥ 70 (Phase 4.3)
    qm_flags = []    # hidden boolean column for filtering
    metrics_last_computed_at = ""   # populated on hosted view for the "last synced" caption

    if IS_HOSTED:
        # === Cloud path: no Yahoo calls ===================================
        #
        # Yahoo's `.info` endpoint (fundamentals) is rate-limited from
        # datacenter IPs, so calling it from Streamlit Cloud gives us
        # N/A for every stock. Instead we read `latest_metrics.csv` —
        # which Frank's Mac wrote and pushed via GitHub — and derive
        # scores from those stored raw metrics using the pure-math
        # scoring functions. Same numbers Frank sees on his Mac.
        stored = read_latest_metrics()
        for _, row in ideas.iterrows():
            symbol = row["symbol"]
            m = metrics_for_symbol(stored, symbol)
            if m is None:
                # Ticker was added on Mac but hasn't been pushed yet.
                v_scores.append("N/A"); v_grades.append("N/A")
                t_scores.append("N/A"); t_grades.append("N/A")
                c_scores.append("N/A"); c_grades.append("N/A")
                c_numeric.append(float("-inf"))
                cur_prices.append("N/A"); past_prices.append("N/A")
                qm_stars.append(""); qm_flags.append(False)
                continue
            v_score = value_score({
                "debt_to_equity":  m["debt_to_equity"],
                "current_ratio":   m["current_ratio"],
                "net_cash_pct":    m["net_cash_pct"],
                "roe":             m["roe"],
                "fcf_yield":       m["fcf_yield"],
            })
            t_score = tech_score({
                "stage_2":            m["stage_2"],
                "dist_from_20d_high": m["dist_from_20d_high"],
                "rs_vs_spy":          m["rs_vs_spy"],
                "atr_pct":            m["atr_pct"],
            })
            c_score = composite_score(v_score, t_score)
            v_scores.append("N/A" if v_score is None else f"{round(v_score)}")
            v_grades.append(_colored_grade(grade_letter(v_score)))
            t_scores.append("N/A" if t_score is None else f"{round(t_score)}")
            t_grades.append(_colored_grade(grade_letter(t_score)))
            c_scores.append("N/A" if c_score is None else f"{round(c_score)}")
            c_grades.append(_colored_grade(grade_letter(c_score)))
            c_numeric.append(c_score if c_score is not None else float("-inf"))
            cur_prices.append(m["current_price"] or "N/A")
            past_prices.append(m["past_30d_price"] or "N/A")
            qm_hit = (
                v_score is not None and v_score >= 70 and
                t_score is not None and t_score >= 70
            )
            qm_stars.append("⭐" if qm_hit else "")
            qm_flags.append(qm_hit)
            if m.get("computed_at"):
                metrics_last_computed_at = m["computed_at"]
    else:
        # === Mac path: fetch from Yahoo AND persist for the phone view =====
        #
        # Same as before, plus we buffer per-symbol raw metrics into
        # `metrics_buffer` and write them to `latest_metrics.csv` at
        # the end of the loop. That's the file the hosted view reads.
        metrics_buffer = []
        with st.spinner("Fetching fundamentals + price history (cached for 30 min)…"):
            spy_history_for_metrics = cached_history("SPY")
            for _, row in ideas.iterrows():
                v_score, v_grade = cached_score_for(row["symbol"], row["asset_type"])
                t_score, t_grade = cached_tech_score_for(row["symbol"])
                c_score = composite_score(v_score, t_score)
                c_grade = grade_letter(c_score)
                v_scores.append("N/A" if v_score is None else f"{round(v_score)}")
                v_grades.append(_colored_grade(v_grade))
                t_scores.append("N/A" if t_score is None else f"{round(t_score)}")
                t_grades.append(_colored_grade(t_grade))
                c_scores.append("N/A" if c_score is None else f"{round(c_score)}")
                c_grades.append(_colored_grade(c_grade))
                c_numeric.append(c_score if c_score is not None else float("-inf"))

                qm_hit = (
                    v_score is not None and v_score >= 70 and
                    t_score is not None and t_score >= 70
                )
                qm_flags.append(qm_hit)
                qm_stars.append("⭐" if qm_hit else "")

                history = cached_history(row["symbol"])
                if history is None or history.empty:
                    cur_prices.append("N/A")
                    past_prices.append("N/A")
                    tech_raw = {"stage_2": None, "dist_from_20d_high": None,
                                "rs_vs_spy": None, "atr_pct": None}
                else:
                    last_close = float(history["Close"].iloc[-1])
                    cur_prices.append(f"${last_close:,.2f}")
                    if len(history) >= 30:
                        past_close = float(history["Close"].iloc[-30])
                        past_prices.append(f"${past_close:,.2f}")
                    else:
                        past_prices.append("N/A")
                    tech_raw = compute_technicals(history, spy_history_for_metrics)

                # Collect the RAW numbers Yahoo gave us so the phone view
                # can score them without hitting Yahoo's rate limits.
                funds_raw = cached_fundamentals(row["symbol"], row["asset_type"])
                metrics_buffer.append({
                    "symbol":             row["symbol"],
                    "current_price":      cur_prices[-1],
                    "past_30d_price":     past_prices[-1],
                    "debt_to_equity":     funds_raw.get("debt_to_equity"),
                    "current_ratio":      funds_raw.get("current_ratio"),
                    "net_cash_pct":       funds_raw.get("net_cash_pct"),
                    "roe":                funds_raw.get("roe"),
                    "fcf_yield":          funds_raw.get("fcf_yield"),
                    "stage_2":            tech_raw.get("stage_2"),
                    "dist_from_20d_high": tech_raw.get("dist_from_20d_high"),
                    "rs_vs_spy":          tech_raw.get("rs_vs_spy"),
                    "atr_pct":            tech_raw.get("atr_pct"),
                })
        # After the loop: persist the metrics so the phone view can read
        # them once Frank pushes to GitHub. Non-fatal if it fails.
        try:
            write_latest_metrics(metrics_buffer)
        except Exception:
            pass
    ideas["qm"]               = qm_stars
    ideas["current_price"]    = cur_prices
    ideas["past_30d_price"]   = past_prices
    ideas["composite_score"]  = c_scores
    ideas["composite_grade"]  = c_grades
    ideas["value_score"]      = v_scores
    ideas["value_grade"]      = v_grades
    ideas["tech_score"]       = t_scores
    ideas["tech_grade"]       = t_grades
    ideas["_composite_num"]   = c_numeric
    ideas["_qm_flag"]         = qm_flags    # hidden boolean for filter

    # Default-sort by composite descending. Highest-ranked ticker
    # bubbles to the top — the whole point of the score columns.
    ideas = ideas.sort_values(
        "_composite_num", ascending=False, kind="mergesort"
    ).reset_index(drop=True)

if len(ideas) == 0:
    st.info(
        "📭 **Your radar is empty.** "
        "Type a ticker in the sidebar (e.g., NVDA, BTC, SPY) and click "
        "**Look up info** to pull in everything Yahoo Finance knows about it."
    )
else:
    st.subheader(f"Your radar — {len(ideas)} ticker(s)")
    st.write(
        "Click any cell in the **theme**, **source**, or **notes** columns "
        "to edit it. To delete a ticker, hover the row and click its trash "
        "icon (or select the row and press Delete). Then click **💾 Save "
        "changes** below to commit."
    )

    # --- 5b. Filter controls (Phase 4.2a) -------------------------
    #
    # Three multiselects let you narrow the table to a slice of your
    # radar — by sector, by your theme tag, or by asset type. Themes
    # are stored comma-separated ("AI, Data Centers"), so we split on
    # commas to build the available choices.
    #
    # Filters DON'T modify ideas.csv — they just hide rows in the
    # display. Clear all selections to see everything again.

    all_sectors = sorted({s for s in ideas["sector"] if s})
    all_assets  = sorted({a for a in ideas["asset_type"] if a})
    theme_set: set = set()
    for raw in ideas["theme"]:
        if not raw:
            continue
        # "AI, Data Centers" -> ["AI", "Data Centers"]
        theme_set.update(t.strip() for t in str(raw).split(",") if t.strip())
    all_themes = sorted(theme_set)

    with st.expander("🔍 Filter the radar", expanded=False):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            sel_sectors = st.multiselect(
                "Sector", all_sectors, default=[],
                help="Show only rows in these sectors. Empty = all sectors."
            )
        with col_f2:
            sel_themes = st.multiselect(
                "Theme", all_themes, default=[],
                help="Show rows tagged with ANY of these themes. "
                     "Empty = all themes."
            )
        with col_f3:
            sel_assets = st.multiselect(
                "Asset type", all_assets, default=[],
                help="Show only stocks / ETFs / crypto. Empty = all types."
            )
        # Q+M filter on its own row — different "shape" of filter.
        qm_only = st.checkbox(
            "⭐ Show only Quality + Momentum picks (value ≥ 70 AND tech ≥ 70)",
            value=False,
            help="The academic sweet spot — strong fundamentals AND "
                 "strong recent price action. ETFs/crypto can never "
                 "satisfy this since their Value Score is N/A.",
        )

    # Apply the filters. Each selection narrows the visible DataFrame;
    # if a list is empty, that filter doesn't restrict anything.
    filtered = ideas.copy()
    if sel_sectors:
        filtered = filtered[filtered["sector"].isin(sel_sectors)]
    if sel_assets:
        filtered = filtered[filtered["asset_type"].isin(sel_assets)]
    if sel_themes:
        # A row matches if any of its themes is in the selected set.
        def _row_matches(theme_cell: str) -> bool:
            if not theme_cell:
                return False
            row_themes = {t.strip() for t in str(theme_cell).split(",")}
            return bool(row_themes & set(sel_themes))
        filtered = filtered[filtered["theme"].apply(_row_matches)]
    if qm_only:
        filtered = filtered[filtered["_qm_flag"]]

    if len(filtered) < len(ideas):
        st.info(
            f"Showing **{len(filtered)} of {len(ideas)}** rows after filters. "
            "Clear all multiselects to see everything."
        )

    # CRITICAL: keep a reference to the FULL pre-filter DataFrame so
    # the save block doesn't silently delete rows hidden by filters.
    # Downstream code (table + expanders) uses `ideas` for display;
    # the save block uses `master_ideas` to merge edits back in.
    master_ideas = ideas.copy()
    ideas = filtered

    # --- 5c. Edit-mode toggle (Phase 4.2c) ------------------------
    #
    # By default, Yahoo-derived metadata (name, sector, sub_sector,
    # asset_type, description) is LOCKED — so a stray click can't
    # corrupt it. Flip this toggle when you need to fix something
    # Yahoo got wrong (e.g. the Bitwise XRP ETF labelled as 'stock').
    #
    # Also here: a "Group by sector" toggle. When ON, the table sorts
    # by sector then sub_sector then composite (still highest-first
    # within each group), so all Technology tickers cluster together,
    # all Financials cluster together, etc.
    #
    # Both toggles hidden on the phone view — that's always read-only.
    if IS_HOSTED:
        metadata_disabled = True
        group_by_sector = st.toggle(
            "📁 Group by sector & sub-sector",
            value=False,
            help="ON: cluster tickers by sector then sub-sector. "
                 "OFF: sort by composite score (highest first).",
        )
    else:
        tog_edit, tog_group = st.columns([1, 1])
        with tog_edit:
            edit_mode = st.toggle(
                "🔓 Edit metadata mode",
                value=False,
                help="OFF (default): Yahoo-derived columns are read-only. "
                     "ON: name, sector, sub_sector, asset_type, and description "
                     "become editable so you can hand-fix Yahoo misclassifications. "
                     "Score and price columns remain locked — they're derived.",
            )
        with tog_group:
            group_by_sector = st.toggle(
                "📁 Group by sector & sub-sector",
                value=False,
                help="ON: cluster tickers by sector then sub-sector. "
                     "OFF: sort by composite score (highest first).",
            )
        metadata_disabled = not edit_mode

    # Apply the group-by-sector re-sort if requested. Composite-desc
    # still runs within each group so the best pick per sector floats
    # to the top of its cluster.
    if group_by_sector:
        ideas = ideas.sort_values(
            by=["sector", "sub_sector", "_composite_num"],
            ascending=[True, True, False],
            kind="mergesort",
        ).reset_index(drop=True)

    # --- Visual borders for grouped view ------------------------------
    # When grouping is ON, we build a DISPLAY copy of the table with
    # labeled separator rows inserted wherever a new sector or
    # sub-sector begins — so each block has an obvious start and end.
    # The real `ideas` DataFrame stays untouched (the expanders and
    # save logic below keep using it); separators are stripped back
    # out before anything is written to disk.
    if group_by_sector:
        _sep_rows = []
        _prev_sec, _prev_sub = object(), object()  # sentinel: never equal
        for _, _r in ideas.iterrows():
            _sec = (str(_r.get("sector") or "").strip()) or "Uncategorized"
            _sub = (str(_r.get("sub_sector") or "").strip()) or "—"
            if _sec != _prev_sec:
                _sep = {c: None for c in ideas.columns}
                _sep["symbol"] = f"📁 {_sec.upper()}"
                _sep["name"] = "━" * 30
                _sep_rows.append(_sep)
                _prev_sec, _prev_sub = _sec, object()
            if _sub != _prev_sub:
                _sep = {c: None for c in ideas.columns}
                _sep["symbol"] = f"└ {_sub}"
                _sep["name"] = "·" * 20
                _sep_rows.append(_sep)
                _prev_sub = _sub
            _sep_rows.append(_r.to_dict())
        ideas_display = pd.DataFrame(_sep_rows, columns=list(ideas.columns))
    else:
        ideas_display = ideas

    edited = st.data_editor(
        ideas_display,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",  # enables row deletion
        key="ideas_editor",
        # column_order = what the user sees, left to right. We move
        # value_score + value_grade up front so they're the headline
        # numbers, not buried past `notes` at the far right.
        column_order=[
            # ⭐ first — instantly spot the Quality+Momentum hits.
            "qm",
            # Prices next — left edge, before the symbol.
            "current_price", "past_30d_price",
            "symbol",
            "composite_score", "composite_grade",
            "value_score", "value_grade",
            "tech_score",  "tech_grade",
            "name", "asset_type", "sector", "sub_sector",
            "theme", "source", "notes",
            "description", "date_added",
            # Note: "_composite_num" and "_qm_flag" are intentionally
            # OMITTED — they're only here for sort/filter logic.
        ],
        column_config={
            # --- Quality + Momentum star (Phase 4.3) ----------------
            "qm": st.column_config.TextColumn(
                "⭐",
                disabled=True,
                help="⭐ when BOTH Value Score and Tech Score are ≥ 70. "
                     "The 'academic sweet spot' — quality fundamentals "
                     "AND strong recent price action. Filter to just "
                     "these via the Filter the radar expander above.",
                width="small",
            ),
            # --- PRICE columns (derived from cached history) --------
            "current_price": st.column_config.TextColumn(
                "current_price",
                disabled=True,
                help="Most recent daily closing price from Yahoo. NOT "
                     "live intraday — refreshes when you click 🔄 Refresh "
                     "fundamentals (or every 30 minutes automatically).",
            ),
            "past_30d_price": st.column_config.TextColumn(
                "past_30d_price",
                disabled=True,
                help="Closing price from 30 TRADING days ago "
                     "(roughly 6 calendar weeks). N/A if the ticker is "
                     "newer than 30 trading days.",
            ),
            # --- Yahoo-derived columns (unlockable via Edit toggle) -
            # symbol stays locked always — it's the row's identity.
            # date_added stays locked — no reason to mess with it.
            # The other five flip based on edit_mode.
            "symbol":      st.column_config.TextColumn("symbol",      disabled=True),
            "name":        st.column_config.TextColumn("name",        disabled=metadata_disabled),
            "asset_type":  st.column_config.TextColumn("asset_type",  disabled=metadata_disabled),
            "sector":      st.column_config.TextColumn("sector",      disabled=metadata_disabled),
            "sub_sector":  st.column_config.TextColumn("sub_sector",  disabled=metadata_disabled),
            "description": st.column_config.TextColumn("description", disabled=metadata_disabled),
            "date_added":  st.column_config.TextColumn("date_added",  disabled=True),
            # --- DERIVED columns (Value Score from yfinance) --------
            "value_score": st.column_config.TextColumn(
                "value_score",
                disabled=True,
                help="0-100 score from 5 fundamentals (debt, current ratio, "
                     "net cash %, ROE, FCF yield). Higher = stronger "
                     "fundamentals. N/A for ETFs and crypto.",
            ),
            "value_grade": st.column_config.TextColumn(
                "value_grade",
                disabled=True,
                help="Letter grade: A=85+ (Excellent), B=70+ (Strong), "
                     "C=50+ (Average), D=25+ (Weak), F<25 (Poor).",
            ),
            "tech_score": st.column_config.TextColumn(
                "tech_score",
                disabled=True,
                help="0-100 score from 4 price-action signals (Weinstein "
                     "Stage 2, distance from 20-day high, relative "
                     "strength vs SPY, ATR sweet-spot). Works for ALL "
                     "asset types — stocks, ETFs, and crypto.",
            ),
            "tech_grade": st.column_config.TextColumn(
                "tech_grade",
                disabled=True,
                help="Letter grade on price action. A=hot uptrend with "
                     "healthy volatility; F=stagnant, lagging, or wildly "
                     "volatile.",
            ),
            "composite_score": st.column_config.TextColumn(
                "composite_score",
                disabled=True,
                help="Headline number: 50% Value + 50% Tech. For ETFs "
                     "and crypto (where Value is N/A), falls back to "
                     "just the Tech Score. Table is sorted by this "
                     "column, highest first.",
            ),
            "composite_grade": st.column_config.TextColumn(
                "composite_grade",
                disabled=True,
                help="Letter grade on the composite. Look for A and B "
                     "rows — those are tickers where BOTH fundamentals "
                     "AND price action point the right direction.",
            ),
            # --- EDITABLE columns (your judgment calls) -------------
            "theme":  st.column_config.TextColumn(
                "theme",
                help="Your investment thesis bucket — e.g., AI, Nuclear Energy, Crypto. "
                     "Be consistent so future filtering works.",
            ),
            "source": st.column_config.TextColumn(
                "source",
                help="Where you heard about this ticker.",
            ),
            "notes":  st.column_config.TextColumn(
                "notes",
                help="Anything else worth remembering.",
            ),
        },
    )

    # Initialize action flags so the handler blocks below always
    # have something to check — even when we hide buttons on hosted.
    save_clicked = refresh_clicked = snap_clicked = False

    if IS_HOSTED:
        # Phone view: only Refresh (cache clear) is meaningful.
        col_refresh, col_hint = st.columns([1, 4])
        with col_refresh:
            refresh_clicked = st.button(
                "🔄 Refresh from Yahoo",
                use_container_width=True,
                help="Clears the 30-minute cache and re-pulls every "
                     "ticker's data from Yahoo.",
            )
        with col_hint:
            st.caption(
                "👉 Read-only view. Sorted by **composite_score**. "
                "To make changes, edit on your Mac and push to GitHub."
            )
    else:
        col_save, col_refresh, col_snap, col_hint = st.columns([1, 1, 1, 2])
        with col_save:
            save_clicked = st.button(
                "💾 Save changes",
                type="primary",
                use_container_width=True,
            )
        with col_refresh:
            refresh_clicked = st.button(
                "🔄 Refresh fundamentals",
                use_container_width=True,
                help="Throws out the 30-minute cache and re-pulls every "
                     "ticker's fundamentals from Yahoo. Slower (1-3 sec "
                     "per stock), but gives you the latest numbers.",
            )
        with col_snap:
            snap_clicked = st.button(
                "📸 Snapshot today",
                use_container_width=True,
                help="Save today's scores + prices to snapshots/. Lets you "
                     "look back at 'what did my radar say on June 1?' weeks "
                     "or months later. Same-day re-clicks overwrite.",
            )
        with col_hint:
            st.caption(
                "👉 Table sorted by **composite_score** (highest first). "
                "Click any column header to re-sort. Edits stay in browser "
                "until you click Save."
            )

    if refresh_clicked:
        # Nuke ALL caches: fundamentals (score + raw dict), history,
        # and tech scores. Otherwise old scores could linger.
        cached_score_for.clear()
        cached_fundamentals.clear()
        cached_history.clear()
        cached_tech_score_for.clear()
        st.rerun()

    if snap_clicked:
        try:
            # We snapshot from `master_ideas` so filtered-out rows are
            # still captured. The full radar always gets snapshotted.
            path = take_snapshot(master_ideas)
            st.success(f"📸 Snapshot saved to **{path.name}** ✓")
        except Exception as err:
            st.error(f"Couldn't write snapshot: {err}")

    if save_clicked:
        # Filter out any blank rows that might have appeared if you tabbed
        # into a new row by accident. A row is "real" only if it has a symbol.
        edited_clean = edited[edited["symbol"].astype(str).str.strip() != ""].copy()
        edited_clean["symbol"] = edited_clean["symbol"].astype(str).str.strip()
        # Strip out the visual separator rows (only present when the
        # group-by-sector toggle is ON) — they're furniture, not data.
        edited_clean = edited_clean[
            ~edited_clean["symbol"].str.startswith(("📁", "└"))
        ]

        # --- Filter-aware merge ------------------------------------
        # When a filter is active, `edited` only contains the VISIBLE
        # rows. If we wrote that to CSV directly we'd silently delete
        # every filtered-out row. Instead:
        #   1. Identify symbols that were visible (in the filter view).
        #   2. Drop them from master_ideas — they'll be replaced.
        #   3. Concatenate the kept master rows with edited_clean.
        # If no filter is active, master_ideas == ideas (the filter)
        # so we end up writing only what's in edited — same as before.
        displayed_symbols = set(
            ideas["symbol"].astype(str).str.strip()  # `ideas` here is the filtered view
        )
        untouched = master_ideas[
            ~master_ideas["symbol"].astype(str).str.strip().isin(displayed_symbols)
        ].copy()
        merged = pd.concat([untouched, edited_clean], ignore_index=True)

        # Re-impose the canonical column order so the CSV stays tidy.
        # NOTE: the derived score columns (composite_score, value_score,
        # tech_score, _composite_num, etc.) are NOT in this list, so
        # they're silently dropped before write. The CSV stays exactly
        # the 10 columns ideas.csv started with.
        column_order = [
            "symbol", "name", "asset_type", "sector", "sub_sector",
            "theme", "description", "source", "date_added", "notes",
        ]
        merged = merged[column_order]

        try:
            written = write_ideas(merged)
            removed = len(master_ideas) - len(merged)
            # Show WHERE we saved (helpful for confirming iCloud mirror
            # + local repo copy both got the update).
            paths_str = "  \n".join(f"• `{p}`" for p in written)
            if removed > 0:
                st.success(
                    f"Saved ✓  ({removed} ticker(s) deleted, "
                    f"{len(merged)} remaining)  \n"
                    f"Written to:  \n{paths_str}"
                )
            else:
                st.success(f"Saved ✓  \nWritten to:  \n{paths_str}")
            st.rerun()
        except Exception as err:
            st.error(f"Couldn't save: {err}")


    # --- 6. Per-ticker detail expanders (Phase 4.2b) ---------------
    #
    # One collapsible drawer per visible ticker — in the SAME sorted
    # order as the table, so the top entry is your highest-composite-
    # scoring idea. Inside each drawer:
    #   - Full Yahoo description
    #   - Two side-by-side breakdown tables (Value + Tech sub-scores)
    #   - 1-year price chart
    #   - Quick stats (latest close, 90 days ago, 90-day change)
    #
    # All data comes from the existing caches — no extra Yahoo calls.

    st.divider()
    st.subheader("🔍 Per-ticker detail")
    st.caption(
        "Click any ticker to expand its full breakdown. Order matches "
        "the table — top entry = your highest composite score."
    )

    # Helper: turn a (raw_value, sub_score) pair into display strings.
    def _fmt_raw(v, decimals=2):
        return "N/A" if v is None else f"{v:.{decimals}f}"
    def _fmt_sub(s):
        return "N/A" if s is None else f"{s:.0f} ({_colored_grade(grade_letter(s))})"

    # ONE batched download for every visible ticker's price history,
    # instead of one Yahoo call per ticker. Cached for 30 minutes.
    @st.cache_data(ttl=1800)
    def cached_histories_batch(symbols: tuple) -> dict:
        return fetch_histories_batch(list(symbols))

    _hist_map = cached_histories_batch(tuple(ideas["symbol"]))

    for _, row in ideas.iterrows():
        symbol = row["symbol"]
        # Build a label that previews the composite grade right on the
        # chevron, so you don't have to expand every one to compare.
        label = (f"📊 {symbol}  —  composite {row['composite_score']} "
                 f"({row['composite_grade']})  ·  {row['name']}")
        with st.expander(label):
            history = _hist_map.get(symbol)
            if history is None or history.empty:
                st.warning(
                    f"No price history available for {symbol}. "
                    "Yahoo may not recognise this ticker, or the network "
                    "call failed. Try **🔄 Refresh fundamentals** to retry."
                )
                continue

            # --- Description ---
            if row.get("description"):
                st.markdown(f"**About:** {row['description']}")

            # --- Two-column breakdown: Value | Tech ---
            bd_v, bd_t = st.columns(2)

            with bd_v:
                st.markdown(f"**Value Score: {row['value_score']} ({row['value_grade']})**")
                # On Mac: fetch fresh from Yahoo (works — home IP).
                # On Cloud: pull from latest_metrics.csv (Yahoo would
                # rate-limit us; Frank's Mac already wrote the numbers).
                if IS_HOSTED:
                    _m = metrics_for_symbol(read_latest_metrics(), symbol) or {}
                    funds = {
                        "debt_to_equity": _m.get("debt_to_equity"),
                        "current_ratio":  _m.get("current_ratio"),
                        "net_cash_pct":   _m.get("net_cash_pct"),
                        "roe":            _m.get("roe"),
                        "fcf_yield":      _m.get("fcf_yield"),
                    }
                else:
                    funds = cached_fundamentals(symbol, row["asset_type"])
                if all(v is None for v in funds.values()):
                    st.caption(f"_N/A — {row['asset_type']}s don't report these._")
                else:
                    # One row per fundamental metric. Raw value on the
                    # left, the linear-interpolated sub-score on the right.
                    table_rows = [
                        ("Debt / Equity",
                         _fmt_raw(funds.get("debt_to_equity")),
                         _fmt_sub(score_debt_to_equity(funds.get("debt_to_equity")))),
                        ("Current Ratio",
                         _fmt_raw(funds.get("current_ratio")),
                         _fmt_sub(score_current_ratio(funds.get("current_ratio")))),
                        ("Net Cash % of MC",
                         _fmt_raw(funds.get("net_cash_pct")),
                         _fmt_sub(score_net_cash_pct(funds.get("net_cash_pct")))),
                        ("ROE %",
                         _fmt_raw(funds.get("roe")),
                         _fmt_sub(score_roe(funds.get("roe")))),
                        ("FCF Yield %",
                         _fmt_raw(funds.get("fcf_yield")),
                         _fmt_sub(score_fcf_yield(funds.get("fcf_yield")))),
                    ]
                    st.dataframe(
                        pd.DataFrame(table_rows, columns=["Metric", "Raw", "Sub-score"]),
                        hide_index=True, use_container_width=True,
                    )

            with bd_t:
                st.markdown(f"**Tech Score: {row['tech_score']} ({row['tech_grade']})**")
                if IS_HOSTED:
                    _m = metrics_for_symbol(read_latest_metrics(), symbol) or {}
                    t_metrics = {
                        "stage_2":            _m.get("stage_2"),
                        "dist_from_20d_high": _m.get("dist_from_20d_high"),
                        "rs_vs_spy":          _m.get("rs_vs_spy"),
                        "atr_pct":            _m.get("atr_pct"),
                    }
                else:
                    t_metrics = compute_technicals(history, cached_history("SPY"))
                if all(v is None for v in t_metrics.values()):
                    st.caption("_N/A — not enough price history._")
                else:
                    # stage_2 is boolean, formatted differently
                    s2_raw = t_metrics.get("stage_2")
                    s2_raw_str = "N/A" if s2_raw is None else ("Yes ✓" if s2_raw else "No ✗")
                    table_rows = [
                        ("Stage 2 trend",
                         s2_raw_str,
                         _fmt_sub(score_stage_2(s2_raw))),
                        ("% below 20-day high",
                         _fmt_raw(t_metrics.get("dist_from_20d_high")),
                         _fmt_sub(score_dist_from_20d_high(t_metrics.get("dist_from_20d_high")))),
                        ("RS vs SPY (90-day)",
                         _fmt_raw(t_metrics.get("rs_vs_spy")),
                         _fmt_sub(score_rs_vs_spy(t_metrics.get("rs_vs_spy")))),
                        ("ATR %",
                         _fmt_raw(t_metrics.get("atr_pct")),
                         _fmt_sub(score_atr_pct(t_metrics.get("atr_pct")))),
                    ]
                    st.dataframe(
                        pd.DataFrame(table_rows, columns=["Metric", "Raw", "Sub-score"]),
                        hide_index=True, use_container_width=True,
                    )

            # --- Full 1-year price chart ---
            st.markdown("**Price history (1 year)**")
            st.line_chart(history["Close"].rename("Close"), height=280)

            # --- Quick stats ---
            last_close = float(history["Close"].iloc[-1])
            if len(history) >= 90:
                close_90d = float(history["Close"].iloc[-90])
                pct_90d = (last_close - close_90d) / close_90d * 100.0
            else:
                close_90d, pct_90d = None, None

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Latest close", f"${last_close:,.2f}")
            col_b.metric(
                "90 days ago",
                "N/A" if close_90d is None else f"${close_90d:,.2f}",
            )
            col_c.metric(
                "90-day change",
                "N/A" if pct_90d is None else f"{pct_90d:+.1f}%",
            )


    # --- 7. Past snapshots viewer (Phase 4.4b) ---------------------
    #
    # Below everything live, a dropdown of historical snapshots. Pick
    # one to see what your radar looked like on that day. Lets you
    # answer "had NVDA's composite been trending up before I bought?"
    st.divider()
    st.subheader("📅 Past snapshots")

    available = list_snapshots()
    if not available:
        st.caption(
            "No snapshots yet. Click **📸 Snapshot today** above to take "
            "your first one. Each daily snapshot saves your scores + "
            "prices so you can look back later."
        )
    else:
        # Newest first in the dropdown — that's almost always what you want.
        options = ["— pick a date —"] + list(reversed(available))
        picked = st.selectbox(
            f"Choose a snapshot ({len(available)} available)",
            options,
            index=0,
        )
        if picked != "— pick a date —":
            snap_df = load_snapshot(picked)
            if snap_df.empty:
                st.warning(f"Snapshot for {picked} is empty or missing.")
            else:
                st.markdown(f"**Radar state on {picked}** "
                            f"({len(snap_df)} tickers):")
                st.dataframe(
                    snap_df,
                    hide_index=True,
                    use_container_width=True,
                )
