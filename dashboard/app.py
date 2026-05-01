"""
FinTrack Dashboard — Streamlit entry point.

Run with:
    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from streamlit_option_menu import option_menu

from dashboard.auth import login_page, check_session, logout
from dashboard.data_loader import load_expenses, load_budget, load_users

st.set_page_config(
    page_title="FinTrack Dashboard",
    page_icon="💰",
    layout="wide",
)

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not check_session():
    login_page()
    st.stop()

# ── Session info ──────────────────────────────────────────────────────────────
chat_id: str = st.session_state["chat_id"]
display_name: str = st.session_state["display_name"]
is_superuser: bool = st.session_state.get("is_superuser", False)

# ── Load data ─────────────────────────────────────────────────────────────────
df_expenses = load_expenses()
df_budget = load_budget()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 💰 FinTrack")
    st.markdown(f"👤 **{display_name}**")
    if is_superuser:
        st.caption("👑 Superuser")
    st.divider()

    menu_options = ["Overview", "Trends", "Budget vs Aktual", "Transaksi", "Analisa AI"]
    menu_icons = ["house-fill", "graph-up-arrow", "bar-chart-line-fill", "receipt", "robot"]
    if is_superuser:
        menu_options.append("Admin")
        menu_icons.append("shield-lock-fill")

    page = option_menu(
        menu_title=None,
        options=menu_options,
        icons=menu_icons,
        default_index=0,
        styles={
            "container": {"padding": "0"},
            "nav-link": {"font-size": "14px", "margin": "2px 0"},
            "nav-link-selected": {"background-color": "#1f77b4"},
        },
    )

    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        logout()

# ── Page routing ──────────────────────────────────────────────────────────────
if page == "Overview":
    from dashboard.pages.overview import render
    render(df_expenses, df_budget, chat_id)

elif page == "Trends":
    from dashboard.pages.trends import render
    render(df_expenses, chat_id)

elif page == "Budget vs Aktual":
    from dashboard.pages.budget import render
    render(df_expenses, df_budget, chat_id)

elif page == "Transaksi":
    from dashboard.pages.transactions import render
    render(df_expenses, chat_id)

elif page == "Analisa AI":
    from dashboard.pages.analysis import render
    render(df_expenses, df_budget, chat_id)

elif page == "Admin" and is_superuser:
    from dashboard.pages.admin import render
    render(df_expenses, df_budget)
