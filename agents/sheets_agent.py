import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_DIR = Path(__file__).parent.parent

import gspread
from google.oauth2.service_account import Credentials

from config import config
from utils.constants import EXPENSES_HEADERS, BUDGET_HEADERS

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _build_creds() -> Credentials:
    sa = config.google_service_account_json.strip()
    if sa.startswith("{"):
        info = json.loads(sa)
        return Credentials.from_service_account_info(info, scopes=_SCOPES)
    # Resolve relative path from project root
    path = Path(sa)
    if not path.is_absolute():
        path = _PROJECT_DIR / path
    return Credentials.from_service_account_file(str(path), scopes=_SCOPES)


def _get_worksheet(sheet_name: str) -> gspread.Worksheet:
    creds = _build_creds()
    client = gspread.authorize(creds)
    ss = client.open_by_key(config.google_sheets_id)
    try:
        ws = ss.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=sheet_name, rows=2000, cols=20)
        headers = EXPENSES_HEADERS if sheet_name == "Expenses" else BUDGET_HEADERS
        ws.append_row(headers)
    return ws


# ── Sync helpers (run via asyncio.to_thread) ────────────────────────────────

def _sync_append_expense(expense: dict) -> int:
    ws = _get_worksheet("Expenses")
    expense["created_at"] = datetime.now(timezone.utc).isoformat()
    row = [
        expense.get("date", ""),
        expense.get("description", ""),
        expense.get("amount", 0),
        expense.get("currency", "IDR"),
        expense.get("category", "Other"),
        expense.get("payment_method", ""),
        expense.get("input_type", "text"),
        expense.get("created_at", ""),
    ]
    ws.append_row(row)
    return len(ws.get_all_values())


def _sync_get_expenses_for_month(month: str) -> list[dict]:
    ws = _get_worksheet("Expenses")
    return [r for r in ws.get_all_records() if str(r.get("date", "")).startswith(month)]


def _sync_get_recent_expenses(n: int) -> list[dict]:
    ws = _get_worksheet("Expenses")
    all_rows = ws.get_all_records()
    result = []
    for i, row in enumerate(all_rows, start=2):
        row["_row"] = i
        result.append(row)
    return result[-n:]


def _sync_update_expense(row_number: int, expense: dict) -> None:
    ws = _get_worksheet("Expenses")
    row = [
        expense.get("date", ""),
        expense.get("description", ""),
        expense.get("amount", 0),
        expense.get("currency", "IDR"),
        expense.get("category", "Other"),
        expense.get("payment_method", ""),
        expense.get("input_type", "text"),
        expense.get("created_at", ""),
    ]
    ws.update(f"A{row_number}:H{row_number}", [row])


def _sync_delete_expense(row_number: int) -> None:
    _get_worksheet("Expenses").delete_rows(row_number)


def _sync_get_budget(month: str) -> list[dict]:
    ws = _get_worksheet("Budget")
    return [r for r in ws.get_all_records() if str(r.get("month", "")) == month]


def _sync_set_budget(month: str, entries: list[dict]) -> None:
    ws = _get_worksheet("Budget")
    all_vals = ws.get_all_values()
    # Find rows to delete (bottom-up to avoid index shift)
    to_delete = [i + 2 for i, row in enumerate(all_vals[1:]) if row and row[0] == month]
    for rn in reversed(to_delete):
        ws.delete_rows(rn)
    for entry in entries:
        ws.append_row([
            month,
            entry.get("currency", "IDR"),
            entry.get("budget_type", "total"),
            entry.get("category", ""),
            entry.get("amount", 0),
            entry.get("notes", ""),
        ])


def _sync_delete_budget(month: str) -> None:
    ws = _get_worksheet("Budget")
    all_vals = ws.get_all_values()
    to_delete = [i + 2 for i, row in enumerate(all_vals[1:]) if row and row[0] == month]
    for rn in reversed(to_delete):
        ws.delete_rows(rn)


def _sync_get_expenses_range(start_month: str, end_month: str) -> list[dict]:
    ws = _get_worksheet("Expenses")
    return [
        r for r in ws.get_all_records()
        if start_month <= str(r.get("date", ""))[:7] <= end_month
    ]


# ── Async public API ─────────────────────────────────────────────────────────

async def append_expense(expense: dict) -> int:
    return await asyncio.to_thread(_sync_append_expense, expense)


async def get_expenses_for_month(month: str) -> list[dict]:
    return await asyncio.to_thread(_sync_get_expenses_for_month, month)


async def get_recent_expenses(n: int = 10) -> list[dict]:
    return await asyncio.to_thread(_sync_get_recent_expenses, n)


async def update_expense(row_number: int, expense: dict) -> None:
    await asyncio.to_thread(_sync_update_expense, row_number, expense)


async def delete_expense(row_number: int) -> None:
    await asyncio.to_thread(_sync_delete_expense, row_number)


async def get_budget(month: str) -> list[dict]:
    return await asyncio.to_thread(_sync_get_budget, month)


async def set_budget(month: str, entries: list[dict]) -> None:
    await asyncio.to_thread(_sync_set_budget, month, entries)


async def delete_budget(month: str) -> None:
    await asyncio.to_thread(_sync_delete_budget, month)


async def get_expenses_range(start_month: str, end_month: str) -> list[dict]:
    return await asyncio.to_thread(_sync_get_expenses_range, start_month, end_month)
