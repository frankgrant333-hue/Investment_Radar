"""
radar/stage.py — Weinstein stage + Vermeulen market posture (Phase 3)
=====================================================================

Shared by the dashboard (app.py), the daily snapshot job, and the PDF
report. Definitions are identical to the Divergence Alert scanner's
Phase 3 code — one set of rules, two tools.

Stage (mechanical approximation of Stan Weinstein's method):
  - MA150 = 150-day simple moving average of daily closes (the
    trading-day equivalent of Weinstein's 30-week average).
  - Slope = MA150 today vs MA150 15 trading days ago:
    rising >= +0.5%, falling <= -0.5%, otherwise flat.
  - Above MA150 + rising         -> Stage 2 — Advancing
  - Above MA150 + flat/falling   -> Stage 3 — Topping
  - At/below MA150 + flat/rising -> Stage 1 — Basing
  - Below MA150 + falling        -> Stage 4 — Declining
  - Needs ~170 trading days (150 for the average + 15 of slope
    lookback); shorter history -> None and the UI shows "n/a".
    Recent IPOs (e.g. CRWV) may legitimately be n/a.
  - In this phase the stage is a DISPLAY LABEL ONLY — it does not
    touch Value / Tech / Composite scoring.

Posture (Chris Vermeulen-style, SPY + QQQ vs their 50d/200d SMAs):
  - RISK-ON — both indexes above both averages
              "Trader sleeve: rules apply normally"
  - CASH    — both indexes below both averages
              "Trader sleeve: stand down — investor sleeve follows
              Nash only"
  - CAUTION — anything else (mixed, or an index's data missing)
              "Trader sleeve: no new entries, tighten stops"
  - The posture gates ADVICE TEXT only. It never places, blocks, or
    changes a trade.
"""

STAGE_MA_DAYS = 150
STAGE_SLOPE_LOOKBACK = 15
STAGE_FLAT_BAND_PCT = 0.5


def weinstein_stage(history) -> dict | None:
    """Stage label + the numbers behind it, or None on short/missing
    history (the caller shows "n/a")."""
    if history is None or len(history) == 0 or "Close" not in history:
        return None
    closes = history["Close"].dropna()
    if len(closes) < STAGE_MA_DAYS + STAGE_SLOPE_LOOKBACK:
        return None
    ma = closes.rolling(STAGE_MA_DAYS).mean()
    ma_now = float(ma.iloc[-1])
    ma_then = float(ma.iloc[-1 - STAGE_SLOPE_LOOKBACK])
    slope_pct = (ma_now / ma_then - 1) * 100
    close = float(closes.iloc[-1])
    if close > ma_now:
        label = ("Stage 2 — Advancing" if slope_pct >= STAGE_FLAT_BAND_PCT
                 else "Stage 3 — Topping")
    else:
        label = ("Stage 4 — Declining" if slope_pct <= -STAGE_FLAT_BAND_PCT
                 else "Stage 1 — Basing")
    return {"label": label, "short": label.split(" — ")[0],
            "close": close, "ma150": ma_now, "slope_pct": slope_pct}


POSTURE_GUIDANCE = {
    "RISK-ON": "Trader sleeve: rules apply normally",
    "CAUTION": "Trader sleeve: no new entries, tighten stops",
    "CASH": "Trader sleeve: stand down — investor sleeve follows Nash only",
}


def _index_vs_mas(history) -> dict | None:
    """One index's close vs its 50-day and 200-day SMAs."""
    if history is None or len(history) == 0 or "Close" not in history:
        return None
    closes = history["Close"].dropna()
    if len(closes) < 200:
        return None
    close = float(closes.iloc[-1])
    ma50 = float(closes.tail(50).mean())
    ma200 = float(closes.tail(200).mean())
    return {"close": close, "ma50": ma50, "ma200": ma200,
            "above50": close > ma50, "above200": close > ma200}


def market_posture(spy_history, qqq_history) -> dict:
    spy = _index_vs_mas(spy_history)
    qqq = _index_vs_mas(qqq_history)
    if spy and qqq and all(m["above50"] and m["above200"] for m in (spy, qqq)):
        posture = "RISK-ON"
    elif spy and qqq and all(not m["above50"] and not m["above200"] for m in (spy, qqq)):
        posture = "CASH"
    else:
        posture = "CAUTION"
    return {"posture": posture, "guidance": POSTURE_GUIDANCE[posture],
            "spy": spy, "qqq": qqq}


def _bits(name: str, m: dict | None) -> str:
    if m is None:
        return f"{name} n/a"
    return (f"{name} {'above' if m['above50'] else 'below'} 50d / "
            f"{'above' if m['above200'] else 'below'} 200d")


# ---------- Extended / don't chase (Phase 4) ----------
# From Frank's Swing Trading Rules sheet (Minervini): a name more than
# +8% above its 50-day simple moving average is EXTENDED — don't chase.
# (The Divergence Alert's climax flag at +25% is a different, more
# extreme warning and is unchanged.)

EXTENDED_PCT = 8.0


def pct_above_50d(history) -> float | None:
    """% above (+) or below (-) the 50-day SMA. None under 50 closes —
    the UI shows "n/a", never a guess."""
    if history is None or len(history) == 0 or "Close" not in history:
        return None
    closes = history["Close"].dropna()
    if len(closes) < 50:
        return None
    return (float(closes.iloc[-1]) / float(closes.tail(50).mean()) - 1) * 100


def is_extended(pct) -> bool:
    """EXTENDED means strictly more than +8% above the 50-day SMA."""
    return pct is not None and pct > EXTENDED_PCT


def posture_line(p: dict) -> str:
    """The full banner text, same wording as the Divergence report:
    'CAUTION — SPY below 50d / above 200d · QQQ ... — Trader sleeve: ...'"""
    return (f"{p['posture']} — {_bits('SPY', p['spy'])} · "
            f"{_bits('QQQ', p['qqq'])} — {p['guidance']}")
