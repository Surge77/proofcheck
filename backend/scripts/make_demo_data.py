"""Generate the demo data set in ../samples (fictional people, fictional app).

Usage (from backend/):
    uv run python scripts/make_demo_data.py

Story: Asha runs a tuition class and collects October fees by UPI. Parents send
screenshots on WhatsApp. The set covers every result ProofCheck can give.

The screenshots are deliberately NOT convincing copies of any real payment app:
a fictional "Demo Pay" brand and a large SAMPLE watermark. A tool that checks
for fake screenshots must not ship a kit for making them.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
SIZE = (720, 1280)


@dataclass(frozen=True)
class Shot:
    file: str
    status_line: str
    amount: str
    payer: str
    utr: str
    when: str


SHOTS = [
    Shot(
        "01-ramesh.png", "Payment Successful", "1,500", "Ramesh Kumar", "512345678901", "3 Oct 2026"
    ),
    Shot("02-priya.png", "Payment Successful", "2,000", "Priya Shah", "610987654321", "4 Oct 2026"),
    Shot(
        "03-sunita.png",
        "Payment Successful",
        "1,500",
        "Sunita Sharma",
        "704512398765",
        "5 Oct 2026",
    ),
    # Not in the statement: this money never arrived.
    Shot(
        "04-vikram.png", "Payment Successful", "1,500", "Vikram Rao", "823456789012", "6 Oct 2026"
    ),
    # Priya's proof sent again for a second child.
    Shot(
        "05-priya-again.png",
        "Payment Successful",
        "2,000",
        "Priya Shah",
        "610987654321",
        "4 Oct 2026",
    ),
    # Screenshot edited from 200 to 2,000.
    Shot("06-meera.png", "Payment Successful", "2,000", "Meera Iyer", "934567890123", "7 Oct 2026"),
    # A failed payment presented as proof.
    Shot("07-kabir.png", "Payment Failed", "1,000", "Kabir Singh", "745678901234", "8 Oct 2026"),
    # Paid after the statement was downloaded.
    Shot(
        "08-arjun.png", "Payment Successful", "1,500", "Arjun Mehta", "856789012345", "14 Oct 2026"
    ),
]

STATEMENT_ROWS = [
    ["State Bank of India"],
    ["Account Name", ":", "ASHA DESHPANDE (DEMO)"],
    ["Account Number", ":", "XXXXXXX0000"],
    ["Statement From", ":", "1 Oct 2026 to 10 Oct 2026"],
    [],
    ["Txn Date", "Value Date", "Description", "Ref No./Cheque No.", "Debit", "Credit", "Balance"],
    ["1 Oct 2026", "1 Oct 2026", "OPENING BALANCE", "", "", "", "12,000.00"],
    ["2 Oct 2026", "2 Oct 2026", "ATM WDL 0001", "", "2,000.00", "", "10,000.00"],
    [
        "3 Oct 2026",
        "3 Oct 2026",
        "BY TRANSFER-UPI/CR/512345678901/RAMESH K/SBIN/ramesh.k@okaxis/fees--",
        "",
        "",
        "1,500.00",
        "11,500.00",
    ],
    [
        "4 Oct 2026",
        "4 Oct 2026",
        "BY TRANSFER-UPI/CR/610987654321/PRIYA SHAH/HDFC/priya@ybl/oct--",
        "",
        "",
        "2,000.00",
        "13,500.00",
    ],
    [
        "5 Oct 2026",
        "5 Oct 2026",
        "BY TRANSFER-UPI/CR/704512398765/S SHARMA/ICIC/sunita.s@okicici/rohan--",
        "",
        "",
        "1,500.00",
        "15,000.00",
    ],
    [
        "6 Oct 2026",
        "6 Oct 2026",
        "BY TRANSFER-UPI/CR/918273645501/NEHA JOSHI/UTIB/neha@paytm/tara fees--",
        "",
        "",
        "1,500.00",
        "16,500.00",
    ],
    [
        "7 Oct 2026",
        "7 Oct 2026",
        "BY TRANSFER-UPI/CR/934567890123/MEERA I/SBIN/meera@oksbi/fees--",
        "",
        "",
        "200.00",
        "16,700.00",
    ],
    [
        "9 Oct 2026",
        "9 Oct 2026",
        "UPI/DR/556677889900/STATIONERY MART/SBIN/shop@ybl/--",
        "",
        "450.00",
        "",
        "16,250.00",
    ],
    ["10 Oct 2026", "10 Oct 2026", "ELECTRICITY BILL", "", "1,100.00", "", "15,150.00"],
]

ROSTER_ROWS = [
    ["name", "amount", "payer", "upi_id"],
    ["Aarav Kumar", "1500", "Ramesh Kumar", ""],
    ["Diya Shah", "2000", "Priya Shah", ""],
    ["Rohan Sharma", "1500", "Sunita Sharma", "sunita.s@okicici"],
    ["Tara Joshi", "1500", "Neha Joshi", ""],
    ["Meera Iyer", "2000", "", ""],
    ["Kabir Singh", "1000", "", ""],
    ["Ishaan Rao", "1500", "Vikram Rao", ""],
    ["Arjun Mehta", "1500", "", ""],
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _watermark(image: Image.Image) -> Image.Image:
    layer = Image.new("RGBA", (1100, 140), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(
        (20, 30), "SAMPLE - NOT A REAL PAYMENT", fill=(200, 0, 0, 90), font=_font(64)
    )
    rotated = layer.rotate(35, expand=True)
    base = image.convert("RGBA")
    base.alpha_composite(rotated, (-120, 640))
    return base.convert("RGB")


def render(shot: Shot) -> Image.Image:
    image = Image.new("RGB", SIZE, "white")
    draw = ImageDraw.Draw(image)
    is_failed = "Failed" in shot.status_line
    draw.rectangle((0, 0, SIZE[0], 120), fill=(40, 40, 40))
    draw.text((40, 38), "Demo Pay (sample app)", fill="white", font=_font(38))
    draw.ellipse((300, 180, 420, 300), fill=(185, 28, 28) if is_failed else (21, 128, 61))
    draw.text((320, 196), "x" if is_failed else "OK", fill="white", font=_font(56))
    rows = [
        (330, shot.status_line, 46),
        (420, f"₹{shot.amount}", 72),
        (540, "Paid to Asha Tuition Classes", 32),
        (600, f"From: {shot.payer}", 32),
        (700, "UPI transaction ID", 28),
        (745, f"{shot.utr[:4]} {shot.utr[4:8]} {shot.utr[8:]}", 34),
        (840, shot.when, 30),
    ]
    for y, text, size in rows:
        font = _font(size)
        width = draw.textlength(text, font=font)
        draw.text(((SIZE[0] - width) / 2, y), text, fill=(15, 23, 42), font=font)
    footer = "SAMPLE DATA - NOT A REAL PAYMENT"
    font = _font(30)
    draw.text(
        ((SIZE[0] - draw.textlength(footer, font=font)) / 2, 1210),
        footer,
        fill=(185, 28, 28),
        font=font,
    )
    return _watermark(image)


def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def main() -> None:
    shots_dir = SAMPLES / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    for shot in SHOTS:
        render(shot).save(shots_dir / shot.file)
    write_csv(SAMPLES / "statement-sbi.csv", STATEMENT_ROWS)
    write_csv(SAMPLES / "roster.csv", ROSTER_ROWS)
    print(f"Wrote {len(SHOTS)} screenshots, a statement and a roster to {SAMPLES}")


if __name__ == "__main__":
    main()
