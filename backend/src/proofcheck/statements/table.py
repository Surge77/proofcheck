"""Turn a bank statement file into rows, find the header, and build credit records."""

import csv
import io
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import PurePath

from python_calamine import CalamineError, CalamineWorkbook

from proofcheck.models import Statement, StatementTxn
from proofcheck.statements.banks import detect_bank, parse_narration, utr_from_ref
from proofcheck.statements.values import parse_amount, parse_date

Row = list[object]

SPREADSHEET_SUFFIXES = {".xls", ".xlsx", ".xlsm", ".ods"}
ZIP_SUFFIXES = {".xlsx", ".xlsm", ".ods"}  # .xls is an uncompressed OLE file
# Bank preambles (name, address, account number, filters) run to ~20 rows.
HEADER_SEARCH_ROWS = 40
# A year of daily transactions is a few thousand rows; these limits only stop abuse.
# The upload is capped at 5 MB, but a zipped spreadsheet can expand to gigabytes.
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_ROWS = 100_000

_ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("txn date", "transaction date", "tran date", "date", "posting date", "value date"),
    "narration": (
        "narration",
        "description",
        "transaction remarks",
        "particulars",
        "remarks",
        "details",
        "transaction details",
    ),
    "credit": ("deposit amt.", "deposit amount", "credit", "credit amount", "deposit", "deposits"),
    "ref": ("chq./ref.no.", "ref no./cheque no.", "chq / ref no.", "cheque number", "ref no."),
    "amount": ("amount", "transaction amount"),
    "drcr": ("dr / cr", "dr/cr", "cr/dr", "type"),
}


class StatementError(ValueError):
    """The file can't be read as a bank statement; the message is safe to show the user."""


@dataclass(frozen=True)
class Columns:
    date: int
    narration: int
    credit: int | None
    ref: int | None
    amount: int | None
    drcr: int | None


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _check_zip_size(data: bytes) -> None:
    """Refuse .xlsx/.ods files that would decompress into far more than any real statement."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            expanded = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile:
        return  # not a zip after all; calamine will report the real problem
    if expanded > MAX_UNCOMPRESSED_BYTES:
        raise StatementError("This spreadsheet is too large to be a bank statement.")


def _read_csv(data: bytes) -> list[Row]:
    try:
        return [list(row) for row in csv.reader(io.StringIO(_decode(data)))]
    except csv.Error as error:  # e.g. a single field over the csv module's 128 KB limit
        raise StatementError("This CSV could not be read. Re-export it from your bank.") from error


def _read_spreadsheet(suffix: str, data: bytes) -> list[Row]:
    if data.lstrip()[:1] == b"<":
        # Some net-banking sites save an HTML page with an .xls name.
        raise StatementError("This .xls is really a web page. Save it as CSV and upload that.")
    if suffix in ZIP_SUFFIXES:
        _check_zip_size(data)
    try:
        workbook = CalamineWorkbook.from_filelike(io.BytesIO(data))
        return [list(row) for row in workbook.get_sheet_by_index(0).to_python()]
    except CalamineError as error:
        raise StatementError(
            "Could not open this spreadsheet. Save it as CSV and retry."
        ) from error


def read_rows(filename: str, data: bytes) -> list[Row]:
    suffix = PurePath(filename).suffix.lower()
    if suffix == ".csv":
        rows = _read_csv(data)
    elif suffix in SPREADSHEET_SUFFIXES:
        rows = _read_spreadsheet(suffix, data)
    else:
        raise StatementError("Upload the statement as a CSV or Excel file (.csv, .xls, .xlsx).")
    if len(rows) > MAX_ROWS:
        raise StatementError(f"The statement has more than {MAX_ROWS:,} rows. Export one month.")
    return rows


def _normalise(cell: object) -> str:
    return " ".join(str(cell).split()).lower() if cell is not None else ""


def _find(header: Sequence[str], aliases: tuple[str, ...]) -> int | None:
    for alias in aliases:  # alias order is priority order ("txn date" before "value date")
        for index, cell in enumerate(header):
            if cell == alias or cell.startswith(alias):
                return index
    return None


def find_columns(rows: Sequence[Row]) -> tuple[int, Columns, list[str]]:
    for index, row in enumerate(rows[:HEADER_SEARCH_ROWS]):
        header = [_normalise(cell) for cell in row]
        found = {key: _find(header, aliases) for key, aliases in _ALIASES.items()}
        date_col, narration_col = found["date"], found["narration"]
        has_money = found["credit"] is not None or (
            found["amount"] is not None and found["drcr"] is not None
        )
        if date_col is not None and narration_col is not None and has_money:
            columns = Columns(
                date_col,
                narration_col,
                found["credit"],
                found["ref"],
                found["amount"],
                found["drcr"],
            )
            return index, columns, [str(cell) for cell in row]
    raise StatementError(
        "Could not find the Date, Narration/Description and Credit/Deposit columns."
    )


def _cell(row: Row, index: int | None) -> object:
    return row[index] if index is not None and index < len(row) else None


def _credit(row: Row, cols: Columns) -> object:
    if cols.credit is not None:
        return _cell(row, cols.credit)
    marker = _normalise(_cell(row, cols.drcr))
    return _cell(row, cols.amount) if marker.startswith("cr") else None


def parse_statement(filename: str, data: bytes) -> Statement:
    rows = read_rows(filename, data)
    header_index, cols, header = find_columns(rows)
    bank = detect_bank(header)
    dates: list[date] = []
    credits: list[StatementTxn] = []
    for offset, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        posted_on = parse_date(_cell(row, cols.date))
        if posted_on is None:  # footers, separators, "Opening Balance" lines
            continue
        dates.append(posted_on)
        amount = parse_amount(_credit(row, cols))
        if amount is None:
            continue
        narration = str(_cell(row, cols.narration) or "").strip()
        info = parse_narration(narration, bank)
        credits.append(
            StatementTxn(
                row=offset,
                posted_on=posted_on,
                amount=amount,
                utr=info.utr or utr_from_ref(_cell(row, cols.ref)),
                payer=info.payer,
                vpa=info.vpa,
                narration=narration,
            )
        )
    if not dates:
        raise StatementError("The statement has no transactions in it.")
    return Statement(
        bank=bank, credits=tuple(credits), period_start=min(dates), period_end=max(dates)
    )
