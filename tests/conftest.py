import pytest

from customs_ai.config import settings
from customs_ai.repositories.database import init_db


@pytest.fixture(autouse=True)
def isolate_runtime(tmp_path, monkeypatch):
    """Keep every test away from real runtime storage/database paths."""
    for name in (
        "APP_NAME",
        "APP_ENV",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "MAX_UPLOAD_SIZE_MB",
        "UPLOAD_ROOT",
        "DB_PATH",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setattr(settings, "db_path", tmp_path / "data" / "app.db")
    monkeypatch.setattr(settings, "upload_root", tmp_path / "data" / "uploads")
    monkeypatch.setattr(settings, "max_upload_size_mb", 50)
    init_db()
