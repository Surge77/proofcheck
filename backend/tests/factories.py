"""Test data builders. Images are drawn on the fly so no binary fixtures are committed."""

import io
from collections.abc import Sequence

from PIL import Image, ImageDraw, ImageFont

DEFAULT_LINES = ("Paid to Ramesh Kumar", "₹1,500", "UPI transaction ID", "5123 4567 8901")


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)  # Linux CI
    except OSError:
        try:
            return ImageFont.truetype("arial.ttf", size)  # Windows
        except OSError:
            return ImageFont.load_default(size)


def receipt_png(
    lines: Sequence[str] = DEFAULT_LINES, size: tuple[int, int] = (720, 400), fmt: str = "PNG"
) -> bytes:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    font = _font(34)
    for row, text in enumerate(lines):
        draw.text((40, 40 + row * 80), text, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, fmt)
    return buffer.getvalue()
