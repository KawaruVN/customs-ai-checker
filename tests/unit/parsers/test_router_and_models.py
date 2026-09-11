from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from customs_ai.parsers.errors import ParserUnsupportedError
from customs_ai.parsers.excel import XlsParser, XlsxParser
from customs_ai.parsers.models import ParsedPdfDocument
from customs_ai.parsers.pdf import PdfParser
from customs_ai.parsers.router import ParserRouter


def test_router_selects_trusted_file_type():
    router = ParserRouter()
    assert isinstance(router.get_parser("pdf"), PdfParser)
    assert isinstance(router.get_parser(".XLSX"), XlsxParser)
    assert isinstance(router.get_parser("xls"), XlsParser)


@pytest.mark.parametrize("file_type", ["csv", "docx", "jpg", "png"])
def test_router_rejects_unsupported_task004_types(file_type):
    with pytest.raises(ParserUnsupportedError) as exc:
        ParserRouter().get_parser(file_type)
    assert exc.value.code == "PARSER_UNSUPPORTED"


def test_parser_output_models_forbid_extra_fields():
    with pytest.raises(ValidationError):
        ParsedPdfDocument(
            document_id="DOC-1",
            page_count=0,
            has_text_layer=False,
            needs_ocr=True,
            pages=[],
            unexpected="nope",
        )


def test_parser_output_is_json_serializable():
    parsed = ParsedPdfDocument(
        document_id="DOC-1",
        page_count=0,
        has_text_layer=False,
        needs_ocr=True,
        pages=[],
    )
    assert '"document_id":"DOC-1"' in parsed.model_dump_json()
