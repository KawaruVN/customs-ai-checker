"""Repository contract tests against isolated real SQLite databases."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
import sqlite3
from threading import Barrier

import pytest

from customs_ai.config import settings
from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, Invoice, InvoiceItem, Party
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.models import (
    ExtractionCandidate,
    ExtractionIssue,
    InvoiceHeaderExtractionResult,
    InvoiceItemExtractionResult,
)
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.models import SourceDocument
from customs_ai.repositories.database import get_connection
from customs_ai.repositories.document_extractions import (
    DocumentExtractionRepository,
    ExtractionConflictError,
    ExtractionNotFoundError,
    ExtractionPersistenceError,
    ExtractionValidationError,
)
from customs_ai.repositories.extraction_models import (
    ExtractionAttempt,
    ExtractionReplacement,
)
from customs_ai.repositories.source_documents import SourceDocumentRepository


def _document(document_id="DOC-1", *, path="synthetic/source.pdf"):
    source = SourceDocument(
        document_id=document_id,
        shipment_id="SHP-SYNTHETIC",
        original_filename="synthetic.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_hash=sha256(document_id.encode()).hexdigest(),
        file_size=10,
        stored_path=str(path),
        upload_time=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.CLASSIFIED,
        detected_document_type="COMMERCIAL_INVOICE",
        classification_confidence=0.99,
        parser_used="synthetic_parser",
        page_count=3,
    )
    SourceDocumentRepository().create(source)
    return source


def _field(value, raw, document_id="DOC-1", **location):
    return CanonicalField(
        normalized_value=value,
        raw_value=raw,
        origin=ValueOrigin.EXTRACTED,
        source_document_id=document_id,
        extraction_method="synthetic",
        confidence=0.95,
        **location,
    )


def _result(document_id="DOC-1", status=ExtractionStatus.EXTRACTED):
    return InvoiceHeaderExtractionResult(
        status=status,
        invoice=Invoice(
            invoice_number=_field("000012", " 000012 ", document_id, page=2),
            invoice_date=_field(date(2026, 10, 28), "2026/10/28", document_id, page=2),
            total_amount=_field(Decimal("12345678901234567890.1200"),
                                "12345678901234567890.1200", document_id, page=3),
            seller=Party(name=_field("Synthetic Seller", "Synthetic Seller", document_id, page=1)),
            items=[InvoiceItem(
                item_code=_field("000042", "000042", document_id, sheet="Items", cell="C7"),
                quantity=_field(Decimal("0.000"), "0.000", document_id, sheet="Items", cell="D7"),
            )],
        ),
        issues=[ExtractionIssue(
            code="SYNTHETIC_REVIEW", message="A synthetic field needs review.",
            field_path="invoice.total_amount", is_review_required=True,
        )] if status == ExtractionStatus.NEEDS_REVIEW else [],
        candidates=[ExtractionCandidate(
            field_path="total_amount", raw_value="12345678901234567890.1200",
            typed_value=Decimal("12345678901234567890.1200"),
            source_document_id=document_id, page=3,
            bounding_box=(0.1, 0.2, 0.3, 0.4), confidence=0.9,
            extraction_method="synthetic",
        )],
    )


def _attempt(document_id="DOC-1", status=ExtractionStatus.EXTRACTED, **updates):
    source = SourceDocumentRepository().get_by_document_id(document_id)
    values = dict(
        document_id=document_id,
        source_file_hash=source.file_hash if source else sha256(b"missing").hexdigest(),
        expected_processing_status=source.processing_status if source else ProcessingStatus.CLASSIFIED,
        result=_result(document_id, status),
        extraction_method="synthetic_deterministic",
    )
    values.update(updates)
    return ExtractionAttempt(**values)


def _replacement(active, status=ExtractionStatus.EXTRACTED, **updates):
    values = _attempt(active.document_id, status).model_dump(mode="python")
    values["expected_active_extraction_id"] = active.extraction_id
    values.update(updates)
    return ExtractionReplacement(**values)


def _scalar(query, parameters=()):
    with closing(get_connection()) as connection:
        return connection.execute(query, parameters).fetchone()[0]


def test_first_extraction_activates_and_preserves_other_source_metadata():
    source = _document()
    repository = DocumentExtractionRepository()
    saved = repository.save_attempt(_attempt())

    assert saved.extraction_id
    assert saved.document_id == source.document_id
    assert saved.attempt_number == 1
    assert saved.is_active is True
    assert saved.status == ExtractionStatus.EXTRACTED
    assert saved.source_file_hash == source.file_hash
    assert saved.schema_version == "0.1"
    assert saved.extraction_method == "synthetic_deterministic"
    assert saved.created_at.tzinfo is not None
    assert saved.created_at.utcoffset().total_seconds() == 0
    assert repository.get_active(source.document_id) == saved
    assert DocumentExtractionRepository().get_by_extraction_id(saved.extraction_id) == saved
    refreshed = SourceDocumentRepository().get_by_document_id(source.document_id)
    assert refreshed.processing_status == ProcessingStatus.EXTRACTED
    assert refreshed.extraction_status == ExtractionStatus.EXTRACTED.value
    for name in ["stored_path", "file_hash", "upload_time", "detected_document_type",
                 "classification_confidence", "parser_used", "page_count", "sheet_count"]:
        assert getattr(refreshed, name) == getattr(source, name)


def test_missing_source_cannot_create_an_orphan_extraction():
    repository = DocumentExtractionRepository()
    with pytest.raises(ExtractionNotFoundError):
        repository.save_attempt(_attempt("DOC-MISSING"))
    assert _scalar("SELECT COUNT(*) FROM document_extractions") == 0
    assert repository.get_active("DOC-MISSING") is None


def test_explicit_replacement_preserves_history_and_only_one_active():
    _document()
    repository = DocumentExtractionRepository()
    first = repository.save_attempt(_attempt())
    second = repository.replace_active(_replacement(first, ExtractionStatus.NEEDS_REVIEW))

    history = repository.list_history("DOC-1")
    assert [record.extraction_id for record in history] == [first.extraction_id, second.extraction_id]
    assert [record.attempt_number for record in history] == [1, 2]
    assert [record.is_active for record in history] == [False, True]
    assert second.supersedes_extraction_id == first.extraction_id
    assert history[0].result == first.result
    assert repository.get_active("DOC-1") == second
    assert _scalar("SELECT COUNT(*) FROM document_extractions WHERE is_active = 1") == 1
    refreshed = SourceDocumentRepository().get_by_document_id("DOC-1")
    assert refreshed.processing_status == ProcessingStatus.NEEDS_REVIEW
    assert refreshed.extraction_status == ExtractionStatus.NEEDS_REVIEW.value


def test_save_is_not_an_implicit_reextraction_or_overwrite():
    _document()
    repository = DocumentExtractionRepository()
    first = repository.save_attempt(_attempt())
    with pytest.raises(ExtractionConflictError):
        repository.save_attempt(_attempt())
    assert repository.list_history("DOC-1") == [first]
    assert repository.get_active("DOC-1") == first


@pytest.mark.parametrize("status", [ExtractionStatus.EXTRACTED, ExtractionStatus.NEEDS_REVIEW])
def test_existing_active_status_always_requires_explicit_replacement(status):
    _document()
    repository = DocumentExtractionRepository()
    first = repository.save_attempt(_attempt(status=status))
    with pytest.raises(ExtractionConflictError):
        repository.save_attempt(_attempt())
    second = repository.replace_active(_replacement(first))
    assert second.is_active is True
    assert repository.get_active("DOC-1").extraction_id == second.extraction_id


def test_failed_first_attempt_is_history_only_and_a_retry_can_activate():
    _document()
    repository = DocumentExtractionRepository()
    failed = repository.save_attempt(_attempt(status=ExtractionStatus.FAILED))
    assert failed.status == ExtractionStatus.FAILED
    assert failed.is_active is False
    assert repository.get_active("DOC-1") is None
    refreshed = SourceDocumentRepository().get_by_document_id("DOC-1")
    assert refreshed.processing_status == ProcessingStatus.FAILED
    assert refreshed.extraction_status == ExtractionStatus.FAILED.value

    successful = repository.save_attempt(_attempt())
    history = repository.list_history("DOC-1")
    assert [record.status for record in history] == [ExtractionStatus.FAILED, ExtractionStatus.EXTRACTED]
    assert [record.attempt_number for record in history] == [1, 2]
    assert repository.get_active("DOC-1") == successful


def test_failed_replacement_does_not_deactivate_prior_active_result():
    _document()
    repository = DocumentExtractionRepository()
    first = repository.save_attempt(_attempt())
    failed = repository.replace_active(_replacement(first, ExtractionStatus.FAILED))
    assert failed.is_active is False
    assert failed.status == ExtractionStatus.FAILED
    assert repository.get_active("DOC-1") == first
    assert len(repository.list_history("DOC-1")) == 2
    refreshed = SourceDocumentRepository().get_by_document_id("DOC-1")
    assert refreshed.processing_status == ProcessingStatus.FAILED
    assert refreshed.extraction_status == ExtractionStatus.FAILED.value

    retry = repository.replace_active(_replacement(first))
    assert retry.attempt_number == 3
    assert repository.get_active("DOC-1") == retry


def test_different_documents_have_independent_active_and_history_records():
    _document("DOC-1")
    _document("DOC-2")
    repository = DocumentExtractionRepository()
    first = repository.save_attempt(_attempt("DOC-1"))
    other = repository.save_attempt(_attempt("DOC-2", ExtractionStatus.NEEDS_REVIEW))
    replacement = repository.replace_active(_replacement(first))
    assert repository.get_active("DOC-1") == replacement
    assert repository.get_active("DOC-2") == other
    assert [record.attempt_number for record in repository.list_history("DOC-2")] == [1]
    assert len(repository.list_history("DOC-1")) == 2


@pytest.mark.parametrize("stale", ["active", "hash", "status"])
def test_stale_replacement_is_rejected_without_any_partial_state(stale):
    _document()
    repository = DocumentExtractionRepository()
    active = repository.save_attempt(_attempt())
    changes = {
        "active": {"expected_active_extraction_id": "missing-extraction"},
        "hash": {"source_file_hash": "f" * 64},
        "status": {"expected_processing_status": ProcessingStatus.PARSED},
    }[stale]
    with pytest.raises(ExtractionConflictError):
        repository.replace_active(_replacement(active, **changes))
    assert repository.get_active("DOC-1") == active
    assert repository.list_history("DOC-1") == [active]
    assert SourceDocumentRepository().get_by_document_id("DOC-1").processing_status == ProcessingStatus.EXTRACTED


def test_missing_active_replacement_is_not_silently_a_first_save():
    _document()
    repository = DocumentExtractionRepository()
    values = _attempt().model_dump(mode="python")
    replacement = ExtractionReplacement(**values, expected_active_extraction_id="missing-extraction")
    with pytest.raises(ExtractionConflictError):
        repository.replace_active(replacement)
    assert repository.list_history("DOC-1") == []


@pytest.mark.parametrize("stale", ["hash", "status"])
def test_first_save_checks_source_snapshot(stale):
    _document()
    changes = {"source_file_hash": "f" * 64} if stale == "hash" else {
        "expected_processing_status": ProcessingStatus.PARSED,
    }
    with pytest.raises(ExtractionConflictError):
        DocumentExtractionRepository().save_attempt(_attempt(**changes))
    assert _scalar("SELECT COUNT(*) FROM document_extractions") == 0


@pytest.mark.parametrize("timing", ["BEFORE", "AFTER"])
def test_metadata_failure_before_or_after_update_rolls_back_replacement(timing):
    _document()
    repository = DocumentExtractionRepository()
    active = repository.save_attempt(_attempt())
    source_before = SourceDocumentRepository().get_by_document_id("DOC-1")
    replacement = _replacement(active, ExtractionStatus.NEEDS_REVIEW)
    with closing(get_connection()) as connection, connection:
        connection.execute(f"""
            CREATE TRIGGER synthetic_metadata_abort {timing} UPDATE OF extraction_status
            ON source_documents BEGIN
                SELECT RAISE(ABORT, 'synthetic sensitive trigger message');
            END
        """)
    with pytest.raises(ExtractionPersistenceError) as error:
        repository.replace_active(replacement)
    assert "sensitive" not in str(error.value)
    assert repository.get_active("DOC-1") == active
    assert repository.list_history("DOC-1") == [active]
    assert SourceDocumentRepository().get_by_document_id("DOC-1") == source_before


def test_zero_metadata_rowcount_rolls_back_deactivation_and_insert():
    _document()
    repository = DocumentExtractionRepository()
    active = repository.save_attempt(_attempt())
    with closing(get_connection()) as connection, connection:
        connection.execute("""
            CREATE TRIGGER synthetic_ignore_metadata BEFORE UPDATE OF extraction_status
            ON source_documents BEGIN SELECT RAISE(IGNORE); END
        """)
    with pytest.raises(ExtractionPersistenceError):
        repository.replace_active(_replacement(active))
    assert repository.get_active("DOC-1") == active
    assert repository.list_history("DOC-1") == [active]


def test_commit_failure_after_metadata_update_rolls_back_and_closes(monkeypatch):
    import customs_ai.repositories.document_extractions as module

    _document()
    repository = DocumentExtractionRepository()
    active = repository.save_attempt(_attempt())
    replacement = _replacement(active, ExtractionStatus.NEEDS_REVIEW)
    observations = []
    opened = []

    class CommitFailureConnection(sqlite3.Connection):
        closed = False

        def commit(self):
            observations.append(self.execute(
                "SELECT processing_status FROM source_documents WHERE document_id = ?",
                ("DOC-1",),
            ).fetchone()[0])
            assert self.execute("SELECT COUNT(*) FROM document_extractions").fetchone()[0] == 2
            raise sqlite3.OperationalError("SYNTHETIC_PRIVATE_COMMIT_FAILURE")

        def close(self):
            self.closed = True
            return super().close()

    def connect():
        connection = sqlite3.connect(str(settings.db_path), factory=CommitFailureConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        opened.append(connection)
        return connection

    with monkeypatch.context() as patch:
        patch.setattr(module, "get_connection", connect)
        with pytest.raises(ExtractionPersistenceError) as error:
            repository.replace_active(replacement)
    assert observations == [ProcessingStatus.NEEDS_REVIEW.value]
    assert opened and all(connection.closed for connection in opened)
    assert "SYNTHETIC_PRIVATE_COMMIT_FAILURE" not in str(error.value)
    assert repository.get_active("DOC-1") == active
    assert repository.list_history("DOC-1") == [active]
    assert SourceDocumentRepository().get_by_document_id("DOC-1").processing_status == ProcessingStatus.EXTRACTED


def test_decimal_date_raw_origin_and_provenance_survive_repository_recreation():
    _document()
    original = _attempt(status=ExtractionStatus.NEEDS_REVIEW)
    record = DocumentExtractionRepository().save_attempt(original)
    fetched = DocumentExtractionRepository().get_by_extraction_id(record.extraction_id)
    assert fetched.result == original.result
    invoice = fetched.result.invoice
    assert invoice.total_amount.normalized_value.as_tuple() == Decimal("12345678901234567890.1200").as_tuple()
    assert invoice.invoice_date.normalized_value == date(2026, 10, 28)
    assert type(invoice.invoice_date.normalized_value) is date
    assert invoice.invoice_number.raw_value == " 000012 "
    assert invoice.invoice_number.normalized_value == "000012"
    assert invoice.invoice_number.origin == ValueOrigin.EXTRACTED
    assert invoice.items[0].quantity.normalized_value.as_tuple() == Decimal("0.000").as_tuple()
    assert invoice.items[0].item_code.cell == "C7"
    assert invoice.items[0].item_code.sheet == "Items"
    assert fetched.result.candidates[0].typed_value.as_tuple() == Decimal("12345678901234567890.1200").as_tuple()
    assert fetched.result.candidates[0].bounding_box == (0.1, 0.2, 0.3, 0.4)
    assert fetched.result.issues[0].is_review_required is True


def test_canonical_item_result_can_be_persisted_without_alternate_schema():
    _document()
    result = InvoiceItemExtractionResult(
        status=ExtractionStatus.NEEDS_REVIEW,
        items=_result().invoice.items,
        issues=[ExtractionIssue(code="ITEM_REVIEW", message="Synthetic issue.", is_review_required=True)],
    )
    saved = DocumentExtractionRepository().save_attempt(_attempt(result=result))
    fetched = DocumentExtractionRepository().get_active("DOC-1")
    assert type(fetched.result) is InvoiceItemExtractionResult
    assert fetched.result == result
    assert saved.status == ExtractionStatus.NEEDS_REVIEW


@pytest.mark.parametrize("method", ["get_by_extraction_id", "get_active", "list_history"])
@pytest.mark.parametrize("invalid", ["", "  ", None, 42])
def test_malformed_lookup_identifiers_are_rejected(method, invalid):
    with pytest.raises(ExtractionValidationError):
        getattr(DocumentExtractionRepository(), method)(invalid)


def test_unknown_identifiers_and_sql_like_identifiers_do_not_execute_sql():
    _document()
    repository = DocumentExtractionRepository()
    assert repository.get_by_extraction_id("00000000-0000-4000-8000-000000000001") is None
    assert repository.get_active("DOC-UNKNOWN") is None
    assert repository.list_history("DOC-UNKNOWN") == []
    assert repository.get_by_extraction_id("x'; DROP TABLE source_documents; --") is None
    assert SourceDocumentRepository().get_by_document_id("DOC-1") is not None


def test_history_order_uses_attempt_sequence_even_when_timestamps_tie():
    _document()
    repository = DocumentExtractionRepository()
    first = repository.save_attempt(_attempt())
    second = repository.replace_active(_replacement(first))
    third = repository.replace_active(_replacement(second))
    with closing(get_connection()) as connection, connection:
        connection.execute("UPDATE document_extractions SET created_at = ?", ("2026-10-28T00:00:00+00:00",))
    assert [r.extraction_id for r in repository.list_history("DOC-1")] == [
        first.extraction_id, second.extraction_id, third.extraction_id,
    ]


def test_mutated_nested_payload_is_revalidated_before_any_write():
    _document()
    attempt = _attempt()
    attempt.result.invoice.total_amount.normalized_value = "SYNTHETIC_INVALID_DECIMAL"
    with pytest.raises(ExtractionValidationError) as error:
        DocumentExtractionRepository().save_attempt(attempt)
    assert "SYNTHETIC_INVALID_DECIMAL" not in str(error.value)
    assert _scalar("SELECT COUNT(*) FROM document_extractions") == 0
    assert SourceDocumentRepository().get_by_document_id("DOC-1").processing_status == ProcessingStatus.CLASSIFIED


def test_corrupted_payload_is_validated_on_read_and_not_returned_as_arbitrary_json():
    _document()
    repository = DocumentExtractionRepository()
    saved = repository.save_attempt(_attempt())
    with closing(get_connection()) as connection, connection:
        connection.execute("UPDATE document_extractions SET payload_json = ? WHERE extraction_id = ?",
                           ('{"unexpected":"SYNTHETIC_PRIVATE_CONTENT"}', saved.extraction_id))
    with pytest.raises(ExtractionPersistenceError) as error:
        repository.get_by_extraction_id(saved.extraction_id)
    assert "SYNTHETIC_PRIVATE_CONTENT" not in str(error.value)


def test_serialized_status_inconsistent_with_database_record_is_rejected():
    _document()
    repository = DocumentExtractionRepository()
    saved = repository.save_attempt(_attempt())
    with closing(get_connection()) as connection, connection:
        connection.execute("UPDATE document_extractions SET status = ? WHERE extraction_id = ?",
                           (ExtractionStatus.NEEDS_REVIEW.value, saved.extraction_id))
    with pytest.raises(ExtractionPersistenceError):
        repository.get_active("DOC-1")


@pytest.mark.parametrize("replacement", [False, True])
def test_simultaneous_writers_have_one_winner_without_duplicate_active(replacement):
    _document()
    repository = DocumentExtractionRepository()
    if replacement:
        first = repository.save_attempt(_attempt())
        attempts = [_replacement(first), _replacement(first)]
    else:
        attempts = [_attempt(), _attempt()]
    barrier = Barrier(2)

    def write(attempt):
        barrier.wait(timeout=10)
        try:
            operation = repository.replace_active if replacement else repository.save_attempt
            return operation(attempt)
        except ExtractionConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(write, attempts))
    winners = [record for record in results if record is not None]
    assert len(winners) == 1
    assert repository.get_active("DOC-1") == winners[0]
    assert _scalar("SELECT COUNT(*) FROM document_extractions WHERE is_active = 1") == 1
    assert len(repository.list_history("DOC-1")) == (2 if replacement else 1)


def test_repository_connections_close_after_success_read_and_rollback(monkeypatch):
    import customs_ai.repositories.document_extractions as module

    _document()
    opened = []

    class TrackedConnection(sqlite3.Connection):
        closed = False

        def close(self):
            self.closed = True
            return super().close()

    def connect():
        connection = sqlite3.connect(str(settings.db_path), factory=TrackedConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        opened.append(connection)
        return connection

    monkeypatch.setattr(module, "get_connection", connect)
    repository = DocumentExtractionRepository()
    saved = repository.save_attempt(_attempt())
    repository.get_by_extraction_id(saved.extraction_id)
    repository.get_active("DOC-1")
    repository.list_history("DOC-1")
    with pytest.raises(ExtractionConflictError):
        repository.save_attempt(_attempt())
    assert len(opened) >= 5
    assert all(connection.closed for connection in opened)


def test_no_raw_payload_or_source_path_leaks_to_logs_or_error_messages(caplog, tmp_path):
    private_value = "SYNTHETIC_CUSTOMER_TAX_000001"
    private_path = tmp_path / private_value / "synthetic.pdf"
    _document(path=private_path)
    attempt = _attempt()
    attempt.result.invoice.invoice_number.raw_value = private_value
    attempt.result.invoice.invoice_number.normalized_value = private_value
    repository = DocumentExtractionRepository()
    repository.save_attempt(attempt)
    with pytest.raises(ExtractionConflictError) as error:
        repository.save_attempt(_attempt())
    combined = caplog.text + str(error.value)
    assert private_value not in combined
    assert str(private_path) not in combined
    assert "12345678901234567890.1200" not in combined


def test_persistence_does_not_open_or_modify_uploaded_source_file(tmp_path):
    source_path = tmp_path / "synthetic_original.pdf"
    source_path.write_bytes(b"%PDF-1.4\nsynthetic immutable source\n")
    before = source_path.read_bytes()
    _document(path=source_path)
    repository = DocumentExtractionRepository()
    first = repository.save_attempt(_attempt())
    repository.replace_active(_replacement(first, ExtractionStatus.FAILED))
    assert source_path.read_bytes() == before
    assert sha256(source_path.read_bytes()).digest() == sha256(before).digest()
