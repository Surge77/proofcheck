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
