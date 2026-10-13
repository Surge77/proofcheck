"""Parse the date and money cells found in Indian bank statement exports."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# Indian banks always write the day first. Never try month-first formats:
# "03/10/2026" must be 3 October, and a US reading would silently corrupt data.
_DATE_FORMATS = (
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d-%m-%Y",
    "%d-%m-%y",
    "%d %b %Y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%d %b %y",
    "%Y-%m-%d",
)
_MONEY = re.compile(r"^\d[\d,]*(\.\d+)?$")


def parse_date(raw: object) -> date | None:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(raw: object) -> Decimal | None:
    """A positive amount, or None for blank, dash, zero or non-numeric cells."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        value = Decimal(str(raw))
    elif isinstance(raw, str):
        text = re.sub(r"\s*(cr|dr)\.?$", "", raw.strip(), flags=re.IGNORECASE)
        if not _MONEY.match(text):
            return None
        try:
            value = Decimal(text.replace(",", ""))
        except InvalidOperation:
            return None
    else:
        return None
    return value if value > 0 else None
