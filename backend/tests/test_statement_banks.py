import pytest

from proofcheck.statements.banks import Bank, detect_bank, parse_narration, utr_from_ref


@pytest.mark.parametrize(
    ("bank", "narration", "utr", "payer", "vpa"),
    [
        (
            "sbi",
            "BY TRANSFER-UPI/CR/512345678901/RAMESH K/SBIN/ramesh@okaxis/Payment--",
            "512345678901",
            "RAMESH K",
            "ramesh@okaxis",
        ),
        (
            "hdfc",
            "UPI-RAMESH KUMAR-ramesh.k@okhdfcbank-SBIN0001234-512345678901-FEES OCT",
            "512345678901",
            "RAMESH KUMAR",
            "ramesh.k@okhdfcbank",
        ),
        (
            "icici",
            "UPI/512345678901/Fees October/ramesh@ybl/State Bank Of I/ICI0a1b2c3d",
            "512345678901",
            None,
            "ramesh@ybl",
        ),
        (
            "kotak",
            "UPI/RAMESH KUMAR/512345678901/tuition fees",
            "512345678901",
            "RAMESH KUMAR",
            None,
        ),
        (
            "generic",
            "IMPS P2A 512345678901 Ramesh",
            "512345678901",
            None,
            None,
        ),
    ],
)
def test_reads_reference_payer_and_upi_id_per_bank(
    bank: Bank, narration: str, utr: str, payer: str | None, vpa: str | None
) -> None:
    info = parse_narration(narration, bank)

    assert (info.utr, info.payer, info.vpa) == (utr, payer, vpa)


def test_narration_without_twelve_digit_reference_has_no_utr() -> None:
    assert parse_narration("NEFT-HDFCN52026100312-ACME LTD", "hdfc").utr is None


def test_prefers_a_whole_twelve_digit_segment_over_digits_inside_text() -> None:
    narration = "UPI/CR/512345678901/RAMESH/SBIN/9876543210@ybl/ref 998877665544x"
    assert parse_narration(narration, "sbi").utr == "512345678901"


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("0000512345678901", "512345678901"),  # HDFC pads the reference to 16 digits
        ("512345678901", "512345678901"),
        ("UPI-512345678901", None),
        ("000000001234", None),
        ("", None),
        (None, None),
    ],
)
def test_reference_column_with_zero_padding(ref: object, expected: str | None) -> None:
    assert utr_from_ref(ref) == expected


@pytest.mark.parametrize(
    ("header", "bank"),
    [
        (["Txn Date", "Value Date", "Description", "Ref No./Cheque No.", "Debit", "Credit"], "sbi"),
        (["Date", "Narration", "Chq./Ref.No.", "Value Dt", "Deposit Amt."], "hdfc"),
        (["S No.", "Transaction Date", "Transaction Remarks", "Deposit Amount (INR )"], "icici"),
        (["Sl. No.", "Transaction Date", "Description", "Chq / Ref No.", "Credit"], "kotak"),
        (["Date", "Details", "Credit"], "generic"),
    ],
)
def test_detects_bank_from_header_row(header: list[str], bank: Bank) -> None:
    assert detect_bank(header) == bank
