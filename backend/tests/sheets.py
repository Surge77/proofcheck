"""Build tiny statement files in memory: CSV text and real .xlsx bytes."""

import csv
import io
import zipfile
from collections.abc import Sequence
from xml.sax.saxutils import escape

Rows = Sequence[Sequence[str]]

SBI_ROWS: Rows = [
    ["Account Name", ":", "ASHA DESHPANDE"],
    ["Account Number", ":", "XXXXXXX1234"],
    [],
    ["Txn Date", "Value Date", "Description", "Ref No./Cheque No.", "Debit", "Credit", "Balance"],
    ["1 Oct 2026", "1 Oct 2026", "ATM WDL", "", "2,000.00", "", "10,000.00"],
    [
        "3 Oct 2026",
        "3 Oct 2026",
        "BY TRANSFER-UPI/CR/512345678901/RAMESH K/SBIN/ramesh@okaxis/Fees--",
        "",
        "",
        "1,500.00",
        "11,500.00",
    ],
    ["5 Oct 2026", "5 Oct 2026", "NEFT-ACME", "", "", "3,000.00", "14,500.00"],
    ["**Computer generated statement**"],
]

HDFC_ROWS: Rows = [
    ["HDFC BANK Ltd.", "Statement of account"],
    [
        "Date",
        "Narration",
        "Chq./Ref.No.",
        "Value Dt",
        "Withdrawal Amt.",
        "Deposit Amt.",
        "Closing Balance",
    ],
    [
        "02/10/26",
        "UPI-PRIYA S-priya@ybl-UTIB0000123-610987654321-OCT",
        "0000610987654321",
        "02/10/26",
        "",
        "2,000.00",
        "20,000.00",
    ],
    [
        "04/10/26",
        "UPI-NO REF-x@ybl-UTIB0000123-NOREF",
        "0000700011112222",
        "04/10/26",
        "",
        "850.00",
        "20,850.00",
    ],
]

KOTAK_DRCR_ROWS: Rows = [
    ["Sl. No.", "Transaction Date", "Description", "Chq / Ref No.", "Amount", "Dr / Cr", "Balance"],
    ["1", "06-10-2026", "UPI/RAMESH KUMAR/512345678901/fees", "", "1,500.00", "CR", "5,000.00"],
    ["2", "07-10-2026", "UPI/SHOP/998877665544/groceries", "", "300.00", "DR", "4,700.00"],
]


def csv_bytes(rows: Rows, encoding: str = "utf-8-sig") -> bytes:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return buffer.getvalue().encode(encoding)


def _cell(ref: str, value: str) -> str:
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def xlsx_bytes(rows: Rows) -> bytes:
    """A minimal valid .xlsx (inline strings only) built from the OOXML parts."""
    sheet_rows = []
    for r, row in enumerate(rows, start=1):
        cells = "".join(_cell(f"{chr(65 + c)}{r}", v) for c, v in enumerate(row) if v)
        sheet_rows.append(f'<row r="{r}">{cells}</row>')
    ns = "http://schemas.openxmlformats.org"
    parts = {
        "[Content_Types].xml": (
            f'<Types xmlns="{ns}/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            f'<Relationships xmlns="{ns}/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{ns}/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            f'<workbook xmlns="{ns}/spreadsheetml/2006/main" xmlns:r="{ns}/officeDocument/2006/relationships">'
            '<sheets><sheet name="Statement" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            f'<Relationships xmlns="{ns}/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{ns}/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>"
        ),
        "xl/worksheets/sheet1.xml": (
            f'<worksheet xmlns="{ns}/spreadsheetml/2006/main"><sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
        ),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, xml in parts.items():
            archive.writestr(name, xml)
    return buffer.getvalue()
