import pytest

from proofcheck.config import get_settings


@pytest.fixture(autouse=True)
def offline_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test talks to a real Ollama server unless it is marked `live`."""
    settings = get_settings()
    monkeypatch.setattr(settings, "ollama_url", "http://127.0.0.1:9")  # nothing listens on port 9
    monkeypatch.setattr(settings, "vision_timeout_s", 0.5)
