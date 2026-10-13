"""Who was supposed to pay, and who actually did.

The roster is a small CSV the user keeps (name, amount, optional payer names and
UPI id). Money in the statement is assigned to a person by UPI id first, then
by name. A credit that could belong to two people is never guessed.
"""

import csv
import io
import re
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from proofcheck.models import Match, RosterEntry, RosterLine, Statement, StatementTxn
from proofcheck.reconcile import format_inr

_HONORIFICS = {"MR", "MRS", "MS", "MISS", "DR", "SMT", "SHRI", "SRI", "KUM", "MASTER"}
# A one-letter typo in a 5+ letter name ("Priyaa" vs "Priya") still matches.
_TYPO_RATIO = 0.85
_NAME_COLUMNS = ("name", "student", "member")
_AMOUNT_COLUMNS = ("amount", "due", "fees", "fee")
_PAYER_COLUMNS = ("payer", "payers", "paid by")
_UPI_COLUMNS = ("upi_id", "upi", "upi id", "vpa")


class RosterError(ValueError):
    """The roster CSV can't be used; the message is safe to show the user."""


def _tokens(name: str) -> list[str]:
    words = re.sub(r"[^A-Za-z]+", " ", name).upper().split()
    return [w for w in words if w not in _HONORIFICS]


def _token_match(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) == 1 or len(b) == 1:
        return a[0] == b[0]
    return min(len(a), len(b)) >= 4 and SequenceMatcher(None, a, b).ratio() >= _TYPO_RATIO


def names_match(a: str, b: str) -> bool:
    """True when every word of the shorter name matches a word of the longer one.

    Initials match a word with that first letter (banks print "RAMESH K"), but at
    least one full word must match: "K" alone is never a person.
    """
    short, long = sorted((_tokens(a), _tokens(b)), key=len)
    if not short:
        return False
    if not all(any(_token_match(t, u) for u in long) for t in short):
        return False
    return any(len(t) > 1 and any(len(u) > 1 and _token_match(t, u) for u in long) for t in short)


def _column(header: Sequence[str], options: tuple[str, ...]) -> str | None:
    return next((h for h in header if h in options), None)


def parse_roster(data: bytes) -> tuple[RosterEntry, ...]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip().lower() for h in reader.fieldnames or []]
    reader.fieldnames = header
    name_col, amount_col = _column(header, _NAME_COLUMNS), _column(header, _AMOUNT_COLUMNS)
    if name_col is None or amount_col is None:
        raise RosterError("The roster needs a 'name' column and an 'amount' column.")
    payer_col, upi_col = _column(header, _PAYER_COLUMNS), _column(header, _UPI_COLUMNS)

    entries: list[RosterEntry] = []
    for row_number, row in enumerate(reader, start=2):
        name = (row.get(name_col) or "").strip()
        try:
            due = Decimal((row.get(amount_col) or "").replace(",", "").strip())
        except InvalidOperation:
            due = Decimal(0)
        if not name or due <= 0:
            raise RosterError(f"Roster row {row_number}: needs a name and an amount above zero.")
        payers = tuple(p.strip() for p in (row.get(payer_col or "") or "").split(";") if p.strip())
        upi_id = (row.get(upi_col or "") or "").strip().lower() or None
        entries.append(RosterEntry(name=name, due=due, payers=payers, upi_id=upi_id))
    if not entries:
        raise RosterError("The roster lists no one.")
    return tuple(entries)


def _owners(entries: Sequence[RosterEntry], payer: str | None, vpa: str | None) -> list[int]:
    if vpa:
        by_upi = [i for i, e in enumerate(entries) if e.upi_id == vpa.lower()]
        if by_upi:
            return by_upi
    if not payer:
        return []
    return [
        i
        for i, e in enumerate(entries)
        if any(names_match(payer, candidate) for candidate in (e.name, *e.payers))
    ]


def _line(entry: RosterEntry, credits: list[StatementTxn], has_claim: bool) -> RosterLine:
    received = sum((c.amount for c in credits), Decimal(0))
    rows = tuple(c.row for c in credits)
    if received >= entry.due:
        status, note = "paid", f"Received {format_inr(received)}."
    elif received > 0:
        short = format_inr(entry.due - received)
        status, note = "partial", f"Received {format_inr(received)}, {short} still due."
    elif has_claim:
        status, note = "claimed", "Sent a screenshot, but no matching money in the statement."
    else:
        status, note = "unpaid", "No payment found."
    return RosterLine(
        name=entry.name, due=entry.due, received=received, status=status, rows=rows, note=note
    )


def summarise(
    entries: Sequence[RosterEntry], statement: Statement, matches: Sequence[Match]
) -> list[RosterLine]:
    """One line per roster person. Credits count even without a screenshot."""
    screenshot_payer = {m.credit.row: m.receipt.payer for m in matches if m.credit is not None}
    credits: list[list[StatementTxn]] = [[] for _ in entries]
    for txn in statement.credits:
        owners = _owners(entries, txn.payer, txn.vpa)
        if not owners and txn.row in screenshot_payer:
            owners = _owners(entries, screenshot_payer[txn.row], None)
        if len(owners) == 1:  # ambiguous credits are left out rather than guessed
            credits[owners[0]].append(txn)

    claimed: set[int] = set()
    for match in matches:
        if match.credit is None and match.status != "duplicate_proof":
            owners = _owners(entries, match.receipt.payer, None)
            if len(owners) == 1:
                claimed.add(owners[0])
    return [_line(e, credits[i], i in claimed) for i, e in enumerate(entries)]
