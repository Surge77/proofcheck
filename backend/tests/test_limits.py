import tempfile

import pytest
from fastapi.testclient import TestClient

from proofcheck import api, limits
from proofcheck.main import create_app
from proofcheck.models import Receipt
from tests.factories import receipt_png
from tests.sheets import SBI_ROWS, csv_bytes


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def fake_extract(source: str, _data: bytes) -> Receipt:
        return Receipt(
            source=source,
            utr=None,
            amount=None,
            payer=None,
            paid_on=None,
            app=None,
            status="unclear",
            method="ocr_only",
            confidence="low",
        )

    monkeypatch.setattr(api, "extract", fake_extract)
    return TestClient(create_app(), base_url="http://127.0.0.1")


def upload(client: TestClient, image: bytes) -> int:
    files = [
        ("screenshots", ("big.png", image, "image/png")),
        ("statement", ("sbi.csv", csv_bytes(SBI_ROWS), "text/csv")),
    ]
    return client.post("/api/check", files=files).status_code


def test_uploads_above_one_megabyte_never_touch_disk(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # SpooledTemporaryFile.rollover() creates its real file through tempfile.TemporaryFile.
    def no_disk(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("an upload was spooled to a temporary file on disk")

    monkeypatch.setattr(tempfile, "TemporaryFile", no_disk)
    big_png = receipt_png() + b"\0" * (3 * 1024 * 1024)  # trailing bytes are ignored by PIL

    assert upload(client, big_png) == 200


def test_request_over_the_body_limit_is_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(limits, "MAX_REQUEST_BYTES", 1024)

    assert upload(client, receipt_png() + b"\0" * 4096) == 413


def test_chunked_request_over_the_limit_is_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(limits, "MAX_REQUEST_BYTES", 1024)

    def body() -> object:
        yield b"x" * 800
        yield b"x" * 800

    response = client.post(
        "/api/check", content=body(), headers={"content-type": "multipart/form-data; boundary=b"}
    )

    assert response.status_code == 413


def test_non_multipart_body_is_rejected(client: TestClient) -> None:
    response = client.post("/api/check", json={"hello": "world"})

    assert response.status_code == 415
