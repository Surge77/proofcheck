from proofcheck.candidates import utr_candidates
from proofcheck.imaging import load_image, to_png
from proofcheck.ocr import read_lines
from tests.factories import receipt_png


def test_reads_reference_and_amount_from_a_rendered_receipt() -> None:
    # Runs the real RapidOCR model: it ships inside the wheel, so this works offline and in CI.
    png = to_png(load_image(receipt_png()), max_side=2000)

    lines = read_lines(png)

    assert [c.value for c in utr_candidates(lines)] == ["512345678901"]
    assert any("1,500" in line or "1500" in line for line in lines)


def test_blank_image_gives_no_lines() -> None:
    png = to_png(load_image(receipt_png(lines=())), max_side=2000)

    assert read_lines(png) == []
