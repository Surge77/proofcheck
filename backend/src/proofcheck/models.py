"""Domain records shared across extraction, statement parsing and reconciliation."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from proofcheck.vision import PaymentStatus, UpiApp

Confidence = Literal["high", "low"]
ExtractionMethod = Literal["ocr+vision", "ocr_only"]


class Receipt(BaseModel):
    """What one payment screenshot claims."""

    model_config = ConfigDict(frozen=True)

    source: str  # the uploaded file name, so the user can find the screenshot again
    utr: str | None
    amount: Decimal | None
    payer: str | None
    paid_on: date | None
    app: UpiApp | None
    status: PaymentStatus
    method: ExtractionMethod
    # "high" only when OCR and the vision model independently agree on UTR and amount.
    confidence: Confidence
    # Plain-language reasons shown to the user when confidence is low.
    issues: tuple[str, ...] = ()


class StatementTxn(BaseModel):
    """One credit (money in) from the bank statement."""

    model_config = ConfigDict(frozen=True)

    row: int  # 1-based row in the uploaded file, so the user can find it
    posted_on: date
    amount: Decimal
    utr: str | None
    payer: str | None
    vpa: str | None
    narration: str


class Statement(BaseModel):
    model_config = ConfigDict(frozen=True)

    bank: str
    credits: tuple[StatementTxn, ...]
    # Dates covered by the file (all rows, not just credits); screenshots outside it are flagged.
    period_start: date
    period_end: date
