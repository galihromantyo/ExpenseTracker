"""Analisa AI page: quick Q&A and deep financial analysis via Gemini."""
import json
import os

import pandas as pd
import streamlit as st

from dashboard.data_loader import get_user_expenses, get_user_budget


# ── Context builder ───────────────────────────────────────────────────────────

def _build_context(exp: pd.DataFrame, bud: pd.DataFrame, n_months: int = 6) -> str:
    if exp.empty:
        return "{}"

    all_months = sorted(exp["month"].dropna().unique().tolist(), reverse=True)
    recent_months = all_months[:n_months]
    recent_exp = exp[exp["month"].isin(recent_months)].copy()

    monthly_totals = (
        recent_exp.groupby(["month", "currency"])["amount"]
        .sum()
        .reset_index()
        .to_dict(orient="records")
    )

    cat_breakdown = (
        recent_exp.groupby(["month", "category"])["amount"]
        .sum()
        .reset_index()
        .to_dict(orient="records")
    )

    bud_info = bud[bud["month"].isin(recent_months)].to_dict(orient="records")

    recent_tx = recent_exp.sort_values("date", ascending=False).head(100).copy()
    recent_tx["date"] = recent_tx["date"].dt.strftime("%Y-%m-%d")
    tx_list = recent_tx[
        ["date", "description", "amount", "currency", "category", "payment_method"]
    ].to_dict(orient="records")

    return json.dumps(
        {
            "period": f"{', '.join(reversed(recent_months))}",
            "monthly_totals": monthly_totals,
            "category_breakdown": cat_breakdown,
            "budget_settings": bud_info,
            "recent_transactions": tx_list,
        },
        ensure_ascii=False,
        default=str,
    )


# ── Gemini caller (sync) ──────────────────────────────────────────────────────

def _call_gemini(prompt: str, timeout: int = 60) -> str:
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY", "")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        if not api_key:
            return "❌ GEMINI_API_KEY tidak ditemukan di konfigurasi."

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            prompt,
            request_options={"timeout": timeout},
        )
        return response.text
    except Exception as e:
        return f"❌ Gagal memanggil AI: {e}"


# ── Prompts ───────────────────────────────────────────────────────────────────

_QA_PROMPT = """\
Kamu adalah asisten keuangan personal. Kamu memiliki akses ke data pengeluaran dan budget user.

Data keuangan user (JSON):
{context}

Instruksi:
- Jawab pertanyaan user berdasarkan data yang tersedia
- Gunakan bahasa Indonesia yang friendly dan mudah dipahami
- Berikan jawaban yang konkret dengan menyebut angka spesifik dari data
- Jika pertanyaan tidak relevan dengan keuangan, tolak dengan sopan
- Maksimal 5-7 kalimat

Pertanyaan: {question}"""


_DEEP_PROMPT = """\
Kamu adalah konsultan keuangan personal yang berpengalaman. \
Berikan analisa mendalam berdasarkan data pengeluaran user berikut.

Data keuangan user (JSON):
{context}

Tulis analisa komprehensif dalam format Markdown dengan 5 bagian berikut. \
Gunakan bahasa Indonesia, sertakan angka spesifik dari data, dan bersikap jujur:

## 📊 Ringkasan Keuangan
Highlight utama dari kondisi keuangan user saat ini.

## 🏆 Kategori Pengeluaran Terbesar
Tiga kategori teratas, berapa persen dari total, dan apakah wajar.

## ⚖️ Status Budget
Apakah pengeluaran sesuai, kurang, atau melebihi budget? Kategori mana yang perlu perhatian?

## 📈 Tren & Pola
Pola pengeluaran yang terdeteksi — tren naik/turun, pola waktu, atau kebiasaan belanja.

## ✅ Rekomendasi Konkret
Minimal 3 langkah spesifik dan actionable yang bisa langsung dilakukan user \
untuk mengoptimalkan keuangan mereka."""


# ── Page render ───────────────────────────────────────────────────────────────

def render(df_expenses: pd.DataFrame, df_budget: pd.DataFrame, chat_id: str) -> None:
    st.header("🤖 Analisa AI")

    exp = get_user_expenses(df_expenses, chat_id)
    bud = get_user_budget(df_budget, chat_id)

    if exp.empty:
        st.info("Belum ada data transaksi. Catat pengeluaran melalui Telegram bot terlebih dahulu.")
        return

    context = _build_context(exp, bud)

    # ── 1. Tanya AI ───────────────────────────────────────────────────────────
    st.subheader("💬 Tanya AI")
    st.caption(
        "Tanyakan apapun tentang data keuangan kamu — kategori terboros, "
        "perbandingan bulan, status budget, dll."
    )

    with st.form("qa_form", clear_on_submit=False):
        question = st.text_input(
            "Pertanyaan",
            placeholder='Contoh: "Bulan lalu paling boros di mana?" '
                        'atau "Apakah saya on-track dengan budget transport?"',
            label_visibility="collapsed",
        )
        ask_btn = st.form_submit_button("🔍 Tanya", use_container_width=True)

    if ask_btn:
        if not question.strip():
            st.warning("Masukkan pertanyaan terlebih dahulu.")
        else:
            with st.spinner("🤔 Sedang menganalisis data kamu..."):
                prompt = _QA_PROMPT.format(context=context, question=question.strip())
                answer = _call_gemini(prompt, timeout=45)
            st.info(answer)

    st.divider()

    # ── 2. Analisa Mendalam ───────────────────────────────────────────────────
    st.subheader("🔬 Analisa Mendalam")
    st.caption(
        "AI akan menganalisis pola pengeluaran, status budget, tren jangka panjang, "
        "dan memberikan rekomendasi konkret untuk 6 bulan terakhir."
    )

    col_run, col_reset = st.columns([3, 1])
    with col_run:
        run_deep = st.button(
            "🚀 Mulai Analisa Mendalam",
            use_container_width=True,
            type="primary",
        )
    with col_reset:
        if st.button("🗑️ Reset", use_container_width=True):
            st.session_state.pop("deep_analysis_result", None)
            st.session_state.pop("deep_analysis_chat_id", None)
            st.rerun()

    if run_deep:
        with st.spinner("🧠 AI sedang menganalisis data kamu secara mendalam... (bisa 30–60 detik)"):
            prompt = _DEEP_PROMPT.format(context=context)
            result = _call_gemini(prompt, timeout=90)
        st.session_state["deep_analysis_result"] = result
        st.session_state["deep_analysis_chat_id"] = chat_id

    if (
        "deep_analysis_result" in st.session_state
        and st.session_state.get("deep_analysis_chat_id") == chat_id
    ):
        st.divider()
        with st.container(border=True):
            st.markdown(st.session_state["deep_analysis_result"])

        col_dl, _ = st.columns([1, 3])
        with col_dl:
            st.download_button(
                label="⬇️ Download Analisa (.txt)",
                data=st.session_state["deep_analysis_result"],
                file_name="fintrack_analisa_mendalam.txt",
                mime="text/plain",
            )
