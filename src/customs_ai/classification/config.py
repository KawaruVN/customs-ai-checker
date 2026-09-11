import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from customs_ai.config import BASE_DIR
from customs_ai.classification.enums import DocumentType


class ClassificationSettingsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    threshold: float = Field(ge=0.0, le=1.0)
    conflict_margin: float = Field(ge=0.0, le=1.0)
    strong_weight: float = Field(ge=0.0, le=1.0)
    supporting_weight: float = Field(ge=0.0, le=1.0)


class ClueConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strong: list[str]
    supporting: list[str]


class DocumentClassificationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    settings: ClassificationSettingsConfig
    clues: dict[str, ClueConfig]

    @model_validator(mode="after")
    def validate_document_types(self) -> "DocumentClassificationConfig":
        configured_keys = set(self.clues)
        auto_classifiable_keys = {
            dt.value for dt in DocumentType if dt not in {DocumentType.OTHER, DocumentType.UNKNOWN}
        }
        invalid_keys = configured_keys - auto_classifiable_keys
        if invalid_keys:
            invalid = ", ".join(sorted(invalid_keys))
            raise ValueError(f"Invalid deterministic classification key(s): {invalid}")

        missing_keys = auto_classifiable_keys - configured_keys
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise ValueError(f"Missing deterministic classification key(s): {missing}")
        return self


def load_classification_config() -> DocumentClassificationConfig:
    config_path = BASE_DIR / "config" / "document_classification.yaml"
    if not config_path.is_file():
        raise FileNotFoundError(f"Classification config not found at {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return DocumentClassificationConfig(**data)
