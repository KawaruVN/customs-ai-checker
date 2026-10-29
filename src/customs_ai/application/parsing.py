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
        try:
            parsed = self.parse_document_readonly(document_id)
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

    def parse_document_readonly(self, document_id: str) -> ParsedDocument:
        """Parse an authoritative source without changing processing metadata.

        Downstream extraction uses this path so parsing never downgrades a
        classified/extracted document to PARSED. The original parse_document
        operation retains its explicit metadata-writing behavior.
        """
        try:
            if not isinstance(document_id, str) or not document_id.strip() or document_id != document_id.strip():
                raise ParserFailedError()
            source = self.repository.get_by_document_id(document_id)
            if source is None:
                raise SourceDocumentNotFoundError()
            source_path = resolve_source_path(source.stored_path)
            parser = self.router.get_parser(source.file_type)
            parsed = parser.parse(document_id, source_path)
            if isinstance(parsed, ParsedPdfDocument):
                model = ParsedPdfDocument
            elif isinstance(parsed, ParsedWorkbook):
                model = ParsedWorkbook
            else:
                raise ParserFailedError()
            # Revalidate mutable nested models and model_construct results.
            validated = model.model_validate(parsed.model_dump(mode="python", warnings="error"))
            if validated.document_id != document_id or validated.file_type != source.file_type:
                raise ParserFailedError()
            return validated
        except ParserError as exc:
            # A path resolver/parser can attach private details as a cause.
            raise exc from None
        except Exception:
            raise ParserFailedError() from None
