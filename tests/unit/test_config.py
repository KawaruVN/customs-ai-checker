
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

import customs_ai.config as config_module
from customs_ai.config import Settings


@pytest.fixture
def isolate_envs(monkeypatch):
    """Prevent host environment variables from polluting config tests."""
    for name in (
        "APP_NAME",
        "APP_ENV",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "MAX_UPLOAD_SIZE_MB",
        "UPLOAD_ROOT",
        "DB_PATH",
        "VISION__ENABLED",
        "VISION__ACCURACY_MODE",
        "VISION__RENDER_DPI",
        "VISION__VLM_LOCAL_ENDPOINT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_config_defaults(isolate_envs, monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "missing.yaml")
    settings = Settings(_env_file=None)

    assert settings.app_name == "Customs AI Checker"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.max_upload_size_mb == 50
    assert settings.upload_root == (config_module.BASE_DIR / "data/uploads").resolve()
    assert settings.db_path == (config_module.BASE_DIR / "data/app.db").resolve()


def test_config_env_override(isolate_envs, monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test Overridden App")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "12")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Test Overridden App"
    assert settings.environment == "production"
    assert settings.log_level == "DEBUG"
    assert settings.max_upload_size_mb == 12


def test_invalid_log_level_raises_validation_error(isolate_envs, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "INVALID_LEVEL")

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)

    assert "log_level" in str(exc.value)


def test_invalid_upload_limit_raises_validation_error(isolate_envs, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "0")

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)

    assert "max_upload_size_mb" in str(exc.value)


def test_yaml_config_loaded(isolate_envs, monkeypatch, tmp_path):
    mock_yaml_path = tmp_path / "app.yaml"
    mock_yaml_path.write_text(
        yaml.safe_dump(
            {
                "app_name": "YAML App",
                "environment": "staging",
                "log_level": "WARNING",
                "max_upload_size_mb": 25,
                "upload_root": "runtime/uploads",
                "db_path": "runtime/test.db",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "CONFIG_FILE", mock_yaml_path)

    settings = Settings(_env_file=None)

    assert settings.app_name == "YAML App"
    assert settings.environment == "staging"
    assert settings.log_level == "WARNING"
    assert settings.max_upload_size_mb == 25
    assert settings.upload_root == (config_module.BASE_DIR / "runtime/uploads").resolve()
    assert settings.db_path == (config_module.BASE_DIR / "runtime/test.db").resolve()


def test_missing_yaml_fallback_gracefully(isolate_envs, monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "missing.yaml")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Customs AI Checker"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_env_file_path_is_absolute():
    env_file_setting = Path(Settings.model_config["env_file"])

    assert env_file_setting.is_absolute()
    assert env_file_setting == config_module.BASE_DIR / ".env"


def test_dotenv_loading_is_cwd_independent(isolate_envs, monkeypatch, tmp_path):
    mock_env_path = tmp_path / "repo_root" / ".env"
    mock_env_path.parent.mkdir()
    mock_env_path.write_text(
        "APP_NAME=CWD Independent App\n"
        "APP_ENV=production\n"
        "LOG_LEVEL=CRITICAL\n",
        encoding="utf-8",
    )

    monkeypatch.setitem(Settings.model_config, "env_file", mock_env_path)

    random_cwd = tmp_path / "random_cwd"
    random_cwd.mkdir()
    monkeypatch.chdir(random_cwd)

    settings = Settings()

    assert settings.app_name == "CWD Independent App"
    assert settings.environment == "production"
    assert settings.log_level == "CRITICAL"


def test_relative_runtime_paths_are_cwd_independent(isolate_envs, monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_ROOT", "custom/uploads")
    monkeypatch.setenv("DB_PATH", "custom/app.db")
    monkeypatch.chdir(tmp_path)

    settings = Settings(_env_file=None)

    assert settings.upload_root == (config_module.BASE_DIR / "custom/uploads").resolve()
    assert settings.db_path == (config_module.BASE_DIR / "custom/app.db").resolve()


def test_absolute_runtime_paths_are_preserved(isolate_envs, monkeypatch, tmp_path):
    upload_root = (tmp_path / "uploads").resolve()
    db_path = (tmp_path / "db" / "app.db").resolve()
    monkeypatch.setenv("UPLOAD_ROOT", str(upload_root))
    monkeypatch.setenv("DB_PATH", str(db_path))

    settings = Settings(_env_file=None)

    assert settings.upload_root == upload_root
    assert settings.db_path == db_path


def test_nested_vision_env_override(isolate_envs, monkeypatch):
    monkeypatch.setenv("VISION__ENABLED", "true")
    monkeypatch.setenv("VISION__RENDER_DPI", "300")
    monkeypatch.setenv("VISION__VLM_LOCAL_ENDPOINT", "http://localhost:9090/layout-parsing")
    configured = Settings(_env_file=None)
    assert configured.vision.enabled is True
    assert configured.vision.render_dpi == 300
    assert configured.vision.vlm_local_endpoint == "http://localhost:9090/layout-parsing"


def test_non_loopback_vision_endpoint_rejected(isolate_envs, monkeypatch):
    monkeypatch.setenv("VISION__VLM_LOCAL_ENDPOINT", "http://192.168.1.2:9090/layout-parsing")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_vision_bounds_rejected(isolate_envs, monkeypatch):
    monkeypatch.setenv("VISION__RENDER_DPI", "9999")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
