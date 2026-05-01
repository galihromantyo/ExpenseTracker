from utils.constants import CATEGORY_EMOJI
from utils.currency import format_amount


def format_expense_confirmation(expense: dict) -> str:
    emoji = CATEGORY_EMOJI.get(expense.get("category", ""), "📋")
    amount_str = format_amount(expense["amount"], expense["currency"])
    return (
        "📋 *Konfirmasi Transaksi*\n\n"
        f"📅 Tanggal    : `{expense['date']}`\n"
        f"💰 Nominal    : *{amount_str}*\n"
        f"💱 Mata Uang  : `{expense['currency']}`\n"
        f"{emoji} Kategori   : {expense.get('category', '-')}\n"
        f"💳 Bayar via  : {expense.get('payment_method', '-')}\n"
        f"📝 Deskripsi  : {expense.get('description', '-')}"
    )


def format_expense_row(expense: dict, index: int) -> str:
    emoji = CATEGORY_EMOJI.get(expense.get("category", ""), "📦")
    amount_str = format_amount(float(expense.get("amount", 0)), expense.get("currency", "IDR"))
    desc = str(expense.get("description", "-"))[:30]
    return f"{index}. `{expense['date']}` | *{amount_str}* | {emoji} {desc}"


def format_report_single(
    month_display: str,
    display_currency: str,
    total_budget: float | None,
    total_spent: float,
    by_category: dict[str, dict],
    converted: bool,
    rate_info: str | None,
) -> str:
    """
    Format report text for a single currency (converted or native).
    by_category: {category: {"spent": float, "budget": float | None}}
    """
    lines: list[str] = [f"📊 *Laporan {month_display}*"]
    if converted:
        lines.append(f"_(semua dikonversi ke {display_currency})_")
    lines.append("─" * 30)

    if total_budget is not None:
        pct = (total_spent / total_budget * 100) if total_budget > 0 else 0
        sisa = total_budget - total_spent
        lines.append(f"💰 Budget Total  : *{format_amount(total_budget, display_currency)}*")
        lines.append(f"📤 Total Keluar  : {format_amount(total_spent, display_currency)} ({pct:.0f}%)")
        sisa_label = f"💵 Sisa Budget   : {format_amount(max(sisa, 0), display_currency)}"
        if sisa < 0:
            sisa_label += f" ⚠️ OVER {format_amount(abs(sisa), display_currency)}"
        lines.append(sisa_label)
    else:
        lines.append(f"📤 Total Keluar  : *{format_amount(total_spent, display_currency)}*")
        lines.append("_(budget belum diset — gunakan /budget untuk mengatur)_")

    if by_category:
        lines.append("\n📂 *Per Kategori:*")
        over_cats: list[str] = []
        for cat, data in sorted(by_category.items(), key=lambda x: x[1]["spent"], reverse=True):
            if data["spent"] <= 0:
                continue
            emoji = CATEGORY_EMOJI.get(cat, "📦")
            spent_str = format_amount(data["spent"], display_currency)
            line = f"{emoji} {cat:<20}: {spent_str}"
            if data.get("budget") is not None:
                sisa_cat = data["budget"] - data["spent"]
                if sisa_cat < 0:
                    line += f" ⚠️ +{format_amount(abs(sisa_cat), display_currency)}"
                    over_cats.append(cat)
                else:
                    line += f" → sisa {format_amount(sisa_cat, display_currency)}"
            lines.append(line)

        if over_cats:
            lines.append("")
            for cat in over_cats:
                lines.append(f"⚠️ _{cat} melebihi budget_")

    lines.append("─" * 30)
    if rate_info:
        lines.append(f"💱 {rate_info}")

    return "\n".join(lines)


def format_report_multi(
    month_display: str,
    sections: dict[str, dict],
) -> str:
    """
    Format report for multi-currency without conversion.
    sections: {currency: {"total_spent": float, "by_category": {...}}}
    """
    lines = [f"📊 *Laporan {month_display}*", "_(multi-currency, tidak dikonversi)_", "─" * 30]
    for currency, data in sections.items():
        lines.append(f"\n*── {currency} ──*")
        lines.append(f"📤 Total Keluar : *{format_amount(data['total_spent'], currency)}*")
        if data.get("by_category"):
            for cat, spent in sorted(data["by_category"].items(), key=lambda x: x[1], reverse=True):
                if spent <= 0:
                    continue
                emoji = CATEGORY_EMOJI.get(cat, "📦")
                lines.append(f"  {emoji} {cat:<20}: {format_amount(spent, currency)}")
    lines.append("─" * 30)
    return "\n".join(lines)
