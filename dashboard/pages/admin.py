"""Admin page: aggregate view across all users (superuser only)."""
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.data_loader import load_users


def render(df_expenses: pd.DataFrame, df_budget: pd.DataFrame) -> None:
    st.header("👑 Admin — Semua User")

    users_df = load_users()

    # ── User selector ─────────────────────────────────────────────────────────
    if not users_df.empty:
        user_options = {
            f"{row['display_name']} (@{row['username']})": str(row["chat_id"])
            for _, row in users_df.iterrows()
        }
        user_options["📊 Semua User (Agregat)"] = "__all__"
        selected_label = st.selectbox("👤 Pilih User", list(user_options.keys()),
                                      index=len(user_options) - 1)
        selected_cid = user_options[selected_label]
    else:
        st.warning("Belum ada user terdaftar.")
        return

    if selected_cid == "__all__":
        view_exp = df_expenses.copy()
    else:
        view_exp = df_expenses[df_expenses["chat_id"] == selected_cid].copy()

    if view_exp.empty:
        st.info("Tidak ada data untuk ditampilkan.")
        return

    # ── Aggregate KPIs ────────────────────────────────────────────────────────
    st.subheader("📊 Statistik Keseluruhan")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Transaksi", len(view_exp))
    with col2:
        active_users = view_exp["chat_id"].nunique()
        st.metric("User Aktif", active_users)
    with col3:
        if not users_df.empty:
            st.metric("Total User Terdaftar", len(users_df))

    # ── Spending by user ──────────────────────────────────────────────────────
    if selected_cid == "__all__" and not users_df.empty:
        st.subheader("💸 Pengeluaran per User")
        user_map = dict(zip(users_df["chat_id"].astype(str), users_df["display_name"]))
        by_user = (
            view_exp.groupby("chat_id")["amount"]
            .sum()
            .reset_index()
        )
        by_user["name"] = by_user["chat_id"].map(user_map).fillna(by_user["chat_id"])
        by_user = by_user.sort_values("amount", ascending=False)
        fig = px.bar(by_user, x="name", y="amount", title="Total Pengeluaran per User",
                     labels={"name": "User", "amount": "Total"}, color="amount",
                     color_continuous_scale="Blues")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── Monthly trend all users ───────────────────────────────────────────────
    st.subheader("📈 Tren Pengeluaran")
    monthly = (
        view_exp.groupby("month")["amount"]
        .sum()
        .reset_index()
        .sort_values("month")
    )
    import pandas as pd
    monthly["month_label"] = monthly["month"].apply(
        lambda m: pd.Timestamp(m + "-01").strftime("%b %Y") if m else m
    )
    fig_line = px.line(monthly, x="month_label", y="amount", markers=True,
                       title="Total Pengeluaran per Bulan",
                       labels={"month_label": "Bulan", "amount": "Total"})
    fig_line.update_xaxes(type="category")
    st.plotly_chart(fig_line, use_container_width=True)

    # ── User management table ────────────────────────────────────────────────
    st.subheader("👥 Daftar User Terdaftar")
    display_cols = ["chat_id", "username", "display_name", "default_currency", "joined_at", "is_active"]
    available = [c for c in display_cols if c in users_df.columns]
    st.dataframe(users_df[available], use_container_width=True, hide_index=True)

    # ── Health metrics ────────────────────────────────────────────────────────
    st.subheader("🩺 Health Metrics")
    st.markdown(f"""
    - Total baris di Expenses: **{len(df_expenses)}**
    - Total baris di Budget: **{len(df_budget)}**
    - User aktif bulan ini: **{view_exp[view_exp['month'] == view_exp['month'].max()]['chat_id'].nunique() if not view_exp.empty else 0}**
    """)
