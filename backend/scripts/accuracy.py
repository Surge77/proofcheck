"""Measure extraction accuracy on real, hand-labelled screenshots.

Usage (from backend/):
    uv run python scripts/accuracy.py ../private/screenshots

The folder holds screenshots plus a `labels.csv` with columns
`file,utr,amount` written by hand. Leave `utr` empty for a screenshot that has
no readable reference. The folder lives under the git-ignored `private/`
directory: it is personal financial data and must never be committed.

Output masks references to their last 4 digits, so results can be shared.
"""

import argparse
import asyncio
import csv
import sys
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from proofcheck.extract import extract, fuse
from proofcheck.imaging import load_image, to_png
from proofcheck.models import Receipt
from proofcheck.ocr import read_lines

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class Label:
    utr: str | None
    amount: Decimal | None


@dataclass(frozen=True)
class Outcome:
    file: str
    label: Label
    fused: Receipt
    ocr_only: Receipt
    seconds: float


def _mask(utr: str | None) -> str:
    return f"********{utr[-4:]}" if utr else "-"


def _amount(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", "").strip()) if raw.strip() else None
    except InvalidOperation:
        sys.exit(f"labels.csv: bad amount {raw!r}")


def load_labels(folder: Path) -> dict[str, Label]:
    path = folder / "labels.csv"
    if not path.is_file():
        sys.exit(f"Missing {path}. Columns: file,utr,amount")
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            row["file"].strip(): Label(
                utr=row["utr"].replace(" ", "").strip() or None, amount=_amount(row["amount"])
            )
            for row in csv.DictReader(handle)
        }


async def measure(label: Label, path: Path) -> Outcome:
    data = path.read_bytes()
    started = time.perf_counter()
    fused = await extract(path.name, data)
    seconds = time.perf_counter() - started
    lines = read_lines(to_png(load_image(data), 2000))
    return Outcome(path.name, label, fused, fuse(path.name, lines, None), seconds)


def _rate(hits: int, total: int) -> str:
    return f"{hits}/{total} ({100 * hits / total:.0f}%)" if total else "n/a"


def report(outcomes: list[Outcome]) -> None:
    print(f"{'file':28} {'truth':>14} {'fused':>14} {'ocr-only':>14} conf  secs")
    for o in outcomes:
        mark = "ok " if o.fused.utr == o.label.utr else "BAD"
        print(
            f"{o.file[:28]:28} {_mask(o.label.utr):>14} {_mask(o.fused.utr):>14} "
            f"{_mask(o.ocr_only.utr):>14} {o.fused.confidence:4} {o.seconds:5.1f} {mark}"
        )

    total = len(outcomes)
    high = [o for o in outcomes if o.fused.confidence == "high"]
    print()
    print("UTR exact, fused     :", _rate(sum(o.fused.utr == o.label.utr for o in outcomes), total))
    print(
        "UTR exact, OCR only  :", _rate(sum(o.ocr_only.utr == o.label.utr for o in outcomes), total)
    )
    print(
        "Amount exact, fused  :",
        _rate(sum(o.fused.amount == o.label.amount for o in outcomes), total),
    )
    # The number that matters most: when we say "high confidence", how often are we right?
    print(
        "High-confidence right:",
        _rate(
            sum(o.fused.utr == o.label.utr and o.fused.amount == o.label.amount for o in high),
            len(high),
        ),
    )
    print("Marked high          :", _rate(len(high), total))
    if outcomes:
        print(f"Seconds per image    : {sum(o.seconds for o in outcomes) / total:.1f} (fused)")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure extraction accuracy on labelled screenshots."
    )
    parser.add_argument("folder", type=Path)
    folder = parser.parse_args().folder
    labels = load_labels(folder)
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    unlabelled = [p.name for p in paths if p.name not in labels]
    if unlabelled:
        sys.exit(f"No label for: {', '.join(unlabelled)}")
    outcomes = [await measure(labels[p.name], p) for p in paths]
    report(outcomes)


if __name__ == "__main__":
    asyncio.run(main())
