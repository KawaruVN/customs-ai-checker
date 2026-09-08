from fastapi.testclient import TestClient
from customs_ai.main import app

def test_health_check_returns_200():
    # Sử dụng context manager để trigger lifespan event
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
