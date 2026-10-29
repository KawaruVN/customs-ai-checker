"""Synthetic documents and real production entry points for invoice integration."""

import asyncio
from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
import openpyxl
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from starlette.datastructures import Headers

from customs_ai.application.composition import build_classification_service, build_invoice_extraction_service
from customs_ai.config import settings
from customs_ai.ingestion.service import IngestionService
from customs_ai.ingestion.validator import SUPPORTED_EXTENSIONS
from customs_ai.repositories.document_extractions import DocumentExtractionRepository
from customs_ai.repositories.source_documents import SourceDocumentRepository


class InvoicePipeline:
    """Fixture generation only; all business processing uses approved modules."""

    def __init__(self, tmp_path):
        self.directory = tmp_path / "synthetic-fixtures"
        self.directory.mkdir()
        self.repo = SourceDocumentRepository()
        self.extractions = DocumentExtractionRepository()

    @staticmethod
    def rows():
        return [
            ["COMMERCIAL INVOICE"],
            ["INVOICE NO", "0000456"],
            ["INVOICE DATE", "2026-10-29"],
            ["SELLER", "Synthetic Exporter"],
            ["BUYER", "Synthetic Importer"],
            ["SHIP TO", "Synthetic Receiver"],
            ["CURRENCY", "USD"],
            ["TOTAL AMOUNT", "123456789012345.1200"],
            ["FREIGHT", "2.50"],
            [],
            [None, None, "ITEM CODE", "DESCRIPTION", "QTY", "UNIT", "UNIT PRICE", "AMOUNT"],
            [None, None, "000009", "Synthetic control motor", "0.00", "PCS", "12.50", "0.00"],
            [None, None, "000010", "TOTAL CONTROL", "2.50", "PCS", "4.00", "10.00"],
            [],
            ["REMARKS", "Synthetic payment terms"],
        ]

    def xlsx(self, rows=None, *, filename="synthetic.xlsx", mutate=None):
        path = self.directory / filename
        book = openpyxl.Workbook()
        book.active.title = "Invoice Data"
        for row in self.rows() if rows is None else rows:
            book.active.append(row)
        if mutate is not None:
            mutate(book)
        book.save(path)
        book.close()
        return path

    def xls(self, rows=None, *, filename="synthetic.xls"):
        import xlwt
        path = self.directory / filename
        book = xlwt.Workbook()
        sheet = book.add_sheet("Invoice Data")
        for r, values in enumerate(self.rows() if rows is None else rows):
            for c, value in enumerate(values):
                if value is not None:
                    if isinstance(value, date):
                        sheet.write(r, c, value, xlwt.easyxf(num_format_str="YYYY-MM-DD"))
                    else:
                        sheet.write(r, c, value)
        book.save(str(path))
        return path

    def pdf(self, pages=None, *, filename="synthetic.pdf"):
        if pages is None:
            pages = [
                "COMMERCIAL INVOICE\nINVOICE NO: 0000456\nINVOICE DATE: 2026-10-29\nSELLER: Synthetic Exporter\nBUYER: Synthetic Importer",
                "TOTAL AMOUNT: 123456789012345.1200\nCURRENCY: USD\nSynthetic invoice page two",
            ]
        path = self.directory / filename
        writer = PdfWriter()
        for text in pages:
            page = writer.add_blank_page(width=612, height=792)
            if text:
                font = DictionaryObject({
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                })
                page[NameObject("/Resources")] = DictionaryObject({
                    NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
                })
                def literal(line):
                    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                commands = " 0 -16 Td ".join(f"({literal(line)}) Tj" for line in text.splitlines())
                stream = DecodedStreamObject()
                stream.set_data(("BT /F1 10 Tf 40 740 Td " + commands + " ET").encode("latin-1"))
                page[NameObject("/Contents")] = writer._add_object(stream)
        with path.open("wb") as handle:
            writer.write(handle)
        return path

    def register(self, path, *, filename=None, shipment_id="SHP-INTEGRATION"):
        upload = UploadFile(
            file=BytesIO(path.read_bytes()), filename=filename or path.name,
            headers=Headers({"content-type": SUPPORTED_EXTENSIONS[path.suffix]}),
        )
        try:
            response, status = asyncio.run(IngestionService(self.repo).ingest(shipment_id, upload))
        finally:
            upload.file.close()
        assert status == 201
        source = self.repo.get_by_document_id(response.document_id)
        assert source.file_hash == sha256(path.read_bytes()).hexdigest()
        assert Path(source.stored_path).resolve().is_relative_to(settings.upload_root.resolve())
        return source

    def classify(self, document_id):
        return build_classification_service(self.repo).classify_document(document_id)

    def extract(self, document_id, *, semantic_provider=None, **preconditions):
        service = build_invoice_extraction_service(self.repo, semantic_provider=semantic_provider)
        return service.extract_document(document_id, **preconditions)

    def source_bytes(self, document_id):
        return Path(self.repo.get_by_document_id(document_id).stored_path).read_bytes()


@pytest.fixture
def invoice_pipeline(tmp_path, monkeypatch):
    # Vision integration tests deliberately replace the factory with controlled
    # local doubles; other tests must never initialize optional OCR engines.
    monkeypatch.setattr(settings.vision, "enabled", False)
    return InvoicePipeline(tmp_path)
