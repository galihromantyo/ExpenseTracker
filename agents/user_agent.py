from agents import sheets_agent
from config import config


async def get_or_register(chat_id: int, username: str, display_name: str) -> dict:
    """
    Return existing user record, or create one with the global default currency.
    Always returns a dict with at least: chat_id, display_name, default_currency.
    """
    user = await sheets_agent.get_user(chat_id)
    if user:
        return user
    await sheets_agent.upsert_user(
        chat_id=chat_id,
        username=username or "",
        display_name=display_name or str(chat_id),
        default_currency=config.default_currency,
    )
    return {
        "chat_id": chat_id,
        "username": username or "",
        "display_name": display_name or str(chat_id),
        "default_currency": config.default_currency,
        "is_active": "True",
    }


async def get_user_currency(chat_id: int) -> str:
    """Return user's preferred currency, falling back to global default."""
    user = await sheets_agent.get_user(chat_id)
    if user:
        currency = str(user.get("default_currency", "")).upper()
        if currency in ("IDR", "USD", "EUR", "GBP"):
            return currency
    return config.default_currency


async def set_currency(chat_id: int, currency: str) -> None:
    await sheets_agent.set_user_currency(chat_id, currency.upper())


async def is_registered(chat_id: int) -> bool:
    user = await sheets_agent.get_user(chat_id)
    return user is not None


async def set_password(chat_id: int, password: str) -> bool:
    import bcrypt
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return await sheets_agent.set_user_password(chat_id, password_hash)


async def get_user(chat_id: int) -> dict | None:
    return await sheets_agent.get_user(chat_id)
