from agents.currency_agent import format_rate_info
from utils.formatter import format_report_single, format_report_multi


def build_report_data(
    expenses: list[dict],
    budget_entries: list[dict],
) -> dict:
    """
    Calculate report figures from raw expense + budget lists.
    Returns a structured dict used by both the text formatter and chart agent.
    """
    # Aggregate spending per category (in original currency, may be mixed)
    by_cat_raw: dict[str, dict[str, float]] = {}
    for exp in expenses:
        cat = exp.get("category", "Other")
        cur = exp.get("currency", "IDR")
        by_cat_raw.setdefault(cat, {}).setdefault(cur, 0.0)
        by_cat_raw[cat][cur] += float(exp.get("amount", 0))

    # Parse budget entries
    total_budget_entry: float | None = None
    cat_budgets: dict[str, float] = {}
    budget_currency: str | None = None
    budget_type: str | None = None

    for b in budget_entries:
        btype = b.get("budget_type", "")
        bcat = str(b.get("category", "")).strip()
        amt = float(b.get("amount", 0))
        cur = b.get("currency", "IDR")
        budget_currency = cur
        if btype == "total" and not bcat:
            total_budget_entry = amt
            budget_type = "total"
        elif btype == "per_category" and bcat:
            cat_budgets[bcat] = amt
            budget_type = "per_category"

    if budget_type == "per_category" and cat_budgets:
        total_budget_entry = sum(cat_budgets.values())

    currencies_in_expenses = {e.get("currency") for e in expenses}
    is_multi_currency = len(currencies_in_expenses) > 1

    return {
        "expenses": expenses,
        "by_cat_raw": by_cat_raw,
        "total_budget": total_budget_entry,
        "cat_budgets": cat_budgets,
        "budget_currency": budget_currency,
        "budget_type": budget_type,
        "is_multi_currency": is_multi_currency,
        "currencies": list(currencies_in_expenses),
    }


def generate_report_text_single(
    report_data: dict,
    month_display: str,
    display_currency: str,
    converted_expenses: list[dict],
    rate_info: dict[str, float],
) -> str:
    """Generate report text when all amounts are in one currency."""
    total_spent = sum(float(e.get("amount", 0)) for e in converted_expenses)

    by_cat: dict[str, dict[str, float | None]] = {}
    for exp in converted_expenses:
        cat = exp.get("category", "Other")
        by_cat.setdefault(cat, {"spent": 0.0, "budget": None})
        by_cat[cat]["spent"] = by_cat[cat]["spent"] + float(exp.get("amount", 0))

    # Attach budget per category
    cat_budgets = report_data.get("cat_budgets", {})
    for cat in by_cat:
        if cat in cat_budgets:
            by_cat[cat]["budget"] = cat_budgets[cat]

    # Include categories with budget but no spending
    for cat, budget in cat_budgets.items():
        if cat not in by_cat:
            by_cat[cat] = {"spent": 0.0, "budget": budget}

    rate_str = format_rate_info(rate_info, display_currency) if rate_info else None

    return format_report_single(
        month_display=month_display,
        display_currency=display_currency,
        total_budget=report_data.get("total_budget"),
        total_spent=total_spent,
        by_category=by_cat,
        converted=bool(rate_info),
        rate_info=rate_str,
    )


def generate_report_text_multi(
    report_data: dict,
    month_display: str,
) -> str:
    """Generate report text grouped by currency (no conversion)."""
    by_cat_raw: dict[str, dict[str, float]] = report_data["by_cat_raw"]

    # Rebuild sections per currency
    sections: dict[str, dict] = {}
    for cat, cur_amounts in by_cat_raw.items():
        for cur, amt in cur_amounts.items():
            sections.setdefault(cur, {"total_spent": 0.0, "by_category": {}})
            sections[cur]["total_spent"] += amt
            sections[cur]["by_category"][cat] = sections[cur]["by_category"].get(cat, 0.0) + amt

    return format_report_multi(month_display=month_display, sections=sections)


def build_chart_data(
    converted_expenses: list[dict],
    display_currency: str,
) -> dict[str, float]:
    """Return {category: total_spent} for chart generation."""
    result: dict[str, float] = {}
    for exp in converted_expenses:
        cat = exp.get("category", "Other")
        result[cat] = result.get(cat, 0.0) + float(exp.get("amount", 0))
    return result
