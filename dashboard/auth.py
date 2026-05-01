"""
Simple session-based auth for the Streamlit dashboard.
Passwords are stored as bcrypt hashes in the Users sheet (password_hash column).
For initial setup, generate a hash with: bcrypt.hashpw(b"yourpassword", bcrypt.gensalt()).decode()

If no password_hash column exists, any password is accepted (dev mode).
"""
import os
from datetime import datetime, timedelta

import bcrypt
import streamlit as st

from dashboard.data_loader import load_users

_SESSION_TIMEOUT_MINUTES = 60


def _get_superuser_ids() -> list[str]:
    raw = os.getenv("SUPERUSER_CHAT_IDS", "")
    return [p.strip() for p in raw.split(",") if p.strip()]


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def login_page() -> None:
    st.title("💰 FinTrack Dashboard")
    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Username (Telegram username)")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if not submitted:
        return

    users_df = load_users()
    if users_df.empty:
        st.error("Belum ada user terdaftar. Gunakan Telegram bot dulu untuk registrasi.")
        return

    match = users_df[users_df["username"] == username.lstrip("@")]
    if match.empty:
        st.error("Username tidak ditemukan.")
        return

    user_row = match.iloc[0]

    # Check password — if no password_hash column yet, accept anything (dev mode)
    if "password_hash" in users_df.columns and user_row.get("password_hash", ""):
        if not _verify_password(password, str(user_row["password_hash"])):
            st.error("Password salah.")
            return
    else:
        st.warning("⚠️ Mode dev: password tidak dicek (kolom password_hash belum ada di sheet Users).")

    superuser_ids = _get_superuser_ids()
    is_superuser = str(user_row["chat_id"]) in superuser_ids

    st.session_state["authenticated"] = True
    st.session_state["chat_id"] = str(user_row["chat_id"])
    st.session_state["display_name"] = str(user_row.get("display_name", username))
    st.session_state["is_superuser"] = is_superuser
    st.session_state["login_time"] = datetime.now()
    st.rerun()


def check_session() -> bool:
    """Return True if a valid session exists, False otherwise."""
    if not st.session_state.get("authenticated"):
        return False
    login_time = st.session_state.get("login_time")
    if login_time and (datetime.now() - login_time) > timedelta(minutes=_SESSION_TIMEOUT_MINUTES):
        logout()
        return False
    return True


def logout() -> None:
    for key in ["authenticated", "chat_id", "display_name", "is_superuser", "login_time"]:
        st.session_state.pop(key, None)
    st.rerun()
