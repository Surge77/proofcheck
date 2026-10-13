import io

import pytest
from PIL import Image

from proofcheck import imaging
from proofcheck.imaging import ImageError, load_image, to_png
from tests.factories import receipt_png


def test_loads_jpeg_and_converts_to_rgb() -> None:
    image = load_image(receipt_png(fmt="JPEG"))

    assert image.mode == "RGB"


def test_rejects_bytes_that_are_not_an_image() -> None:
    with pytest.raises(ImageError):
        load_image(b"definitely not a picture")


def test_rejects_images_over_the_pixel_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    # Shrink the budget instead of building a real 80-megapixel image in memory.
    monkeypatch.setattr(imaging, "MAX_PIXELS", 1000)

    with pytest.raises(ImageError):
        load_image(receipt_png(size=(100, 100)))


def test_to_png_shrinks_long_side_and_keeps_aspect_ratio() -> None:
    image = load_image(receipt_png(size=(1080, 2400)))

    shrunk = Image.open(io.BytesIO(to_png(image, max_side=1024)))

    assert shrunk.size == (461, 1024)


def test_to_png_never_upscales_small_images() -> None:
    image = load_image(receipt_png(size=(300, 200)))

    same = Image.open(io.BytesIO(to_png(image, max_side=1024)))

    assert same.size == (300, 200)
