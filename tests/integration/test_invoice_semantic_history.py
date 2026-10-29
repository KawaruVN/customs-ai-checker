"""Production composition, semantic trust boundaries and committed SQLite state."""

from contextlib import closing
from decimal import Decimal
from hashlib import sha256

import pytest

from customs_ai.classification.enums import DocumentType
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.headers import DeterministicInvoiceHeaderExtractor
from customs_ai.extraction.models import ExtractionCandidate
from customs_ai.extraction.semantic import SemanticInvoiceResponse
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.parsers.errors import ParserFailedError
from customs_ai.repositories.database import get_connection
from customs_ai.repositories.document_extractions import DocumentExtractionRepository


class Proposals:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def extract(self, request):
        self.requests.append(request)
        return self.response(request)


def candidate(document_id, **changes):
    return ExtractionCandidate(**{
        "field_path": "freight", "raw_value": "2.50", "typed_value": Decimal("2.50"),
        "source_document_id": document_id, "sheet": "Invoice Data", "cell": "B9",
        **changes,
    })


def prepared(pipeline, path=None):
    source = pipeline.register(path or pipeline.xlsx())
    classified = pipeline.classify(source.document_id)
    assert classified.document_type == DocumentType.COMMERCIAL_INVOICE
    assert pipeline.repo.get_by_document_id(source.document_id).processing_status == ProcessingStatus.CLASSIFIED
    return source


def test_grounded_fill_crosses_real_parser_classification_codec_and_database(invoice_pipeline, monkeypatch):
    p = invoice_pipeline
    source = prepared(p)
    before = sha256(p.source_bytes(source.document_id)).hexdigest()
    original_extract = DeterministicInvoiceHeaderExtractor.extract

    def miss_optional_freight(extractor, document):
        # A deliberate deterministic miss at one seam exercises fill-only
        # behavior; parsing, source classification, grounding and storage remain
        # production implementations. No alternate extraction logic is supplied.
        result = original_extract(extractor, document)
        result.invoice.freight = None
        result.candidates = [c for c in result.candidates if c.field_path != "freight"]
        return type(result).model_validate(result.model_dump(mode="python"))

    monkeypatch.setattr(DeterministicInvoiceHeaderExtractor, "extract", miss_optional_freight)
    provider = Proposals(lambda request: SemanticInvoiceResponse(
        document_id=request.document_id, candidates=[candidate(request.document_id)],
    ))
    outcome = p.extract(source.document_id, semantic_provider=provider)
    stored = DocumentExtractionRepository().get_active(source.document_id)
    assert outcome.persisted and stored.result.status == ExtractionStatus.EXTRACTED
    assert len(provider.requests) == 1
    assert stored.result.invoice.freight.normalized_value.as_tuple() == Decimal("2.50").as_tuple()
    assert stored.result.invoice.freight.raw_value == "2.50"
    assert stored.result.invoice.freight.extraction_method == "semantic_grounded_header"
    assert stored.result.invoice.freight.cell == "B9"
    assert stored.result.invoice.invoice_number.normalized_value == "0000456"
    assert [i.item_code.normalized_value for i in stored.result.invoice.items] == ["000009", "000010"]
    assert sha256(p.source_bytes(source.document_id)).hexdigest() == before


@pytest.mark.parametrize("malice", [
    "document", "field", "provenance", "coordinate", "type", "fabrication", "overwrite", "exception", "malformed",
])
def test_bad_semantic_output_never_changes_deterministic_data_or_disguises_success(invoice_pipeline, malice, caplog):
    p = invoice_pipeline
    source = prepared(p)

    def response(request):
        if malice == "exception":
            raise RuntimeError("SYNTHETIC_PRIVATE_PROVIDER_PAYLOAD")
        if malice == "malformed":
            return {"document_id": request.document_id, "candidates": [], "unexpected": "SYNTHETIC_PRIVATE_PROVIDER_PAYLOAD"}
        changes = {
            "document": {}, "field": {"field_path": "items[0].amount"},
            "provenance": {"source_document_id": "DOC-WRONG"},
            "coordinate": {"cell": "X999"}, "type": {"typed_value": "2.50"},
            "fabrication": {"raw_value": "999.00", "typed_value": Decimal("999.00")},
            "overwrite": {"field_path": "invoice_number", "cell": "B2", "raw_value": "999999", "typed_value": "999999"},
        }[malice]
        return SemanticInvoiceResponse(
            document_id="DOC-WRONG" if malice == "document" else request.document_id,
            candidates=[candidate(request.document_id, **changes)],
        )

    provider = Proposals(response)
    outcome = p.extract(source.document_id, semantic_provider=provider)
    stored = DocumentExtractionRepository().get_active(source.document_id)
    assert len(provider.requests) == 1
    assert stored.result == outcome.result
    assert stored.result.status == ExtractionStatus.NEEDS_REVIEW
    assert any(issue.code.startswith("SEMANTIC_") for issue in stored.result.issues)
    assert stored.result.invoice.invoice_number.normalized_value == "0000456"
    assert stored.result.invoice.freight.normalized_value == Decimal("2.50")
    assert stored.result.invoice.items[1].description.normalized_value == "TOTAL CONTROL"
    assert "SYNTHETIC_PRIVATE_PROVIDER_PAYLOAD" not in caplog.text + str(outcome.result.issues)


def test_deterministic_conflict_stays_sticky_after_semantic_proposal_and_replacement(invoice_pipeline):
    p = invoice_pipeline
    rows = p.rows()
    rows.extend([["INVOICE NO", "0000999"]])
    source = prepared(p, p.xlsx(rows))
    provider = Proposals(lambda request: SemanticInvoiceResponse(
        document_id=request.document_id,
        candidates=[candidate(request.document_id, field_path="invoice_number", raw_value="0000456", typed_value="0000456", cell="B2")],
    ))
    first = p.extract(source.document_id, semantic_provider=provider)
    second = p.extract(source.document_id, semantic_provider=provider,
                       expected_active_extraction_id=first.record.extraction_id)
    history = DocumentExtractionRepository().list_history(source.document_id)
    assert len(history) == 2 and [r.is_active for r in history] == [False, True]
    for record in history:
        assert record.result.invoice.invoice_number is None
        assert record.status == ExtractionStatus.NEEDS_REVIEW
        assert any(i.code == "CONFLICTING_FIELD_VALUES" for i in record.result.issues)
        assert {c.raw_value for c in record.result.candidates if c.field_path == "invoice_number"} >= {"0000456", "0000999"}
    assert second.record.extraction_id == history[-1].extraction_id


def test_history_success_review_failure_and_retry_remain_distinct(invoice_pipeline, monkeypatch):
    from customs_ai.application.parsing import DocumentParsingService

    p = invoice_pipeline
    source = prepared(p)
    immutable = p.source_bytes(source.document_id)
    first = p.extract(source.document_id)
    refused = p.extract(source.document_id)
    assert not refused.persisted
    review = p.extract(source.document_id, expected_active_extraction_id=first.record.extraction_id,
                       semantic_provider=Proposals(lambda request: None))
    assert review.record.status == ExtractionStatus.NEEDS_REVIEW
    with monkeypatch.context() as patch:
        def unavailable(*args):
            raise ParserFailedError()
        patch.setattr(DocumentParsingService, "parse_document_readonly", unavailable)
        failed = p.extract(source.document_id, expected_active_extraction_id=review.record.extraction_id)
    assert failed.persisted and not failed.record.is_active
    assert failed.result.status == ExtractionStatus.FAILED
    assert p.extractions.get_active(source.document_id).extraction_id == review.record.extraction_id
    latest = p.repo.get_by_document_id(source.document_id)
    assert latest.processing_status == ProcessingStatus.FAILED and latest.extraction_status == "FAILED"
    retried = p.extract(source.document_id, expected_active_extraction_id=review.record.extraction_id)
    history = DocumentExtractionRepository().list_history(source.document_id)
    assert [r.status for r in history] == [ExtractionStatus.EXTRACTED, ExtractionStatus.NEEDS_REVIEW,
                                         ExtractionStatus.FAILED, ExtractionStatus.EXTRACTED]
    assert [r.attempt_number for r in history] == [1, 2, 3, 4]
    assert sum(r.is_active for r in history) == 1
    assert retried.record == p.extractions.get_active(source.document_id)
    assert all(r.result.invoice.invoice_number.raw_value == "0000456" for r in history if r.status != ExtractionStatus.FAILED)
    assert p.source_bytes(source.document_id) == immutable


@pytest.mark.parametrize("stale", ["active", "hash", "status"])
def test_preflight_stale_request_cannot_change_committed_pipeline_state(invoice_pipeline, stale):
    p = invoice_pipeline
    source = prepared(p)
    first = p.extract(source.document_id)
    before = p.repo.get_by_document_id(source.document_id)
    arguments = {"expected_active_extraction_id": first.record.extraction_id}
    arguments.update({
        "active": {"expected_active_extraction_id": "stale-id"},
        "hash": {"expected_source_file_hash": "0" * 64},
        "status": {"expected_processing_status": ProcessingStatus.CLASSIFIED},
    }[stale])
    refused = p.extract(source.document_id, **arguments)
    assert not refused.persisted
    assert p.extractions.list_history(source.document_id) == [first.record]
    assert p.extractions.get_active(source.document_id) == first.record
    assert p.repo.get_by_document_id(source.document_id) == before


@pytest.mark.parametrize("timing", ["BEFORE", "AFTER"])
def test_real_sqlite_metadata_failure_rolls_back_entire_pipeline_replacement(invoice_pipeline, timing):
    p = invoice_pipeline
    source = prepared(p)
    first = p.extract(source.document_id)
    before = p.repo.get_by_document_id(source.document_id)
    with closing(get_connection()) as connection, connection:
        connection.execute(f"""CREATE TRIGGER synthetic_invoice_abort {timing} UPDATE OF extraction_status
            ON source_documents BEGIN SELECT RAISE(ABORT, 'SYNTHETIC_PRIVATE_DB_PAYLOAD'); END""")
    failed = p.extract(source.document_id, expected_active_extraction_id=first.record.extraction_id)
    assert not failed.persisted and failed.result.status == ExtractionStatus.FAILED
    assert p.extractions.get_active(source.document_id) == first.record
    assert p.extractions.list_history(source.document_id) == [first.record]
    assert p.repo.get_by_document_id(source.document_id) == before
    assert "SYNTHETIC_PRIVATE_DB_PAYLOAD" not in str(failed.result.issues)


@pytest.mark.parametrize("change", ["classification", "hash"])
def test_repository_boundary_source_race_is_rejected_under_writer_lock(invoice_pipeline, monkeypatch, change):
    p = invoice_pipeline
    source = prepared(p)
    first = p.extract(source.document_id)
    original = DocumentExtractionRepository.replace_active

    def race(repository, request):
        if change == "classification":
            current = p.repo.get_by_document_id(source.document_id)
            p.repo.update_classification_metadata(source.document_id, "PACKING_LIST", 0.99, current.processing_status)
        else:
            with closing(get_connection()) as connection, connection:
                connection.execute("UPDATE source_documents SET file_hash = ? WHERE document_id = ?", ("f" * 64, source.document_id))
        return original(repository, request)

    monkeypatch.setattr(DocumentExtractionRepository, "replace_active", race)
    refused = p.extract(source.document_id, expected_active_extraction_id=first.record.extraction_id)
    assert not refused.persisted
    assert refused.result.status == ExtractionStatus.FAILED
    assert p.extractions.get_active(source.document_id) == first.record
    assert p.extractions.list_history(source.document_id) == [first.record]


def test_uploaded_source_path_containment_and_log_privacy(invoice_pipeline, tmp_path, caplog):
    p = invoice_pipeline
    source = prepared(p)
    before = p.source_bytes(source.document_id)
    provider_marker = "SYNTHETIC_TAX_ID_00009999_PRIVATE_PAYLOAD"

    def provider_failure(request):
        raise RuntimeError(provider_marker + source.stored_path)

    outcome = p.extract(source.document_id, semantic_provider=Proposals(provider_failure))
    assert outcome.persisted
    assert p.source_bytes(source.document_id) == before
    for sensitive in [provider_marker, source.stored_path, "Synthetic Exporter", "0000456", "123456789012345.1200"]:
        assert sensitive not in caplog.text
    outside = tmp_path / "outside.xlsx"
    outside.write_bytes(before)
    with closing(get_connection()) as connection, connection:
        connection.execute("UPDATE source_documents SET stored_path = ? WHERE document_id = ?", (str(outside), source.document_id))
    refused = p.extract(source.document_id, expected_active_extraction_id=outcome.record.extraction_id)
    assert not refused.persisted and refused.result.status == ExtractionStatus.FAILED
    assert p.extractions.get_active(source.document_id) == outcome.record
    assert len(p.extractions.list_history(source.document_id)) == 1
    assert str(outside) not in caplog.text + str(refused.result.issues)


def test_production_factories_are_lazy_and_native_path_never_calls_network_or_ocr(invoice_pipeline, monkeypatch):
    import socket
    from customs_ai.config import settings
    from customs_ai.vision.providers.rapidocr import RapidOcrProvider

    p = invoice_pipeline
    source = p.register(p.pdf())
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected model/network initialization")
    monkeypatch.setattr(settings.vision, "enabled", True)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(RapidOcrProvider, "_get_engine", forbidden)
    classified = p.classify(source.document_id)
    assert classified.document_type == DocumentType.COMMERCIAL_INVOICE
    outcome = p.extract(source.document_id)
    assert outcome.persisted and outcome.result.invoice.invoice_number.normalized_value == "0000456"
    assert p.extractions.get_active(source.document_id).result == outcome.result
    assert outcome.result.status == ExtractionStatus.NEEDS_REVIEW


def test_fresh_process_import_and_default_factory_have_no_remote_or_runtime_side_effects(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys

    environment = os.environ.copy()
    database = tmp_path / "import-only" / "app.db"
    uploads = tmp_path / "import-only" / "uploads"
    environment.update({
        "DB_PATH": str(database), "UPLOAD_ROOT": str(uploads),
        "VISION__ENABLED": "false", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
    })
    program = """
import socket
import sys
def blocked(*args, **kwargs):
    raise AssertionError('Unexpected network operation during import or construction')
socket.socket.connect = blocked
socket.create_connection = blocked
from customs_ai.application.composition import build_invoice_extraction_service
service = build_invoice_extraction_service()
assert service.semantic is None and service.vision is None
assert not {'openai', 'anthropic', 'google.generativeai', 'rapidocr', 'onnxruntime'}.intersection(sys.modules)
print('Import and default factory passed without network or model initialization')
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", program], cwd=tmp_path, env=environment,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "default factory passed" in result.stdout
    assert not database.exists() and not uploads.exists()
