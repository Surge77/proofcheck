from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import pytest

from proofcheck.extract import extract, fuse
from proofcheck.imaging import ImageError
from proofcheck.ocr import LineReader
from proofcheck.vision import VisionError, VisionReading
from tests.factories import receipt_png

LINES = ["Payment Successful", "₹1,500", "UPI transaction ID", "5123 4567 8901"]


def reading(**overrides: object) -> VisionReading:
    fields: dict[str, object] = {
        "app": "gpay",
        "status": "success",
        "amount": Decimal("1500"),
        "utr": "512345678901",
        "payer": "Ramesh Kumar",
        "paid_on": date(2026, 10, 3),
    }
    return VisionReading.model_validate({**fields, **overrides})


def test_both_models_agree_gives_high_confidence() -> None:
    receipt = fuse("a.png", LINES, reading())

    assert receipt.utr == "512345678901"
    assert receipt.amount == Decimal("1500")
    assert receipt.payer == "Ramesh Kumar"
    assert receipt.confidence == "high"
    assert receipt.issues == ()


def test_vision_utr_not_seen_by_ocr_is_replaced_by_labelled_ocr_value() -> None:
    receipt = fuse("a.png", LINES, reading(utr="512345678907"))

    assert receipt.utr == "512345678901"
    assert receipt.confidence == "low"
    assert any("UTR" in issue for issue in receipt.issues)


def test_vision_amount_not_printed_on_screen_falls_back_to_ocr_amount() -> None:
    receipt = fuse("a.png", LINES, reading(amount=Decimal("15000")))

    assert receipt.amount == Decimal("1500")
    assert receipt.confidence == "low"


@pytest.mark.parametrize("status", ["pending", "failed", "unclear"])
def test_non_success_status_is_low_confidence_with_reason(status: str) -> None:
    receipt = fuse("a.png", LINES, reading(status=status))

    assert receipt.status == status
    assert receipt.confidence == "low"
    assert any(status in issue for issue in receipt.issues)


def test_without_vision_uses_single_labelled_ocr_reference() -> None:
    receipt = fuse("a.png", LINES, None)

    assert receipt.utr == "512345678901"
    assert receipt.amount == Decimal("1500")
    assert receipt.status == "success"
    assert receipt.method == "ocr_only"
    assert receipt.confidence == "low"


def test_without_vision_several_unlabelled_numbers_leave_utr_empty() -> None:
    receipt = fuse("a.png", ["512345678901", "998877665544"], None)

    assert receipt.utr is None
    assert receipt.status == "unclear"
    assert any("reference" in issue for issue in receipt.issues)


def test_vision_reference_with_spaces_is_normalised() -> None:
    receipt = fuse("a.png", LINES, reading(utr="5123 4567 8901"))

    assert receipt.utr == "512345678901"
    assert receipt.confidence == "high"


def fake_ocr(lines: Sequence[str]) -> LineReader:
    def read(_png: bytes) -> list[str]:
        return list(lines)

    return read


async def test_extract_runs_ocr_then_vision() -> None:
    async def fake_vision(_png: bytes, ocr_lines: Sequence[str]) -> VisionReading:
        assert list(ocr_lines) == LINES
        return reading()

    receipt = await extract("a.png", receipt_png(), fake_ocr(LINES), fake_vision)

    assert receipt.confidence == "high"
    assert receipt.method == "ocr+vision"


async def test_extract_falls_back_to_ocr_when_vision_fails() -> None:
    async def broken_vision(_png: bytes, _lines: Sequence[str]) -> VisionReading:
        raise VisionError("down")

    receipt = await extract("a.png", receipt_png(), fake_ocr(LINES), broken_vision)

    assert receipt.method == "ocr_only"
    assert receipt.utr == "512345678901"


async def test_extract_rejects_non_images() -> None:
    with pytest.raises(ImageError):
        await extract("a.png", b"nope", fake_ocr(LINES))
