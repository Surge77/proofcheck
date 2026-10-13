"""Turn one screenshot into a Receipt by cross-checking OCR and the vision model.

The rule is simple: a fact is "high confidence" only when two independent
open models agree on it. OCR sees exact characters but not meaning; Gemma sees
meaning but can misread digits. Each one checks the other.
"""

import asyncio
import re
from collections.abc import Awaitable, Callable, Sequence
from decimal import Decimal

from proofcheck.candidates import amount_appears, amounts_in, utr_candidates
from proofcheck.imaging import load_image, to_png
from proofcheck.models import Receipt
from proofcheck.ocr import LineReader, read_lines
from proofcheck.vision import PaymentStatus, VisionError, VisionReading, read_receipt

VisionReader = Callable[[bytes, Sequence[str]], Awaitable[VisionReading]]

# OCR needs enough pixels to read 12 small digits; the vision model must fit in 4 GB of VRAM.
OCR_MAX_SIDE = 2000
VISION_MAX_SIDE = 1024

_SUCCESS_WORDS = re.compile(r"\b(success(ful)?|completed|paid)\b", re.IGNORECASE)
_FAILURE_WORDS = re.compile(
    r"\b(fail(ed|ure)?|pending|declined|reversed|refunded|processing|cancell?ed)\b", re.IGNORECASE
)


def _ocr_utr(lines: Sequence[str]) -> str | None:
    candidates = utr_candidates(lines)
    labelled = [c.value for c in candidates if c.is_labelled]
    if len(labelled) == 1:
        return labelled[0]
    if not labelled and len(candidates) == 1:
        return candidates[0].value
    return None


def _ocr_amount(lines: Sequence[str]) -> Decimal | None:
    distinct = set(amounts_in(lines))
    return distinct.pop() if len(distinct) == 1 else None


def _fuse_utr(
    lines: Sequence[str], vision_utr: str | None, issues: list[str]
) -> tuple[str | None, bool]:
    """Returns (utr, confirmed_by_both)."""
    seen_by_ocr = {c.value for c in utr_candidates(lines)}
    claimed = re.sub(r"\s", "", vision_utr or "")
    if claimed in seen_by_ocr:
        return claimed, True
    fallback = _ocr_utr(lines)
    if claimed:
        issues.append("The vision model's UTR was not confirmed by OCR; please check it.")
    if fallback is None:
        issues.append("Could not tell which number is the UPI reference.")
    return fallback, False


def _fuse_amount(
    lines: Sequence[str], vision_amount: Decimal | None, issues: list[str]
) -> tuple[Decimal | None, bool]:
    if vision_amount is not None and amount_appears(vision_amount, lines):
        return vision_amount, True
    fallback = _ocr_amount(lines)
    if fallback is None:
        issues.append("Could not read the amount.")
    elif vision_amount is not None:
        issues.append("The vision model's amount was not printed on the screenshot.")
    return fallback, False


def _fuse_status(
    lines: Sequence[str], vision_status: PaymentStatus | None, issues: list[str]
) -> tuple[PaymentStatus, bool]:
    """Returns (status, confirmed_by_screen_text).

    Gemma reads the status, but text planted in a screenshot can talk it into
    "success". The OCR'd words must agree before a success counts as confirmed.
    """
    text = " ".join(lines)
    shows_success = bool(_SUCCESS_WORDS.search(text))
    shows_failure = bool(_FAILURE_WORDS.search(text))
    status: PaymentStatus
    if vision_status is None:
        status = "success" if shows_success and not shows_failure else "unclear"
    elif vision_status == "success" and shows_failure:
        status = "unclear"
        issues.append("The screenshot text mentions a failed or pending payment.")
    else:
        status = vision_status
    if status != "success":
        issues.append(f"Screenshot does not show a successful payment (status: {status}).")
    elif not shows_success:
        issues.append("No 'success' or 'paid' wording was found on the screenshot.")
    return status, status == "success" and shows_success and not shows_failure


def _words(text: str) -> list[str]:
    return re.sub(r"[^A-Za-z]+", " ", text).upper().split()


def _fuse_payer(lines: Sequence[str], payer: str | None, issues: list[str]) -> str | None:
    """Keep Gemma's payer name only if every word of it is printed on the screenshot."""
    if not payer:
        return None
    on_screen = set(_words(" ".join(lines)))
    words = _words(payer)
    if words and all(word in on_screen for word in words):
        return payer
    issues.append("The payer's name was not found in the screenshot text, so it was left out.")
    return None


def fuse(source: str, lines: Sequence[str], reading: VisionReading | None) -> Receipt:
    issues: list[str] = []
    if reading is None:
        issues.append("Read with OCR only (the local vision model was unavailable).")
    utr, utr_ok = _fuse_utr(lines, reading.utr if reading else None, issues)
    amount, amount_ok = _fuse_amount(lines, reading.amount if reading else None, issues)
    status, status_ok = _fuse_status(lines, reading.status if reading else None, issues)

    is_high = reading is not None and utr_ok and amount_ok and status_ok
    return Receipt(
        source=source,
        utr=utr,
        amount=amount,
        payer=_fuse_payer(lines, reading.payer, issues) if reading else None,
        paid_on=reading.paid_on if reading else None,
        app=reading.app if reading else None,
        status=status,
        method="ocr+vision" if reading else "ocr_only",
        confidence="high" if is_high else "low",
        issues=tuple(issues),
    )


async def extract(
    source: str,
    data: bytes,
    ocr: LineReader = read_lines,
    vision: VisionReader = read_receipt,
) -> Receipt:
    """Raises ImageError when `data` is not a usable image."""
    image = load_image(data)
    # OCR is CPU-bound (~1.5 s); keep it off the event loop so the server stays responsive.
    lines = await asyncio.to_thread(ocr, to_png(image, OCR_MAX_SIDE))
    try:
        reading: VisionReading | None = await vision(to_png(image, VISION_MAX_SIDE), lines)
    except VisionError:
        reading = None
    return fuse(source, lines, reading)
