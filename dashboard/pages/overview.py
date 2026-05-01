"""Overview page: KPI cards, bar chart top categories, treemap."""
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.data_loader import get_user_expenses, get_user_budget


def _get_month_options(df: pd.DataFrame) -> list[str]:
    if df.empty or "month" not in df.columns:
        return []
    return sorted(df["month"].dropna().unique().tolist(), reverse=True)


def render(df_expenses: pd.DataFrame, df_budget: pd.DataFrame, chat_id: str) -> None:
    st.header("🏠 Overview")

    exp = get_user_expenses(df_expenses, chat_id)
    bud = get_user_budget(df_budget, chat_id)

    if exp.empty:
        st.info("Belum ada data transaksi. Catat pengeluaran melalui Telegram bot terlebih dahulu.")
        return

    months = _get_month_options(exp)
    today_month = date.today().strftime("%Y-%m")
    default_idx = months.index(today_month) if today_month in months else 0

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_month = st.selectbox("📅 Pilih Bulan", months, index=default_idx)
    with col2:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

    month_exp = exp[exp["month"] == selected_month]
    if month_exp.empty:
        st.warning(f"Tidak ada transaksi di {selected_month}.")
        return

    primary_currency = month_exp["currency"].mode()[0] if not month_exp.empty else "IDR"
    same_currency = month_exp[month_exp["currency"] == primary_currency]
    total_spent = same_currency["amount"].sum()

    # MoM comparison
    months_sorted = sorted(months)
    cur_idx = months_sorted.index(selected_month) if selected_month in months_sorted else -1
    mom_pct = None
    if cur_idx > 0:
        prev_month = months_sorted[cur_idx - 1]
        prev_exp = exp[exp["month"] == prev_month]
        prev_total = prev_exp[prev_exp["currency"] == primary_currency]["amount"].sum()
        if prev_total > 0:
            mom_pct = (total_spent - prev_total) / prev_total * 100

    # Budget
    month_bud = bud[bud["month"] == selected_month]
    total_budget = None
    if not month_bud.empty:
        total_bud_row = month_bud[month_bud["budget_type"] == "total"]
        if not total_bud_row.empty:
            total_budget = total_bud_row["amount"].sum()

    # KPI cards
    c1, c2, c3 = st.columns(3)
    mom_str = f" ({'▲' if mom_pct and mom_pct > 0 else '▼'} {abs(mom_pct):.1f}% MoM)" if mom_pct is not None else ""
    with c1:
        st.metric("💸 Total Keluar", f"{primary_currency} {total_spent:,.0f}{mom_str}")
    with c2:
        if total_budget:
            sisa = total_budget - total_spent
            pct_used = total_spent / total_budget * 100
            st.metric("💵 Sisa Budget", f"{primary_currency} {max(sisa, 0):,.0f}",
                      delta=f"{pct_used:.0f}% terpakai", delta_color="inverse")
        else:
            st.metric("💵 Sisa Budget", "—", help="Budget belum diset. Gunakan /budget di Telegram.")
    with c3:
        st.metric("🧾 Jumlah Transaksi", len(month_exp))

    st.divider()

    # Bar chart — top 8 categories
    by_cat = (
        same_currency.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
        .head(8)
    )
    fig_bar = px.bar(
        by_cat, x="category", y="amount",
        title=f"📊 Top Kategori — {selected_month}",
        labels={"category": "Kategori", "amount": f"Jumlah ({primary_currency})"},
        color="amount",
        color_continuous_scale="Blues",
    )
    fig_bar.update_layout(showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig_bar, use_container_width=True)

    # Treemap — proportional view
    fig_tree = px.treemap(
        same_currency,
        path=["category"],
        values="amount",
        title=f"🌳 Proporsi Pengeluaran — {selected_month}",
        color="amount",
        color_continuous_scale="RdYlGn_r",
    )
    fig_tree.update_traces(textinfo="label+percent root")
    fig_tree.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig_tree, use_container_width=True)
