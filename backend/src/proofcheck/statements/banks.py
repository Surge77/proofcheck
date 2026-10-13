"""Per-bank knowledge: how to recognise an export and read its narration column.

The narration (also called Description or Transaction Remarks) is where a bank
packs a UPI credit's reference number, the sender's name and UPI id, each bank
in its own layout. The UTR rules are shared; the payer rules differ.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Bank = Literal["sbi", "hdfc", "icici", "kotak", "generic"]

_SEGMENT_SPLIT = re.compile(r"[/\-\s]+")
_TWELVE = re.compile(r"^\d{12}$")
# Fallback for narrations without delimiters. `(?![\d@])` skips UPI ids like 919876543210@paytm.
_TWELVE_IN_TEXT = re.compile(r"(?<!\d)\d{12}(?![\d@])")
# No hyphen in the local part: HDFC uses "-" as its field separator.
_VPA = re.compile(r"[A-Za-z0-9._]{2,}@[A-Za-z]{2,}")

_PAYER: dict[Bank, re.Pattern[str]] = {
    "sbi": re.compile(r"UPI/CR/\d{12}/([^/]+)/", re.IGNORECASE),
    "hdfc": re.compile(r"^UPI-([^-]+)-", re.IGNORECASE),
    "kotak": re.compile(r"^UPI/([^/]+)/\d{12}", re.IGNORECASE),
}


@dataclass(frozen=True)
class NarrationInfo:
    utr: str | None
    payer: str | None
    vpa: str | None


def _utr(narration: str) -> str | None:
    for segment in _SEGMENT_SPLIT.split(narration):
        if _TWELVE.match(segment):
            return segment
    match = _TWELVE_IN_TEXT.search(narration)
    return match.group() if match else None


def _payer(narration: str, bank: Bank) -> str | None:
    pattern = _PAYER.get(bank)
    match = pattern.search(narration.strip()) if pattern else None
    if match is None:
        return None
    name = match.group(1).strip()
    return name if name and not name.isdigit() else None


def parse_narration(narration: str, bank: Bank) -> NarrationInfo:
    vpa = _VPA.search(narration)
    return NarrationInfo(
        utr=_utr(narration), payer=_payer(narration, bank), vpa=vpa.group() if vpa else None
    )


def utr_from_ref(ref: object) -> str | None:
    """A UTR from a reference column. HDFC pads it with zeros to 16 digits."""
    if not isinstance(ref, str | int):
        return None
    digits = str(ref).strip()
    if not digits.isdigit():
        return None
    trimmed = digits.lstrip("0")
    return trimmed if len(trimmed) == 12 else None


def detect_bank(header: Sequence[str]) -> Bank:
    cells = [cell.strip().lower() for cell in header]
    if "narration" in cells and any(c.startswith("deposit amt") for c in cells):
        return "hdfc"
    if "transaction remarks" in cells:
        return "icici"
    if "txn date" in cells and "description" in cells:
        return "sbi"
    if "sl. no." in cells or any(c.startswith("chq / ref") for c in cells):
        return "kotak"
    return "generic"
