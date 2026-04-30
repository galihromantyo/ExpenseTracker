from datetime import date

import httpx

_BASE_URL = "https://api.frankfurter.app/latest"


async def get_rates(base: str, targets: list[str]) -> dict[str, float]:
    """
    Fetch exchange rates from frankfurter.app.
    Returns {currency_code: rate} where rate = units of target per 1 base.
    """
    symbols = [t for t in targets if t != base]
    if not symbols:
        return {base: 1.0}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(_BASE_URL, params={"base": base, "symbols": ",".join(symbols)})
        resp.raise_for_status()
        data = resp.json()

    rates: dict[str, float] = {base: 1.0}
    rates.update(data.get("rates", {}))
    return rates


async def convert_expenses(
    expenses: list[dict],
    target_currency: str,
) -> tuple[list[dict], dict[str, float]]:
    """
    Convert all expenses to target_currency.
    Returns (converted_expenses, rate_info).
    rate_info: {source_currency: units_of_target_per_1_source}
    """
    source_currencies = {e["currency"] for e in expenses if e["currency"] != target_currency}
    if not source_currencies:
        return expenses, {}

    # For each source currency, get rate vs target
    rate_info: dict[str, float] = {}
    for src in source_currencies:
        rates = await get_rates(src, [target_currency])
        rate_info[src] = rates.get(target_currency, 1.0)

    converted = []
    for exp in expenses:
        if exp["currency"] == target_currency:
            converted.append(exp)
        else:
            rate = rate_info.get(exp["currency"], 1.0)
            new_exp = dict(exp)
            new_exp["amount"] = float(exp["amount"]) * rate
            new_exp["currency"] = target_currency
            converted.append(new_exp)

    return converted, rate_info


def format_rate_info(rate_info: dict[str, float], target_currency: str) -> str:
    if not rate_info:
        return ""
    parts = []
    for src, rate in rate_info.items():
        if target_currency == "IDR":
            parts.append(f"1 {src} = Rp {rate:,.0f}".replace(",", "."))
        else:
            parts.append(f"1 {src} = {rate:.4f} {target_currency}")
    today = date.today().strftime("%d %b %Y")
    return f"Rate: {' | '.join(parts)} ({today}, frankfurter.app)"
