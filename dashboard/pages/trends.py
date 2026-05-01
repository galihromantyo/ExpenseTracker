"""Trends page: monthly line chart, stacked bar, and day-of-week × week heatmap."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.data_loader import get_user_expenses

_DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DOW_ID = {"Monday": "Sen", "Tuesday": "Sel", "Wednesday": "Rab",
           "Thursday": "Kam", "Friday": "Jum", "Saturday": "Sab", "Sunday": "Min"}


def _fmt_month(m: str) -> str:
    try:
        return pd.Timestamp(m + "-01").strftime("%b %Y")
    except Exception:
        return m


def render(df_expenses: pd.DataFrame, chat_id: str) -> None:
    st.header("📈 Trend Bulanan")

    exp = get_user_expenses(df_expenses, chat_id)
    if exp.empty:
        st.info("Belum ada data transaksi.")
        return

    primary_currency = exp["currency"].mode()[0]
    same_currency = exp[exp["currency"] == primary_currency].copy()

    months = sorted(same_currency["month"].dropna().unique().tolist())
    if len(months) < 2:
        st.info("Perlu minimal 2 bulan data untuk menampilkan tren.")

    # ── Line chart: total per month ──────────────────────────────────────────
    monthly_total = (
        same_currency.groupby("month")["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total"})
        .sort_values("month")
    )
    monthly_total["month_label"] = monthly_total["month"].apply(_fmt_month)

    fig_line = px.line(
        monthly_total, x="month_label", y="total",
        markers=True,
        title=f"📉 Total Pengeluaran per Bulan ({primary_currency})",
        labels={"month_label": "Bulan", "total": f"Total ({primary_currency})"},
    )
    fig_line.update_traces(line_color="#1f77b4", marker_size=8)
    fig_line.update_xaxes(type="category")
    st.plotly_chart(fig_line, use_container_width=True)

    # ── Stacked bar: per category per month ──────────────────────────────────
    cat_month = (
        same_currency.groupby(["month", "category"])["amount"]
        .sum()
        .reset_index()
    )
    cat_month["month_label"] = cat_month["month"].apply(_fmt_month)

    all_cats = cat_month["category"].unique().tolist()
    selected_cats = st.multiselect(
        "Filter kategori (kosongkan = tampilkan semua)",
        options=all_cats,
        default=[],
    )
    if selected_cats:
        cat_month = cat_month[cat_month["category"].isin(selected_cats)]

    # Preserve chronological month order
    month_order = [_fmt_month(m) for m in sorted(cat_month["month"].unique())]
    fig_stack = px.bar(
        cat_month, x="month_label", y="amount", color="category",
        title="📊 Pengeluaran per Kategori per Bulan",
        labels={"month_label": "Bulan", "amount": f"Jumlah ({primary_currency})", "category": "Kategori"},
        barmode="stack",
        category_orders={"month_label": month_order},
    )
    fig_stack.update_xaxes(type="category")
    st.plotly_chart(fig_stack, use_container_width=True)

    # ── Heatmap: day-of-week × week-range ────────────────────────────────────
    st.subheader("🗓️ Pola Pengeluaran per Hari dalam Seminggu")
    heat_df = same_currency.copy()
    # Compute week start (Monday) and week end (Sunday) for each row
    heat_df["week_start"] = heat_df["date"] - pd.to_timedelta(heat_df["date"].dt.dayofweek, unit="D")
    heat_df["week_label"] = (
        heat_df["week_start"].dt.strftime("%d/%m")
        + " – "
        + (heat_df["week_start"] + pd.Timedelta(days=6)).dt.strftime("%d/%m")
    )

    # Chronological order of weeks
    week_order = (
        heat_df[["week_label", "week_start"]]
        .drop_duplicates()
        .sort_values("week_start")["week_label"]
        .tolist()
    )

    heatmap_data = (
        heat_df.groupby(["week_label", "day_of_week"])["amount"]
        .sum()
        .reset_index()
    )
    heatmap_pivot = heatmap_data.pivot(
        index="day_of_week", columns="week_label", values="amount"
    ).fillna(0)

    # Reorder columns chronologically, rows by day-of-week
    heatmap_pivot = heatmap_pivot.reindex(columns=week_order, fill_value=0)
    ordered_rows = [d for d in _DOW_ORDER if d in heatmap_pivot.index]
    heatmap_pivot = heatmap_pivot.loc[ordered_rows]
    heatmap_pivot.index = [_DOW_ID.get(d, d) for d in heatmap_pivot.index]

    fig_heat = go.Figure(data=go.Heatmap(
        z=heatmap_pivot.values,
        x=heatmap_pivot.columns.tolist(),
        y=heatmap_pivot.index.tolist(),
        colorscale="YlOrRd",
        hoverongaps=False,
        colorbar=dict(title=primary_currency),
    ))
    fig_heat.update_layout(
        title=f"Intensitas Pengeluaran per Hari ({primary_currency})",
        xaxis_title="Minggu",
        yaxis_title="Hari",
        xaxis=dict(type="category"),
        height=350,
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # ── Summary table ────────────────────────────────────────────────────────
    st.subheader("📋 Ringkasan per Bulan")
    monthly_total["trend"] = monthly_total["total"].diff().apply(
        lambda x: "▲" if x and x > 0 else ("▼" if x and x < 0 else "—")
    )
    display_table = monthly_total[["month_label", "total", "trend"]].copy()
    display_table.columns = ["Bulan", f"Total ({primary_currency})", "Trend"]
    st.dataframe(display_table, use_container_width=True, hide_index=True)
