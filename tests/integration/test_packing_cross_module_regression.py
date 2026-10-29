"""Real upload/classify/extract boundaries, classification faults and lazy imports."""

from hashlib import sha256
from pathlib import Path
import os
import subprocess
import sys

import pytest

from customs_ai.application.composition import build_classification_service, build_packing_extraction_service
from customs_ai.classification.deterministic import DeterministicClassifier
from customs_ai.classification.enums import DocumentType
from customs_ai.classification.errors import ClassificationFailedError
from customs_ai.config import settings
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.repositories.document_extractions import DocumentExtractionRepository


def _assert_refused_unchanged(pipeline, source, before_metadata):
    outcome = pipeline.extract(source.document_id)
    assert not outcome.persisted and outcome.record is None
    assert DocumentExtractionRepository().list_history(source.document_id) == []
    assert pipeline.repo.get_by_document_id(source.document_id) == before_metadata
    pipeline.assert_immutable(source)
    return outcome


def test_wrong_document_id_from_classification_fault_cannot_classify_or_extract_uploaded_source(packing_pipeline, monkeypatch):
    p = packing_pipeline
    source = p.register(p.xlsx())
    classify = DeterministicClassifier.classify

    def wrong_identity(classifier, document, filename=None):
        output = classify(classifier, document, filename=filename)
        assert output.document_type == DocumentType.PACKING_LIST
        return output.model_copy(update={"document_id": "DOC-OTHER-SYNTHETIC"})

    with monkeypatch.context() as patch:
        patch.setattr(DeterministicClassifier, "classify", wrong_identity)
        with pytest.raises(ClassificationFailedError):
            p.classify(source.document_id)
    current = p.repo.get_by_document_id(source.document_id)
    assert current.processing_status != ProcessingStatus.CLASSIFIED
    assert current.detected_document_type is None
    _assert_refused_unchanged(p, source, current)


def test_mutated_nonfinite_classification_result_is_revalidated_before_metadata_write(packing_pipeline, monkeypatch):
    p = packing_pipeline
    source = p.register(p.xlsx())
    classify = DeterministicClassifier.classify

    def invalid_confidence(classifier, document, filename=None):
        output = classify(classifier, document, filename=filename)
        output.confidence = float("nan")
        return output

    with monkeypatch.context() as patch:
        patch.setattr(DeterministicClassifier, "classify", invalid_confidence)
        with pytest.raises(ClassificationFailedError):
            p.classify(source.document_id)
    current = p.repo.get_by_document_id(source.document_id)
    assert current.detected_document_type is None
    _assert_refused_unchanged(p, source, current)


def test_commercial_invoice_filename_does_not_override_real_packing_content(packing_pipeline):
    p = packing_pipeline
    source = p.register(p.xlsx(), filename="commercial-invoice.xlsx")
    classification = p.classify(source.document_id)
    assert classification.document_id == source.document_id
    assert classification.document_type == DocumentType.PACKING_LIST
    assert classification.confidence >= 0.5 and classification.evidence
    outcome = p.extract(source.document_id)
    assert outcome.persisted and outcome.result.status == ExtractionStatus.EXTRACTED
    assert outcome.result.packing_list.packing_list_number.normalized_value == "0000456"
    assert [item.item_code.normalized_value for item in outcome.result.packing_list.items] == ["000009", "000010"]
    p.assert_roundtrip(source, outcome)


def test_invoice_named_packing_is_classified_invoice_and_refused_by_packing_service(packing_pipeline):
    p = packing_pipeline
    rows = [["COMMERCIAL INVOICE"], ["INVOICE NO", "INV-0001"], ["TOTAL AMOUNT", "12.50"], ["UNIT PRICE", "12.50"]]
    source = p.register(p.xlsx(rows), filename="packing-list.xlsx")
    classification = p.classify(source.document_id)
    assert classification.document_type == DocumentType.COMMERCIAL_INVOICE
    before = p.repo.get_by_document_id(source.document_id)
    outcome = _assert_refused_unchanged(p, source, before)
    assert outcome.result.packing_list.items == []


@pytest.mark.parametrize("rows,filename", [
    ([["Unrelated synthetic memorandum"], ["Reference", "0001"]], "unknown.xlsx"),
    ([["GROSS WEIGHT", "12.50"]], "weak.xlsx"),
    ([["Unrelated synthetic memorandum"]], "PACKING LIST.xlsx"),
])
def test_unknown_weak_or_filename_only_evidence_never_creates_packing_history(packing_pipeline, rows, filename):
    p = packing_pipeline
    source = p.register(p.xlsx(rows), filename=filename)
    classification = p.classify(source.document_id)
    assert classification.document_type == DocumentType.UNKNOWN
    assert classification.confidence < 0.5
    before = p.repo.get_by_document_id(source.document_id)
    assert before.processing_status == ProcessingStatus.NEEDS_REVIEW
    _assert_refused_unchanged(p, source, before)


@pytest.mark.parametrize("kind,confidence", [("COMMERCIAL_INVOICE", 0.99), ("UNKNOWN", 0.99), ("PACKING_LIST", 0.1)])
def test_inconsistent_stored_classification_cannot_be_repaired_by_current_content_alone(packing_pipeline, kind, confidence):
    p = packing_pipeline
    source = p.register(p.xlsx())
    assert p.classify(source.document_id).document_type == DocumentType.PACKING_LIST
    p.repo.update_classification_metadata(source.document_id, kind, confidence, ProcessingStatus.CLASSIFIED)
    before = p.repo.get_by_document_id(source.document_id)
    _assert_refused_unchanged(p, source, before)


def test_uploaded_but_unclassified_packing_is_not_implicitly_classified_by_extraction(packing_pipeline):
    p = packing_pipeline
    source = p.register(p.xlsx())
    assert source.processing_status == ProcessingStatus.UPLOADED
    _assert_refused_unchanged(p, source, source)


def test_uploaded_supported_ingestion_type_without_parser_cannot_be_packing_source(packing_pipeline):
    p = packing_pipeline
    path = p.directory / "synthetic-packing.csv"
    path.write_text("PACKING LIST,0001\nDESCRIPTION,QTY\nSynthetic gear,2\n", encoding="utf-8")
    source = p.register(path)
    assert source.file_type == "csv" and source.file_hash == sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ClassificationFailedError):
        p.classify(source.document_id)
    before = p.repo.get_by_document_id(source.document_id)
    _assert_refused_unchanged(p, source, before)


def test_unexpected_classifier_exception_is_private_and_leaves_no_classified_or_extraction_record(packing_pipeline, monkeypatch, caplog):
    p = packing_pipeline
    source = p.register(p.xlsx())
    sentinel = "SYNTHETIC_PRIVATE_CLASSIFICATION_PAYLOAD_000987"

    def fail(*args, **kwargs):
        raise RuntimeError(sentinel + source.stored_path)

    with monkeypatch.context() as patch:
        patch.setattr(DeterministicClassifier, "classify", fail)
        with pytest.raises(ClassificationFailedError) as error:
            p.classify(source.document_id)
    assert sentinel not in str(error.value) + caplog.text
    assert source.stored_path not in str(error.value) + caplog.text
    current = p.repo.get_by_document_id(source.document_id)
    assert current.processing_status != ProcessingStatus.CLASSIFIED
    _assert_refused_unchanged(p, source, current)


def test_real_native_production_factories_never_load_models_or_connect_network(packing_pipeline, monkeypatch):
    import socket
    from customs_ai.vision.providers.rapidocr import RapidOcrProvider

    p = packing_pipeline
    source = p.register(p.pdf())
    def blocked(*args, **kwargs):
        raise AssertionError("Unexpected model/network operation")
    monkeypatch.setattr(settings.vision, "enabled", True)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(RapidOcrProvider, "_get_engine", blocked)
    classified = p.classify(source.document_id)
    assert classified.document_type == DocumentType.PACKING_LIST
    outcome = p.extract(source.document_id)
    assert outcome.persisted and outcome.result.status == ExtractionStatus.NEEDS_REVIEW
    assert outcome.result.packing_list.packing_list_number.normalized_value == "0000456"
    p.assert_roundtrip(source, outcome)


def test_fresh_process_packing_and_classification_factories_have_no_import_side_effects(tmp_path):
    root = Path(__file__).resolve().parents[2]
    database = tmp_path / "fresh-runtime" / "app.db"
    uploads = tmp_path / "fresh-runtime" / "uploads"
    environment = os.environ.copy()
    environment.update({"DB_PATH": str(database), "UPLOAD_ROOT": str(uploads), "VISION__ENABLED": "false",
                        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(root / "src")})
    program = """
import socket, sys, threading
def blocked(*args, **kwargs):
    raise AssertionError('Unexpected network operation')
socket.socket.connect = blocked
socket.create_connection = blocked
before = {thread.ident for thread in threading.enumerate()}
from customs_ai.application.composition import build_classification_service, build_packing_extraction_service
packing = build_packing_extraction_service()
classification = build_classification_service()
assert packing.vision is None and classification.vision_service is None
assert not {'openai', 'anthropic', 'google.generativeai', 'rapidocr', 'onnxruntime'}.intersection(sys.modules)
assert {thread.ident for thread in threading.enumerate()} == before
print('PACKING_FACTORY_IMPORT_OK')
"""
    process = subprocess.run([sys.executable, "-B", "-c", program], cwd=tmp_path, env=environment,
                             capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    assert "PACKING_FACTORY_IMPORT_OK" in process.stdout
    assert not database.exists() and not uploads.exists() and not database.parent.exists()
