from pathlib import Path

from customs_ai.application.parsing import DocumentParsingService
from customs_ai.classification.config import load_classification_config
from customs_ai.classification.deterministic import DeterministicClassifier
from customs_ai.classification.enums import DocumentType
from customs_ai.classification.service import DocumentClassificationService
from customs_ai.config import settings
from customs_ai.parsers.router import ParserRouter
from customs_ai.repositories.source_documents import SourceDocumentRepository


def _create_mock_pdf_in_repo(tmp_path: Path, document_id: str, text: str) -> None:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    doc_dir = settings.upload_root / "SHP-INTEGRATION" / document_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_path = doc_dir / "original.pdf"

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)

    with open(file_path, "wb") as handle:
        writer.write(handle)

    repo = SourceDocumentRepository()
    from datetime import datetime, timezone
    from customs_ai.ingestion.enums import ProcessingStatus
    from customs_ai.ingestion.models import SourceDocument
    
    doc = SourceDocument(
        document_id=document_id,
        shipment_id="SHP-INTEGRATION",
        original_filename="invoice_filename.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_hash=document_id,
        file_size=file_path.stat().st_size,
        stored_path=str(file_path.resolve()),
        upload_time=datetime.now(timezone.utc),
        processing_status=ProcessingStatus.UPLOADED,
    )
    repo.create(doc)


def test_full_classification_pipeline_content_overrides_filename(tmp_path):
    # Filename says "invoice_filename.pdf", but content says "PACKING LIST". Content MUST win.
    _create_mock_pdf_in_repo(tmp_path, "DOC-INT-1", "PACKING LIST 12345")
    
    repo = SourceDocumentRepository()
    parsing_service = DocumentParsingService(repo, ParserRouter())
    classifier = DeterministicClassifier(load_classification_config())
    classification_service = DocumentClassificationService(repo, parsing_service, classifier)

    result = classification_service.classify_document("DOC-INT-1")

    assert result.document_type == DocumentType.PACKING_LIST
    assert result.confidence > 0.5

    db_doc = repo.get_by_document_id("DOC-INT-1")
    assert db_doc.detected_document_type == "PACKING_LIST"
    assert db_doc.processing_status.value == "CLASSIFIED"
    assert db_doc.page_count == 1
    assert db_doc.parser_used == "pypdf"
