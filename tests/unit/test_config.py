import pytest
from pydantic import ValidationError
from customs_ai.config import Settings

def test_config_defaults():
    settings = Settings()
    assert settings.app_name == "Customs AI Checker"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"

def test_config_env_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Test Overridden App")
    monkeypatch.setenv("APP_ENV", "production")  # Test explicit alias support
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    settings = Settings()
    
    assert settings.app_name == "Test Overridden App"
    assert settings.environment == "production"  # Validate mapping success
    assert settings.log_level == "DEBUG"

def test_invalid_log_level_raises_validation_error(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "INVALID_LEVEL")
    
    with pytest.raises(ValidationError) as exc:
        Settings()
        
    assert "log_level" in str(exc.value)
    assert "Input should be" in str(exc.value)
