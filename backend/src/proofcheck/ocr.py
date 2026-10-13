"""Local text recognition with RapidOCR (PP-OCR models on onnxruntime).

The models ship inside the `rapidocr` wheel, so reading a screenshot never
touches the network.
"""

import logging
from functools import lru_cache
from typing import Any, Protocol

# RapidOCR logs every model path at INFO on start-up; that is noise for users.
logging.getLogger("RapidOCR").setLevel(logging.WARNING)


class LineReader(Protocol):
    def __call__(self, image_png: bytes, /) -> list[str]: ...


@lru_cache(maxsize=1)
def _engine() -> Any:
    # Imported lazily: loading the models takes ~1.5 s and tests that stub OCR shouldn't pay it.
    from rapidocr import RapidOCR

    return RapidOCR()


def read_lines(image_png: bytes) -> list[str]:
    """Text lines in reading order. Empty list when the image has no text."""
    result = _engine()(image_png)
    return [str(text) for text in (result.txts or ())]
