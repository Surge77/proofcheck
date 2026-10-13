"""Pure text rules for pulling UPI references and amounts out of OCR lines.

These run on every screenshot and are the ground truth the vision model is
checked against, so they are deliberately strict: a value Gemma reports is only
trusted when OCR independently saw the same digits.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# A UPI reference (UTR / RRN) is exactly 12 digits. Apps print it plain or in
# groups of four. The lookarounds stop us from cutting 12 digits out of a longer
# number, and `(?<!\+)` / `(?<!\d )` skip phone numbers like "+91 98765 43210".
_UTR = re.compile(r"(?<!\d)(?<!\d )(?<!\+)\d(?: ?\d){11}(?! ?\d)")

_UTR_LABEL = re.compile(
    r"\b(utr|rrn|upi\s*ref(erence)?|ref(erence)?\s*(no|number|id)|"
    r"(upi\s*)?transaction\s*id|txn\s*id)\b",
    re.IGNORECASE,
)

_AMOUNT = re.compile(r"(?:₹|\brs\.?|\binr)\s*(\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True)
class UtrCandidate:
    value: str
    # True when a "UTR"/"Ref No"/"Transaction ID" label sits on the same or previous line.
    is_labelled: bool


def utr_candidates(lines: Sequence[str]) -> list[UtrCandidate]:
    found: dict[str, UtrCandidate] = {}
    for index, line in enumerate(lines):
        previous = lines[index - 1] if index > 0 else ""
        is_labelled = bool(_UTR_LABEL.search(line) or _UTR_LABEL.search(previous))
        for match in _UTR.finditer(line):
            value = match.group().replace(" ", "")
            if value not in found:
                found[value] = UtrCandidate(value=value, is_labelled=is_labelled)
    return list(found.values())


def _to_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None


def amounts_in(lines: Sequence[str]) -> list[Decimal]:
    """Amounts printed next to a currency marker (₹, Rs, INR)."""
    amounts: list[Decimal] = []
    for line in lines:
        for match in _AMOUNT.finditer(line):
            value = _to_decimal(match.group(1))
            if value is not None:
                amounts.append(value)
    return amounts


def amount_appears(amount: Decimal, lines: Sequence[str]) -> bool:
    """True if `amount` is printed anywhere as a whole number (commas ignored)."""
    for line in lines:
        for raw in _NUMBER.findall(line.replace(",", "")):
            if _to_decimal(raw) == amount:
                return True
    return False
