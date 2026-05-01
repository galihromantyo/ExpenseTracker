"""
Seed synthetic test data into the TEST Google Spreadsheet.

Usage:
    # Make sure MODE=test in .env, then:
    python seed_test_data.py

    # Or override directly:
    MODE=test python seed_test_data.py

Generates:
  - 3 users: Alice (GBP), Budi (IDR), Carol (EUR)
  - 4 months: Feb–May 2026 (May = partial, ~2 weeks)
  - Expenses + budgets per user
  - Safe to re-run: clears existing test data first
"""
import json
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent
load_dotenv(dotenv_path=_ROOT / ".env", encoding="utf-8-sig")
sys.path.insert(0, str(_ROOT))

import gspread
from google.oauth2.service_account import Credentials

from utils.constants import EXPENSES_HEADERS, BUDGET_HEADERS, USERS_HEADERS

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Config ────────────────────────────────────────────────────────────────────

MODE = os.getenv("MODE", "prod").lower()
if MODE != "test":
    print("❌ MODE is not 'test'. Set MODE=test in .env before running this script.")
    sys.exit(1)

SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID_TEST", "")
if not SHEETS_ID:
    print("❌ GOOGLE_SHEETS_ID_TEST is not set in .env.")
    sys.exit(1)

SA_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

# ── Test users ────────────────────────────────────────────────────────────────

USERS = [
    {"chat_id": "1001", "username": "alice_fin", "display_name": "Alice", "default_currency": "GBP"},
    {"chat_id": "1002", "username": "budi_finance", "display_name": "Budi", "default_currency": "IDR"},
    {"chat_id": "1003", "username": "carol_eu", "display_name": "Carol", "default_currency": "EUR"},
]

# ── Category templates per user ───────────────────────────────────────────────

ALICE_CATS = {
    "Rent & Housing": (1500, 1500), "Groceries": (180, 250), "Food & Dining": (150, 300),
    "Transport": (80, 150), "Subscriptions": (25, 40), "Shopping": (50, 200),
    "Health & Medical": (0, 80), "Entertainment": (20, 60), "Personal Care": (30, 70),
}
BUDI_CATS = {
    "Rent & Housing": (3500000, 3500000), "Groceries": (800000, 1200000),
    "Food & Dining": (500000, 900000), "Transport": (200000, 400000),
    "Subscriptions": (100000, 150000), "Shopping": (200000, 600000),
    "Remittance": (0, 500000), "Utilities & Bills": (200000, 350000),
    "Health & Medical": (0, 300000),
}
CAROL_CATS = {
    "Rent & Housing": (900, 900), "Groceries": (200, 320), "Food & Dining": (100, 250),
    "Transport": (60, 120), "Subscriptions": (30, 50), "Education": (0, 100),
    "Shopping": (50, 180), "Entertainment": (30, 80),
}

USER_CATS = {
    "1001": (ALICE_CATS, "GBP"),
    "1002": (BUDI_CATS, "IDR"),
    "1003": (CAROL_CATS, "EUR"),
}

PAYMENT_METHODS = {
    "GBP": ["Monzo", "Revolut", "Contactless", "Credit Card", "Cash"],
    "IDR": ["GoPay", "OVO", "Dana", "Bank Transfer", "Cash", "QRIS"],
    "EUR": ["Revolut", "Credit Card", "Cash", "Bank Transfer"],
}

DESCRIPTIONS = {
    "Rent & Housing": ["Monthly rent", "Sewa bulan ini", "Loyer mensuel"],
    "Groceries": ["Tesco weekly shop", "Belanja Indomaret", "Lidl groceries",
                  "Alfamart", "Supermarket", "Market run"],
    "Food & Dining": ["Pret A Manger lunch", "Makan siang warteg", "McDonald's",
                      "Kopi kenangan", "Coffee & pastry", "Grab Food order",
                      "Dinner with friends", "Makan malam", "Boulangerie"],
    "Transport": ["TfL Oyster top-up", "Grab", "Gojek ojek", "Bus ticket",
                  "KRL Commuter Line", "Metro ticket", "Uber"],
    "Subscriptions": ["Netflix", "Spotify", "iCloud storage", "YouTube Premium",
                      "Microsoft 365", "Disney+"],
    "Shopping": ["ASOS order", "Shopee", "H&M", "Tokopedia", "Amazon", "Zara"],
    "Health & Medical": ["Gym membership", "Pharmacy", "Doctor visit", "Apotek"],
    "Utilities & Bills": ["Electric bill", "Listrik PLN", "Internet Indihome",
                          "Water bill", "Phone top-up"],
    "Remittance": ["Wise transfer to family", "Kirim uang ke Jakarta"],
    "Entertainment": ["Cinema ticket", "Bioskop", "Concert", "Museum entry"],
    "Personal Care": ["Haircut", "Potong rambut", "Skincare", "Salon"],
    "Education": ["Udemy course", "Book", "Language class"],
    "Travel": ["Flight booking", "Hotel", "Airbnb"],
    "Insurance": ["Health insurance premium"],
    "Other": ["Miscellaneous", "Lain-lain"],
}

# ── Date ranges ───────────────────────────────────────────────────────────────

MONTHS = [
    ("2026-02", date(2026, 2, 1), date(2026, 2, 28)),
    ("2026-03", date(2026, 3, 1), date(2026, 3, 31)),
    ("2026-04", date(2026, 4, 1), date(2026, 4, 30)),
    ("2026-05", date(2026, 5, 1), date(2026, 5, 15)),  # partial — current month
]

BUDGETS = {
    "1001": {  # Alice GBP
        "2026-02": [("total", "", 3000)],
        "2026-03": [("per_category", "Rent & Housing", 1500), ("per_category", "Groceries", 250),
                    ("per_category", "Food & Dining", 300), ("per_category", "Transport", 120),
                    ("per_category", "Shopping", 150)],
        "2026-04": [("per_category", "Rent & Housing", 1500), ("per_category", "Groceries", 250),
                    ("per_category", "Food & Dining", 300), ("per_category", "Transport", 120),
                    ("per_category", "Shopping", 150)],
        "2026-05": [("total", "", 3000)],
    },
    "1002": {  # Budi IDR
        "2026-02": [("total", "", 8000000)],
        "2026-03": [("per_category", "Rent & Housing", 3500000), ("per_category", "Groceries", 1000000),
                    ("per_category", "Food & Dining", 800000), ("per_category", "Transport", 350000)],
        "2026-04": [("per_category", "Rent & Housing", 3500000), ("per_category", "Groceries", 1000000),
                    ("per_category", "Food & Dining", 800000), ("per_category", "Transport", 350000)],
        "2026-05": [("total", "", 8000000)],
    },
    "1003": {  # Carol EUR
        "2026-02": [("total", "", 2000)],
        "2026-03": [("per_category", "Rent & Housing", 900), ("per_category", "Groceries", 300),
                    ("per_category", "Food & Dining", 200), ("per_category", "Transport", 100)],
        "2026-04": [("per_category", "Rent & Housing", 900), ("per_category", "Groceries", 300),
                    ("per_category", "Food & Dining", 200), ("per_category", "Transport", 100)],
        "2026-05": [("total", "", 2000)],
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_creds() -> Credentials:
    if SA_JSON.startswith("{"):
        info = json.loads(SA_JSON)
        return Credentials.from_service_account_info(info, scopes=_SCOPES)
    path = Path(SA_JSON)
    if not path.is_absolute():
        path = _ROOT / path
    return Credentials.from_service_account_file(str(path), scopes=_SCOPES)


def _get_or_create_ws(ss: gspread.Spreadsheet, name: str, headers: list) -> gspread.Worksheet:
    try:
        ws = ss.worksheet(name)
        ws.clear()
        ws.append_row(headers)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=2000, cols=20)
        ws.append_row(headers)
    return ws


def _rand_date(start: date, end: date) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()


def _generate_expenses(chat_id: str, cats: dict, currency: str,
                        start: date, end: date, n_per_month: int = 20) -> list[list]:
    rows = []
    cat_list = list(cats.keys())
    methods = PAYMENT_METHODS[currency]
    # Weight: frequent categories appear more
    weights = [3 if c in ("Food & Dining", "Groceries", "Transport") else 1 for c in cat_list]
    for _ in range(n_per_month):
        cat = random.choices(cat_list, weights=weights)[0]
        lo, hi = cats[cat]
        if lo == hi:
            amount = lo
        elif lo == 0 and hi == 0:
            continue
        elif lo == 0:
            if random.random() < 0.3:  # 30% chance of occasional spend
                amount = round(random.uniform(hi * 0.3, hi), 2)
            else:
                continue
        else:
            amount = round(random.uniform(lo, hi), 2)
        if amount <= 0:
            continue
        descs = DESCRIPTIONS.get(cat, ["Expense"])
        rows.append([
            chat_id,
            _rand_date(start, end),
            random.choice(descs),
            amount,
            currency,
            cat,
            random.choice(methods),
            "text",
            f"{start.isoformat()}T09:00:00+00:00",
        ])
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    random.seed(42)

    print(f"Connecting to test spreadsheet: {SHEETS_ID}")
    creds = _build_creds()
    client = gspread.authorize(creds)
    ss = client.open_by_key(SHEETS_ID)

    # Create/clear sheets
    ws_users = _get_or_create_ws(ss, "Users", USERS_HEADERS)
    ws_expenses = _get_or_create_ws(ss, "Expenses", EXPENSES_HEADERS)
    ws_budget = _get_or_create_ws(ss, "Budget", BUDGET_HEADERS)

    # Users
    for u in USERS:
        ws_users.append_row([
            u["chat_id"], u["username"], u["display_name"],
            u["default_currency"], "2026-02-01T09:00:00+00:00", "True",
        ])
    print(f"✅ Users: {len(USERS)} seeded")

    # Expenses
    expense_rows: list[list] = []
    for month_str, start, end in MONTHS:
        n = 15 if month_str == "2026-05" else 22  # fewer rows for partial month
        for u in USERS:
            cid = u["chat_id"]
            cats, currency = USER_CATS[cid]
            expense_rows.extend(_generate_expenses(cid, cats, currency, start, end, n_per_month=n))

    # Sort by date
    expense_rows.sort(key=lambda r: r[1])
    if expense_rows:
        ws_expenses.append_rows(expense_rows)
    print(f"✅ Expenses: {len(expense_rows)} rows seeded across {len(MONTHS)} months × {len(USERS)} users")

    # Budgets
    budget_rows: list[list] = []
    for cid, month_budgets in BUDGETS.items():
        for month_str, entries in month_budgets.items():
            currency = next(u["default_currency"] for u in USERS if u["chat_id"] == cid)
            for btype, cat, amount in entries:
                budget_rows.append([cid, month_str, currency, btype, cat, amount, ""])
    if budget_rows:
        ws_budget.append_rows(budget_rows)
    print(f"✅ Budgets: {len(budget_rows)} entries seeded")

    print("\n🎉 Test data seeded successfully!")
    print(f"   Spreadsheet: https://docs.google.com/spreadsheets/d/{SHEETS_ID}")
    print("   Users: Alice (GBP/1001), Budi (IDR/1002), Carol (EUR/1003)")
    print("   Months: Feb–May 2026 (May partial)")


if __name__ == "__main__":
    main()
