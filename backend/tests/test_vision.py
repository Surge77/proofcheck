import json
from decimal import Decimal
from typing import Any

import pytest

from proofcheck import vision
from proofcheck.vision import VisionError, is_available, read_receipt

GOOD_REPLY = {
    "app": "gpay",
    "status": "success",
    "amount": "1500.00",
    "utr": "512345678901",
    "payer": "Ramesh Kumar",
    "paid_on": "2026-10-03",
}


def stub_chat(reply: str, calls: list[dict[str, Any]] | None = None) -> Any:
    async def fake_chat(prompt: str, image: bytes, schema: dict[str, Any]) -> str:
        if calls is not None:
            calls.append({"prompt": prompt, "image": image, "schema": schema})
        return reply

    return fake_chat


async def test_parses_a_well_formed_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vision, "_chat", stub_chat(json.dumps(GOOD_REPLY)))

    reading = await read_receipt(b"png", ["UPI transaction ID", "512345678901"])

    assert reading.utr == "512345678901"
    assert reading.amount == Decimal("1500.00")
    assert reading.status == "success"


async def test_sends_image_and_ocr_lines_as_hints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(vision, "_chat", stub_chat(json.dumps(GOOD_REPLY), calls))

    await read_receipt(b"png-bytes", ["Paid to Asha", "UTR 512345678901"])

    assert calls[0]["image"] == b"png-bytes"
    assert "UTR 512345678901" in calls[0]["prompt"]
    assert calls[0]["schema"]["required"]


async def test_null_fields_are_allowed_when_not_visible(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = {**GOOD_REPLY, "utr": None, "amount": None, "payer": None, "paid_on": None}
    monkeypatch.setattr(vision, "_chat", stub_chat(json.dumps(reply)))

    reading = await read_receipt(b"png", [])

    assert reading.utr is None
    assert reading.amount is None


@pytest.mark.parametrize(
    "reply",
    [
        "not json at all",
        json.dumps({**GOOD_REPLY, "status": "maybe"}),
        json.dumps({**GOOD_REPLY, "amount": "fifteen hundred"}),
    ],
)
async def test_malformed_reply_raises_vision_error(
    monkeypatch: pytest.MonkeyPatch, reply: str
) -> None:
    monkeypatch.setattr(vision, "_chat", stub_chat(reply))

    with pytest.raises(VisionError):
        await read_receipt(b"png", [])


async def test_unreachable_ollama_raises_vision_error() -> None:
    with pytest.raises(VisionError):
        await read_receipt(b"png", [])


async def test_is_available_false_when_ollama_is_down() -> None:
    assert await is_available() is False
