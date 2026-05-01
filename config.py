import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", encoding="utf-8-sig")


@dataclass
class Config:
    telegram_bot_token: str
    ai_provider: str
    gemini_api_key: str
    gemini_model: str
    openai_api_key: str
    google_sheets_id: str
    google_sheets_id_test: str
    google_service_account_json: str
    default_currency: str
    superuser_chat_ids: list[int]
    mode: str  # "prod" or "test"

    @property
    def active_sheets_id(self) -> str:
        """Return test or prod spreadsheet ID based on MODE."""
        if self.mode == "test" and self.google_sheets_id_test:
            return self.google_sheets_id_test
        return self.google_sheets_id


def _load() -> Config:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    if provider not in ("gemini", "openai"):
        raise ValueError("AI_PROVIDER must be 'gemini' or 'openai'")

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    openai_key = os.getenv("OPENAI_API_KEY", "")

    if provider == "gemini" and not gemini_key:
        raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini")
    if provider == "openai" and not openai_key:
        raise ValueError("OPENAI_API_KEY is required when AI_PROVIDER=openai")

    sheets_id = os.getenv("GOOGLE_SHEETS_ID")
    if not sheets_id:
        raise ValueError("GOOGLE_SHEETS_ID is required")

    sheets_id_test = os.getenv("GOOGLE_SHEETS_ID_TEST", "")

    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is required")

    currency = os.getenv("DEFAULT_CURRENCY", "IDR").upper()
    if currency not in ("IDR", "USD", "EUR", "GBP"):
        raise ValueError("DEFAULT_CURRENCY must be one of: IDR, USD, EUR, GBP")

    raw_superusers = os.getenv("SUPERUSER_CHAT_IDS", "")
    superuser_ids: list[int] = []
    for part in raw_superusers.split(","):
        part = part.strip()
        if part:
            try:
                superuser_ids.append(int(part))
            except ValueError:
                pass

    mode = os.getenv("MODE", "prod").lower()
    if mode not in ("prod", "test"):
        mode = "prod"

    return Config(
        telegram_bot_token=token,
        ai_provider=provider,
        gemini_api_key=gemini_key,
        gemini_model=gemini_model,
        openai_api_key=openai_key,
        google_sheets_id=sheets_id,
        google_sheets_id_test=sheets_id_test,
        google_service_account_json=sa_json,
        default_currency=currency,
        superuser_chat_ids=superuser_ids,
        mode=mode,
    )


config = _load()
