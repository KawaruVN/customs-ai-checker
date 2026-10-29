"""Real uploaded Packing sources through production services and SQLite lifecycle."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import sqlite3
from threading import Barrier

import pytest

from customs_ai.application.parsing import DocumentParsingService
from customs_ai.classification.enums import DocumentType
from customs_ai.config import settings
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.parsers.errors import ParserFailedError
from customs_ai.repositories.database import get_connection
from customs_ai.repositories.document_extractions import DocumentExtractionRepository


def prepared(pipeline):
    source = pipeline.register(pipeline.xlsx())
    assert pipeline.classify(source.document_id).document_type == DocumentType.PACKING_LIST
    return source


def assert_unchanged(pipeline, source, first, before):
    fresh = DocumentExtractionRepository()
    assert fresh.get_active(source.document_id) == first.record
    assert fresh.list_history(source.document_id) == [first.record]
    assert pipeline.repo.get_by_document_id(source.document_id) == before
    pipeline.assert_immutable(source)


def test_success_review_failed_replacement_and_retry_keep_active_distinct(packing_pipeline, monkeypatch):
    p = packing_pipeline
    source = prepared(p)
    first = p.extract(source.document_id)
    assert first.result.status == ExtractionStatus.EXTRACTED
    p.assert_roundtrip(source, first)
    refused = p.extract(source.document_id)
    assert not refused.persisted and refused.active_record == first.record
    second = p.extract(source.document_id, expected_active_extraction_id=first.record.extraction_id)
    assert second.persisted and second.record.attempt_number == 2
    p.assert_roundtrip(source, second)
    with monkeypatch.context() as patch:
        def unavailable(*args, **kwargs):
            raise ParserFailedError() from RuntimeError("SYNTHETIC_PRIVATE_PARSE_FAILURE")
        patch.setattr(DocumentParsingService, "parse_document_readonly", unavailable)
        failed = p.extract(source.document_id, expected_active_extraction_id=second.record.extraction_id)
    assert failed.persisted and failed.result.status == ExtractionStatus.FAILED
    assert not failed.record.is_active and failed.active_record == second.record
    p.assert_roundtrip(source, failed)
    latest = p.repo.get_by_document_id(source.document_id)
    assert latest.processing_status.value == latest.extraction_status == "FAILED"
    assert p.extractions.get_active(source.document_id) == second.record
    retried = p.extract(source.document_id, expected_active_extraction_id=second.record.extraction_id)
    p.assert_roundtrip(source, retried)
    history = DocumentExtractionRepository().list_history(source.document_id)
    assert [r.attempt_number for r in history] == [1, 2, 3, 4]
    assert [r.status for r in history] == [ExtractionStatus.EXTRACTED, ExtractionStatus.EXTRACTED,
                                         ExtractionStatus.FAILED, ExtractionStatus.EXTRACTED]
    assert [r.is_active for r in history] == [False, False, False, True]
    assert history[0].result.packing_list.items[1].item_code.normalized_value == "000010"
    assert history[2].supersedes_extraction_id is None
    assert "SYNTHETIC_PRIVATE_PARSE_FAILURE" not in str(failed)


def test_review_pdf_replacement_still_requires_exact_active_id(packing_pipeline):
    p = packing_pipeline
    source = p.register(p.pdf())
    assert p.classify(source.document_id).document_type == DocumentType.PACKING_LIST
    first = p.extract(source.document_id)
    assert first.result.status == ExtractionStatus.NEEDS_REVIEW
    refused = p.extract(source.document_id)
    assert not refused.persisted
    second = p.extract(source.document_id, expected_active_extraction_id=first.record.extraction_id)
    assert second.result.status == ExtractionStatus.NEEDS_REVIEW
    assert any(i.code == "PDF_PACKING_ITEMS_UNSUPPORTED" for i in second.result.issues)
    p.assert_roundtrip(source, second)
    assert [r.is_active for r in p.extractions.list_history(source.document_id)] == [False, True]


@pytest.mark.parametrize("stale", ["active", "hash", "status"])
def test_stale_requested_state_does_not_change_uploaded_pipeline(packing_pipeline, stale):
    p = packing_pipeline
    source = prepared(p)
    first = p.extract(source.document_id)
    before = p.repo.get_by_document_id(source.document_id)
    arguments = {"expected_active_extraction_id": first.record.extraction_id}
    arguments.update({"active": {"expected_active_extraction_id": "STALE"},
                      "hash": {"expected_source_file_hash": "f" * 64},
                      "status": {"expected_processing_status": "CLASSIFIED"}}[stale])
    outcome = p.extract(source.document_id, **arguments)
    assert not outcome.persisted
    assert_unchanged(p, source, first, before)


@pytest.mark.parametrize("change", ["classification", "filename", "hash", "processing_status"])
def test_real_repository_writer_lock_rechecks_full_source_snapshot(packing_pipeline, monkeypatch, change):
    p = packing_pipeline
    source = prepared(p)
    first = p.extract(source.document_id)
    real_replace = DocumentExtractionRepository.replace_active
    def race(repository, request):
        column, value = {
            "classification": ("detected_document_type", "COMMERCIAL_INVOICE"),
            "filename": ("original_filename", "changed.xlsx"),
            "hash": ("file_hash", "f" * 64),
            "processing_status": ("processing_status", "FAILED"),
        }[change]
        with closing(get_connection()) as connection, connection:
            connection.execute(f"UPDATE source_documents SET {column}=? WHERE document_id=?", (value, source.document_id))
        return real_replace(repository, request)
    monkeypatch.setattr(DocumentExtractionRepository, "replace_active", race)
    outcome = p.extract(source.document_id, expected_active_extraction_id=first.record.extraction_id)
    assert not outcome.persisted and outcome.result.status == ExtractionStatus.FAILED
    assert p.extractions.get_active(source.document_id) == first.record
    assert p.extractions.list_history(source.document_id) == [first.record]
    p.assert_immutable(source)


@pytest.mark.parametrize("event", ["BEFORE INSERT ON document_extractions", "AFTER INSERT ON document_extractions",
    "AFTER UPDATE OF is_active ON document_extractions", "BEFORE UPDATE OF extraction_status ON source_documents",
    "AFTER UPDATE OF extraction_status ON source_documents"])
def test_real_sqlite_abort_leaves_entire_packing_pipeline_transaction_unchanged(packing_pipeline, event, caplog):
    p = packing_pipeline
    source = prepared(p)
    first = p.extract(source.document_id)
    before = p.repo.get_by_document_id(source.document_id)
    with closing(get_connection()) as connection, connection:
        connection.execute(f"CREATE TRIGGER synthetic_packing_abort {event} BEGIN SELECT RAISE(ABORT,'PRIVATE_SQL_SENTINEL'); END")
    failed = p.extract(source.document_id, expected_active_extraction_id=first.record.extraction_id)
    assert not failed.persisted and failed.result.status == ExtractionStatus.FAILED
    assert_unchanged(p, source, first, before)
    assert "PRIVATE_SQL_SENTINEL" not in caplog.text + str(failed.result.issues)
    assert source.stored_path not in caplog.text


def test_real_packing_pipeline_commit_failure_rolls_back_after_metadata(packing_pipeline, monkeypatch):
    import customs_ai.repositories.document_extractions as module
    p = packing_pipeline
    source = prepared(p)
    first = p.extract(source.document_id)
    before = p.repo.get_by_document_id(source.document_id)
    opened, observations = [], []
    class BrokenCommit(sqlite3.Connection):
        closed = False
        def commit(self):
            observations.append(self.execute("SELECT COUNT(*) FROM document_extractions").fetchone()[0])
            assert self.execute("SELECT processing_status FROM source_documents").fetchone()[0] == "EXTRACTED"
            raise sqlite3.OperationalError("PRIVATE_COMMIT_SENTINEL")
        def close(self):
            self.closed = True
            return super().close()
    def connect():
        connection = sqlite3.connect(str(settings.db_path), factory=BrokenCommit)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        opened.append(connection)
        return connection
    with monkeypatch.context() as patch:
        patch.setattr(module, "get_connection", connect)
        failed = p.extract(source.document_id, expected_active_extraction_id=first.record.extraction_id)
    assert not failed.persisted and failed.result.status == ExtractionStatus.FAILED
    assert observations == [2] and all(c.closed for c in opened)
    assert_unchanged(p, source, first, before)
    assert "PRIVATE_COMMIT_SENTINEL" not in str(failed)


def test_concurrent_production_extractions_have_one_successful_replacement(packing_pipeline, monkeypatch):
    p = packing_pipeline
    source = prepared(p)
    first = p.extract(source.document_id)
    real_replace = DocumentExtractionRepository.replace_active
    barrier = Barrier(2)
    def race(repository, request):
        barrier.wait(timeout=20)
        return real_replace(repository, request)
    monkeypatch.setattr(DocumentExtractionRepository, "replace_active", race)
    def extract(_):
        return p.extract(source.document_id, expected_active_extraction_id=first.record.extraction_id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(extract, range(2)))
    assert sum(outcome.persisted for outcome in outcomes) == 1
    winner = next(outcome for outcome in outcomes if outcome.persisted)
    loser = next(outcome for outcome in outcomes if not outcome.persisted)
    assert loser.result.status == ExtractionStatus.FAILED
    p.assert_roundtrip(source, winner)
    assert len(p.extractions.list_history(source.document_id)) == 2


def test_invoice_v1_and_packing_v2_pipeline_records_coexist_without_rewriting(invoice_pipeline, packing_pipeline):
    import json
    p, invoice = packing_pipeline, invoice_pipeline
    invoice_source = invoice.register(invoice.xlsx(), shipment_id="SHP-INVOICE")
    assert invoice.classify(invoice_source.document_id).document_type == DocumentType.COMMERCIAL_INVOICE
    invoice_outcome = invoice.extract(invoice_source.document_id)
    assert invoice_outcome.persisted
    with closing(get_connection()) as connection:
        original = connection.execute("SELECT payload_json FROM document_extractions WHERE extraction_id=?",
                                      (invoice_outcome.record.extraction_id,)).fetchone()[0]
    assert json.loads(original)["format_version"] == 1
    source = prepared(p)
    outcome = p.extract(source.document_id)
    p.assert_roundtrip(source, outcome)
    fresh = DocumentExtractionRepository()
    assert fresh.get_by_extraction_id(invoice_outcome.record.extraction_id) == invoice_outcome.record
    with closing(get_connection()) as connection:
        unchanged = connection.execute("SELECT payload_json FROM document_extractions WHERE extraction_id=?",
                                       (invoice_outcome.record.extraction_id,)).fetchone()[0]
    assert unchanged == original
    assert fresh.get_active(invoice_source.document_id).result.invoice.invoice_number.normalized_value == "0000456"
