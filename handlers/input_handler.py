import io

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from agents import extraction_agent, normalize_agent, sheets_agent, user_agent
from utils.currency import detect_currency
from utils.date_parser import parse_report_month, format_month_display, month_to_str
from utils.formatter import format_expense_confirmation
from utils.state import (
    get_state, set_state, clear_state, update_data,
    FLOW_INPUT, FLOW_REPORT, FLOW_BUDGET, FLOW_EDIT,
    STEP_CONFIRMING, STEP_EDITING_VALUE, STEP_ENTER_VALUE,
    STEP_ASK_MONTH, STEP_ASK_BUDGET_TOTAL, STEP_ASK_BUDGET_CATEGORY,
    STEP_ASK_EXPORT_RANGE,
)
from config import config
from utils.constants import CATEGORIES


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Simpan", callback_data="expense:confirm"),
        InlineKeyboardButton("✏️ Edit", callback_data="expense:edit_menu"),
        InlineKeyboardButton("❌ Batal", callback_data="expense:cancel"),
    ]])


async def _process_input(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          text: str | None = None,
                          image_bytes: bytes | None = None,
                          image_mime: str = "image/jpeg",
                          audio_bytes: bytes | None = None,
                          audio_mime: str = "audio/ogg",
                          input_type: str = "text") -> None:
    chat_id = update.effective_user.id
    user_currency = await user_agent.get_user_currency(chat_id)

    await update.message.reply_text("⏳ Sedang memproses input kamu...")

    try:
        if image_bytes:
            raw = await extraction_agent.extract_from_image(image_bytes, image_mime)
        elif audio_bytes:
            raw = await extraction_agent.extract_from_audio(audio_bytes, audio_mime)
        else:
            raw = await extraction_agent.extract_from_text(text or "")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal memproses dengan AI: {e}\n\nCoba lagi atau ketik manual.")
        return

    if not raw or raw.get("amount") is None:
        await update.message.reply_text(
            "⚠️ Tidak berhasil mengekstrak data transaksi.\n\n"
            "Coba format yang lebih jelas, contoh:\n"
            "_Makan siang Rp 35.000 GoPay_",
            parse_mode="Markdown",
        )
        return

    if raw.get("currency") is None:
        if text:
            detected = detect_currency(text)
            raw["currency"] = detected or user_currency
        else:
            raw["currency"] = user_currency

    expense = normalize_agent.normalize_expense(raw, user_currency)
    expense["input_type"] = input_type

    set_state(context.user_data, FLOW_INPUT, STEP_CONFIRMING, {"expense": expense})

    await update.message.reply_text(
        format_expense_confirmation(expense),
        parse_mode="Markdown",
        reply_markup=_confirm_keyboard(),
    )


# ── Main dispatcher ──────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    flow, step, data = get_state(context.user_data)
    msg = update.message
    chat_id = update.effective_user.id

    if flow == FLOW_INPUT and step == STEP_EDITING_VALUE:
        field = data.get("edit_field")
        expense = data.get("expense", {})
        new_val = msg.text.strip() if msg.text else ""
        if field and new_val:
            if field == "amount":
                from utils.currency import normalize_amount
                val = normalize_amount(new_val)
                expense[field] = val if val is not None else expense.get(field)
            elif field == "currency":
                expense[field] = new_val.upper() if new_val.upper() in ("IDR", "USD", "EUR", "GBP") else expense[field]
            elif field == "category":
                from agents.normalize_agent import normalize_category
                expense[field] = normalize_category(new_val)
            elif field == "payment_method":
                from agents.normalize_agent import normalize_payment_method
                expense[field] = normalize_payment_method(new_val)
            else:
                expense[field] = new_val
            update_data(context.user_data, expense=expense, edit_field=None)
            set_state(context.user_data, FLOW_INPUT, STEP_CONFIRMING, {**data, "expense": expense, "edit_field": None})
        await msg.reply_text(
            format_expense_confirmation(expense),
            parse_mode="Markdown",
            reply_markup=_confirm_keyboard(),
        )
        return

    if flow == FLOW_REPORT and step == STEP_ASK_MONTH:
        if not msg.text:
            return
        parsed = parse_report_month(msg.text)
        if not parsed:
            await msg.reply_text("⚠️ Format tidak dikenali. Contoh: _April 2026_ atau _2026-04_", parse_mode="Markdown")
            return
        year, month = parsed
        month_str = month_to_str(year, month)
        month_display = format_month_display(year, month)
        from handlers.callback_handler import _run_report_for_month
        await _run_report_for_month(update, context, month_str, month_display)
        return

    if flow == FLOW_BUDGET and step == STEP_ASK_MONTH:
        if not msg.text:
            return
        parsed = parse_report_month(msg.text)
        if not parsed:
            await msg.reply_text("⚠️ Format tidak dikenali. Contoh: _April 2026_ atau _2026-04_", parse_mode="Markdown")
            return
        year, month = parsed
        month_str = month_to_str(year, month)
        month_display = format_month_display(year, month)
        from handlers.callback_handler import _start_budget_type_step
        await _start_budget_type_step(update, context, month_str, month_display)
        return

    if flow == FLOW_BUDGET and step == STEP_ASK_BUDGET_TOTAL:
        if not msg.text:
            return
        from utils.currency import normalize_amount
        amount = normalize_amount(msg.text)
        if amount is None or amount <= 0:
            await msg.reply_text("⚠️ Nominal tidak valid. Masukkan angka, contoh: _5jt_ atau _5000000_", parse_mode="Markdown")
            return
        month_str = data.get("month", "")
        month_display = data.get("month_display", "")
        currency = data.get("currency", await user_agent.get_user_currency(chat_id))
        entries = [{"currency": currency, "budget_type": "total", "category": "", "amount": amount}]
        await sheets_agent.set_budget(chat_id, month_str, entries)
        clear_state(context.user_data)
        from utils.currency import format_amount
        await msg.reply_text(
            f"✅ Budget *{month_display}* berhasil diset: *{format_amount(amount, currency)}*\n\n"
            f"Gunakan /laporan untuk melihat laporan.",
            parse_mode="Markdown",
        )
        return

    if flow == FLOW_BUDGET and step == STEP_ASK_BUDGET_CATEGORY:
        if not msg.text:
            return
        from utils.currency import normalize_amount
        amount = normalize_amount(msg.text)
        category_queue: list[str] = data.get("category_queue", [])
        budget_data: list[dict] = data.get("budget_data", [])
        currency = data.get("currency", await user_agent.get_user_currency(chat_id))
        current_cat = data.get("current_category", "")

        if amount is None:
            await msg.reply_text("⚠️ Nominal tidak valid. Masukkan angka atau _0_ untuk skip.", parse_mode="Markdown")
            return

        if amount > 0:
            budget_data.append({
                "currency": currency,
                "budget_type": "per_category",
                "category": current_cat,
                "amount": amount,
            })
        update_data(context.user_data, budget_data=budget_data)

        if category_queue:
            next_cat = category_queue[0]
            remaining = category_queue[1:]
            update_data(context.user_data, category_queue=remaining, current_category=next_cat)
            from utils.currency import format_amount
            await msg.reply_text(
                f"💰 Budget untuk *{next_cat}*?\n_(ketik 0 untuk skip)_",
                parse_mode="Markdown",
            )
        else:
            month_str = data.get("month", "")
            month_display = data.get("month_display", "")
            if budget_data:
                await sheets_agent.set_budget(chat_id, month_str, budget_data)
                total = sum(e["amount"] for e in budget_data)
                from utils.currency import format_amount
                lines = [f"✅ Budget *{month_display}* per kategori berhasil disimpan!\n"]
                for e in budget_data:
                    from utils.constants import CATEGORY_EMOJI
                    emoji = CATEGORY_EMOJI.get(e["category"], "📦")
                    lines.append(f"{emoji} {e['category']}: {format_amount(e['amount'], currency)}")
                lines.append(f"\n💰 Total budget: {format_amount(total, currency)}")
                lines.append("\nGunakan /laporan untuk melihat laporan.")
                await msg.reply_text("\n".join(lines), parse_mode="Markdown")
            else:
                await msg.reply_text("ℹ️ Tidak ada budget yang disimpan (semua di-skip).")
            clear_state(context.user_data)
        return

    if flow == FLOW_EDIT and step == STEP_ENTER_VALUE:
        if not msg.text:
            return
        from handlers.callback_handler import _apply_edit_value
        await _apply_edit_value(update, context, msg.text.strip())
        return

    from utils.state import FLOW_EXPORT
    if flow == FLOW_EXPORT and step == STEP_ASK_EXPORT_RANGE:
        if not msg.text:
            return
        tokens = msg.text.split()
        start_month = end_month = None
        for split in range(1, len(tokens)):
            p1 = parse_report_month(" ".join(tokens[:split]))
            p2 = parse_report_month(" ".join(tokens[split:]))
            if p1 and p2:
                start_month = month_to_str(*p1)
                end_month = month_to_str(*p2)
                break
        if not start_month:
            p = parse_report_month(msg.text)
            if p:
                start_month = end_month = month_to_str(*p)
        if not start_month:
            await msg.reply_text("⚠️ Format tidak dikenali. Contoh: _April 2026_ atau _Jan 2026 Apr 2026_", parse_mode="Markdown")
            return
        from handlers.command_handler import _do_export
        await _do_export(update, context, start_month, end_month)
        return

    if flow is not None and flow != FLOW_INPUT:
        await msg.reply_text(
            "⚠️ Kamu sedang dalam alur lain. Selesaikan dulu atau ketik /start untuk membatalkan."
        )
        return

    if msg.photo:
        photo = msg.photo[-1]
        f = await photo.get_file()
        image_bytes = bytes(await f.download_as_bytearray())
        await _process_input(update, context, image_bytes=image_bytes, input_type="photo")

    elif msg.document and msg.document.mime_type == "application/pdf":
        f = await msg.document.get_file()
        pdf_bytes = bytes(await f.download_as_bytearray())
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception as e:
            await msg.reply_text(f"❌ Gagal membaca PDF: {e}")
            return
        await _process_input(update, context, text=text, input_type="pdf")

    elif msg.voice:
        f = await msg.voice.get_file()
        audio_bytes = bytes(await f.download_as_bytearray())
        await _process_input(update, context, audio_bytes=audio_bytes,
                              audio_mime=msg.voice.mime_type or "audio/ogg", input_type="voice")

    elif msg.audio:
        f = await msg.audio.get_file()
        audio_bytes = bytes(await f.download_as_bytearray())
        await _process_input(update, context, audio_bytes=audio_bytes,
                              audio_mime=msg.audio.mime_type or "audio/mpeg", input_type="audio")

    elif msg.text:
        await _process_input(update, context, text=msg.text, input_type="text")
