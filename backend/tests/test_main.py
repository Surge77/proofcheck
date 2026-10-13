from fastapi.testclient import TestClient

from proofcheck.main import create_app


def test_health_reports_ok() -> None:
    client = TestClient(create_app(), base_url="http://127.0.0.1")

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_api_path_is_404_not_the_spa() -> None:
    client = TestClient(create_app(), base_url="http://127.0.0.1")

    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
