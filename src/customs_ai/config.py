from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = BASE_DIR / "config" / "app.yaml"
ENV_FILE = BASE_DIR / ".env"


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """Load non-secret application settings from config/app.yaml."""

    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)
        if CONFIG_FILE.exists():
            with CONFIG_FILE.open("r", encoding="utf-8") as file:
                self.yaml_data = yaml.safe_load(file) or {}
        else:
            self.yaml_data = {}

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return self.yaml_data.get(field_name), field_name, False

    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, _ = self.get_field_value(field, field_name)
            if field_value is not None:
                values[field_key] = field_value
        return values


class VisionSettingsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    accuracy_mode: bool = True
    render_dpi: int = Field(default=200, ge=72, le=600)
    max_render_pixels: int = Field(default=16_000_000, ge=1_000_000, le=100_000_000)
    max_visual_pages: int = Field(default=50, ge=1, le=500)

    min_meaningful_chars: int = Field(default=12, ge=1, le=10_000)
    max_control_ratio: float = Field(default=0.02, ge=0.0, le=1.0)
    max_replacement_ratio: float = Field(default=0.01, ge=0.0, le=1.0)
    min_meaningful_ratio: float = Field(default=0.45, ge=0.0, le=1.0)
    min_confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    min_soft_text_overlap: float = Field(default=0.35, ge=0.0, le=1.0)

    vlm_local_endpoint: str = "http://127.0.0.1:9090/layout-parsing"
    vlm_connect_timeout_seconds: float = Field(default=2.0, gt=0.0, le=30.0)
    vlm_read_timeout_seconds: float = Field(default=60.0, gt=0.0, le=300.0)
    vlm_max_response_bytes: int = Field(default=5_000_000, ge=1_024, le=50_000_000)
    vlm_max_concurrency: int = Field(default=1, ge=1, le=4)

    @field_validator("vlm_local_endpoint")
    @classmethod
    def require_loopback_endpoint(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("VLM endpoint must use HTTP or HTTPS.")
        if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("VLM endpoint must use a loopback host.")
        if not parsed.path or parsed.path == "/":
            raise ValueError("VLM endpoint must include the inference path.")
        return value


class Settings(BaseSettings):
    app_name: str = "Customs AI Checker"
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT", "environment"),
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    max_upload_size_mb: int = Field(default=50, gt=0)
    upload_root: Path = Path("data/uploads")
    db_path: Path = Path("data/app.db")
    vision: VisionSettingsConfig = Field(default_factory=VisionSettingsConfig)

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @model_validator(mode="after")
    def resolve_runtime_paths(self) -> "Settings":
        if not self.upload_root.is_absolute():
            self.upload_root = (BASE_DIR / self.upload_root).resolve()
        else:
            self.upload_root = self.upload_root.resolve()

        if not self.db_path.is_absolute():
            self.db_path = (BASE_DIR / self.db_path).resolve()
        else:
            self.db_path = self.db_path.resolve()
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()

