from fastapi.testclient import TestClient

from app.main import app, get_frontend_origins


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-business-process-assistant",
    }


def test_frontend_origins_preserve_local_and_normalize_configured(monkeypatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGINS", " https://example.vercel.app/,https://preview.example.com ")
    assert get_frontend_origins() == [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "https://example.vercel.app",
        "https://preview.example.com",
    ]
