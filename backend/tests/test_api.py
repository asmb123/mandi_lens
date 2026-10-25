from fastapi.testclient import TestClient

from app.api import settings
from app.main import app


client = TestClient(app)


def test_health() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_comparison_rejects_negative_values() -> None:
    response = client.post("/api/comparison", json={"board_price": -1, "offered_price": 2})
    assert response.status_code == 422


def test_ocr_rejects_unsupported_upload() -> None:
    response = client.post("/api/ocr", files={"file": ("board.txt", b"not an image", "text/plain")})
    assert response.status_code == 415


def test_ocr_reports_missing_provider_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "sarvam_api_key", None)
    response = client.post(
        "/api/ocr",
        files={"file": ("board.jpg", b"not a real image", "image/jpeg")},
    )
    assert response.status_code == 502
    assert "API key" in response.json()["detail"]
