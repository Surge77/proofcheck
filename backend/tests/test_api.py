import json
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from proofcheck import api
from proofcheck.main import create_app
from proofcheck.models import Receipt
from tests.factories import receipt_png
from tests.sheets import SBI_ROWS, csv_bytes

ROSTER = b"name,amount\nRamesh Kumar,1500\nMeera,2000\n"


def fake_receipt(source: str, utr: str | None = "512345678901") -> Receipt:
    return Receipt(
        source=source,
        utr=utr,
        amount=Decimal("1500"),
        payer="Ramesh Kumar",
        paid_on=None,
        app="gpay",
        status="success",
        method="ocr+vision",
        confidence="high",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def fake_extract(source: str, _data: bytes) -> Receipt:
        return fake_receipt(source)

    monkeypatch.setattr(api, "extract", fake_extract)
    return TestClient(create_app(), base_url="http://127.0.0.1")


def post(client: TestClient, screenshots: list[tuple[str, bytes, str]], **extra: Any) -> Any:
    files: list[tuple[str, tuple[str, bytes, str]]] = [("screenshots", s) for s in screenshots]
    files.append(
        ("statement", ("sbi.csv", extra.get("statement", csv_bytes(SBI_ROWS)), "text/csv"))
    )
    if "roster" in extra:
        files.append(("roster", ("roster.csv", extra["roster"], "text/csv")))
    return client.post("/api/check", files=files)


def events(response: Any) -> list[dict[str, Any]]:
    return [json.loads(line) for line in response.text.splitlines() if line]


def test_streams_progress_then_a_report(client: TestClient) -> None:
    png = ("a.png", receipt_png(), "image/png")
    response = post(client, [png, ("b.png", receipt_png(), "image/png")], roster=ROSTER)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    stream = events(response)
    assert [e["type"] for e in stream] == ["progress", "progress", "report"]
    assert stream[1]["done"] == 2
    report = stream[-1]["report"]
    assert [m["status"] for m in report["matches"]] == ["verified", "duplicate_proof"]
    assert report["counts"]["verified"] == 1
    assert {line["name"]: line["status"] for line in report["roster"]} == {
        "Ramesh Kumar": "paid",
        "Meera": "unpaid",
    }


def test_non_image_upload_becomes_an_unreadable_row(client: TestClient) -> None:
    response = post(client, [("notes.txt", b"hello", "text/plain")])

    [match] = events(response)[-1]["report"]["matches"]
    assert match["status"] == "unreadable"
    assert match["receipt"]["source"] == "notes.txt"


def test_file_names_are_reduced_to_a_safe_basename(client: TestClient) -> None:
    response = post(client, [("../../etc/" + "x" * 300 + ".png", receipt_png(), "image/png")])

    source = events(response)[-1]["report"]["matches"][0]["receipt"]["source"]
    assert "/" not in source
    assert len(source) <= 120


def test_bad_statement_is_rejected_before_any_screenshot_is_read(client: TestClient) -> None:
    response = post(client, [("a.png", receipt_png(), "image/png")], statement=b"%PDF")

    assert response.status_code == 422
    assert "columns" in response.json()["detail"]


def test_bad_roster_is_rejected_with_its_message(client: TestClient) -> None:
    response = post(client, [("a.png", receipt_png(), "image/png")], roster=b"who\nx\n")

    assert response.status_code == 422
    assert "name" in response.json()["detail"]


def test_too_many_screenshots_is_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api, "MAX_SCREENSHOTS", 2)
    png = ("a.png", receipt_png(), "image/png")

    response = post(client, [png, png, png])

    assert response.status_code == 413


def test_oversized_statement_is_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api, "MAX_STATEMENT_BYTES", 10)

    response = post(client, [("a.png", receipt_png(), "image/png")])

    assert response.status_code == 413


def test_health_reports_vision_model_status(client: TestClient) -> None:
    body = client.get("/api/health").json()

    assert body["status"] == "ok"
    assert body["vision"] is False  # tests point Ollama at a dead port
    assert body["model"] == "gemma3:4b"


def test_unexpected_extraction_failure_becomes_an_unreadable_row(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken_extract(_source: str, _data: bytes) -> Receipt:
        raise RuntimeError("onnxruntime fell over")

    monkeypatch.setattr(api, "extract", broken_extract)

    response = post(client, [("a.png", receipt_png(), "image/png")])

    [match] = events(response)[-1]["report"]["matches"]
    assert match["status"] == "unreadable"
    assert "onnxruntime" not in response.text  # internal details stay internal
