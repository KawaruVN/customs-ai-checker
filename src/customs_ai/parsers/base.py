from pathlib import Path
from typing import Protocol

from customs_ai.parsers.models import ParsedDocument


class LocalParser(Protocol):
    parser_name: str

    def parse(self, document_id: str, file_path: Path) -> ParsedDocument:
        ...
