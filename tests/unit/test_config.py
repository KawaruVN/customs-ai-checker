from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

import customs_ai.config as config_module
from customs_ai.config import Settings


@pytest.fixture
def isolate_envs(monkeypatch):
    """Prevent host environment variables from polluting config tests."""
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)


def test_config_defaults(isolate_envs, monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "missing.yaml")
    settings = Settings(_env_file=None)

    assert settings.app_name == "Customs AI Checker"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_config_env_override(isolate_envs, monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test Overridden App")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Test Overridden App"
    assert settings.environment == "production"
    assert settings.log_level == "DEBUG"


def test_invalid_log_level_raises_validation_error(isolate_envs, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "INVALID_LEVEL")

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)

    assert "log_level" in str(exc.value)


def test_yaml_config_loaded(isolate_envs, monkeypatch, tmp_path):
    mock_yaml_path = tmp_path / "app.yaml"
    mock_yaml_path.write_text(
        yaml.safe_dump(
            {
                "app_name": "YAML App",
                "environment": "staging",
                "log_level": "WARNING",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "CONFIG_FILE", mock_yaml_path)

    settings = Settings(_env_file=None)

    assert settings.app_name == "YAML App"
    assert settings.environment == "staging"
    assert settings.log_level == "WARNING"


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


def test_dotenv_loading_is_cwd_independent(
    isolate_envs, monkeypatch, tmp_path
):
    mock_env_path = tmp_path / "repo_root" / ".env"
    mock_env_path.parent.mkdir()
    mock_env_path.write_text(
        "APP_NAME=CWD Independent App\n"
        "APP_ENV=production\n"
        "LOG_LEVEL=CRITICAL\n",
        encoding="utf-8",
    )

    # Use an absolute dotenv path through the same model_config mechanism
    # used by production Settings, then launch from another CWD.
    monkeypatch.setitem(Settings.model_config, "env_file", mock_env_path)

    random_cwd = tmp_path / "random_cwd"
    random_cwd.mkdir()
    monkeypatch.chdir(random_cwd)

    settings = Settings()

    assert settings.app_name == "CWD Independent App"
    assert settings.environment == "production"
    assert settings.log_level == "CRITICAL"
