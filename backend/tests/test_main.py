from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from proofcheck.main import create_app, static_file


def test_health_reports_ok() -> None:
    client = TestClient(create_app(), base_url="http://127.0.0.1")

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_api_path_is_404_not_the_spa() -> None:
    client = TestClient(create_app(), base_url="http://127.0.0.1")

    response = client.get("/api/does-not-exist")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "",
        "../secret.txt",
        "assets/../../secret.txt",
        "C:/Windows/win.ini",
        r"\\attacker\share\x",  # UNC path
        "nul\0byte",
        "missing.js",
    ],
)
def test_static_file_refuses_anything_outside_the_build(tmp_path: Path, path: str) -> None:
    (tmp_path / "secret.txt").write_text("no")
    root = tmp_path / "dist"
    root.mkdir()

    assert static_file(root, path) is None


def test_static_file_serves_real_files_in_the_build(tmp_path: Path) -> None:
    (tmp_path / "icon.svg").write_text("<svg/>")

    assert static_file(tmp_path, "icon.svg") == tmp_path / "icon.svg"
