"""Packing v2 and shared repository invariants against isolated real SQLite."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date, datetime, time, timezone
from decimal import Decimal
from hashlib import sha256
import json
import sqlite3
from threading import Barrier

import pytest

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, Invoice, PackingList, PackingItem
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.models import ExtractionCandidate, InvoiceHeaderExtractionResult, InvoiceItemExtractionResult
from customs_ai.extraction.packing_models import PackingListHeaderExtractionResult, PackingItemExtractionResult
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.models import SourceDocument
from customs_ai.repositories.database import get_connection
from customs_ai.repositories.document_extractions import DocumentExtractionRepository, ExtractionConflictError, ExtractionCorruptionError, ExtractionPersistenceError
from customs_ai.repositories.extraction_models import ExtractionAttempt, ExtractionReplacement, ExtractionRecord, serialize_result, deserialize_result
from customs_ai.repositories.source_documents import SourceDocumentRepository


DOC = "PACK-STORAGE"


def field(value, raw, doc=DOC, **where):
    return CanonicalField(origin=ValueOrigin.EXTRACTED, normalized_value=value, raw_value=raw,
                          source_document_id=doc, extraction_method="synthetic", confidence=0.95, **where)


def result(status=ExtractionStatus.EXTRACTED, doc=DOC):
    return PackingListHeaderExtractionResult(status=status, packing_list=PackingList(
        packing_list_number=field("000012", "000012", doc, page=2),
        date=field(date(2026, 10, 29), "2026/10/29", doc, page=1),
        gross_weight=field(Decimal("12345678901234567890.1200"), "12345678901234567890.1200", doc, page=2),
        invoice_references=[field("000045", "000045", doc, page=1), field("发票-000046", "发票-000046", doc, page=2)],
        items=[PackingItem(description=field("Động cơ 电机", "Động cơ 电机", doc, sheet="货物", cell="B8"),
                           quantity=field(Decimal("0.000"), "0.000", doc, sheet="货物", cell="C8"),
                           net_weight=field(Decimal("-2.50"), "-2.50", doc, sheet="货物", cell="D8"))],
    ), candidates=[ExtractionCandidate(field_path="header.gross_weight", raw_value="12345678901234567890.1200",
         typed_value=Decimal("12345678901234567890.1200"), source_document_id=doc, page=2,
         bounding_box=(0.1, 0.2, 0.3, 0.4), extraction_method="synthetic", confidence=0.9)])


def source(doc=DOC, kind="PACKING_LIST"):
    value = SourceDocument(document_id=doc, shipment_id="SHP-SYNTHETIC", original_filename="synthetic.xlsx",
        file_type="xlsx", mime_type="application/octet-stream", file_hash=sha256(doc.encode()).hexdigest(),
        file_size=1, stored_path="synthetic.xlsx", upload_time=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.CLASSIFIED, detected_document_type=kind, classification_confidence=0.9)
    SourceDocumentRepository().create(value)
    return value


def attempt(status=ExtractionStatus.EXTRACTED, doc=DOC, **updates):
    src = SourceDocumentRepository().get_by_document_id(doc)
    data = dict(document_id=doc, source_file_hash=src.file_hash,
                expected_processing_status=src.processing_status, expected_source_document=src,
                result=result(status, doc))
    data.update(updates)
    return ExtractionAttempt(**data)


def replace(active, status=ExtractionStatus.EXTRACTED, **updates):
    return ExtractionReplacement(**attempt(status, active.document_id, **updates).model_dump(mode="python"),
                                 expected_active_extraction_id=active.extraction_id)


def sql(query, params=()):
    with closing(get_connection()) as connection, connection:
        return connection.execute(query, params).fetchall()


@pytest.mark.parametrize("typed", [None, True, False, 0, -99, 0.0, 1.25, "000012", "2026-10-29",
    Decimal("0.000"), Decimal("-12345678901234567890.1200"), date(2026, 10, 29),
    datetime(2026, 10, 29, 1, 2, 3), datetime(2026, 10, 29, tzinfo=timezone.utc),
    time(12, 34, 56), time(12, 34, tzinfo=timezone.utc)])
def test_v2_lossless_typed_values_and_canonical_source_through_sqlite(typed):
    source()
    value = result()
    value.candidates[0].typed_value = typed
    record = DocumentExtractionRepository().save_attempt(attempt(result=value))
    restored = DocumentExtractionRepository().get_by_extraction_id(record.extraction_id)
    assert restored == record
    actual = restored.result.candidates[0].typed_value
    assert type(actual) is type(typed) and actual == typed
    if isinstance(typed, Decimal):
        assert actual.as_tuple() == typed.as_tuple()
    assert restored.result.packing_list.date.normalized_value == date(2026, 10, 29)
    assert restored.result.packing_list.gross_weight.normalized_value.as_tuple() == Decimal("12345678901234567890.1200").as_tuple()
    assert restored.result.packing_list.items[0].quantity.normalized_value.as_tuple() == Decimal("0.000").as_tuple()
    assert len(restored.result.packing_list.invoice_references) == 2
    assert restored.schema_version == "0.1"
    wire = json.loads(sql("SELECT payload_json FROM document_extractions")[0][0])
    assert (wire["format_version"], wire["result_type"]) == (2, "packing_list")


@pytest.mark.parametrize("model", [InvoiceHeaderExtractionResult, InvoiceItemExtractionResult])
def test_invoice_v1_rows_stay_v1_and_byte_identical_after_packing_write(model):
    src = source("INVOICE", "COMMERCIAL_INVOICE")
    value = model(status=ExtractionStatus.NEEDS_REVIEW, **({"invoice": Invoice()} if model is InvoiceHeaderExtractionResult else {}))
    legacy = serialize_result(value)
    assert json.loads(legacy)["format_version"] == 1
    record = DocumentExtractionRepository().save_attempt(ExtractionAttempt(document_id=src.document_id,
        source_file_hash=src.file_hash, expected_processing_status=src.processing_status, result=value))
    source()
    DocumentExtractionRepository().save_attempt(attempt())
    assert sql("SELECT payload_json FROM document_extractions WHERE extraction_id=?", (record.extraction_id,))[0][0] == legacy
    assert DocumentExtractionRepository().get_by_extraction_id(record.extraction_id).result == value


@pytest.mark.parametrize("version,kind", [(1,"packing_list"),(2,"invoice"),(2,"invoice_items"),(3,"packing_list"),(True,"packing_list"),(2,"unknown")])
def test_unsupported_version_discriminator_pairs_fail_closed(version, kind):
    wire = json.loads(serialize_result(result()))
    wire.update(format_version=version, result_type=kind)
    with pytest.raises(ValueError, match="Invalid serialized"):
        deserialize_result(json.dumps(wire))


@pytest.mark.parametrize("mutation", ["missing_type","extra_key","wrong_status","wrong_decimal","wrong_date","wrong_tag","missing_tag","wrong_payload","coerced_decimal","missing_field"])
def test_malformed_or_coerced_packing_envelopes_are_rejected(mutation):
    wire = json.loads(serialize_result(result()))
    data = wire["result"]
    if mutation == "missing_type": del wire["result_type"]
    elif mutation == "extra_key": wire["unexpected"] = 1
    elif mutation == "wrong_status": data["status"] = "PASS"
    elif mutation == "wrong_decimal": data["packing_list"]["gross_weight"]["normalized_value"] = "NaN"
    elif mutation == "wrong_date": data["packing_list"]["date"]["normalized_value"] = "2026-02-30"
    elif mutation == "wrong_tag": data["candidates"][0]["typed_value"] = {"type":"bool","value":1}
    elif mutation == "missing_tag": del data["candidates"][0]["typed_value"]
    elif mutation == "wrong_payload": data["invoice"] = data.pop("packing_list")
    elif mutation == "coerced_decimal": data["packing_list"]["items"][0]["quantity"]["normalized_value"] = 0
    elif mutation == "missing_field": del data["packing_list"]["items"]
    with pytest.raises(ValueError): deserialize_result(json.dumps(wire))


@pytest.mark.parametrize("wire", ['{"format_version":2,"format_version":2,"result_type":"packing_list","result":{}}',
    '{"format_version":2,"result_type":"packing_list","result":{"x":1,"x":2}}', "NaN", "[]", "null"])
def test_duplicate_keys_and_nonobject_json_are_rejected(wire):
    with pytest.raises(ValueError): deserialize_result(wire)


def test_item_only_packing_is_not_a_composed_storage_contract():
    with pytest.raises(ValueError): serialize_result(PackingItemExtractionResult(status=ExtractionStatus.NEEDS_REVIEW))


@pytest.mark.parametrize("status", list(ExtractionStatus))
def test_first_attempt_and_explicit_history_replacement(status):
    source()
    repo = DocumentExtractionRepository()
    first = repo.save_attempt(attempt(status))
    assert first.is_active == (status != ExtractionStatus.FAILED)
    assert SourceDocumentRepository().get_by_document_id(DOC).processing_status.value == status.value
    second = repo.replace_active(replace(first)) if first.is_active else repo.save_attempt(attempt())
    assert second.attempt_number == 2 and second.is_active
    assert [r.attempt_number for r in repo.list_history(DOC)] == [1,2]
    assert sum(r.is_active for r in repo.list_history(DOC)) == 1


def test_failed_replacement_keeps_prior_active_and_latest_status_separate():
    source(); repo = DocumentExtractionRepository(); first = repo.save_attempt(attempt())
    failed = repo.replace_active(replace(first, ExtractionStatus.FAILED))
    assert not failed.is_active and failed.supersedes_extraction_id is None
    assert repo.get_active(DOC) == first
    assert SourceDocumentRepository().get_by_document_id(DOC).processing_status == ProcessingStatus.FAILED
    assert repo.list_history(DOC)[1] == failed


@pytest.mark.parametrize("change", ["hash","status","filename","classification"])
def test_full_source_snapshot_cas_rejects_stale_attempt_without_writes(change):
    source(); value = attempt()
    column, new = {"hash":("file_hash", "0"*64), "status":("processing_status","FAILED"),
                   "filename":("original_filename","changed.xlsx"), "classification":("classification_confidence",0.8)}[change]
    # Column names are test constants, values stay parameterized.
    sql(f"UPDATE source_documents SET {column}=? WHERE document_id=?", (new,DOC))
    with pytest.raises(ExtractionConflictError): DocumentExtractionRepository().save_attempt(value)
    assert sql("SELECT count(*) FROM document_extractions")[0][0] == 0


def test_missing_and_stale_active_ids_never_overwrite():
    source(); repo=DocumentExtractionRepository(); first=repo.save_attempt(attempt())
    with pytest.raises(ExtractionConflictError): repo.save_attempt(attempt())
    stale=replace(first); stale.expected_active_extraction_id="STALE"
    with pytest.raises(ExtractionConflictError): repo.replace_active(stale)
    assert repo.list_history(DOC)==[first]


@pytest.mark.parametrize("event", ["BEFORE INSERT ON document_extractions", "AFTER INSERT ON document_extractions",
    "AFTER UPDATE OF is_active ON document_extractions", "BEFORE UPDATE OF processing_status ON source_documents",
    "AFTER UPDATE OF processing_status ON source_documents"])
def test_sqlite_trigger_abort_rolls_back_deactivation_insert_and_metadata(event):
    source(); repo=DocumentExtractionRepository(); first=repo.save_attempt(attempt())
    before=SourceDocumentRepository().get_by_document_id(DOC)
    sql(f"CREATE TRIGGER synthetic_abort {event} BEGIN SELECT RAISE(ABORT,'SYNTHETIC PRIVATE'); END")
    with pytest.raises(ExtractionPersistenceError) as error: repo.replace_active(replace(first))
    assert "SYNTHETIC PRIVATE" not in str(error.value)
    assert repo.get_active(DOC)==first and repo.list_history(DOC)==[first]
    assert SourceDocumentRepository().get_by_document_id(DOC)==before


def test_two_real_sqlite_writers_cannot_both_replace_same_active():
    source(); repo=DocumentExtractionRepository(); first=repo.save_attempt(attempt()); pending=replace(first)
    barrier=Barrier(2)
    def write():
        barrier.wait()
        try: return DocumentExtractionRepository().replace_active(pending)
        except ExtractionConflictError: return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:write(),range(2)))
    assert sum(r is not None for r in results)==1
    history=repo.list_history(DOC)
    assert [r.attempt_number for r in history]==[1,2] and sum(r.is_active for r in history)==1


@pytest.mark.parametrize("kind", [None,"COMMERCIAL_INVOICE","UNKNOWN"])
def test_packing_result_cannot_be_written_to_other_document_type(kind):
    source(kind=kind)
    with pytest.raises(ExtractionConflictError): DocumentExtractionRepository().save_attempt(attempt())
    assert sql("SELECT count(*) FROM document_extractions")[0][0]==0


def test_invoice_result_cannot_replace_active_packing_even_when_failed():
    source(); repo=DocumentExtractionRepository(); first=repo.save_attempt(attempt())
    wrong=InvoiceHeaderExtractionResult(invoice=Invoice(),status=ExtractionStatus.FAILED)
    with pytest.raises(ExtractionConflictError): repo.replace_active(replace(first,result=wrong))
    assert repo.get_active(DOC)==first


@pytest.mark.parametrize("tamper", ["source","status","type"])
def test_tampered_storage_provenance_status_or_type_fails_closed(tamper):
    source(); repo=DocumentExtractionRepository(); saved=repo.save_attempt(attempt())
    wire=json.loads(serialize_result(saved.result))
    if tamper=="source": wire["result"]["packing_list"]["date"]["source_document_id"]="OTHER"
    elif tamper=="type":
        wire.update(format_version=1,result_type="invoice")
    if tamper=="status": sql("UPDATE document_extractions SET status='FAILED',is_active=0")
    else: sql("UPDATE document_extractions SET payload_json=?",(json.dumps(wire),))
    with pytest.raises(ExtractionCorruptionError): repo.get_by_extraction_id(saved.extraction_id)


def test_mutated_nested_canonical_provenance_is_revalidated_before_insert():
    source(); pending=attempt(); pending.result.packing_list.date.source_document_id="OTHER"
    with pytest.raises(ExtractionPersistenceError): DocumentExtractionRepository().save_attempt(pending)
    assert sql("SELECT count(*) FROM document_extractions")[0][0]==0


def test_commit_failure_after_all_packing_updates_rolls_back_and_closes(monkeypatch):
    from customs_ai.config import settings
    import customs_ai.repositories.document_extractions as module
    source(); repo=DocumentExtractionRepository(); first=repo.save_attempt(attempt())
    pending=replace(first,ExtractionStatus.NEEDS_REVIEW); opened=[]; observations=[]
    class BrokenCommit(sqlite3.Connection):
        closed=False
        def commit(self):
            observations.append(self.execute("SELECT processing_status FROM source_documents").fetchone()[0])
            assert self.execute("SELECT count(*) FROM document_extractions").fetchone()[0]==2
            raise sqlite3.OperationalError("SYNTHETIC PRIVATE COMMIT")
        def close(self): self.closed=True; return super().close()
    def connect():
        connection=sqlite3.connect(str(settings.db_path),factory=BrokenCommit)
        connection.row_factory=sqlite3.Row; connection.execute("PRAGMA foreign_keys=ON"); opened.append(connection)
        return connection
    with monkeypatch.context() as patch:
        patch.setattr(module,"get_connection",connect)
        with pytest.raises(ExtractionPersistenceError) as error: repo.replace_active(pending)
    assert observations==["NEEDS_REVIEW"] and all(c.closed for c in opened)
    assert "SYNTHETIC PRIVATE COMMIT" not in str(error.value)
    assert repo.get_active(DOC)==first and repo.list_history(DOC)==[first]
    assert SourceDocumentRepository().get_by_document_id(DOC).processing_status==ProcessingStatus.EXTRACTED


def test_unique_active_attempt_sequence_and_foreign_keys_still_protect_packing():
    source(); repo=DocumentExtractionRepository(); first=repo.save_attempt(attempt())
    for assignments,parameters in [
        ("extraction_id=?",("COPY-1",)),
        ("extraction_id=?,attempt_number=2",("COPY-2",)),
        ("extraction_id=?,document_id='MISSING',attempt_number=2,is_active=0",("COPY-3",)),
    ]:
        # Actual constraints are exercised by INSERT SELECT; assignment variants are test constants.
        original=dict(sql("SELECT * FROM document_extractions")[0])
        original["extraction_id"]=parameters[0]
        if "attempt_number=2" in assignments: original["attempt_number"]=2
        if "MISSING" in assignments: original.update(document_id="MISSING",is_active=0)
        columns=",".join(original); placeholders=",".join("?" for _ in original)
        with pytest.raises(sqlite3.IntegrityError): sql(f"INSERT INTO document_extractions({columns}) VALUES({placeholders})",tuple(original.values()))
    assert repo.list_history(DOC)==[first]


def test_corrupt_missing_unique_active_index_fails_closed_on_read():
    source(); repo=DocumentExtractionRepository(); repo.save_attempt(attempt())
    sql("DROP INDEX one_active_extraction_per_document")
    sql("""INSERT INTO document_extractions SELECT 'SECOND',document_id,2,payload_json,status,
        is_active,created_at,schema_version,extraction_method,source_file_hash,NULL FROM document_extractions""")
    with pytest.raises(ExtractionCorruptionError): repo.get_active(DOC)
    with pytest.raises(ExtractionCorruptionError): repo.list_history(DOC)


def test_history_keeps_different_rows_same_family_and_no_ddl_migration():
    before=[tuple(row) for row in sql("SELECT type,name,sql FROM sqlite_master ORDER BY name")]
    source(); repo=DocumentExtractionRepository(); first=repo.save_attempt(attempt())
    second=repo.replace_active(replace(first,ExtractionStatus.NEEDS_REVIEW))
    repo.replace_active(replace(second,ExtractionStatus.FAILED))
    after=[tuple(row) for row in sql("SELECT type,name,sql FROM sqlite_master ORDER BY name")]
    assert before==after
    assert [r.attempt_number for r in repo.list_history(DOC)]==[1,2,3]
    assert repo.get_active(DOC)==second


@pytest.mark.parametrize("tag", [{"type":"decimal","value":"1.2000x"},{"type":"decimal","value":"Infinity"},
    {"type":"date","value":"2026-02-30"},{"type":"datetime","value":"2026-10-29"},
    {"type":"time","value":"25:00:00"},{"type":"unknown","value":"text"}])
def test_corrupt_typed_value_encodings_fail_closed(tag):
    wire=json.loads(serialize_result(result())); wire["result"]["candidates"][0]["typed_value"]=tag
    with pytest.raises(ValueError): deserialize_result(json.dumps(wire))


def test_historical_discriminator_survives_later_source_reclassification():
    source(); repo=DocumentExtractionRepository(); saved=repo.save_attempt(attempt())
    sql("UPDATE source_documents SET detected_document_type='COMMERCIAL_INVOICE'")
    assert repo.get_active(DOC)==saved and repo.list_history(DOC)==[saved]
    wrong=InvoiceHeaderExtractionResult(invoice=Invoice(),status=ExtractionStatus.FAILED)
    with pytest.raises(ExtractionConflictError): repo.replace_active(replace(saved,result=wrong))
    assert repo.get_active(DOC)==saved


def test_stored_packing_application_method_cannot_be_relabelled_as_invoice():
    source(); repo=DocumentExtractionRepository()
    saved=repo.save_attempt(attempt(extraction_method="packing_extraction_service"))
    invoice=InvoiceHeaderExtractionResult(invoice=Invoice(),status=ExtractionStatus.EXTRACTED)
    sql("UPDATE document_extractions SET payload_json=?",(serialize_result(invoice),))
    with pytest.raises(ExtractionCorruptionError): repo.get_by_extraction_id(saved.extraction_id)
