from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from customs_ai.parsers.errors import FileCorruptedError, ParserFailedError, PdfEncryptedError
from customs_ai.parsers.models import ParsedPdfDocument, ParsedPdfPage


class PdfParser:
    parser_name = "pypdf"

    def parse(self, document_id: str, file_path: Path) -> ParsedPdfDocument:
        try:
            reader = PdfReader(str(file_path), strict=False)
            if reader.is_encrypted:
                try:
                    password_result = reader.decrypt("")
                except Exception as exc:
                    raise PdfEncryptedError() from exc
                if not password_result:
                    raise PdfEncryptedError()

            pages: list[ParsedPdfPage] = []
            has_text_layer = False
            for page_number, page in enumerate(reader.pages, start=1):
                try:
                    extracted = page.extract_text()
                except Exception as exc:
                    raise FileCorruptedError("pdf") from exc
                text = extracted if extracted is not None else ""
                if text.strip():
                    has_text_layer = True
                pages.append(ParsedPdfPage(page=page_number, text=text))

            return ParsedPdfDocument(
                document_id=document_id,
                page_count=len(pages),
                has_text_layer=has_text_layer,
                needs_ocr=not has_text_layer,
                pages=pages,
            )
        except PdfEncryptedError:
            raise
        except (PdfReadError, EOFError, ValueError) as exc:
            raise FileCorruptedError("pdf") from exc
        except FileCorruptedError:
            raise
        except Exception as exc:
            raise ParserFailedError() from exc
