from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from agents import sheets_agent, currency_agent, report_agent, chart_agent
from utils.date_parser import format_month_display, month_to_str
from utils.formatter import format_expense_confirmation
from utils.currency import format_amount
from utils.state import (
    get_state, set_state, clear_state, update_data,
    FLOW_INPUT, FLOW_REPORT, FLOW_BUDGET, FLOW_EDIT, FLOW_DELETE,
    STEP_CONFIRMING, STEP_EDITING_VALUE, STEP_ENTER_VALUE,
    STEP_ASK_BUDGET_TYPE, STEP_ASK_BUDGET_TOTAL, STEP_ASK_BUDGET_CATEGORY,
    STEP_ASK_CURRENCY_CHOICE, STEP_ASK_CHART, STEP_SELECT_EXPENSE,
    STEP_SELECT_FIELD, STEP_CONFIRM_DELETE, STEP_ASK_MONTH,
)
from utils.constants import CATEGORIES, CATEGORY_EMOJI, SUPPORTED_CURRENCIES
from config import config


# ── Shared helpers ───────────────────────────────────────────────────────────

async def _run_report_for_month(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    month_str: str,
    month_display: str,
) -> None:
    """Fetch expenses + budget for month, then decide next step."""
    msg = update.message or update.callback_query.message

    await msg.reply_text(f"⏳ Mengambil data {month_display}...")

    try:
        expenses = await sheets_agent.get_expenses_for_month(month_str)
        budget_entries = await sheets_agent.get_budget(month_str)
    except Exception as e:
        await msg.reply_text(f"❌ Gagal membaca Google Sheets: {e}")
        clear_state(context.user_data)
        return

    if not expenses:
        await msg.reply_text(f"📭 Tidak ada transaksi di {month_display}.")
        clear_state(context.user_data)
        return

    rd = report_agent.build_report_data(expenses, budget_entries)

    set_state(context.user_data, FLOW_REPORT, None, {
        "month": month_str,
        "month_display": month_display,
        "expenses": expenses,
        "budget_entries": budget_entries,
        "report_data": rd,
    })

    if rd["is_multi_currency"]:
        currencies_str = " & ".join(rd["currencies"])
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🔄 Konversi ke {config.default_currency}",
                                  callback_data="report:currency:convert")],
            [InlineKeyboardButton(f"📋 Pisah per mata uang ({currencies_str})",
                                  callback_data="report:currency:separate")],
        ])
        set_state(context.user_data, FLOW_REPORT, STEP_ASK_CURRENCY_CHOICE,
                  context.user_data.get("data", {}))
        await msg.reply_text(
            f"💱 Ada pengeluaran dalam beberapa mata uang: *{currencies_str}*\nTampilkan bagaimana?",
            parse_mode="Markdown",
            reply_markup=kb,
        )
    else:
        # Single currency — generate report directly
        display_currency = rd["currencies"][0] if rd["currencies"] else config.default_currency
        await _generate_and_send_report(update, context, display_currency, convert=False)


async def _generate_and_send_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    display_currency: str,
    convert: bool,
    separate: bool = False,
) -> None:
    _, _, data = get_state(context.user_data)
    msg = update.message or update.callback_query.message
    expenses = data.get("expenses", [])
    rd = data.get("report_data", {})
    month_display = data.get("month_display", "")
    rate_info: dict = {}

    if separate:
        text = report_agent.generate_report_text_multi(rd, month_display)
        converted_expenses = expenses
    else:
        if convert:
            try:
                converted_expenses, rate_info = await currency_agent.convert_expenses(expenses, display_currency)
            except Exception as e:
                await msg.reply_text(f"⚠️ Gagal mengambil kurs: {e}\nMenampilkan tanpa konversi.")
                separate = True
                text = report_agent.generate_report_text_multi(rd, month_display)
                converted_expenses = expenses
            else:
                text = report_agent.generate_report_text_single(
                    rd, month_display, display_currency, converted_expenses, rate_info
                )
        else:
            converted_expenses = expenses
            text = report_agent.generate_report_text_single(
                rd, month_display, display_currency, converted_expenses, rate_info
            )

    # Store for chart generation
    update_data(context.user_data,
                converted_expenses=converted_expenses,
                display_currency=display_currency,
                separate=separate)

    await msg.reply_text(text, parse_mode="Markdown")

    # Ask about chart
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Bar chart", callback_data="report:chart:bar"),
        InlineKeyboardButton("🥧 Pie chart", callback_data="report:chart:pie"),
        InlineKeyboardButton("⏭️ Tidak perlu", callback_data="report:chart:no"),
    ]])
    set_state(context.user_data, FLOW_REPORT, STEP_ASK_CHART, context.user_data.get("data", {}))
    await msg.reply_text("Mau lihat chart pengeluaran?", reply_markup=kb)


def _format_existing_budget(entries: list[dict], month_display: str) -> str:
    lines = [f"💰 Budget *{month_display}* sudah ada:\n"]
    for e in entries:
        btype = e.get("budget_type", "total")
        amount = float(e.get("amount", 0))
        currency = e.get("currency", "IDR")
        if btype == "total":
            lines.append(f"📦 Total: {format_amount(amount, currency)}")
        else:
            cat = e.get("category", "-")
            emoji = CATEGORY_EMOJI.get(cat, "📦")
            lines.append(f"{emoji} {cat}: {format_amount(amount, currency)}")
    lines.append("\nMau diapakan?")
    return "\n".join(lines)


async def _start_budget_type_step(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    month_str: str,
    month_display: str,
) -> None:
    msg = update.message or update.callback_query.message

    try:
        existing = await sheets_agent.get_budget(month_str)
    except Exception as e:
        await msg.reply_text(f"❌ Gagal membaca Google Sheets: {e}")
        clear_state(context.user_data)
        return

    set_state(context.user_data, FLOW_BUDGET, STEP_ASK_BUDGET_TYPE, {
        "month": month_str,
        "month_display": month_display,
    })

    if existing:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Tetap", callback_data="budget:manage:keep")],
            [InlineKeyboardButton("✏️ Ganti", callback_data="budget:manage:replace")],
            [InlineKeyboardButton("🗑️ Hapus", callback_data="budget:manage:delete")],
            [InlineKeyboardButton("❌ Batal", callback_data="budget:cancel")],
        ])
        await msg.reply_text(
            _format_existing_budget(existing, month_display),
            parse_mode="Markdown",
            reply_markup=kb,
        )
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Total saja", callback_data="budget:type:total")],
            [InlineKeyboardButton("📂 Per kategori", callback_data="budget:type:per_category")],
            [InlineKeyboardButton("❌ Batal", callback_data="budget:cancel")],
        ])
        await msg.reply_text(
            f"💰 Set budget *{month_display}*\n\nPilih jenis budget:",
            parse_mode="Markdown",
            reply_markup=kb,
        )


# ── Main callback dispatcher ─────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data_str = query.data or ""

    # ── Expense confirmation ──────────────────────────────────────────────────
    if data_str == "expense:confirm":
        await _cb_expense_confirm(update, context)

    elif data_str == "expense:cancel":
        clear_state(context.user_data)
        await query.edit_message_text("❌ Input dibatalkan.")

    elif data_str == "expense:edit_menu":
        await _cb_expense_edit_menu(update, context)

    elif data_str.startswith("expense:field:"):
        field = data_str.split(":", 2)[2]
        await _cb_expense_edit_field(update, context, field)

    # ── Report flow ───────────────────────────────────────────────────────────
    elif data_str.startswith("report:month:"):
        await _cb_report_month(update, context, data_str)

    elif data_str == "report:currency:convert":
        await query.edit_message_text("⏳ Mengambil kurs...")
        _, _, d = get_state(context.user_data)
        await _generate_and_send_report(update, context, config.default_currency, convert=True)

    elif data_str == "report:currency:separate":
        await query.edit_message_text("⏳ Menyusun laporan...")
        _, _, d = get_state(context.user_data)
        await _generate_and_send_report(update, context, config.default_currency, convert=False, separate=True)

    elif data_str.startswith("report:chart:"):
        chart_choice = data_str.split(":", 2)[2]
        await _cb_report_chart(update, context, chart_choice)

    # ── Budget flow ───────────────────────────────────────────────────────────
    elif data_str.startswith("budget:month:"):
        await _cb_budget_month(update, context, data_str)

    elif data_str == "budget:type:total":
        await _cb_budget_type_total(update, context)

    elif data_str == "budget:type:per_category":
        await _cb_budget_type_per_category(update, context)

    elif data_str.startswith("budget:cat:"):
        category = data_str.split(":", 2)[2]
        await _cb_budget_cat_select(update, context, category)

    elif data_str == "budget:done":
        await _cb_budget_done(update, context)

    elif data_str == "budget:manage:keep":
        clear_state(context.user_data)
        await query.edit_message_text("✅ Budget tidak diubah.")

    elif data_str == "budget:manage:replace":
        _, _, data = get_state(context.user_data)
        month_display = data.get("month_display", "")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Total saja", callback_data="budget:type:total")],
            [InlineKeyboardButton("📂 Per kategori", callback_data="budget:type:per_category")],
            [InlineKeyboardButton("❌ Batal", callback_data="budget:cancel")],
        ])
        await query.edit_message_text(
            f"💰 Set budget baru untuk *{month_display}*\n\nPilih jenis budget:",
            parse_mode="Markdown",
            reply_markup=kb,
        )

    elif data_str == "budget:manage:delete":
        await _cb_budget_manage_delete(update, context)

    elif data_str == "budget:cancel":
        clear_state(context.user_data)
        await query.edit_message_text("❌ Pengaturan budget dibatalkan.")

    # ── Edit flow ─────────────────────────────────────────────────────────────
    elif data_str.startswith("edit:select:"):
        row_num = int(data_str.split(":", 2)[2])
        await _cb_edit_select(update, context, row_num)

    elif data_str.startswith("edit:field:"):
        field = data_str.split(":", 2)[2]
        await _cb_edit_field(update, context, field)

    elif data_str == "edit:cancel":
        clear_state(context.user_data)
        await query.edit_message_text("❌ Edit dibatalkan.")

    # ── Delete flow ───────────────────────────────────────────────────────────
    elif data_str.startswith("delete:select:"):
        row_num = int(data_str.split(":", 2)[2])
        await _cb_delete_select(update, context, row_num)

    elif data_str.startswith("delete:confirm:"):
        row_num = int(data_str.split(":", 2)[2])
        await _cb_delete_confirm(update, context, row_num)

    elif data_str == "delete:cancel":
        clear_state(context.user_data)
        await query.edit_message_text("❌ Penghapusan dibatalkan.")

    # ── Export flow ───────────────────────────────────────────────────────────
    elif data_str.startswith("export:range:"):
        await _cb_export_range(update, context, data_str)

    # ── Set currency ──────────────────────────────────────────────────────────
    elif data_str.startswith("currency:set:"):
        code = data_str.split(":", 2)[2]
        config.default_currency = code
        await query.edit_message_text(f"✅ Mata uang default diubah ke *{code}*.", parse_mode="Markdown")


# ── Expense confirm ──────────────────────────────────────────────────────────

async def _cb_expense_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, _, data = get_state(context.user_data)
    expense = data.get("expense")
    if not expense:
        await query.edit_message_text("⚠️ Data transaksi tidak ditemukan. Coba input ulang.")
        return
    try:
        await sheets_agent.append_expense(expense)
    except Exception as e:
        await query.edit_message_text(f"❌ Gagal menyimpan ke Google Sheets: {e}")
        return
    clear_state(context.user_data)
    amount_str = format_amount(expense["amount"], expense["currency"])
    await query.edit_message_text(f"✅ *{amount_str}* berhasil dicatat!", parse_mode="Markdown")


async def _cb_expense_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    fields = [
        ("📅 Tanggal", "date"), ("💰 Nominal", "amount"), ("💱 Mata Uang", "currency"),
        ("🏷️ Kategori", "category"), ("💳 Metode Bayar", "payment_method"), ("📝 Deskripsi", "description"),
    ]
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"expense:field:{key}")] for label, key in fields]
        + [[InlineKeyboardButton("↩️ Kembali", callback_data="expense:back")]]
    )
    await query.edit_message_text("✏️ Field mana yang ingin diedit?", reply_markup=kb)


async def _cb_expense_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str) -> None:
    query = update.callback_query
    _, _, data = get_state(context.user_data)
    expense = data.get("expense", {})
    update_data(context.user_data, edit_field=field)
    set_state(context.user_data, FLOW_INPUT, STEP_EDITING_VALUE, {**data, "edit_field": field})

    hints = {
        "date": "Masukkan tanggal baru (contoh: `28 April 2026` atau `2026-04-28`)",
        "amount": "Masukkan nominal baru (contoh: `35k` atau `35000`)",
        "currency": "Masukkan kode mata uang: `IDR`, `USD`, `EUR`, atau `GBP`",
        "category": f"Masukkan kategori baru:\n{', '.join(CATEGORIES)}",
        "payment_method": "Masukkan metode bayar (contoh: `GoPay`, `Revolut`, `Cash`)",
        "description": "Masukkan deskripsi baru",
    }
    await query.edit_message_text(hints.get(field, f"Masukkan nilai baru untuk {field}:"), parse_mode="Markdown")


# ── Report month ─────────────────────────────────────────────────────────────

async def _cb_report_month(update: Update, context: ContextTypes.DEFAULT_TYPE, data_str: str) -> None:
    query = update.callback_query
    month_val = data_str.split(":", 2)[2]
    if month_val == "custom":
        set_state(context.user_data, FLOW_REPORT, STEP_ASK_MONTH, {})
        await query.edit_message_text(
            "✏️ Masukkan bulan laporan (contoh: _April 2026_ atau _2026-04_):",
            parse_mode="Markdown",
        )
        return
    from utils.date_parser import format_month_display as fmd
    year, month = int(month_val[:4]), int(month_val[5:7])
    await query.edit_message_text(f"⏳ Memuat laporan {fmd(year, month)}...")
    await _run_report_for_month(update, context, month_val, fmd(year, month))


async def _cb_report_chart(update: Update, context: ContextTypes.DEFAULT_TYPE, chart_type: str) -> None:
    query = update.callback_query
    if chart_type == "no":
        await query.edit_message_text("✅ Laporan selesai.")
        clear_state(context.user_data)
        return

    _, _, data = get_state(context.user_data)
    converted_expenses = data.get("converted_expenses", data.get("expenses", []))
    display_currency = data.get("display_currency", config.default_currency)
    month_display = data.get("month_display", "")
    separate = data.get("separate", False)

    await query.edit_message_text("⏳ Membuat chart...")

    if separate:
        # Build chart from all expenses regardless of currency — group by category
        by_cat: dict[str, float] = {}
        for exp in converted_expenses:
            cat = exp.get("category", "Other")
            by_cat[cat] = by_cat.get(cat, 0.0) + float(exp.get("amount", 0))
        chart_currency = "mixed"
    else:
        by_cat = report_agent.build_chart_data(converted_expenses, display_currency)
        chart_currency = display_currency

    buf = chart_agent.generate_chart(by_cat, chart_currency, month_display, chart_type)
    clear_state(context.user_data)
    await query.message.reply_photo(photo=buf, caption=f"📊 Pengeluaran {month_display}")


# ── Budget month ──────────────────────────────────────────────────────────────

async def _cb_budget_month(update: Update, context: ContextTypes.DEFAULT_TYPE, data_str: str) -> None:
    query = update.callback_query
    month_val = data_str.split(":", 2)[2]
    if month_val == "custom":
        set_state(context.user_data, FLOW_BUDGET, STEP_ASK_MONTH, {})
        await query.edit_message_text(
            "✏️ Masukkan bulan (contoh: _April 2026_ atau _2026-04_):",
            parse_mode="Markdown",
        )
        return
    year, month = int(month_val[:4]), int(month_val[5:7])
    from utils.date_parser import format_month_display as fmd
    await query.edit_message_text(f"⏳ Mempersiapkan budget {fmd(year, month)}...")
    await _start_budget_type_step(update, context, month_val, fmd(year, month))


async def _cb_budget_type_total(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, _, data = get_state(context.user_data)
    month_str = data.get("month", "")
    month_display = data.get("month_display", "")

    # Ask for currency
    cur = config.default_currency
    set_state(context.user_data, FLOW_BUDGET, STEP_ASK_BUDGET_TOTAL, {
        **data,
        "currency": cur,
    })
    await query.edit_message_text(
        f"💰 Budget total untuk *{month_display}* \\({cur}\\)?\n"
        "_Ketik nominalnya, contoh: `5jt` atau `5000000`_",
        parse_mode="MarkdownV2",
    )


async def _cb_budget_type_per_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, _, data = get_state(context.user_data)
    month_str = data.get("month", "")

    # Get categories with existing transactions OR show all
    try:
        existing_expenses = await sheets_agent.get_expenses_for_month(month_str)
        active_cats = list({e.get("category", "Other") for e in existing_expenses})
    except Exception:
        active_cats = []

    # Show all 15 categories + existing ones
    all_cats = list(dict.fromkeys(active_cats + CATEGORIES))

    buttons = []
    for cat in all_cats:
        emoji = CATEGORY_EMOJI.get(cat, "📦")
        buttons.append([InlineKeyboardButton(f"{emoji} {cat}", callback_data=f"budget:cat:{cat}")])
    buttons.append([InlineKeyboardButton("✅ Selesai (simpan yang sudah diisi)", callback_data="budget:done")])
    buttons.append([InlineKeyboardButton("❌ Batal", callback_data="budget:cancel")])

    set_state(context.user_data, FLOW_BUDGET, STEP_ASK_BUDGET_CATEGORY, {
        **data,
        "budget_data": [],
        "currency": config.default_currency,
        "all_categories": all_cats,
    })
    await query.edit_message_text(
        "📂 Pilih kategori untuk diisi budgetnya satu per satu.\n"
        "Tekan tombol kategori untuk set budget, lalu tekan *Selesai* bila sudah semua.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _cb_budget_cat_select(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str) -> None:
    query = update.callback_query
    _, _, data = get_state(context.user_data)
    currency = data.get("currency", config.default_currency)
    # Start asking for this category's budget via text
    set_state(context.user_data, FLOW_BUDGET, STEP_ASK_BUDGET_CATEGORY, {
        **data,
        "current_category": category,
        "category_queue": [],
    })
    emoji = CATEGORY_EMOJI.get(category, "📦")
    await query.message.reply_text(
        f"{emoji} Budget untuk *{category}* ({currency})?\n_(ketik 0 untuk skip)_",
        parse_mode="Markdown",
    )


async def _cb_budget_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, _, data = get_state(context.user_data)
    budget_data: list[dict] = data.get("budget_data", [])
    month_str = data.get("month", "")
    month_display = data.get("month_display", "")
    currency = data.get("currency", config.default_currency)

    if not budget_data:
        await query.edit_message_text("ℹ️ Tidak ada budget yang diisi.")
        clear_state(context.user_data)
        return

    try:
        await sheets_agent.set_budget(month_str, budget_data)
    except Exception as e:
        await query.edit_message_text(f"❌ Gagal menyimpan budget: {e}")
        return

    total = sum(e["amount"] for e in budget_data)
    lines = [f"✅ Budget *{month_display}* per kategori tersimpan!\n"]
    for e in budget_data:
        emoji = CATEGORY_EMOJI.get(e["category"], "📦")
        lines.append(f"{emoji} {e['category']}: {format_amount(e['amount'], currency)}")
    lines.append(f"\n💰 Total: {format_amount(total, currency)}")
    clear_state(context.user_data)
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown")


async def _cb_budget_manage_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, _, data = get_state(context.user_data)
    month_str = data.get("month", "")
    month_display = data.get("month_display", "")
    try:
        await sheets_agent.delete_budget(month_str)
    except Exception as e:
        await query.edit_message_text(f"❌ Gagal menghapus budget: {e}")
        return
    clear_state(context.user_data)
    await query.edit_message_text(
        f"🗑️ Budget *{month_display}* berhasil dihapus.", parse_mode="Markdown"
    )


# ── Edit flow ────────────────────────────────────────────────────────────────

async def _cb_edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE, row_num: int) -> None:
    query = update.callback_query
    _, _, data = get_state(context.user_data)
    candidates = data.get("candidates", [])
    expense = next((r for r in candidates if r.get("_row") == row_num), None)
    if not expense:
        await query.edit_message_text("⚠️ Transaksi tidak ditemukan.")
        return

    set_state(context.user_data, FLOW_EDIT, STEP_SELECT_FIELD, {"expense": expense})

    fields = [
        ("📅 Tanggal", "date"), ("💰 Nominal", "amount"), ("💱 Mata Uang", "currency"),
        ("🏷️ Kategori", "category"), ("💳 Metode Bayar", "payment_method"), ("📝 Deskripsi", "description"),
    ]
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"edit:field:{key}")] for label, key in fields]
        + [[InlineKeyboardButton("❌ Batal", callback_data="edit:cancel")]]
    )
    await query.edit_message_text(
        f"✏️ Edit transaksi:\n{format_expense_confirmation(expense)}\n\nField mana?",
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def _cb_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str) -> None:
    query = update.callback_query
    _, _, data = get_state(context.user_data)
    set_state(context.user_data, FLOW_EDIT, STEP_ENTER_VALUE, {**data, "edit_field": field})

    hints = {
        "date": "Masukkan tanggal baru (contoh: `28 April 2026`)",
        "amount": "Masukkan nominal baru (contoh: `35k`)",
        "currency": "Masukkan kode: `IDR`, `USD`, `EUR`, atau `GBP`",
        "category": f"Masukkan kategori:\n{', '.join(CATEGORIES)}",
        "payment_method": "Masukkan metode bayar (contoh: `GoPay`, `Revolut`)",
        "description": "Masukkan deskripsi baru",
    }
    await query.edit_message_text(hints.get(field, f"Masukkan nilai baru untuk {field}:"), parse_mode="Markdown")


async def _apply_edit_value(
    update: Update, context: ContextTypes.DEFAULT_TYPE, new_value: str
) -> None:
    """Called from input_handler when edit flow is in STEP_ENTER_VALUE."""
    _, _, data = get_state(context.user_data)
    expense = dict(data.get("expense", {}))
    field = data.get("edit_field", "")
    msg = update.message

    if field == "amount":
        from utils.currency import normalize_amount
        val = normalize_amount(new_value)
        expense[field] = val if val is not None else expense.get(field)
    elif field == "currency":
        expense[field] = new_value.upper() if new_value.upper() in ("IDR", "USD", "EUR", "GBP") else expense[field]
    elif field == "category":
        from agents.normalize_agent import normalize_category
        expense[field] = normalize_category(new_value)
    elif field == "payment_method":
        from agents.normalize_agent import normalize_payment_method
        expense[field] = normalize_payment_method(new_value)
    elif field == "date":
        from agents.normalize_agent import normalize_date
        expense[field] = normalize_date(new_value)
    else:
        expense[field] = new_value

    row_num = expense.get("_row")
    if not row_num:
        await msg.reply_text("⚠️ Tidak bisa menemukan baris di Sheets.")
        clear_state(context.user_data)
        return

    try:
        await sheets_agent.update_expense(row_num, expense)
    except Exception as e:
        await msg.reply_text(f"❌ Gagal update Sheets: {e}")
        return

    clear_state(context.user_data)
    await msg.reply_text(
        f"✅ Transaksi berhasil diupdate!\n\n{format_expense_confirmation(expense)}",
        parse_mode="Markdown",
    )


# ── Delete flow ───────────────────────────────────────────────────────────────

async def _cb_delete_select(update: Update, context: ContextTypes.DEFAULT_TYPE, row_num: int) -> None:
    query = update.callback_query
    _, _, data = get_state(context.user_data)
    candidates = data.get("candidates", [])
    expense = next((r for r in candidates if r.get("_row") == row_num), None)
    if not expense:
        await query.edit_message_text("⚠️ Transaksi tidak ditemukan.")
        return

    set_state(context.user_data, FLOW_DELETE, STEP_CONFIRM_DELETE, {"expense": expense})

    from utils.currency import format_amount
    amount_str = format_amount(float(expense.get("amount", 0)), expense.get("currency", "IDR"))
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑️ Ya, hapus", callback_data=f"delete:confirm:{row_num}"),
        InlineKeyboardButton("❌ Batal", callback_data="delete:cancel"),
    ]])
    await query.edit_message_text(
        f"🗑️ Yakin ingin menghapus transaksi ini?\n\n"
        f"📅 {expense.get('date')} | {amount_str} | {expense.get('category', '-')}\n"
        f"📝 {expense.get('description', '-')}",
        reply_markup=kb,
    )


async def _cb_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, row_num: int) -> None:
    query = update.callback_query
    try:
        await sheets_agent.delete_expense(row_num)
    except Exception as e:
        await query.edit_message_text(f"❌ Gagal menghapus: {e}")
        return
    clear_state(context.user_data)
    await query.edit_message_text("✅ Transaksi berhasil dihapus.")


# ── Export ────────────────────────────────────────────────────────────────────

async def _cb_export_range(update: Update, context: ContextTypes.DEFAULT_TYPE, data_str: str) -> None:
    query = update.callback_query
    parts = data_str.split(":", 3)  # export:range:start:end or export:range:custom
    if parts[2] == "custom":
        from utils.state import FLOW_EXPORT, STEP_ASK_EXPORT_RANGE
        set_state(context.user_data, FLOW_EXPORT, STEP_ASK_EXPORT_RANGE, {})
        await query.edit_message_text(
            "✏️ Masukkan rentang bulan (contoh: `Jan 2026 Apr 2026` atau `April 2026`):",
            parse_mode="Markdown",
        )
        return

    start_month = parts[2]
    end_month = parts[3] if len(parts) > 3 else start_month
    from handlers.command_handler import _do_export
    await query.edit_message_text("⏳ Menyiapkan file CSV...")
    await _do_export(update, context, start_month, end_month)
