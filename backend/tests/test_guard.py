import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from proofcheck import api
from proofcheck.config import Settings
from proofcheck.main import create_app
from tests.factories import receipt_png
from tests.sheets import SBI_ROWS, csv_bytes

FILES = [
    ("screenshots", ("a.png", receipt_png(), "image/png")),
    ("statement", ("sbi.csv", csv_bytes(SBI_ROWS), "text/csv")),
]


def test_request_with_a_foreign_host_header_is_refused() -> None:
    # A DNS-rebinding page reaches 127.0.0.1 but still sends its own hostname.
    client = TestClient(create_app(), base_url="http://evil.example")

    assert client.get("/api/health").status_code == 400


def test_post_from_another_website_is_refused() -> None:
    client = TestClient(create_app(), base_url="http://127.0.0.1")

    response = client.post("/api/check", files=FILES, headers={"origin": "https://evil.example"})

    assert response.status_code == 403


@pytest.mark.parametrize("origin", ["http://127.0.0.1:8000", "http://localhost:5173"])
def test_post_from_proofcheck_itself_is_allowed(origin: str) -> None:
    client = TestClient(create_app(), base_url="http://127.0.0.1")

    response = client.post("/api/health", headers={"origin": origin})

    assert response.status_code == 405  # reached the router: method not allowed, not forbidden


def test_only_one_check_runs_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "_is_running", True)
    client = TestClient(create_app(), base_url="http://127.0.0.1")

    response = client.post("/api/check", files=FILES)

    assert response.status_code == 429


@pytest.mark.parametrize("url", ["http://192.168.1.20:11434", "https://ollama.example.com"])
def test_settings_refuse_a_vision_server_off_this_machine(url: str) -> None:
    with pytest.raises(ValidationError, match="this machine"):
        Settings(ollama_url=url)


def test_settings_refuse_listening_on_the_network_unless_allowed() -> None:
    with pytest.raises(ValidationError, match="allow_lan"):
        Settings(host="0.0.0.0")

    assert Settings(host="0.0.0.0", allow_lan=True).host == "0.0.0.0"
