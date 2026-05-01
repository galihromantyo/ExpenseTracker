"""
Loads data from Google Sheets and caches it for 5 minutes.
All functions return pandas DataFrames.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

# Allow imports from the project root
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=_ROOT / ".env", encoding="utf-8-sig")

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
_CACHE_TTL = 300  # 5 minutes


def _get_sheets_id() -> str:
    mode = os.getenv("MODE", "prod").lower()
    if mode == "test":
        sid = os.getenv("GOOGLE_SHEETS_ID_TEST", "")
        if sid:
            return sid
    return os.getenv("GOOGLE_SHEETS_ID", "")


def _build_creds() -> Credentials:
    sa = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if sa.startswith("{"):
        info = json.loads(sa)
        return Credentials.from_service_account_info(info, scopes=_SCOPES)
    path = Path(sa)
    if not path.is_absolute():
        path = _ROOT / path
    return Credentials.from_service_account_file(str(path), scopes=_SCOPES)


@st.cache_resource(ttl=_CACHE_TTL)
def _get_client():
    return gspread.authorize(_build_creds())


def _open_sheet(sheet_name: str) -> list[dict]:
    client = _get_client()
    ss = client.open_by_key(_get_sheets_id())
    try:
        ws = ss.worksheet(sheet_name)
        return ws.get_all_records()
    except gspread.WorksheetNotFound:
        return []


@st.cache_data(ttl=_CACHE_TTL)
def load_expenses() -> pd.DataFrame:
    rows = _open_sheet("Expenses")
    if not rows:
        return pd.DataFrame(columns=[
            "chat_id", "date", "description", "amount", "currency",
            "category", "payment_method", "input_type", "created_at",
        ])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["chat_id"] = df["chat_id"].astype(str)
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["day_of_week"] = df["date"].dt.day_name()
    df["week_of_month"] = ((df["date"].dt.day - 1) // 7 + 1).astype(str)
    return df


@st.cache_data(ttl=_CACHE_TTL)
def load_budget() -> pd.DataFrame:
    rows = _open_sheet("Budget")
    if not rows:
        return pd.DataFrame(columns=[
            "chat_id", "month", "currency", "budget_type", "category", "amount", "notes",
        ])
    df = pd.DataFrame(rows)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["chat_id"] = df["chat_id"].astype(str)
    return df


@st.cache_data(ttl=_CACHE_TTL)
def load_users() -> pd.DataFrame:
    rows = _open_sheet("Users")
    if not rows:
        return pd.DataFrame(columns=[
            "chat_id", "username", "display_name", "default_currency", "joined_at", "is_active",
        ])
    df = pd.DataFrame(rows)
    df["chat_id"] = df["chat_id"].astype(str)
    return df


def get_user_expenses(df_expenses: pd.DataFrame, chat_id: str) -> pd.DataFrame:
    return df_expenses[df_expenses["chat_id"] == str(chat_id)].copy()


def get_user_budget(df_budget: pd.DataFrame, chat_id: str) -> pd.DataFrame:
    return df_budget[df_budget["chat_id"] == str(chat_id)].copy()
