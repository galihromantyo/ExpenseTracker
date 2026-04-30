from datetime import date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from agents import sheets_agent, export_agent
from utils.date_parser import parse_report_month, format_month_display, month_to_str
from utils.formatter import format_expense_row
from utils.state import (
    set_state, clear_state,
    FLOW_REPORT, FLOW_BUDGET, FLOW_EDIT, FLOW_DELETE, FLOW_EXPORT,
    STEP_ASK_MONTH, STEP_SELECT_EXPENSE, STEP_ASK_EXPORT_RANGE,
)
from utils.constants import SUPPORTED_CURRENCIES, CATEGORIES
from config import config

HELP_TEXT = (
    "📖 *Panduan agen\\_exptrackerviz*\n\n"
    "*Input expense:*\n"
    "Langsung kirim teks, foto struk, PDF, atau voice note — bot akan memproses otomatis\\.\n"
    "Atau gunakan /input untuk memulai dengan menu\\.\n\n"
    "*Commands:*\n"
    "/laporan \\[bulan\\] — laporan budget & pengeluaran\n"
    "/budget \\[bulan\\] — set atau update budget\n"
    "/history \\[n\\] — n transaksi terakhir \\(default 10\\)\n"
    "/edit — edit transaksi yang dicatat\n"
    "/hapus — hapus transaksi\n"
    "/export \\[mulai\\] \\[akhir\\] — export CSV\n"
    "/setcurrency — ubah mata uang default\n"
    "/help — tampilkan panduan ini\n\n"
    f"_Mata uang default saat ini: *{config.default_currency}*_"
)


def _month_picker_keyboard(prefix: str) -> InlineKeyboardMarkup:
    today = date.today()
    prev = date(today.year, today.month, 1)
    from datetime import timedelta
    prev = (prev - timedelta(days=1))
    rows = [
        [
            InlineKeyboardButton(
                f"📅 Bulan ini ({format_month_display(today.year, today.month)})",
                callback_data=f"{prefix}:month:{month_to_str(today.year, today.month)}",
            )
        ],
        [
            InlineKeyboardButton(
                f"⬅️ Bulan lalu ({format_month_display(prev.year, prev.month)})",
                callback_data=f"{prefix}:month:{month_to_str(prev.year, prev.month)}",
            )
        ],
        [InlineKeyboardButton("🗓️ Pilih bulan lain...", callback_data=f"{prefix}:month:custom")],
    ]
    return InlineKeyboardMarkup(rows)


# ── /start ───────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(context.user_data)
    await update.message.reply_text(
        "👋 Halo\\! Saya *agen\\_exptrackerviz*, asisten keuangan pribadi kamu\\.\n\n"
        "Langsung kirim *teks, foto struk, PDF,* atau *voice note* untuk mencatat pengeluaran\\.\n\n"
        "Ketik /help untuk melihat semua perintah yang tersedia\\.",
        parse_mode="MarkdownV2",
    )


# ── /help ────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")


# ── /input ───────────────────────────────────────────────────────────────────

async def cmd_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(context.user_data)
    await update.message.reply_text(
        "📥 Silakan kirim pengeluaran kamu dalam format apapun:\n\n"
        "• *Teks* — contoh: _lunch £12 Pret Monzo_\n"
        "• *Foto* — foto struk / bukti bayar\n"
        "• *PDF* — dokumen transaksi\n"
        "• *Voice note* — ceritakan pengeluarannya",
        parse_mode="Markdown",
    )


# ── /laporan ─────────────────────────────────────────────────────────────────

async def cmd_laporan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(context.user_data)
    args = context.args
    if args:
        text = " ".join(args)
        parsed = parse_report_month(text)
        if parsed:
            year, month = parsed
            month_str = month_to_str(year, month)
            month_display = format_month_display(year, month)
            set_state(context.user_data, FLOW_REPORT, None, {
                "month": month_str,
                "month_display": month_display,
            })
            # Trigger report directly via callback mechanism by passing to input handler
            from handlers.callback_handler import _run_report_for_month
            await _run_report_for_month(update, context, month_str, month_display)
            return
        else:
            await update.message.reply_text(
                "⚠️ Format bulan tidak dikenali. Contoh: `/laporan April 2026` atau `/laporan 2026-04`",
                parse_mode="Markdown",
            )
            return

    set_state(context.user_data, FLOW_REPORT, STEP_ASK_MONTH, {})
    await update.message.reply_text(
        "📅 Laporan bulan apa?",
        reply_markup=_month_picker_keyboard("report"),
    )


# ── /budget ──────────────────────────────────────────────────────────────────

async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(context.user_data)
    args = context.args
    if args:
        text = " ".join(args)
        parsed = parse_report_month(text)
        if parsed:
            year, month = parsed
            month_str = month_to_str(year, month)
            month_display = format_month_display(year, month)
            set_state(context.user_data, FLOW_BUDGET, None, {
                "month": month_str,
                "month_display": month_display,
            })
            from handlers.callback_handler import _start_budget_type_step
            await _start_budget_type_step(update, context, month_str, month_display)
            return

    set_state(context.user_data, FLOW_BUDGET, STEP_ASK_MONTH, {})
    await update.message.reply_text(
        "📅 Set budget untuk bulan apa?",
        reply_markup=_month_picker_keyboard("budget"),
    )


# ── /history ─────────────────────────────────────────────────────────────────

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(context.user_data)
    n = 10
    if context.args:
        try:
            n = min(int(context.args[0]), 50)
        except ValueError:
            pass

    await update.message.reply_text("⏳ Mengambil riwayat transaksi...")
    try:
        rows = await sheets_agent.get_recent_expenses(n)
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal membaca Google Sheets: {e}")
        return

    if not rows:
        await update.message.reply_text("📭 Belum ada transaksi yang dicatat.")
        return

    lines = [f"📋 *{len(rows)} Transaksi Terakhir*\n"]
    for i, row in enumerate(rows, 1):
        lines.append(format_expense_row(row, i))

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── /edit ────────────────────────────────────────────────────────────────────

async def cmd_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(context.user_data)
    await update.message.reply_text("⏳ Mengambil transaksi terakhir...")
    try:
        rows = await sheets_agent.get_recent_expenses(10)
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal membaca Google Sheets: {e}")
        return

    if not rows:
        await update.message.reply_text("📭 Belum ada transaksi.")
        return

    set_state(context.user_data, FLOW_EDIT, STEP_SELECT_EXPENSE, {"candidates": rows})

    lines = ["✏️ *Pilih transaksi yang ingin diedit:*\n"]
    keyboard_rows = []
    for i, row in enumerate(rows, 1):
        lines.append(format_expense_row(row, i))
        keyboard_rows.append([
            InlineKeyboardButton(f"{i}. {row.get('date', '')} | {row.get('description', '')[:25]}",
                                 callback_data=f"edit:select:{row['_row']}")
        ])
    keyboard_rows.append([InlineKeyboardButton("❌ Batal", callback_data="edit:cancel")])

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await update.message.reply_text("Pilih transaksi:", reply_markup=InlineKeyboardMarkup(keyboard_rows))


# ── /hapus ───────────────────────────────────────────────────────────────────

async def cmd_hapus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(context.user_data)
    await update.message.reply_text("⏳ Mengambil transaksi terakhir...")
    try:
        rows = await sheets_agent.get_recent_expenses(10)
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal membaca Google Sheets: {e}")
        return

    if not rows:
        await update.message.reply_text("📭 Belum ada transaksi.")
        return

    set_state(context.user_data, FLOW_DELETE, STEP_SELECT_EXPENSE, {"candidates": rows})

    lines = ["🗑️ *Pilih transaksi yang ingin dihapus:*\n"]
    keyboard_rows = []
    for i, row in enumerate(rows, 1):
        lines.append(format_expense_row(row, i))
        keyboard_rows.append([
            InlineKeyboardButton(f"{i}. {row.get('date', '')} | {row.get('description', '')[:25]}",
                                 callback_data=f"delete:select:{row['_row']}")
        ])
    keyboard_rows.append([InlineKeyboardButton("❌ Batal", callback_data="delete:cancel")])

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    await update.message.reply_text("Pilih transaksi:", reply_markup=InlineKeyboardMarkup(keyboard_rows))


# ── /export ──────────────────────────────────────────────────────────────────

async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(context.user_data)
    today = date.today()
    # Parse optional args: /export Apr 2026 Apr 2026  or /export 2026-04 2026-04
    args_text = " ".join(context.args) if context.args else ""
    if args_text:
        # Try to find two month references separated by space
        tokens = args_text.split()
        # Simple heuristic: try pairs
        start_month = end_month = None
        for split in range(1, len(tokens)):
            p1 = parse_report_month(" ".join(tokens[:split]))
            p2 = parse_report_month(" ".join(tokens[split:]))
            if p1 and p2:
                start_month = month_to_str(*p1)
                end_month = month_to_str(*p2)
                break
        if not start_month:
            p = parse_report_month(args_text)
            if p:
                start_month = end_month = month_to_str(*p)
        if start_month and end_month:
            await _do_export(update, context, start_month, end_month)
            return

    # Ask for range
    set_state(context.user_data, FLOW_EXPORT, STEP_ASK_EXPORT_RANGE, {})
    cur_month = month_to_str(today.year, today.month)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📅 Bulan ini saja ({format_month_display(today.year, today.month)})",
                              callback_data=f"export:range:{cur_month}:{cur_month}")],
        [InlineKeyboardButton("✏️ Masukkan rentang bulan sendiri",
                              callback_data="export:range:custom")],
    ])
    await update.message.reply_text("📂 Export data ke CSV — pilih rentang:", reply_markup=kb)


async def _do_export(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     start_month: str, end_month: str) -> None:
    await update.message.reply_text("⏳ Menyiapkan file CSV...")
    try:
        rows = await sheets_agent.get_expenses_range(start_month, end_month)
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal membaca Google Sheets: {e}")
        return

    label = start_month if start_month == end_month else f"{start_month}_to_{end_month}"
    buf, filename = export_agent.generate_csv(rows, label)
    clear_state(context.user_data)
    await update.message.reply_document(
        document=buf, filename=filename,
        caption=f"✅ Export selesai — {len(rows)} transaksi ({start_month} s/d {end_month})",
    )


# ── /setcurrency ─────────────────────────────────────────────────────────────

async def cmd_setcurrency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    clear_state(context.user_data)
    current = config.default_currency
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"{'✅ ' if c == current else ''}{c}", callback_data=f"currency:set:{c}")
        for c in SUPPORTED_CURRENCIES
    ]])
    await update.message.reply_text(
        f"💱 Mata uang default saat ini: *{current}*\n\nPilih mata uang baru:",
        parse_mode="Markdown",
        reply_markup=kb,
    )
