"""Budget vs Aktual page: cumulative spending line, grouped bar, progress bars."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.data_loader import get_user_expenses, get_user_budget


def render(df_expenses: pd.DataFrame, df_budget: pd.DataFrame, chat_id: str) -> None:
    st.header("⚖️ Budget vs Aktual")

    exp = get_user_expenses(df_expenses, chat_id)
    bud = get_user_budget(df_budget, chat_id)

    if exp.empty:
        st.info("Belum ada data transaksi.")
        return

    months = sorted(exp["month"].dropna().unique().tolist(), reverse=True)
    today_month = date.today().strftime("%Y-%m")
    default_idx = months.index(today_month) if today_month in months else 0
    selected_month = st.selectbox("📅 Pilih Bulan", months, index=default_idx)

    month_exp = exp[exp["month"] == selected_month]
    month_bud = bud[bud["month"] == selected_month]

    primary_currency = month_exp["currency"].mode()[0] if not month_exp.empty else "IDR"
    same_currency = month_exp[month_exp["currency"] == primary_currency]

    # ── Cumulative spending line vs budget ────────────────────────────────────
    st.subheader("📉 Akumulasi Pengeluaran Harian")
    daily = (
        same_currency.groupby(same_currency["date"].dt.date)["amount"]
        .sum()
        .reset_index()
        .rename(columns={"date": "day", "amount": "daily"})
        .sort_values("day")
    )
    daily["cumulative"] = daily["daily"].cumsum()

    total_budget_row = month_bud[month_bud["budget_type"] == "total"]
    total_budget = float(total_budget_row["amount"].sum()) if not total_budget_row.empty else None

    fig_cum = go.Figure()
    fig_cum.add_trace(go.Scatter(
        x=daily["day"], y=daily["cumulative"],
        mode="lines+markers", name="Pengeluaran Kumulatif",
        line=dict(color="#1f77b4", width=2),
    ))
    if total_budget:
        fig_cum.add_hline(
            y=total_budget, line_dash="dash", line_color="red",
            annotation_text=f"Budget {primary_currency} {total_budget:,.0f}",
            annotation_position="top left",
        )
    fig_cum.update_layout(
        xaxis_title="Tanggal",
        yaxis_title=f"Kumulatif ({primary_currency})",
        height=350,
    )
    st.plotly_chart(fig_cum, use_container_width=True)

    # ── Budget vs Aktual per category ────────────────────────────────────────
    st.subheader("📊 Budget vs Aktual per Kategori")
    cat_spent = same_currency.groupby("category")["amount"].sum().to_dict()
    cat_bud_rows = month_bud[month_bud["budget_type"] == "per_category"]
    cat_budget = dict(zip(cat_bud_rows["category"], cat_bud_rows["amount"].astype(float)))

    all_cats = sorted(set(cat_spent.keys()) | set(cat_budget.keys()))
    if not all_cats:
        st.info("Belum ada data untuk ditampilkan.")
        return

    has_cat_budget = bool(cat_budget)

    if not has_cat_budget:
        st.info(
            "ℹ️ Budget bulan ini diset sebagai **total** (bukan per kategori). "
            "Lihat garis budget di grafik akumulasi di atas."
        )

    spent_vals = [cat_spent.get(c, 0) for c in all_cats]
    budget_vals = [cat_budget.get(c, None) for c in all_cats]
    colors = []
    for c in all_cats:
        s = cat_spent.get(c, 0)
        b = cat_budget.get(c)
        if b is None:
            colors.append("#4a90d9")   # blue — no category budget
        elif s > b:
            colors.append("#d62728")   # red — over budget
        else:
            colors.append("#2ca02c")   # green — under budget

    fig_bar = go.Figure()

    if has_cat_budget:
        # Budget: wide grey background bar (rendered first, behind)
        budget_x = [v if v is not None else 0 for v in budget_vals]
        fig_bar.add_trace(go.Bar(
            y=all_cats,
            x=budget_x,
            orientation="h",
            name="Budget",
            marker=dict(
                color="rgba(180,180,180,0.45)",
                line=dict(color="rgba(120,120,120,0.8)", width=1.5),
            ),
            width=0.7,
            text=[f"{primary_currency} {v:,.0f}" if v else "" for v in budget_x],
            textposition="outside",
            textfont=dict(color="#888", size=11),
        ))

    # Actual: narrower colored bar on top
    fig_bar.add_trace(go.Bar(
        y=all_cats,
        x=spent_vals,
        orientation="h",
        name="Aktual",
        marker_color=colors,
        width=0.4 if has_cat_budget else 0.7,
        text=[f"{primary_currency} {v:,.0f}" for v in spent_vals],
        textposition="outside",
    ))

    fig_bar.update_layout(
        barmode="overlay",
        xaxis_title=f"Jumlah ({primary_currency})",
        height=max(300, len(all_cats) * 55),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(b=80, r=160),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Progress bars ─────────────────────────────────────────────────────────
    if cat_budget:
        st.subheader("📏 Progress per Kategori")
        for cat in all_cats:
            s = cat_spent.get(cat, 0)
            b = cat_budget.get(cat)
            if b is None:
                continue
            pct = min(s / b, 1.0) if b > 0 else 0
            over = s > b
            label = (
                f"{'⚠️ ' if over else ''}{cat}: "
                f"{primary_currency} {s:,.0f} / {primary_currency} {b:,.0f} ({pct*100:.0f}%)"
            )
            st.progress(pct, text=label)

    # ── Insight ───────────────────────────────────────────────────────────────
    over_cats = [c for c in all_cats if cat_budget.get(c) and cat_spent.get(c, 0) > cat_budget[c]]
    if over_cats:
        st.warning(f"⚠️ {len(over_cats)} kategori melebihi budget bulan ini: {', '.join(over_cats)}")
    elif cat_budget:
        st.success("✅ Semua kategori masih dalam budget bulan ini.")
