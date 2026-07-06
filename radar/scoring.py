"""
radar/scoring.py
================

Pure math, no internet, no pandas. Given the raw inputs the data
fetchers produce, turn them into 0-to-100 scores and A-F grade
letters per PHASE_4_PLAN.md Sections 5 and 6.

Why this file is separated from `fundamentals.py` / `technicals.py`:
  - Fetching numbers from Yahoo is slow and can fail.
  - Scoring numbers is fast and deterministic.
Mixing them would mean we can't test scoring logic without the
internet. Keeping them apart is one of the easiest "this is what
clean code looks like" wins in Python.

How to read this file:
  1. Two threshold tables at the top — VALUE and TECH — straight
     from the plan. Change THESE if you want to retune.
  2. Two math helpers: `_linear_score()` (Value-style, simple slope)
     and `_band_score()` (Tech ATR-style, 100 inside a range,
     0 outside outer bounds).
  3. Tiny sub-scorers (one per metric).
  4. Two public functions: `value_score()` and `tech_score()`.
     Both take a dict of raw numbers, return averaged 0-100 or None.
  5. `grade_letter()` — turns any 0-100 score into A/B/C/D/F.
"""

from typing import Optional


# --- 1. Thresholds (from PHASE_4_PLAN.md Section 5b) -----------------
#
# For each metric: (floor, ceiling).
#   - Hitting the ceiling (or beyond) earns 100.
#   - Hitting the floor (or worse) earns 0.
#   - In between scales linearly.
#
# `higher_is_better` flips the direction for metrics where SMALLER
# numbers are good (debt). For those, the "ceiling" is the LOW number
# and the "floor" is the HIGH number — that's why we read direction
# from the flag, not from which threshold is numerically bigger.

_THRESHOLDS = {
    # metric_name: (floor, ceiling, higher_is_better)
    "debt_to_equity":  (2.0,    0.25, False),   # lower is safer
    "current_ratio":   (1.0,    2.5,  True),    # higher is safer
    "net_cash_pct":    (-25.0,  25.0, True),    # +25% of mkt cap = 100
    "roe":             (0.0,    25.0, True),    # 25%+ return = 100
    "fcf_yield":       (0.0,    10.0, True),    # 10%+ yield = 100
}


# --- 2. The one math function ---------------------------------------

def _linear_score(value: Optional[float], floor: float, ceiling: float,
                  higher_is_better: bool) -> Optional[float]:
    """
    Map a raw number onto a 0-100 scale by linear interpolation
    between `floor` (worst) and `ceiling` (best).

    Examples (higher_is_better=True, floor=0, ceiling=10):
        value=0   →   0     (at the floor)
        value=5   →  50     (halfway)
        value=10  → 100     (at the ceiling)
        value=15  → 100     (past the ceiling — clamped)
        value=-3  →   0     (past the floor — clamped)

    Returns None if `value` is None — we never invent a score from
    missing data. The caller is expected to handle None by averaging
    over the metrics that DID return a number.
    """
    if value is None:
        return None

    # Flip the axis so the math always treats "bigger = better".
    if not higher_is_better:
        value, floor, ceiling = -value, -floor, -ceiling

    # Now: floor < ceiling always. (If not, the threshold table is wrong.)
    if ceiling == floor:
        return 50.0  # degenerate config — never hit if table is correct

    # Linear interpolation, then clamp to [0, 100].
    raw = (value - floor) / (ceiling - floor) * 100.0
    if raw < 0:
        return 0.0
    if raw > 100:
        return 100.0
    return raw


# --- 3. One sub-scorer per metric -----------------------------------
#
# These are tiny on purpose — they're just convenience wrappers that
# look up the right thresholds and call _linear_score. Having one per
# metric (instead of a single mega-function) makes it obvious which
# metric is which when you read app code that uses them.

def score_debt_to_equity(value: Optional[float]) -> Optional[float]:
    """e.g. 0.30 → ~93. None → None."""
    floor, ceiling, hib = _THRESHOLDS["debt_to_equity"]
    return _linear_score(value, floor, ceiling, hib)

def score_current_ratio(value: Optional[float]) -> Optional[float]:
    """e.g. 4.10 → 100. None → None."""
    floor, ceiling, hib = _THRESHOLDS["current_ratio"]
    return _linear_score(value, floor, ceiling, hib)

def score_net_cash_pct(value: Optional[float]) -> Optional[float]:
    """e.g. +8 → 66. Value is already a percent (8 = 8%, not 0.08)."""
    floor, ceiling, hib = _THRESHOLDS["net_cash_pct"]
    return _linear_score(value, floor, ceiling, hib)

def score_roe(value: Optional[float]) -> Optional[float]:
    """e.g. 95 → 100. Value is a percent (95 = 95%, not 0.95)."""
    floor, ceiling, hib = _THRESHOLDS["roe"]
    return _linear_score(value, floor, ceiling, hib)

def score_fcf_yield(value: Optional[float]) -> Optional[float]:
    """e.g. 2 → 20. Value is a percent (2 = 2%, not 0.02)."""
    floor, ceiling, hib = _THRESHOLDS["fcf_yield"]
    return _linear_score(value, floor, ceiling, hib)


# --- 4. The public function the dashboard imports -------------------

def value_score(funds: dict) -> Optional[float]:
    """
    Take a dict of raw fundamentals and return the averaged 0-100
    Value Score for one ticker.

    Parameters
    ----------
    funds : dict
        Keys (any of these may be missing or None):
            debt_to_equity, current_ratio, net_cash_pct, roe, fcf_yield

    Returns
    -------
    float between 0 and 100, or None if not a single metric could be
    scored (the ETF / crypto / no-data case).

    Why this returns None instead of 0 for "no data":
        A 0 means "we measured this and it's terrible." None means
        "we never measured it." Mixing them up would punish ETFs for
        not being stocks, which is obviously wrong.
    """
    sub_scores = [
        score_debt_to_equity(funds.get("debt_to_equity")),
        score_current_ratio(funds.get("current_ratio")),
        score_net_cash_pct(funds.get("net_cash_pct")),
        score_roe(funds.get("roe")),
        score_fcf_yield(funds.get("fcf_yield")),
    ]

    # Keep only the sub-scores we could actually compute.
    valid = [s for s in sub_scores if s is not None]
    if not valid:
        return None

    return sum(valid) / len(valid)


# --- 4a. Tech Score thresholds (from PHASE_4_PLAN.md Section 6) -----
#
# Three of the four tech metrics are simple linear (floor → ceiling).
# The fourth, ATR%, is a BAND — too low is bad (dead stock), too high
# is bad (casino), the sweet spot in the middle earns 100. That needs
# a different shape.
#
# Format for linear metrics:        (floor, ceiling, higher_is_better)
# Format for the band metric (atr): (outer_low, inner_low, inner_high, outer_high)
#   - At or below outer_low  → 0
#   - At or above outer_high → 0
#   - Anywhere between inner_low and inner_high → 100
#   - Between outer_low → inner_low: linear interp 0 → 100
#   - Between inner_high → outer_high: linear interp 100 → 0

_TECH_THRESHOLDS = {
    "dist_from_20d_high": (20.0, 2.0, False),   # 0% below high (or 2%) = perfect; 20% below = dead
    "rs_vs_spy":          (-20.0, 20.0, True),  # +20% beat = 100; -20% lag = 0
}
_ATR_BAND = (0.5, 2.0, 5.0, 10.0)   # the sweet-spot band


# --- 4b. The band math function ------------------------------------

def _band_score(value, outer_low, inner_low, inner_high, outer_high):
    """
    Score a "sweet spot" metric: 100 inside the inner band, 0 outside
    the outer band, linear interpolation in the wings.

    Picture it as a flat plateau between inner_low and inner_high,
    with sloped ramps coming up from outer_low on the left and going
    down to outer_high on the right.

        ^ score
    100 ┤      ┌─────────┐
        │     /           \
        │    /             \
      0 ┤───┘               └───
        └───────────────────────→ value
           OL  IL       IH  OH

    Returns None if value is None.
    """
    if value is None:
        return None
    if value <= outer_low or value >= outer_high:
        return 0.0
    if inner_low <= value <= inner_high:
        return 100.0
    if value < inner_low:
        # Left ramp: outer_low → inner_low maps to 0 → 100
        return (value - outer_low) / (inner_low - outer_low) * 100.0
    # Right ramp: inner_high → outer_high maps to 100 → 0
    return (outer_high - value) / (outer_high - inner_high) * 100.0


# --- 4c. Tech sub-scorers ------------------------------------------

def score_stage_2(value):
    """
    Boolean metric: True (in Stage 2 uptrend) = 100, False = 0,
    None (couldn't compute, e.g. ticker too new) = None.
    """
    if value is None:
        return None
    return 100.0 if value else 0.0

def score_dist_from_20d_high(value):
    """
    Percent below the 20-day high. 0% (at the high) = 100. The
    plan says "within 0-2% of high" earns 100; we cap at 2% so
    bouncing right at the high doesn't score lower than 2% off.
    """
    if value is None:
        return None
    # Treat anything <=2% below high as 100 (plan's "within 0-2%")
    if value <= 2.0:
        return 100.0
    floor, ceiling, hib = _TECH_THRESHOLDS["dist_from_20d_high"]
    return _linear_score(value, floor, ceiling, hib)

def score_rs_vs_spy(value):
    """
    Relative strength vs SPY over the trailing window. +20% or
    better → 100, -20% or worse → 0, flat (0) → 50.
    """
    floor, ceiling, hib = _TECH_THRESHOLDS["rs_vs_spy"]
    return _linear_score(value, floor, ceiling, hib)

def score_atr_pct(value):
    """
    ATR-as-percent-of-price band scorer. 2-5% earns 100. Outside
    0.5-10% earns 0. The wings interpolate linearly.
    """
    return _band_score(value, *_ATR_BAND)


# --- 4d. Public function: average the four tech sub-scores ---------

def tech_score(metrics: dict):
    """
    Take a dict of raw technical metrics and return the averaged
    0-100 Tech Score.

    Parameters
    ----------
    metrics : dict
        Keys (any may be missing or None):
            stage_2, dist_from_20d_high, rs_vs_spy, atr_pct

    Returns
    -------
    float between 0 and 100, or None if not a single metric could
    be scored. (Should be rare for tech — price data is universal.)

    Tech Score works for stocks, ETFs, AND crypto — unlike Value
    Score, which is fundamentals-only.
    """
    sub_scores = [
        score_stage_2(metrics.get("stage_2")),
        score_dist_from_20d_high(metrics.get("dist_from_20d_high")),
        score_rs_vs_spy(metrics.get("rs_vs_spy")),
        score_atr_pct(metrics.get("atr_pct")),
    ]
    valid = [s for s in sub_scores if s is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


# --- 4e. Composite Score (Section 7) -------------------------------

def composite_score(value: Optional[float],
                    tech: Optional[float]) -> Optional[float]:
    """
    Combine Value Score and Tech Score into one headline number.

    Per PHASE_4_PLAN.md Section 7:
        composite = 0.5 * value + 0.5 * tech         (both present)
        composite = tech                              (value is N/A — ETF/crypto)
        composite = value                             (tech is N/A — very rare)
        composite = None                              (both are N/A)

    Why a transparent fallback rule instead of "treat N/A as 0":
        Treating N/A as 0 would punish ETFs for not being stocks — a
        category error. The fallback says "we'll use whatever signal
        we DO have." A 100% tech-only score for an ETF is honest:
        it's literally what we have to go on.
    """
    if value is None and tech is None:
        return None
    if value is None:
        return tech
    if tech is None:
        return value
    return 0.5 * value + 0.5 * tech


# --- 5. Score → grade letter ----------------------------------------

def grade_letter(score: Optional[float]) -> str:
    """
    Convert a 0-100 score to the A-F letter from Section 5a.

    >>> grade_letter(76)
    'B'
    >>> grade_letter(None)
    'N/A'
    """
    if score is None:
        return "N/A"
    if score >= 85: return "A"
    if score >= 70: return "B"
    if score >= 50: return "C"
    if score >= 25: return "D"
    return "F"


# --- 6. Run-this-file-directly: walk through the NVDA worked example -

if __name__ == "__main__":
    # The exact example from PHASE_4_PLAN.md Section 5c. If we get
    # 76 ± 1 here, the scorer matches the plan.
    nvda_funds = {
        "debt_to_equity": 0.30,
        "current_ratio":  4.10,
        "net_cash_pct":   8.0,
        "roe":            95.0,
        "fcf_yield":      2.0,
    }

    print("Worked example — NVDA from PHASE_4_PLAN.md Section 5c:")
    print(f"  debt_to_equity = 0.30  -> sub-score "
          f"{score_debt_to_equity(0.30):.1f}  (plan says ~93)")
    print(f"  current_ratio  = 4.10  -> sub-score "
          f"{score_current_ratio(4.10):.1f}  (plan says 100)")
    print(f"  net_cash_pct   = +8    -> sub-score "
          f"{score_net_cash_pct(8.0):.1f}  (plan says 66)")
    print(f"  roe            = 95    -> sub-score "
          f"{score_roe(95.0):.1f}  (plan says 100)")
    print(f"  fcf_yield      = 2     -> sub-score "
          f"{score_fcf_yield(2.0):.1f}  (plan says 20)")
    score = value_score(nvda_funds)
    print(f"\nValue Score = {score:.1f}  Grade = {grade_letter(score)}  "
          f"(plan says 76 B)")

    # Edge cases — quick gut checks
    print("\nEdge-case sanity checks:")
    print(f"  All None (an ETF):           {value_score({})}  "
          f"-> grade {grade_letter(value_score({}))}")
    print(f"  Only ROE known (= 25%):      "
          f"{value_score({'roe': 25.0}):.1f}  -> grade "
          f"{grade_letter(value_score({'roe': 25.0}))}")
    print(f"  Debt-to-equity at floor (2): "
          f"{score_debt_to_equity(2.0):.1f}  (should be 0)")
    print(f"  Debt-to-equity at 0:         "
          f"{score_debt_to_equity(0.0):.1f}  (should be 100)")

    # --- Tech Score sanity checks (Section 6) -----------------------
    print("\nTech Score — sub-score sanity checks:")
    print(f"  stage_2 = True              -> {score_stage_2(True):.0f}   (should be 100)")
    print(f"  stage_2 = False             -> {score_stage_2(False):.0f}   (should be 0)")
    print(f"  dist_from_20d_high = 0%     -> "
          f"{score_dist_from_20d_high(0.0):.1f} (should be 100)")
    print(f"  dist_from_20d_high = 10%    -> "
          f"{score_dist_from_20d_high(10.0):.1f} (should be ~55)")
    print(f"  dist_from_20d_high = 20%    -> "
          f"{score_dist_from_20d_high(20.0):.1f} (should be 0)")
    print(f"  rs_vs_spy = +20%            -> "
          f"{score_rs_vs_spy(20.0):.1f} (should be 100)")
    print(f"  rs_vs_spy = 0%              -> "
          f"{score_rs_vs_spy(0.0):.1f} (should be 50)")
    print(f"  rs_vs_spy = -20%            -> "
          f"{score_rs_vs_spy(-20.0):.1f} (should be 0)")
    print(f"  atr_pct = 3% (sweet spot)   -> "
          f"{score_atr_pct(3.0):.1f} (should be 100)")
    print(f"  atr_pct = 0.5% (dead)       -> "
          f"{score_atr_pct(0.5):.1f} (should be 0)")
    print(f"  atr_pct = 10% (casino)      -> "
          f"{score_atr_pct(10.0):.1f} (should be 0)")
    print(f"  atr_pct = 1.25% (halfway up) -> "
          f"{score_atr_pct(1.25):.1f} (should be 50)")
    print(f"  atr_pct = 7.5% (halfway dn) -> "
          f"{score_atr_pct(7.5):.1f} (should be 50)")

    # End-to-end tech score example: hot uptrending stock
    hot = {"stage_2": True, "dist_from_20d_high": 1.0,
           "rs_vs_spy": 15.0, "atr_pct": 3.5}
    t = tech_score(hot)
    print(f"\nHot uptrending stock: tech_score = {t:.1f}  "
          f"grade = {grade_letter(t)}")

    # Stagnant stock
    cold = {"stage_2": False, "dist_from_20d_high": 18.0,
            "rs_vs_spy": -10.0, "atr_pct": 0.8}
    t = tech_score(cold)
    print(f"Stagnant stock:       tech_score = {t:.1f}  "
          f"grade = {grade_letter(t)}")

    # --- Composite Score sanity checks (Section 7) -----------------
    print("\nComposite Score — fallback rules:")
    print(f"  Stock w/ value=80, tech=60:  composite = "
          f"{composite_score(80, 60):.1f}   (should be 70 — average)")
    print(f"  ETF w/ value=None, tech=72:  composite = "
          f"{composite_score(None, 72):.1f}   (should be 72 — tech only)")
    print(f"  Stock w/ value=85, tech=None: composite = "
          f"{composite_score(85, None):.1f}   (should be 85 — value only)")
    print(f"  Both None:                    composite = "
          f"{composite_score(None, None)}   (should be None)")
