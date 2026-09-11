import os
import pytest
import yaml
from pathlib import Path
from pydantic import ValidationError

from customs_ai.config import Settings
import customs_ai.config as config_module

@pytest.fixture
def isolate_envs(monkeypatch):
    """Ensure tests are not polluted by the host machine's environment variables."""
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

def test_config_defaults(isolate_envs, monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "ENV_FILE", tmp_path / "nonexistent.env")
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "nonexistent.yaml")
    
    settings = Settings(_env_file=None)
    assert settings.app_name == "Customs AI Checker"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"

def test_config_env_override(isolate_envs, monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test Overridden App")
    monkeypatch.setenv("ENVIRONMENT", "production") 
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
    assert "Input should be" in str(exc.value)

def test_yaml_config_loaded(isolate_envs, monkeypatch, tmp_path):
    # Create an isolated mock YAML file
    mock_yaml_path = tmp_path / "app.yaml"
    with open(mock_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump({
            "app_name": "YAML App",
            "environment": "staging",
            "log_level": "WARNING"
        }, f)
        
    # Patch CONFIG_FILE to mock file
    monkeypatch.setattr(config_module, "CONFIG_FILE", mock_yaml_path)
    
    # Isolate dotenv parsing to verify YAML is actually loading and taking precedence
    settings = Settings(_env_file=None)
    assert settings.app_name == "YAML App"
    assert settings.environment == "staging"
    assert settings.log_level == "WARNING"

def test_missing_yaml_fallback_gracefully(isolate_envs, monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "missing.yaml")
    
    settings = Settings(_env_file=None)
    assert settings.app_name == "Customs AI Checker"
    assert settings.environment == "development"

def test_cwd_regression_absolute_env_file(isolate_envs, tmp_path):
    # 1. Assert the class is statically configured with the absolute path
    env_file_setting = Settings.model_config.get("env_file")
    assert env_file_setting == str(config_module.ENV_FILE)
    assert Path(env_file_setting).is_absolute()
    
    # 2. Emulate the process launched from a completely different CWD
    repo_root = tmp_path / "repo_root"
    random_cwd = tmp_path / "random_cwd"
    repo_root.mkdir()
    random_cwd.mkdir()
    
    # Write the .env file in the mock repository root
    env_file_path = repo_root / ".env"
    with open(env_file_path, "w", encoding="utf-8") as f:
        f.write("APP_NAME='CWD Independent App'\n")
        f.write("ENVIRONMENT='production'\n")
        f.write("LOG_LEVEL='CRITICAL'\n")
        
    original_cwd = os.getcwd()
    os.chdir(random_cwd)
    
    try:
        # Load from the absolute path explicitly to test that it is readable from another CWD
        settings = Settings(_env_file=str(env_file_path))
        assert settings.app_name == "CWD Independent App"
        assert settings.environment == "production"
        assert settings.log_level == "CRITICAL"
    finally:
        os.chdir(original_cwd)
