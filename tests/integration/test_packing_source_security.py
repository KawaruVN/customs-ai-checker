"""Source containment and privacy faults after genuine upload/classification."""

import ast
from contextlib import closing
from pathlib import Path

import pytest

from customs_ai.application.parsing import DocumentParsingService
from customs_ai.classification.enums import DocumentType
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.packing_headers import DeterministicPackingHeaderExtractor
from customs_ai.extraction.packing_items import DeterministicPackingItemExtractor
from customs_ai.repositories.database import get_connection
from customs_ai.repositories.document_extractions import DocumentExtractionRepository
from customs_ai.repositories.source_documents import SourceDocumentRepository


def prepare(p):
    source = p.register(p.xlsx())
    assert p.classify(source.document_id).document_type == DocumentType.PACKING_LIST
    return source


def update_path(source, stored_path):
    with closing(get_connection()) as connection, connection:
        connection.execute("UPDATE source_documents SET stored_path=? WHERE document_id=?", (str(stored_path), source.document_id))


def assert_refused(p, source, before, outcome):
    assert not outcome.persisted and outcome.record is None
    assert p.extractions.list_history(source.document_id) == []
    assert p.repo.get_by_document_id(source.document_id) == before


def test_relative_traversal_to_identical_bytes_outside_upload_root_is_refused(packing_pipeline, tmp_path, caplog):
    from customs_ai.config import settings
    p = packing_pipeline
    source = prepare(p)
    original = p.source_bytes(source.document_id)
    outside = settings.upload_root.parent / "PRIVATE_SOURCE_SENTINEL.xlsx"
    outside.write_bytes(original)
    update_path(source, "../PRIVATE_SOURCE_SENTINEL.xlsx")
    before = p.repo.get_by_document_id(source.document_id)
    outcome = p.extract(source.document_id)
    assert_refused(p, source, before, outcome)
    assert Path(source.stored_path).read_bytes() == original and outside.read_bytes() == original
    assert "PRIVATE_SOURCE_SENTINEL" not in str(outcome.result.issues) + caplog.text
    assert str(outside) not in caplog.text


def test_real_directory_link_escape_is_refused_even_with_correct_source_hash(packing_pipeline, tmp_path, caplog):
    from customs_ai.config import settings
    p = packing_pipeline
    source = prepare(p)
    original = p.source_bytes(source.document_id)
    outside = tmp_path / "outside-upload"
    outside.mkdir()
    (outside / "original.xlsx").write_bytes(original)
    link = settings.upload_root / "escape-link"
    assert outside.resolve().is_relative_to(tmp_path.resolve())
    assert link.parent.resolve().is_relative_to(settings.upload_root.resolve())
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        if getattr(error, "winerror", None) != 1314:
            raise
        # Restricted Windows accounts lack symbolic-link privilege. An actual
        # NTFS junction exercises the same resolved directory-escape boundary.
        import _winapi
        _winapi.CreateJunction(str(outside), str(link))
        assert link.is_junction()
    try:
        assert (link / "original.xlsx").resolve() == (outside / "original.xlsx").resolve()
        update_path(source, link / "original.xlsx")
        before = p.repo.get_by_document_id(source.document_id)
        outcome = p.extract(source.document_id)
        assert_refused(p, source, before, outcome)
        assert Path(source.stored_path).read_bytes() == original
        assert (outside / "original.xlsx").read_bytes() == original
        assert str(outside) not in caplog.text + str(outcome.result.issues)
    finally:
        if link.is_junction():
            link.rmdir()
        else:
            link.unlink()


def test_missing_uploaded_file_creates_no_attempt_or_metadata_change(packing_pipeline):
    p = packing_pipeline
    source = prepare(p)
    path = Path(source.stored_path)
    original = path.read_bytes()
    before = p.repo.get_by_document_id(source.document_id)
    path.unlink()
    try:
        outcome = p.extract(source.document_id)
        assert_refused(p, source, before, outcome)
    finally:
        path.write_bytes(original)
    p.assert_immutable(source)


def test_changed_uploaded_bytes_are_refused_without_overwriting_them(packing_pipeline):
    p = packing_pipeline
    source = prepare(p)
    path = Path(source.stored_path)
    original = path.read_bytes()
    altered = original + b"SYNTHETIC_EXTERNAL_CHANGE"
    path.write_bytes(altered)
    before = p.repo.get_by_document_id(source.document_id)
    try:
        outcome = p.extract(source.document_id)
        assert_refused(p, source, before, outcome)
        assert path.read_bytes() == altered
    finally:
        path.write_bytes(original)
    p.assert_immutable(source)


@pytest.mark.parametrize("component", ["parser", "header", "items"])
def test_private_execution_exceptions_commit_only_sanitized_failed_attempt(packing_pipeline, monkeypatch, caplog, component):
    p = packing_pipeline
    source = prepare(p)
    before = p.repo.get_by_document_id(source.document_id)
    sentinel = "PRIVATE_COMMERCIAL_SENTINEL_000987"
    def fail(*args, **kwargs):
        raise RuntimeError(sentinel + source.stored_path)
    with monkeypatch.context() as patch:
        owner, method = {
            "parser": (DocumentParsingService, "parse_document_readonly"),
            "header": (DeterministicPackingHeaderExtractor, "extract"),
            "items": (DeterministicPackingItemExtractor, "extract"),
        }[component]
        patch.setattr(owner, method, fail)
        outcome = p.extract(source.document_id)
    assert outcome.persisted and outcome.result.status == ExtractionStatus.FAILED
    assert not outcome.record.is_active and outcome.active_record is None
    p.assert_roundtrip(source, outcome)
    latest = p.repo.get_by_document_id(source.document_id)
    assert latest.processing_status.value == latest.extraction_status == "FAILED"
    assert latest.parser_used == before.parser_used
    assert sentinel not in caplog.text + str(outcome.result.issues)
    assert source.stored_path not in caplog.text + str(outcome.result.issues)


def test_authoritative_source_id_cannot_be_substituted_by_repository_fault(packing_pipeline, monkeypatch):
    p = packing_pipeline
    source = prepare(p)
    other_rows = p.rows()
    other_rows[1][1] = "0000999"
    other = p.register(p.xlsx(other_rows, filename="other.xlsx"))
    original_get = SourceDocumentRepository.get_by_document_id
    def wrong_identity(repository, document_id):
        return original_get(repository, other.document_id if document_id == source.document_id else document_id)
    with monkeypatch.context() as patch:
        patch.setattr(SourceDocumentRepository, "get_by_document_id", wrong_identity)
        outcome = p.extract(source.document_id)
    assert not outcome.persisted
    assert p.extractions.list_history(source.document_id) == []
    assert p.extractions.list_history(other.document_id) == []
    p.assert_immutable(source)
    p.assert_immutable(other)


def test_application_service_contains_no_sql_or_sqlite_access():
    root = Path(__file__).resolve().parents[2]
    path = root / "src" / "customs_ai" / "application" / "packing_extraction.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name != "sqlite3" for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module not in {"sqlite3", "customs_ai.repositories.database"}
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not node.value.lstrip().upper().startswith(("SELECT ", "INSERT ", "UPDATE ", "DELETE ", "BEGIN IMMEDIATE"))
