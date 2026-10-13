from datetime import date
from decimal import Decimal

import pytest

from proofcheck.statements import StatementError, parse_statement
from tests.sheets import HDFC_ROWS, KOTAK_DRCR_ROWS, SBI_ROWS, csv_bytes, xlsx_bytes


def test_sbi_csv_skips_preamble_and_keeps_only_credits() -> None:
    statement = parse_statement("sbi.csv", csv_bytes(SBI_ROWS))

    assert statement.bank == "sbi"
    assert [c.amount for c in statement.credits] == [Decimal("1500.00"), Decimal("3000.00")]
    first = statement.credits[0]
    assert (first.utr, first.payer, first.posted_on) == (
        "512345678901",
        "RAMESH K",
        date(2026, 10, 3),
    )
    assert first.row == 6


def test_period_covers_debits_too() -> None:
    statement = parse_statement("sbi.csv", csv_bytes(SBI_ROWS))

    assert (statement.period_start, statement.period_end) == (date(2026, 10, 1), date(2026, 10, 5))


def test_non_upi_credit_has_no_reference() -> None:
    statement = parse_statement("sbi.csv", csv_bytes(SBI_ROWS))

    assert statement.credits[1].utr is None


def test_hdfc_falls_back_to_zero_padded_reference_column() -> None:
    statement = parse_statement("hdfc.csv", csv_bytes(HDFC_ROWS))

    assert statement.bank == "hdfc"
    assert [c.utr for c in statement.credits] == ["610987654321", "700011112222"]


def test_amount_with_dr_cr_column_keeps_only_cr_rows() -> None:
    statement = parse_statement("kotak.csv", csv_bytes(KOTAK_DRCR_ROWS))

    assert [(c.utr, c.amount) for c in statement.credits] == [("512345678901", Decimal("1500.00"))]


def test_reads_xlsx_with_the_same_rules() -> None:
    statement = parse_statement("statement.xlsx", xlsx_bytes(SBI_ROWS))

    assert [c.utr for c in statement.credits] == ["512345678901", None]


def test_reads_windows_1252_csv() -> None:
    rows = [
        *SBI_ROWS[:4],
        [*SBI_ROWS[5][:2], "UPI/CR/512345678901/JOSÉ/SBIN/j@ok/x", "", "", "10", ""],
    ]

    statement = parse_statement("sbi.csv", csv_bytes(rows, encoding="cp1252"))

    assert statement.credits[0].payer == "JOSÉ"


@pytest.mark.parametrize(
    ("name", "data", "message"),
    [
        ("notes.pdf", b"%PDF-1.7", "CSV or Excel"),
        ("sbi.csv", csv_bytes([["hello", "world"], ["1", "2"]]), "columns"),
        ("sbi.xls", b"<html><table><tr><td>x</td></tr></table></html>", "Save it as CSV"),
        ("sbi.csv", csv_bytes(SBI_ROWS[:4]), "no transactions"),
    ],
)
def test_unusable_files_raise_a_helpful_error(name: str, data: bytes, message: str) -> None:
    with pytest.raises(StatementError, match=message):
        parse_statement(name, data)
