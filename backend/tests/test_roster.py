from datetime import date
from decimal import Decimal

import pytest

from proofcheck.models import Match, Receipt, RosterLine, Statement, StatementTxn
from proofcheck.roster import RosterError, names_match, parse_roster, summarise


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("RAMESH K", "Ramesh Kumar", True),  # banks truncate surnames to an initial
        ("Mr. Ramesh Kumar", "RAMESH KUMAR", True),
        ("SMT SUNITA SHARMA", "Sunita Sharma", True),
        ("Priyaa Shah", "Priya Shah", True),  # one-letter typo
        ("Ramesh Sharma", "Ramesh Kumar", False),
        ("K", "Kumar", False),  # an initial alone is never enough
        ("", "Ramesh", False),
    ],
)
def test_names_match(a: str, b: str, expected: bool) -> None:
    assert names_match(a, b) is expected


def test_parses_roster_with_optional_payer_aliases_and_upi_id() -> None:
    data = (
        b"name,amount,payer,upi_id\n"
        b"Aarav,1500,Sunita Sharma;Raj Sharma,sunita@okaxis\n"
        b"Meera,2000,,\n"
    )

    aarav, meera = parse_roster(data)

    assert aarav.payers == ("Sunita Sharma", "Raj Sharma")
    assert aarav.upi_id == "sunita@okaxis"
    assert meera.due == Decimal("2000")
    assert meera.payers == ()


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"who,how much\nA,1\n", "name"),
        (b"name,amount\n,1500\n", "row 2"),
        (b"name,amount\nAarav,abc\n", "row 2"),
        (b"name,amount\n", "no one"),
    ],
)
def test_roster_errors_name_the_problem(data: bytes, message: str) -> None:
    with pytest.raises(RosterError, match=message):
        parse_roster(data)


def credit(row: int, amount: str, payer: str | None, vpa: str | None = None) -> StatementTxn:
    return StatementTxn(
        row=row,
        posted_on=date(2026, 10, 3),
        amount=Decimal(amount),
        utr=f"5123456789{row:02d}",
        payer=payer,
        vpa=vpa,
        narration="",
    )


def statement(*credits: StatementTxn) -> Statement:
    return Statement(
        bank="sbi", credits=credits, period_start=date(2026, 10, 1), period_end=date(2026, 10, 10)
    )


def unverified_claim(payer: str) -> Match:
    receipt = Receipt(
        source="claim.png",
        utr="999999999999",
        amount=Decimal("1500"),
        payer=payer,
        paid_on=date(2026, 10, 4),
        app="gpay",
        status="success",
        method="ocr+vision",
        confidence="high",
    )
    return Match(receipt=receipt, credit=None, status="not_in_statement", note="")


ROSTER = (
    b"name,amount,payer,upi_id\n"
    b"Aarav,1500,Sunita Sharma,sunita@okaxis\n"
    b"Meera Iyer,2000,,\n"
    b"Kabir,1000,,\n"
)


def by_name(lines: list[RosterLine]) -> dict[str, RosterLine]:
    return {line.name: line for line in lines}


def test_paid_by_upi_id_partial_by_name_and_unpaid() -> None:
    lines = by_name(
        summarise(
            parse_roster(ROSTER),
            statement(credit(5, "1500", "S SHARMA", "sunita@okaxis"), credit(6, "1000", "MEERA I")),
            [],
        )
    )

    assert lines["Aarav"].status == "paid"
    assert lines["Meera Iyer"].status == "partial"
    assert lines["Meera Iyer"].received == Decimal("1000")
    assert lines["Kabir"].status == "unpaid"


def test_claim_without_money_is_claimed_not_paid() -> None:
    lines = by_name(summarise(parse_roster(ROSTER), statement(), [unverified_claim("Kabir")]))

    assert lines["Kabir"].status == "claimed"


def test_credit_matching_two_people_is_not_assigned() -> None:
    roster = parse_roster(b"name,amount\nRamesh Kumar,500\nRamesh Kulkarni,500\n")

    lines = summarise(roster, statement(credit(5, "500", "RAMESH K")), [])

    assert [line.status for line in lines] == ["unpaid", "unpaid"]
