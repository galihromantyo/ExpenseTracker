import re
from datetime import date, timedelta

from utils.constants import CATEGORIES

_PAYMENT_MAP: dict[str, str] = {
    # Indonesia
    "gopay": "GoPay", "go-pay": "GoPay", "go pay": "GoPay",
    "ovo": "OVO",
    "dana": "Dana",
    "shopeepay": "ShopeePay", "shopee pay": "ShopeePay", "shopee": "ShopeePay",
    "linkaja": "LinkAja", "link aja": "LinkAja",
    "qris": "QRIS",
    "jenius": "Jenius",
    "flip": "Flip",
    # Bank transfer
    "bca": "Bank Transfer", "mandiri": "Bank Transfer", "bri": "Bank Transfer",
    "bni": "Bank Transfer", "cimb": "Bank Transfer", "btn": "Bank Transfer",
    "tf": "Bank Transfer", "transfer": "Bank Transfer",
    "barclays": "Bank Transfer", "hsbc": "Bank Transfer", "lloyds": "Bank Transfer",
    "natwest": "Bank Transfer", "santander": "Bank Transfer", "starling": "Bank Transfer",
    # UK / International
    "revolut": "Revolut",
    "monzo": "Monzo",
    "apple pay": "Apple Pay", "applepay": "Apple Pay",
    "google pay": "Google Pay", "googlepay": "Google Pay", "gpay": "Google Pay",
    "wise": "Wise", "transferwise": "Wise",
    "paypal": "PayPal",
    "contactless": "Contactless",
    # Cards
    "cc": "Credit Card", "credit card": "Credit Card", "kartu kredit": "Credit Card",
    "debit": "Debit Card", "debit card": "Debit Card",
    "amex": "American Express", "american express": "American Express",
    "visa": "Visa",
    "mastercard": "Mastercard", "master card": "Mastercard",
    # Cash
    "cash": "Cash", "tunai": "Cash",
}


def normalize_payment_method(raw: str | None) -> str:
    if not raw:
        return "Cash"
    key = raw.strip().lower()
    return _PAYMENT_MAP.get(key, raw.strip().title())


def normalize_date(raw: str | None) -> str:
    today = date.today()
    if not raw:
        return today.isoformat()
    s = raw.strip().lower()
    if s in ("today", "hari ini", "tadi", "sekarang"):
        return today.isoformat()
    if s in ("yesterday", "kemarin"):
        return (today - timedelta(days=1)).isoformat()
    raw = raw.strip()
    # Already ISO YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    # DD/MM/YY or DD/MM/YYYY (UK/European receipt format)
    m = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})$", raw)
    if m:
        d_str, mo_str, y_str = m.groups()
        y = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
        try:
            return date(y, int(mo_str), int(d_str)).isoformat()
        except ValueError:
            try:
                return date(y, int(d_str), int(mo_str)).isoformat()
            except ValueError:
                pass
    # "10 April 2026" / "April 10, 2026"
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
        "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    m2 = re.match(r"^(\d{1,2})\s+(\w+)\s+(\d{4})$", raw)
    if m2:
        d_str, mon_name, y_str = m2.groups()
        mo = months.get(mon_name.lower())
        if mo:
            try:
                return date(int(y_str), mo, int(d_str)).isoformat()
            except ValueError:
                pass
    m3 = re.match(r"^(\w+)\s+(\d{1,2}),?\s+(\d{4})$", raw)
    if m3:
        mon_name, d_str, y_str = m3.groups()
        mo = months.get(mon_name.lower())
        if mo:
            try:
                return date(int(y_str), mo, int(d_str)).isoformat()
            except ValueError:
                pass
    # Fallback: return today (avoid storing unparseable dates)
    return today.isoformat()


def normalize_category(raw: str | None) -> str:
    if not raw:
        return "Other"
    # Exact match first
    if raw in CATEGORIES:
        return raw
    # Case-insensitive match
    lower = raw.lower()
    for cat in CATEGORIES:
        if cat.lower() == lower:
            return cat
    return "Other"


def normalize_expense(raw: dict, default_currency: str) -> dict:
    """Return a clean, normalised expense dict from raw AI output."""
    exp = dict(raw)

    exp["date"] = normalize_date(exp.get("date"))

    if exp.get("amount") is not None:
        try:
            exp["amount"] = float(exp["amount"])
        except (TypeError, ValueError):
            exp["amount"] = 0.0
    else:
        exp["amount"] = 0.0

    currency = exp.get("currency")
    exp["currency"] = currency if currency in ("IDR", "USD", "EUR", "GBP") else default_currency

    exp["payment_method"] = normalize_payment_method(exp.get("payment_method"))
    exp["category"] = normalize_category(exp.get("category"))

    if not exp.get("description"):
        exp["description"] = "-"

    return exp
