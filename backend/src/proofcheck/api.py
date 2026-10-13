"""HTTP API: upload screenshots + a statement (+ optional roster), stream back a report.

Nothing uploaded is written to disk or logged. Files live in memory for the
length of one request and are gone when it ends.
"""

import json
from collections.abc import AsyncIterator
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from proofcheck import vision
from proofcheck.config import get_settings
from proofcheck.extract import extract
from proofcheck.imaging import ImageError
from proofcheck.models import Receipt, RosterEntry, Statement
from proofcheck.report import build_report, unreadable_receipt
from proofcheck.roster import RosterError, parse_roster
from proofcheck.statements import StatementError, parse_statement

MAX_SCREENSHOTS = 60
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_STATEMENT_BYTES = 5 * 1024 * 1024
MAX_ROSTER_BYTES = 256 * 1024
MAX_NAME_LENGTH = 120

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "vision": await vision.is_available(),
        "model": get_settings().vision_model,
    }


def _safe_name(raw: str | None) -> str:
    # The name is only ever displayed, never used as a path, but keep it tidy anyway.
    name = PureWindowsPath(PurePosixPath(raw or "upload").name).name
    return name[-MAX_NAME_LENGTH:] or "upload"


async def _read(upload: UploadFile, limit: int, what: str) -> bytes:
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"The {what} is larger than {limit // 1024} KB.")
    return data


async def _statement(upload: UploadFile) -> Statement:
    data = await _read(upload, MAX_STATEMENT_BYTES, "bank statement")
    try:
        return parse_statement(_safe_name(upload.filename), data)
    except StatementError as error:
        raise HTTPException(422, str(error)) from error


async def _roster(upload: UploadFile | None) -> tuple[RosterEntry, ...] | None:
    if upload is None:
        return None
    try:
        return parse_roster(await _read(upload, MAX_ROSTER_BYTES, "roster"))
    except RosterError as error:
        raise HTTPException(422, str(error)) from error


async def _receipt(upload: UploadFile) -> Receipt:
    source = _safe_name(upload.filename)
    if not (upload.content_type or "").startswith("image/"):
        return unreadable_receipt(source, "This file is not an image.")
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        return unreadable_receipt(source, "Image is larger than 8 MB.")
    try:
        return await extract(source, data)
    except ImageError as error:
        return unreadable_receipt(source, str(error))


def _line(event: dict[str, object]) -> bytes:
    return (json.dumps(event, default=str) + "\n").encode()


@router.post("/check")
async def check(
    screenshots: Annotated[list[UploadFile], File()],
    statement: Annotated[UploadFile, File()],
    roster: Annotated[UploadFile | None, File()] = None,
) -> StreamingResponse:
    if len(screenshots) > MAX_SCREENSHOTS:
        raise HTTPException(413, f"Upload at most {MAX_SCREENSHOTS} screenshots at a time.")
    # Validate the cheap inputs first, so a bad statement fails before minutes of OCR.
    parsed_statement = await _statement(statement)
    entries = await _roster(roster)

    async def stream() -> AsyncIterator[bytes]:
        receipts: list[Receipt] = []
        for upload in screenshots:
            # One at a time on purpose: the GPU holds one vision model and can't run two.
            receipts.append(await _receipt(upload))
            yield _line(
                {
                    "type": "progress",
                    "done": len(receipts),
                    "total": len(screenshots),
                    "receipt": receipts[-1].model_dump(mode="json"),
                }
            )
        report = build_report(receipts, parsed_statement, entries)
        yield _line({"type": "report", "report": report.model_dump(mode="json")})

    return StreamingResponse(stream(), media_type="application/x-ndjson")
