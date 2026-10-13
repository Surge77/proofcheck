"""Decode untrusted screenshot bytes into a normalised RGB image."""

import io

from PIL import Image, ImageOps, UnidentifiedImageError

# Phone screenshots are ~2-5 megapixels; a phone *photo* of a screen is ~12-24 MP.
# Anything bigger is not a payment proof, and at 40 MP the RGB copies made while
# decoding, rotating and resizing peak near half a gigabyte. Refused before decoding.
MAX_PIXELS = 25_000_000


class ImageError(ValueError):
    """The upload is not a usable image."""


def load_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        width, height = image.size  # read from the header only, pixels not decoded yet
        if width * height > MAX_PIXELS:
            raise ImageError(
                f"Image is too large to be a payment screenshot "
                f"(over {MAX_PIXELS // 1_000_000} megapixels)."
            )
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ImageError("File is not a readable image.") from error
    # Photos of a screen carry an EXIF rotation; apply it so text is upright for OCR.
    return ImageOps.exif_transpose(image).convert("RGB")


def to_png(image: Image.Image, max_side: int) -> bytes:
    """PNG bytes with the long side capped at `max_side` (never upscaled)."""
    resized = image.copy()
    resized.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    resized.save(buffer, "PNG")
    return buffer.getvalue()
