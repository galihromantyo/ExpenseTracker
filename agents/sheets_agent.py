import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_DIR = Path(__file__).parent.parent
_log = logging.getLogger(__name__)

import gspread
from google.oauth2.service_account import Credentials

from config import config
from utils.constants import EXPENSES_HEADERS, BUDGET_HEADERS, USERS_HEADERS

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _build_creds() -> Credentials:
    sa = config.google_service_account_json.strip()
    if sa.startswith("{"):
        info = json.loads(sa)
        return Credentials.from_service_account_info(info, scopes=_SCOPES)
    path = Path(sa)
    if not path.is_absolute():
        path = _PROJECT_DIR / path
    return Credentials.from_service_account_file(str(path), scopes=_SCOPES)


def _get_worksheet(sheet_name: str) -> gspread.Worksheet:
    creds = _build_creds()
    client = gspread.authorize(creds)
    ss = client.open_by_key(config.active_sheets_id)
    try:
        ws = ss.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=sheet_name, rows=2000, cols=20)
        if sheet_name == "Expenses":
            ws.append_row(EXPENSES_HEADERS)
        elif sheet_name == "Budget":
            ws.append_row(BUDGET_HEADERS)
        elif sheet_name == "Users":
            ws.append_row(USERS_HEADERS)
    return ws


# ── Sync helpers ─────────────────────────────────────────────────────────────

def _sync_append_expense(chat_id: int, expense: dict) -> int:
    ws = _get_worksheet("Expenses")
    expense["created_at"] = datetime.now(timezone.utc).isoformat()
    row = [
        str(chat_id),
        expense.get("date", ""),
        expense.get("description", ""),
        expense.get("amount", 0),
        expense.get("currency", "IDR"),
        expense.get("category", "Other"),
        expense.get("payment_method", ""),
        expense.get("input_type", "text"),
        expense.get("created_at", ""),
    ]
    _log.info("Appending to Sheets [chat_id=%s date=%s amount=%s %s]",
              chat_id, expense.get("date"), expense.get("amount"), expense.get("currency"))
    ws.append_row(row, value_input_option="RAW")
    total = len(ws.get_all_values())
    _log.info("Sheets write OK — worksheet now has %d rows (incl. header)", total)
    return total


def _sync_get_expenses_for_month(chat_id: int, month: str) -> list[dict]:
    ws = _get_worksheet("Expenses")
    return [
        r for r in ws.get_all_records()
        if str(r.get("chat_id", "")) == str(chat_id)
        and str(r.get("date", "")).startswith(month)
    ]


def _sync_get_recent_expenses(chat_id: int, n: int) -> list[dict]:
    ws = _get_worksheet("Expenses")
    all_rows = ws.get_all_records()
    result = []
    for i, row in enumerate(all_rows, start=2):
        if str(row.get("chat_id", "")) == str(chat_id):
            row["_row"] = i
            result.append(row)
    return result[-n:]


def _sync_update_expense(row_number: int, expense: dict) -> None:
    ws = _get_worksheet("Expenses")
    row = [
        str(expense.get("chat_id", "")),
        expense.get("date", ""),
        expense.get("description", ""),
        expense.get("amount", 0),
        expense.get("currency", "IDR"),
        expense.get("category", "Other"),
        expense.get("payment_method", ""),
        expense.get("input_type", "text"),
        expense.get("created_at", ""),
    ]
    ws.update(f"A{row_number}:I{row_number}", [row])


def _sync_delete_expense(row_number: int) -> None:
    _get_worksheet("Expenses").delete_rows(row_number)


def _sync_get_budget(chat_id: int, month: str) -> list[dict]:
    ws = _get_worksheet("Budget")
    return [
        r for r in ws.get_all_records()
        if str(r.get("chat_id", "")) == str(chat_id)
        and str(r.get("month", "")) == month
    ]


def _sync_set_budget(chat_id: int, month: str, entries: list[dict]) -> None:
    ws = _get_worksheet("Budget")
    all_vals = ws.get_all_values()
    to_delete = [
        i + 2 for i, row in enumerate(all_vals[1:])
        if row and str(row[0]) == str(chat_id) and len(row) > 1 and row[1] == month
    ]
    for rn in reversed(to_delete):
        ws.delete_rows(rn)
    for entry in entries:
        ws.append_row([
            str(chat_id),
            month,
            entry.get("currency", "IDR"),
            entry.get("budget_type", "total"),
            entry.get("category", ""),
            entry.get("amount", 0),
            entry.get("notes", ""),
        ])


def _sync_delete_budget(chat_id: int, month: str) -> None:
    ws = _get_worksheet("Budget")
    all_vals = ws.get_all_values()
    to_delete = [
        i + 2 for i, row in enumerate(all_vals[1:])
        if row and str(row[0]) == str(chat_id) and len(row) > 1 and row[1] == month
    ]
    for rn in reversed(to_delete):
        ws.delete_rows(rn)


def _sync_get_expenses_range(chat_id: int, start_month: str, end_month: str) -> list[dict]:
    ws = _get_worksheet("Expenses")
    return [
        r for r in ws.get_all_records()
        if str(r.get("chat_id", "")) == str(chat_id)
        and start_month <= str(r.get("date", ""))[:7] <= end_month
    ]


# ── Users sheet ───────────────────────────────────────────────────────────────

def _sync_get_user(chat_id: int) -> dict | None:
    ws = _get_worksheet("Users")
    for row in ws.get_all_records():
        if str(row.get("chat_id", "")) == str(chat_id):
            return row
    return None


def _sync_upsert_user(chat_id: int, username: str, display_name: str,
                       default_currency: str, is_active: bool = True) -> None:
    ws = _get_worksheet("Users")
    all_vals = ws.get_all_values()
    for i, row in enumerate(all_vals[1:], start=2):
        if row and str(row[0]) == str(chat_id):
            ws.update(f"A{i}:F{i}", [[
                str(chat_id), username, display_name,
                default_currency, row[4], str(is_active),
            ]])
            return
    # New user
    ws.append_row([
        str(chat_id),
        username,
        display_name,
        default_currency,
        datetime.now(timezone.utc).isoformat(),
        str(is_active),
    ])


def _sync_set_user_currency(chat_id: int, currency: str) -> None:
    ws = _get_worksheet("Users")
    all_vals = ws.get_all_values()
    for i, row in enumerate(all_vals[1:], start=2):
        if row and str(row[0]) == str(chat_id):
            ws.update_cell(i, 4, currency)
            return


def _sync_set_user_password(chat_id: int, password_hash: str) -> bool:
    ws = _get_worksheet("Users")
    all_vals = ws.get_all_values()
    for i, row in enumerate(all_vals[1:], start=2):
        if row and str(row[0]) == str(chat_id):
            ws.update_cell(i, 7, password_hash)
            return True
    return False


def _sync_get_all_expenses_for_month(month: str) -> list[dict]:
    """Superuser: all users, one month."""
    ws = _get_worksheet("Expenses")
    return [r for r in ws.get_all_records() if str(r.get("date", "")).startswith(month)]


def _sync_get_all_users() -> list[dict]:
    """Superuser: list all registered users."""
    ws = _get_worksheet("Users")
    return ws.get_all_records()


def _sync_get_expenses_range_all_users(start_month: str, end_month: str) -> list[dict]:
    """Superuser: all users, date range — used by dashboard admin page."""
    ws = _get_worksheet("Expenses")
    return [
        r for r in ws.get_all_records()
        if start_month <= str(r.get("date", ""))[:7] <= end_month
    ]


# ── Async public API ──────────────────────────────────────────────────────────

async def append_expense(chat_id: int, expense: dict) -> int:
    return await asyncio.to_thread(_sync_append_expense, chat_id, expense)


async def get_expenses_for_month(chat_id: int, month: str) -> list[dict]:
    return await asyncio.to_thread(_sync_get_expenses_for_month, chat_id, month)


async def get_recent_expenses(chat_id: int, n: int = 10) -> list[dict]:
    return await asyncio.to_thread(_sync_get_recent_expenses, chat_id, n)


async def update_expense(row_number: int, expense: dict) -> None:
    await asyncio.to_thread(_sync_update_expense, row_number, expense)


async def delete_expense(row_number: int) -> None:
    await asyncio.to_thread(_sync_delete_expense, row_number)


async def get_budget(chat_id: int, month: str) -> list[dict]:
    return await asyncio.to_thread(_sync_get_budget, chat_id, month)


async def set_budget(chat_id: int, month: str, entries: list[dict]) -> None:
    await asyncio.to_thread(_sync_set_budget, chat_id, month, entries)


async def delete_budget(chat_id: int, month: str) -> None:
    await asyncio.to_thread(_sync_delete_budget, chat_id, month)


async def get_expenses_range(chat_id: int, start_month: str, end_month: str) -> list[dict]:
    return await asyncio.to_thread(_sync_get_expenses_range, chat_id, start_month, end_month)


async def get_user(chat_id: int) -> dict | None:
    return await asyncio.to_thread(_sync_get_user, chat_id)


async def upsert_user(chat_id: int, username: str, display_name: str,
                      default_currency: str, is_active: bool = True) -> None:
    await asyncio.to_thread(_sync_upsert_user, chat_id, username, display_name,
                             default_currency, is_active)


async def set_user_currency(chat_id: int, currency: str) -> None:
    await asyncio.to_thread(_sync_set_user_currency, chat_id, currency)


async def set_user_password(chat_id: int, password_hash: str) -> bool:
    return await asyncio.to_thread(_sync_set_user_password, chat_id, password_hash)


async def get_all_expenses_for_month(month: str) -> list[dict]:
    return await asyncio.to_thread(_sync_get_all_expenses_for_month, month)


async def get_all_users() -> list[dict]:
    return await asyncio.to_thread(_sync_get_all_users)


async def get_expenses_range_all_users(start_month: str, end_month: str) -> list[dict]:
    return await asyncio.to_thread(_sync_get_expenses_range_all_users, start_month, end_month)
