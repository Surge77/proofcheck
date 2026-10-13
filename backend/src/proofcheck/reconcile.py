"""Check each screenshot's claim against the money that actually arrived.

Pure and deterministic: no models run here. The bank statement is the source of
truth; a screenshot is only a claim about it. We never call anything "fake":
a missing UTR may simply not have settled yet, so the wording says what we saw.
"""

from collections.abc import Sequence
from decimal import Decimal

from proofcheck.models import Match, Receipt, Statement, StatementTxn


def format_inr(amount: Decimal) -> str:
    """₹ with Indian digit grouping: 245000 -> ₹2,45,000."""
    whole, _, fraction = f"{amount:.2f}".partition(".")
    head, tail = whole[:-3], whole[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    text = ",".join([*groups, tail])
    return f"₹{text}" if fraction == "00" else f"₹{text}.{fraction}"


def _found(receipt: Receipt, txn: StatementTxn) -> Match:
    if receipt.amount is None:
        note = f"Reference found: {format_inr(txn.amount)} arrived (screenshot amount unreadable)."
        return Match(receipt=receipt, credit=txn, status="verified", note=note)
    if receipt.amount == txn.amount:
        note = (
            f"{format_inr(txn.amount)} arrived on {txn.posted_on:%d %b} (statement row {txn.row})."
        )
        return Match(receipt=receipt, credit=txn, status="verified", note=note)
    note = (
        f"Screenshot says {format_inr(receipt.amount)} but the bank received "
        f"{format_inr(txn.amount)} for this reference."
    )
    return Match(receipt=receipt, credit=txn, status="amount_mismatch", note=note)


def _missing(receipt: Receipt, statement: Statement) -> Match:
    paid_on = receipt.paid_on
    if paid_on is not None and not statement.period_start <= paid_on <= statement.period_end:
        note = (
            f"Screenshot is dated {paid_on:%d %b %Y}, outside this statement "
            f"({statement.period_start:%d %b} - {statement.period_end:%d %b}). Check a newer one."
        )
        return Match(receipt=receipt, credit=None, status="outside_period", note=note)
    note = "This reference is not in the statement. It may be fake, or not settled yet."
    if receipt.status != "success":
        note += f" The screenshot itself shows the payment as {receipt.status}."
    return Match(receipt=receipt, credit=None, status="not_in_statement", note=note)


def reconcile(receipts: Sequence[Receipt], statement: Statement) -> list[Match]:
    """One Match per receipt, in upload order."""
    by_utr = {txn.utr: txn for txn in statement.credits if txn.utr}
    first_use: dict[str, str] = {}
    matches: list[Match] = []
    for receipt in receipts:
        if receipt.utr is None:
            note = "Could not read a UPI reference from this screenshot. Check it by hand."
            matches.append(Match(receipt=receipt, credit=None, status="unreadable", note=note))
            continue
        if receipt.utr in first_use:
            note = f"Same reference as {first_use[receipt.utr]}: one payment shown twice."
            matches.append(Match(receipt=receipt, credit=None, status="duplicate_proof", note=note))
            continue
        first_use[receipt.utr] = receipt.source
        txn = by_utr.get(receipt.utr)
        matches.append(_found(receipt, txn) if txn else _missing(receipt, statement))
    return matches
