"""
radar/lookup.py
===============

Given a ticker symbol, hit Yahoo Finance and return everything the
dashboard needs to pre-fill the "Add a new ticker" form. This is the
Radar's "act as my brain" function — Frank should never have to know
what sector NVDA is in, or that Bitcoin's Yahoo symbol is BTC-USD.

Designed to be safe: never raises, never crashes the dashboard.
On any failure (network down, ticker doesn't exist, missing fields)
it returns a dict with `found=False` and lets the UI explain politely.
"""

import yfinance as yf


# --- Helpers ----------------------------------------------------------

def _classify_asset_type(quote_type: str | None,
                         long_name: str | None = None) -> str:
    """
    Map Yahoo's `quoteType` field to our three asset_type buckets:
    stock / etf / crypto.

    Sometimes Yahoo mislabels crypto-trust / Bitwise-style products
    as EQUITY when they're really ETFs. As a backstop, we check the
    `long_name` for ETF/Trust/Fund keywords.
    """
    if quote_type:
        q = quote_type.upper()
        if q == "ETF":
            return "etf"
        if q == "CRYPTOCURRENCY":
            return "crypto"

    # Name-based backstop. Catches "Bitwise XRP ETF", "Grayscale
    # Bitcoin Trust", "SPDR Gold Shares", etc.
    if long_name:
        n = long_name.upper()
        for keyword in ("ETF", "TRUST", "ETN", "ETP", "FUND"):
            if keyword in n:
                return "etf"

    return "stock"


# Crypto symbol aliases — these short symbols mean cryptocurrency to
# Frank, but Yahoo will happily resolve them to grantor trusts or
# crypto-ETFs if asked literally. We force the `-USD` form FIRST so
# typing "BTC" gives you actual Bitcoin (BTC-USD), not an ETF.
_CRYPTO_ALIASES = {
    "BTC":   "BTC-USD",
    "ETH":   "ETH-USD",
    "SOL":   "SOL-USD",
    "ADA":   "ADA-USD",
    "DOGE":  "DOGE-USD",
    "XRP":   "XRP-USD",
    "DOT":   "DOT-USD",
    "MATIC": "MATIC-USD",
    "AVAX":  "AVAX-USD",
    "LTC":   "LTC-USD",
    "LINK":  "LINK-USD",
    "BCH":   "BCH-USD",
    "UNI":   "UNI-USD",
}


def _first_sentence(text: str | None, max_chars: int = 240) -> str:
    """
    Trim Yahoo's `longBusinessSummary` (often multi-paragraph) down to
    the first sentence or `max_chars`, whichever comes first. Keeps the
    radar table readable.
    """
    if not text:
        return ""
    text = text.strip()
    # End of the first sentence is usually ". " (period followed by space).
    end = text.find(". ")
    if end != -1 and end + 1 <= max_chars:
        return text[: end + 1]
    # Otherwise hard-truncate and add an ellipsis to signal there's more.
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def _fetch_info(symbol: str) -> dict:
    """
    Single call to yfinance, wrapped in try/except so any network /
    parsing failure returns an empty dict instead of bubbling up.
    """
    try:
        return yf.Ticker(symbol).info or {}
    except Exception:
        return {}


# --- The one function the app imports ---------------------------------

def lookup_ticker(symbol: str) -> dict:
    """
    Look up a ticker on Yahoo Finance and return a dict the form can
    pre-fill straight from.

    Parameters
    ----------
    symbol : str
        The ticker as Frank typed it. Case and whitespace don't matter.

    Returns
    -------
    dict with these keys:
        symbol       — the canonical symbol Yahoo recognises. May be
                       different from what was typed (e.g., BTC → BTC-USD).
        name         — full name (e.g., "NVIDIA Corporation").
        asset_type   — one of "stock", "etf", "crypto".
        sector       — e.g., "Technology". Empty string for ETFs/crypto.
        sub_sector   — e.g., "Semiconductors". Empty for ETFs/crypto.
        description  — one-sentence company summary.
        found        — True if Yahoo gave us usable data, False otherwise.

    Never raises. On a complete miss (bad ticker, no network, etc.):
        {"symbol": "<what was typed>", "found": False}
    """
    if not symbol or not symbol.strip():
        return {"symbol": "", "found": False}

    typed = symbol.strip().upper()

    # Build the list of candidate symbols to try, in order.
    # 1. KNOWN crypto aliases — try the -USD form FIRST. So typing
    #    "BTC" resolves to actual Bitcoin, not the Grayscale trust.
    # 2. The symbol as typed (covers stocks and ETFs).
    # 3. Same symbol with "-USD" appended (catches less common crypto
    #    like "FET" → "FET-USD"), but only if no suffix and not in aliases.
    candidates = []
    if typed in _CRYPTO_ALIASES:
        candidates.append(_CRYPTO_ALIASES[typed])
    candidates.append(typed)
    if "-" not in typed and typed not in _CRYPTO_ALIASES:
        candidates.append(f"{typed}-USD")

    for candidate in candidates:
        info = _fetch_info(candidate)

        # Yahoo signals "I don't know this ticker" by returning either
        # no info dict, or an info dict missing the basic name fields.
        name = info.get("longName") or info.get("shortName")
        if not name:
            continue  # try the next candidate

        return {
            "symbol":      candidate,
            "name":        name,
            "asset_type":  _classify_asset_type(info.get("quoteType"), name),
            "sector":      info.get("sector") or "",
            "sub_sector":  info.get("industry") or "",
            "description": _first_sentence(info.get("longBusinessSummary")),
            "found":       True,
        }

    # Nothing matched.
    return {"symbol": typed, "found": False}


# --- Run-this-file-directly block for ad-hoc testing -----------------

if __name__ == "__main__":
    # Quick CLI test: `python -m radar.lookup NVDA`
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m radar.lookup <SYMBOL> [SYMBOL ...]")
        raise SystemExit(1)

    for s in sys.argv[1:]:
        result = lookup_ticker(s)
        print(f"\n--- {s} ---")
        for k, v in result.items():
            print(f"  {k:12s} = {v!r}")
