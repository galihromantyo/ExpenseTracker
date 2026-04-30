import re

CURRENCY_SYMBOLS: dict[str, str] = {
    "Rp": "IDR", "IDR": "IDR",
    "$": "USD",  "USD": "USD",
    "€": "EUR",  "EUR": "EUR",
    "£": "GBP",  "GBP": "GBP",
}

# (symbol, is_prefix)
_DISPLAY: dict[str, tuple[str, bool]] = {
    "IDR": ("Rp", True),
    "USD": ("$", True),
    "EUR": ("€", True),
    "GBP": ("£", True),
}


def detect_currency(text: str) -> str | None:
    """Return currency code if a currency symbol/code is found in text, else None."""
    text_stripped = text.strip()
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in text_stripped or symbol.upper() in text_stripped.upper():
            return code
    return None


def normalize_amount(text: str) -> float | None:
    """
    Parse a human-readable amount string to float.
    Handles k/rb/m/jt shortcuts, European/IDR thousand-separator formats.
    Returns None if parsing fails.
    """
    t = text.strip().lower()

    # Strip currency tokens
    for sym in ("rp", "idr", "usd", "eur", "gbp", "$", "€", "£"):
        t = t.replace(sym, "").strip()

    # European / IDR format: 1.000,50 → 1000.50
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", t):
        t = t.replace(".", "").replace(",", ".")
    else:
        # Strip commas used as thousand separators in en-US format
        t = t.replace(",", "")

    multiplier = 1.0
    if t.endswith("juta") or t.endswith("jt"):
        multiplier = 1_000_000
        t = re.sub(r"(juta|jt)$", "", t)
    elif t.endswith("ribu") or t.endswith("rb"):
        multiplier = 1_000
        t = re.sub(r"(ribu|rb)$", "", t)
    elif t.endswith("m"):
        multiplier = 1_000_000
        t = t[:-1]
    elif t.endswith("k"):
        multiplier = 1_000
        t = t[:-1]

    try:
        return float(t) * multiplier
    except ValueError:
        return None


def format_amount(amount: float, currency: str) -> str:
    """Return a display string like 'Rp 25.000' or '£ 12.50'."""
    symbol, is_prefix = _DISPLAY.get(currency, (currency, True))
    if currency == "IDR":
        # Use dots as thousand separators, no decimals
        formatted = f"{amount:,.0f}".replace(",", ".")
    else:
        formatted = f"{amount:,.2f}"
    return f"{symbol} {formatted}" if is_prefix else f"{formatted} {symbol}"
