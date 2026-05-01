"""Transactions page: filterable table + CSV export."""
import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from dashboard.data_loader import get_user_expenses


def render(df_expenses: pd.DataFrame, chat_id: str) -> None:
    st.header("🧾 Transaksi")

    exp = get_user_expenses(df_expenses, chat_id)
    if exp.empty:
        st.info("Belum ada data transaksi.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filter", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            min_date = exp["date"].min().date() if not exp.empty else date.today() - timedelta(days=90)
            max_date = exp["date"].max().date() if not exp.empty else date.today()
            date_range = st.date_input("Rentang Tanggal", value=(min_date, max_date),
                                       min_value=min_date, max_value=max_date)
        with col2:
            all_cats = sorted(exp["category"].dropna().unique().tolist())
            selected_cats = st.multiselect("Kategori", all_cats, default=[])

        col3, col4 = st.columns(2)
        with col3:
            all_methods = sorted(exp["payment_method"].dropna().unique().tolist())
            selected_methods = st.multiselect("Metode Bayar", all_methods, default=[])
        with col4:
            keyword = st.text_input("🔎 Cari deskripsi", "")

    filtered = exp.copy()

    if len(date_range) == 2:
        start_d, end_d = date_range
        filtered = filtered[
            (filtered["date"].dt.date >= start_d) &
            (filtered["date"].dt.date <= end_d)
        ]

    if selected_cats:
        filtered = filtered[filtered["category"].isin(selected_cats)]
    if selected_methods:
        filtered = filtered[filtered["payment_method"].isin(selected_methods)]
    if keyword:
        filtered = filtered[
            filtered["description"].str.contains(keyword, case=False, na=False)
        ]

    display_cols = ["date", "description", "amount", "currency", "category", "payment_method", "input_type"]
    display = filtered[display_cols].copy()
    display["date"] = display["date"].dt.strftime("%Y-%m-%d")
    display = display.sort_values("date", ascending=False)

    st.markdown(f"**{len(display)} transaksi** ditemukan")
    st.dataframe(display, use_container_width=True, hide_index=True)

    # ── CSV export ────────────────────────────────────────────────────────────
    csv_buf = io.StringIO()
    display.to_csv(csv_buf, index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇️ Export CSV",
        data=csv_buf.getvalue().encode("utf-8-sig"),
        file_name="transaksi_export.csv",
        mime="text/csv",
    )
