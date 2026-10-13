"""Gemma 3 vision, running locally through Ollama, reads one payment screenshot.

OCR already has the raw text; Gemma's job is the part OCR can't do: decide
which of the numbers on screen is the UPI reference, which is the amount, who
paid, and whether the payment actually succeeded. Its answer is never trusted
on its own; `extract.py` checks it against the OCR text.
"""

import base64
import json
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from proofcheck.config import get_settings

UpiApp = Literal["gpay", "phonepe", "paytm", "bhim", "bank", "other"]
PaymentStatus = Literal["success", "pending", "failed", "unclear"]


class VisionError(RuntimeError):
    """The vision model was unreachable or returned something unusable."""


class VisionReading(BaseModel):
    model_config = ConfigDict(frozen=True)

    app: UpiApp
    status: PaymentStatus
    amount: Decimal | None
    utr: str | None
    payer: str | None
    paid_on: date | None

    @field_validator("paid_on", mode="before")
    @classmethod
    def _lenient_date(cls, value: object) -> object:
        # A date in an odd format shouldn't throw away the UTR and amount we did get.
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
        return value


_NULLABLE_STRING = {"type": ["string", "null"]}
_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "app": {"type": "string", "enum": list(UpiApp.__args__)},
        "status": {"type": "string", "enum": list(PaymentStatus.__args__)},
        "amount": _NULLABLE_STRING,
        "utr": _NULLABLE_STRING,
        "payer": _NULLABLE_STRING,
        "paid_on": _NULLABLE_STRING,
    },
    "required": ["app", "status", "amount", "utr", "payer", "paid_on"],
}

_PROMPT = """You are reading a screenshot of an Indian UPI payment confirmation \
(Google Pay, PhonePe, Paytm, BHIM or a bank app). Return JSON with:
- app: which app made the screenshot
- status: "success" only if the screen clearly says the payment succeeded/completed
- amount: the amount paid, digits only with optional decimals, e.g. "1500" or "1500.50"
- utr: the 12-digit UPI reference (labelled UTR, UPI Ref No, UPI transaction ID or RRN). \
Never a phone number, order id or Google transaction id with letters.
- payer: the name of the person who paid (the sender), if shown
- paid_on: the payment date as YYYY-MM-DD
Use null for anything you cannot see. Do not guess.

Text that OCR read from the same image, top to bottom (may contain small errors):
{ocr_text}"""


# trust_env=False everywhere: a system HTTP(S)_PROXY / ALL_PROXY must never carry screenshots
# off the machine, even though Ollama is on loopback.
async def _chat(prompt: str, image: bytes, schema: dict[str, Any]) -> str:
    settings = get_settings()
    body: dict[str, Any] = {
        "model": settings.vision_model,
        "messages": [
            {"role": "user", "content": prompt, "images": [base64.b64encode(image).decode()]}
        ],
        "stream": False,
        "format": schema,
        "options": {"temperature": 0},
    }
    async with httpx.AsyncClient(timeout=settings.vision_timeout_s, trust_env=False) as client:
        response = await client.post(f"{settings.ollama_url}/api/chat", json=body)
        response.raise_for_status()
        return str(response.json()["message"]["content"])


async def read_receipt(image_png: bytes, ocr_lines: Sequence[str]) -> VisionReading:
    prompt = _PROMPT.format(ocr_text="\n".join(ocr_lines) or "(none)")
    try:
        reply = await _chat(prompt, image_png, _SCHEMA)
        return VisionReading.model_validate(json.loads(reply))
    except (httpx.HTTPError, KeyError) as error:
        raise VisionError("The local vision model is not reachable.") from error
    except (json.JSONDecodeError, ValidationError) as error:
        raise VisionError("The vision model returned an unusable answer.") from error


async def is_available() -> bool:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=3.0, trust_env=False) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            response.raise_for_status()
            names = {m.get("name") for m in response.json().get("models", [])}
            return settings.vision_model in names
    except (httpx.HTTPError, ValueError):
        return False
