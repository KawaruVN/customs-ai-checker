from customs_ai.application.paths import resolve_source_path
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.parsers.errors import (
    ParserError,
    ParserFailedError,
    SourceDocumentNotFoundError,
)
from customs_ai.parsers.models import ParsedDocument, ParsedPdfDocument, ParsedWorkbook
from customs_ai.parsers.router import ParserRouter
from customs_ai.repositories.source_documents import SourceDocumentRepository


class DocumentParsingService:
    def __init__(
        self,
        repository: SourceDocumentRepository,
        router: ParserRouter | None = None,
    ) -> None:
        self.repository = repository
        self.router = router or ParserRouter()

    def parse_document(self, document_id: str) -> ParsedDocument:
        source_document = self.repository.get_by_document_id(document_id)
        if source_document is None:
            raise SourceDocumentNotFoundError()

        source_path = resolve_source_path(source_document.stored_path)
        parser = self.router.get_parser(source_document.file_type)

        try:
            parsed = parser.parse(document_id, source_path)
            if isinstance(parsed, ParsedPdfDocument):
                self.repository.update_parsing_metadata(
                    document_id=document_id,
                    processing_status=ProcessingStatus.PARSED,
                    parser_used=parsed.parser_used,
                    page_count=parsed.page_count,
                    sheet_count=None,
                )
            elif isinstance(parsed, ParsedWorkbook):
                self.repository.update_parsing_metadata(
                    document_id=document_id,
                    processing_status=ProcessingStatus.PARSED,
                    parser_used=parsed.parser_used,
                    page_count=None,
                    sheet_count=parsed.sheet_count,
                )
            else:  # pragma: no cover - router/parser contract guard
                raise ParserFailedError()
            return parsed
        except ParserError:
            raise
        except Exception as exc:
            raise ParserFailedError() from exc
