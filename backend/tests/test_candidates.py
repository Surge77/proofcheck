from decimal import Decimal

import pytest

from proofcheck.candidates import amount_appears, amounts_in, utr_candidates


def values(lines: list[str]) -> list[str]:
    return [c.value for c in utr_candidates(lines)]


def test_finds_plain_twelve_digit_reference() -> None:
    assert values(["UPI transaction ID", "512345678901"]) == ["512345678901"]


def test_joins_reference_printed_in_groups_of_four() -> None:
    assert values(["UTR: 5123 4567 8901"]) == ["512345678901"]


@pytest.mark.parametrize(
    "line",
    [
        "51234567890",  # 11 digits
        "5123456789012",  # 13 digits: part of a longer id, not a UTR
        "Order 12345678901234",
    ],
)
def test_ignores_runs_that_are_not_exactly_twelve_digits(line: str) -> None:
    assert values([line]) == []


def test_ignores_phone_number_with_country_code() -> None:
    # "+91 98765 43210" is also 12 digits once the spaces go.
    assert values(["Ramesh +91 98765 43210"]) == []


def test_marks_candidate_labelled_on_same_or_previous_line() -> None:
    found = utr_candidates(["UPI Ref No", "512345678901", "Txn 998877665544 misc"])

    labelled = {c.value: c.is_labelled for c in found}
    assert labelled == {"512345678901": True, "998877665544": False}


def test_deduplicates_candidates_keeping_first_position() -> None:
    assert values(["UTR 512345678901", "Copy 512345678901"]) == ["512345678901"]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("₹1,500", Decimal("1500")),
        ("₹ 2,45,000.50", Decimal("245000.50")),
        ("Rs. 750", Decimal("750")),
        ("INR 99.9", Decimal("99.9")),
    ],
)
def test_reads_amounts_with_currency_marker(line: str, expected: Decimal) -> None:
    assert amounts_in([line]) == [expected]


def test_amount_without_currency_marker_is_not_listed() -> None:
    assert amounts_in(["1,500"]) == []


@pytest.mark.parametrize(
    ("amount", "lines", "expected"),
    [
        (Decimal("1500"), ["1,500"], True),
        (Decimal("1500.00"), ["₹1500"], True),
        (Decimal("1500"), ["15,000"], False),
        (Decimal("150"), ["1,500"], False),
        (Decimal("1500.50"), ["1,500.50 paid"], True),
    ],
)
def test_amount_appears_matches_whole_numbers_only(
    amount: Decimal, lines: list[str], expected: bool
) -> None:
    assert amount_appears(amount, lines) is expected
