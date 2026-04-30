import json
from datetime import date

from config import config
from utils.constants import CATEGORIES

_PROMPT_TEMPLATE = """You are a personal finance assistant for an Indonesian user living in London or Jakarta.

Extract expense transaction information from the input and return ONLY a valid JSON object.

Today's date: {today}

Return this exact JSON structure (use null for unknown fields):
{{
  "date": "YYYY-MM-DD",
  "description": "short description",
  "amount": 12345.67,
  "currency": "IDR|USD|EUR|GBP|null",
  "category": "one from the list below",
  "payment_method": "standardised name"
}}

Categories: {categories}

Currency detection:
- Rp, IDR, rb, k, jt, m (no $ prefix) → IDR
- $, USD, dollar → USD
- €, EUR, euro → EUR
- £, GBP, pound → GBP
- If unclear → null

Amount: strip currency symbols; 25k/25rb → 25000; 1.5jt/1.5m → 1500000

Payment method standardisation:
GoPay/OVO/Dana/ShopeePay/LinkAja/QRIS/Jenius/Flip → use as-is
BCA/Mandiri/BRI/BNI/CIMB/tf/transfer/Barclays/HSBC/Lloyds/NatWest/Santander/Starling → Bank Transfer
apple pay/applepay → Apple Pay
google pay/gpay → Google Pay
revolut → Revolut | monzo → Monzo | wise/transferwise → Wise | paypal → PayPal
contactless → Contactless
cc/credit card/kartu kredit → Credit Card
debit/debit card → Debit Card
cash/tunai → Cash
amex/american express → American Express
visa → Visa | mastercard → Mastercard

Return ONLY the JSON object."""


def _build_prompt() -> str:
    return _PROMPT_TEMPLATE.format(
        today=date.today().isoformat(),
        categories=", ".join(CATEGORIES),
    )


def _parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:])
        if text.endswith("```"):
            text = text[: text.rfind("```")]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


# ── Gemini helpers ──────────────────────────────────────────────────────────

async def _gemini_text(prompt: str, user_text: str) -> dict:
    import google.generativeai as genai
    genai.configure(api_key=config.gemini_api_key)
    model = genai.GenerativeModel(config.gemini_model)
    resp = await model.generate_content_async(
        f"{prompt}\n\nUser input:\n{user_text}",
        generation_config=genai.GenerationConfig(response_mime_type="application/json"),
    )
    return _parse(resp.text)


async def _gemini_image(prompt: str, image_bytes: bytes, mime_type: str) -> dict:
    import google.generativeai as genai
    genai.configure(api_key=config.gemini_api_key)
    model = genai.GenerativeModel(config.gemini_model)
    resp = await model.generate_content_async(
        [prompt + "\n\nExtract from this receipt image:", {"mime_type": mime_type, "data": image_bytes}],
        generation_config=genai.GenerationConfig(response_mime_type="application/json"),
    )
    return _parse(resp.text)


async def _gemini_audio(prompt: str, audio_bytes: bytes, mime_type: str) -> dict:
    import google.generativeai as genai
    genai.configure(api_key=config.gemini_api_key)
    model = genai.GenerativeModel(config.gemini_model)
    resp = await model.generate_content_async(
        [prompt + "\n\nExtract expense from this voice note:", {"mime_type": mime_type, "data": audio_bytes}],
        generation_config=genai.GenerationConfig(response_mime_type="application/json"),
    )
    return _parse(resp.text)


# ── OpenAI helpers ──────────────────────────────────────────────────────────

async def _openai_text(prompt: str, user_text: str) -> dict:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=config.openai_api_key)
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_text}],
        response_format={"type": "json_object"},
    )
    return _parse(resp.choices[0].message.content)


async def _openai_image(prompt: str, image_bytes: bytes, mime_type: str) -> dict:
    import base64
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=config.openai_api_key)
    b64 = base64.b64encode(image_bytes).decode()
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": [
                {"type": "text", "text": "Extract from this receipt:"},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
            ]},
        ],
        response_format={"type": "json_object"},
    )
    return _parse(resp.choices[0].message.content)


async def _openai_audio(audio_bytes: bytes) -> str:
    import io
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=config.openai_api_key)
    transcript = await client.audio.transcriptions.create(
        model="whisper-1",
        file=("voice.ogg", io.BytesIO(audio_bytes), "audio/ogg"),
    )
    return transcript.text


# ── Public API ──────────────────────────────────────────────────────────────

async def extract_from_text(text: str) -> dict:
    prompt = _build_prompt()
    if config.ai_provider == "gemini":
        return await _gemini_text(prompt, text)
    return await _openai_text(prompt, text)


async def extract_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    prompt = _build_prompt()
    if config.ai_provider == "gemini":
        return await _gemini_image(prompt, image_bytes, mime_type)
    return await _openai_image(prompt, image_bytes, mime_type)


async def extract_from_audio(audio_bytes: bytes, mime_type: str = "audio/ogg") -> dict:
    prompt = _build_prompt()
    if config.ai_provider == "gemini":
        return await _gemini_audio(prompt, audio_bytes, mime_type)
    # OpenAI: transcribe first then extract
    transcript = await _openai_audio(audio_bytes)
    return await _openai_text(prompt, transcript)
