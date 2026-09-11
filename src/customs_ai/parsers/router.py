from customs_ai.parsers.base import LocalParser
from customs_ai.parsers.errors import ParserUnsupportedError
from customs_ai.parsers.excel import XlsParser, XlsxParser
from customs_ai.parsers.pdf import PdfParser


class ParserRouter:
    def __init__(self) -> None:
        self._parsers: dict[str, LocalParser] = {
            "pdf": PdfParser(),
            "xlsx": XlsxParser(),
            "xls": XlsParser(),
        }

    def get_parser(self, file_type: str) -> LocalParser:
        normalized = file_type.lower().lstrip(".")
        parser = self._parsers.get(normalized)
        if parser is None:
            raise ParserUnsupportedError(normalized)
        return parser
