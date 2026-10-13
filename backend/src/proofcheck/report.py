"""Assemble the final report the UI renders: matches, counts and the roster."""

from collections import Counter
from collections.abc import Sequence
from datetime import date

from pydantic import BaseModel, ConfigDict

from proofcheck.models import Match, MatchStatus, Receipt, RosterEntry, RosterLine, Statement
from proofcheck.reconcile import reconcile
from proofcheck.roster import summarise


class Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    bank: str
    period_start: date
    period_end: date
    matches: list[Match]
    counts: dict[MatchStatus, int]
    roster: list[RosterLine] | None


def unreadable_receipt(source: str, reason: str) -> Receipt:
    """A placeholder for an upload we couldn't read at all, so it still shows up as a row."""
    return Receipt(
        source=source,
        utr=None,
        amount=None,
        payer=None,
        paid_on=None,
        app=None,
        status="unclear",
        method="ocr_only",
        confidence="low",
        issues=(reason,),
    )


def build_report(
    receipts: Sequence[Receipt], statement: Statement, roster: Sequence[RosterEntry] | None
) -> Report:
    matches = reconcile(receipts, statement)
    return Report(
        bank=statement.bank,
        period_start=statement.period_start,
        period_end=statement.period_end,
        matches=matches,
        counts=dict(Counter(m.status for m in matches)),
        roster=summarise(roster, statement, matches) if roster else None,
    )
