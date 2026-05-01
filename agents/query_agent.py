import asyncio
import json
from datetime import date, timedelta

import google.generativeai as genai

from agents import sheets_agent
from config import config

_GEMINI_TIMEOUT = 45
_MAX_ROWS = 500
_MAX_MONTHS = 6


def _build_context(expenses: list[dict], budget_entries: list[dict]) -> str:
    """Serialize data to a compact JSON string for Gemini context."""
    trimmed = expenses[-_MAX_ROWS:]
    return json.dumps({
        "expenses": trimmed,
        "budget": budget_entries,
    }, ensure_ascii=False, default=str)


def _date_range_for_query(n_months: int = _MAX_MONTHS) -> tuple[str, str]:
    today = date.today()
    end = today.strftime("%Y-%m")
    start_date = today.replace(day=1)
    for _ in range(n_months - 1):
        start_date = (start_date - timedelta(days=1)).replace(day=1)
    return start_date.strftime("%Y-%m"), end


async def answer(chat_id: int, question: str) -> str:
    """
    Fetch up to _MAX_MONTHS months of expenses + current budget,
    send to Gemini as context, return natural-language answer.
    """
    start_month, end_month = _date_range_for_query()
    current_month = date.today().strftime("%Y-%m")

    try:
        expenses, budget_entries = await asyncio.gather(
            sheets_agent.get_expenses_range(chat_id, start_month, end_month),
            sheets_agent.get_budget(chat_id, current_month),
        )
    except Exception as e:
        return f"❌ Gagal mengambil data: {e}"

    if not expenses:
        return (
            "📭 Belum ada data transaksi yang bisa dianalisis.\n"
            "Coba catat beberapa pengeluaran dulu, lalu tanya lagi."
        )

    context = _build_context(expenses, budget_entries)

    prompt = (
        "Kamu adalah asisten keuangan pribadi yang membantu menganalisis data pengeluaran.\n"
        "Jawab pertanyaan pengguna berdasarkan data JSON di bawah ini.\n"
        "Gunakan bahasa Indonesia yang ramah dan ringkas (maksimal 5 kalimat).\n"
        "Jangan buat-buat data yang tidak ada di JSON.\n"
        "Jika pertanyaan tidak relevan dengan data keuangan, tolak dengan sopan.\n\n"
        f"Data transaksi (rentang {start_month} s/d {end_month}):\n"
        f"```json\n{context}\n```\n\n"
        f"Pertanyaan pengguna: {question}"
    )

    genai.configure(api_key=config.gemini_api_key)
    model = genai.GenerativeModel(config.gemini_model)

    try:
        response = await asyncio.wait_for(
            model.generate_content_async(prompt),
            timeout=_GEMINI_TIMEOUT,
        )
        return response.text.strip()
    except asyncio.TimeoutError:
        return "⏱️ Waktu habis saat memproses pertanyaan. Coba lagi."
    except Exception as e:
        return f"❌ Gagal memproses pertanyaan: {e}"
