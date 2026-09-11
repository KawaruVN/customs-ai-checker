from fastapi.testclient import TestClient

from customs_ai.config import settings
from customs_ai.main import app


def valid_pdf(payload: bytes = b"synthetic") -> bytes:
    return b"%PDF-1.7\n" + payload


def test_upload_new_duplicate_and_cross_shipment(tmp_path):
    content = valid_pdf(b"api-flow")
    with TestClient(app) as client:
        first = client.post(
            "/shipments/SHP-001/documents",
            files={"file": ("invoice.pdf", content, "application/pdf")},
        )
        assert first.status_code == 201
        first_data = first.json()
        assert first_data["is_duplicate"] is False
        assert "stored_path" not in first_data
        assert str(tmp_path) not in first.text

        duplicate = client.post(
            "/shipments/SHP-001/documents",
            files={"file": ("renamed.pdf", content, "application/pdf")},
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["is_duplicate"] is True
        assert duplicate.json()["document_id"] == first_data["document_id"]

        other_shipment = client.post(
            "/shipments/SHP-002/documents",
            files={"file": ("invoice.pdf", content, "application/pdf")},
        )
        assert other_shipment.status_code == 201
        assert other_shipment.json()["document_id"] != first_data["document_id"]


def test_invalid_shipment_id():
    with TestClient(app) as client:
        response = client.post(
            "/shipments/SHP!001/documents",
            files={"file": ("invoice.pdf", valid_pdf(), "application/pdf")},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_SHIPMENT_ID"


def test_unsupported_extension():
    with TestClient(app) as client:
        response = client.post(
            "/shipments/SHP-001/documents",
            files={"file": ("payload.exe", b"synthetic", "application/octet-stream")},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "FILE_UNSUPPORTED"


def test_empty_file():
    with TestClient(app) as client:
        response = client.post(
            "/shipments/SHP-001/documents",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "FILE_EMPTY"


def test_oversized_file(monkeypatch):
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    prefix = b"%PDF-1.7\n"
    content = prefix + b"A" * (1024 * 1024 + 1 - len(prefix))
    with TestClient(app) as client:
        response = client.post(
            "/shipments/SHP-OVER/documents",
            files={"file": ("large.pdf", content, "application/pdf")},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "FILE_TOO_LARGE"
    assert not (settings.upload_root / "SHP-OVER").exists()


def test_mime_mismatch():
    with TestClient(app) as client:
        response = client.post(
            "/shipments/SHP-001/documents",
            files={"file": ("invoice.pdf", valid_pdf(), "text/plain")},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "FILE_MIME_MISMATCH"


def test_invalid_content_signature():
    with TestClient(app) as client:
        response = client.post(
            "/shipments/SHP-001/documents",
            files={"file": ("invoice.pdf", b"not a pdf", "application/pdf")},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "FILE_INVALID_CONTENT"


def test_duplicate_request_still_validates_current_content():
    content = valid_pdf(b"same-bytes")
    with TestClient(app) as client:
        first = client.post(
            "/shipments/SHP-DUP/documents",
            files={"file": ("invoice.pdf", content, "application/pdf")},
        )
        assert first.status_code == 201

        second = client.post(
            "/shipments/SHP-DUP/documents",
            files={"file": ("invoice.csv", content, "text/csv")},
        )
        assert second.status_code == 400
        assert second.json()["detail"]["code"] == "FILE_INVALID_CONTENT"


def test_internal_repository_failure_returns_500(monkeypatch):
    import customs_ai.api.routes.documents as documents_route

    def fail_create(document):
        raise RuntimeError("synthetic database failure")

    monkeypatch.setattr(documents_route.service.repo, "create", fail_create)

    with TestClient(app) as client:
        response = client.post(
            "/shipments/SHP-FAIL/documents",
            files={"file": ("invoice.pdf", valid_pdf(b"failure"), "application/pdf")},
        )

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["code"] == "INGESTION_FAILED"
    assert "path" not in detail["message"].lower()
    assert not list(settings.upload_root.rglob("original.*"))


def test_health_regression():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
