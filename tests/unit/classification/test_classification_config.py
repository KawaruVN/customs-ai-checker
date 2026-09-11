import copy

import pytest
from pydantic import ValidationError

from customs_ai.classification.config import (
    DocumentClassificationConfig,
    load_classification_config,
)


def _valid_payload() -> dict:
    return load_classification_config().model_dump(mode="python")


def test_valid_config_loads():
    config = load_classification_config()
    assert config.settings.threshold > 0.0
    assert config.settings.conflict_margin > 0.0
    assert "COMMERCIAL_INVOICE" in config.clues


def test_out_of_range_threshold_and_weights():
    payload = _valid_payload()
    payload["settings"]["threshold"] = 1.5
    with pytest.raises(ValidationError):
        DocumentClassificationConfig.model_validate(payload)

    payload = _valid_payload()
    payload["settings"]["strong_weight"] = -0.1
    with pytest.raises(ValidationError):
        DocumentClassificationConfig.model_validate(payload)


def test_invalid_document_type_key():
    payload = _valid_payload()
    payload["clues"]["NOT_A_REAL_TYPE"] = {"strong": [], "supporting": []}
    with pytest.raises(ValidationError):
        DocumentClassificationConfig.model_validate(payload)


def test_other_and_unknown_cannot_be_deterministic_clue_targets():
    for key in ("OTHER", "UNKNOWN"):
        payload = _valid_payload()
        payload["clues"][key] = {"strong": ["SHOULD NOT AUTO CLASSIFY"], "supporting": []}
        with pytest.raises(ValidationError):
            DocumentClassificationConfig.model_validate(payload)


def test_missing_classifiable_document_type_is_rejected():
    payload = _valid_payload()
    del payload["clues"]["PACKING_LIST"]
    with pytest.raises(ValidationError):
        DocumentClassificationConfig.model_validate(payload)


def test_missing_required_settings():
    payload = _valid_payload()
    del payload["settings"]["conflict_margin"]
    with pytest.raises(ValidationError):
        DocumentClassificationConfig.model_validate(payload)


def test_cwd_independent_config_loading(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = load_classification_config()
    assert "PACKING_LIST" in config.clues
