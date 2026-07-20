from fastapi.testclient import TestClient

from app.main import app


def test_health_live() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "fames-r-office-pro-backend",
    }


def test_health_ready() -> None:
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "fames-r-office-pro-backend",
        "database": "ready",
    }
