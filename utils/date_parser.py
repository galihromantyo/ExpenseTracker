import re
from datetime import date, timedelta

_MONTHS_ID = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12,
}
_MONTHS_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTHS = {**_MONTHS_ID, **_MONTHS_EN}

_MONTHS_ID_DISPLAY = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def parse_report_month(text: str) -> tuple[int, int] | None:
    """
    Parse a month/year string from user input.
    Returns (year, month) or None.
    Accepts: "April 2026", "2026-04", "04/2026", "bulan ini", "bulan lalu"
    """
    t = text.strip().lower()
    today = date.today()

    if t in ("bulan ini", "this month", "sekarang", "now"):
        return today.year, today.month
    if t in ("bulan lalu", "last month", "kemarin bulan"):
        prev = today.replace(day=1) - timedelta(days=1)
        return prev.year, prev.month

    # "April 2026" / "Apr 2026"
    for name, num in _MONTHS.items():
        m = re.search(rf"\b{re.escape(name)}\b\s+(\d{{4}})", t)
        if m:
            return int(m.group(1)), num
        m = re.search(rf"(\d{{4}})\s+\b{re.escape(name)}\b", t)
        if m:
            return int(m.group(1)), num

    # "2026-04" or "04/2026"
    m = re.match(r"^(\d{4})[-/](\d{1,2})$", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d{1,2})[-/](\d{4})$", t)
    if m:
        return int(m.group(2)), int(m.group(1))

    return None


def month_to_str(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def format_month_display(year: int, month: int) -> str:
    return f"{_MONTHS_ID_DISPLAY[month]} {year}"
