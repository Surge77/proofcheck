from datetime import date
from decimal import Decimal

import pytest

from proofcheck.models import Receipt, Statement, StatementTxn
from proofcheck.reconcile import format_inr, reconcile

UTR_A = "512345678901"
UTR_B = "610987654321"


def receipt(source: str = "a.png", utr: str | None = UTR_A, **overrides: object) -> Receipt:
    fields: dict[str, object] = {
        "source": source,
        "utr": utr,
        "amount": Decimal("1500"),
        "payer": "Ramesh Kumar",
        "paid_on": date(2026, 10, 3),
        "app": "gpay",
        "status": "success",
        "method": "ocr+vision",
        "confidence": "high",
    }
    return Receipt.model_validate({**fields, **overrides})


def credit(utr: str | None = UTR_A, amount: str = "1500", row: int = 5) -> StatementTxn:
    return StatementTxn(
        row=row,
        posted_on=date(2026, 10, 3),
        amount=Decimal(amount),
        utr=utr,
        payer="RAMESH K",
        vpa=None,
        narration=f"UPI/CR/{utr}/RAMESH K",
    )


def statement(*credits: StatementTxn) -> Statement:
    return Statement(
        bank="sbi", credits=credits, period_start=date(2026, 10, 1), period_end=date(2026, 10, 10)
    )


def test_reference_and_amount_found_is_verified() -> None:
    [match] = reconcile([receipt()], statement(credit()))

    assert match.status == "verified"
    assert match.credit is not None
    assert match.credit.row == 5


def test_reference_found_with_different_amount_is_mismatch() -> None:
    [match] = reconcile([receipt(amount=Decimal("15000"))], statement(credit()))

    assert match.status == "amount_mismatch"
    assert "1,500" in match.note
    assert "15,000" in match.note


def test_reference_missing_inside_period_is_not_in_statement() -> None:
    [match] = reconcile([receipt(utr=UTR_B)], statement(credit()))

    assert match.status == "not_in_statement"
    assert match.credit is None


def test_reference_missing_but_dated_after_statement_is_outside_period() -> None:
    [match] = reconcile([receipt(utr=UTR_B, paid_on=date(2026, 10, 12))], statement(credit()))

    assert match.status == "outside_period"


def test_same_reference_sent_twice_flags_the_second_copy() -> None:
    first, second = reconcile([receipt("a.png"), receipt("b.png")], statement(credit()))

    assert first.status == "verified"
    assert second.status == "duplicate_proof"
    assert "a.png" in second.note


def test_unreadable_reference_is_its_own_status() -> None:
    [match] = reconcile([receipt(utr=None)], statement(credit()))

    assert match.status == "unreadable"


def test_failed_screenshot_whose_reference_is_absent_says_so() -> None:
    [match] = reconcile([receipt(utr=UTR_B, status="failed")], statement(credit()))

    assert match.status == "not_in_statement"
    assert "failed" in match.note


def test_money_that_arrived_wins_over_a_failed_looking_screenshot() -> None:
    [match] = reconcile([receipt(status="unclear")], statement(credit()))

    assert match.status == "verified"


def test_missing_amount_on_receipt_still_verifies_by_reference() -> None:
    [match] = reconcile([receipt(amount=None)], statement(credit()))

    assert match.status == "verified"
    assert "amount" in match.note


@pytest.mark.parametrize(
    ("amount", "text"),
    [
        ("5", "₹5"),
        ("999", "₹999"),
        ("1500", "₹1,500"),
        ("245000", "₹2,45,000"),
        ("12345678.5", "₹1,23,45,678.50"),
        ("100000", "₹1,00,000"),
    ],
)
def test_format_inr_uses_indian_grouping(amount: str, text: str) -> None:
    assert format_inr(Decimal(amount)) == text
