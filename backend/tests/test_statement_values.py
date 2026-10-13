from datetime import date, datetime
from decimal import Decimal

import pytest

from proofcheck.statements.values import parse_amount, parse_date


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("03/10/2026", date(2026, 10, 3)),  # HDFC/ICICI: day first, never month first
        ("03/10/26", date(2026, 10, 3)),
        ("03-10-2026", date(2026, 10, 3)),
        ("3 Oct 2026", date(2026, 10, 3)),  # SBI
        ("03-Oct-2026", date(2026, 10, 3)),
        ("03-Oct-26", date(2026, 10, 3)),
        ("2026-10-03", date(2026, 10, 3)),
        (" 03/10/2026 ", date(2026, 10, 3)),
        (datetime(2026, 10, 3, 14, 5), date(2026, 10, 3)),  # spreadsheet cells come typed
        (date(2026, 10, 3), date(2026, 10, 3)),
    ],
)
def test_parses_indian_bank_date_formats(raw: object, expected: date) -> None:
    assert parse_date(raw) == expected


@pytest.mark.parametrize("raw", ["", "Opening Balance", "31/02/2026", None, 45000.0])
def test_unparseable_dates_are_none(raw: object) -> None:
    assert parse_date(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,500.00", Decimal("1500.00")),
        ("2,45,000.50", Decimal("245000.50")),  # lakh grouping
        ("750", Decimal("750")),
        (" 99.90 ", Decimal("99.90")),
        ("1,500.00 CR", Decimal("1500.00")),
        (1500.5, Decimal("1500.5")),
        (1500, Decimal("1500")),
    ],
)
def test_parses_amounts(raw: object, expected: Decimal) -> None:
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["", "-", "  ", None, "abc", "0", "0.00", 0])
def test_blank_or_zero_amounts_are_none(raw: object) -> None:
    assert parse_amount(raw) is None
