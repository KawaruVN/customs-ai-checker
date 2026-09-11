from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CellValue = str | int | float | bool | date | datetime | time | None


class ParserModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParsedPdfPage(ParserModel):
    page: int
    text: str


class ParsedPdfDocument(ParserModel):
    document_id: str
    file_type: Literal["pdf"] = "pdf"
    parser_used: Literal["pypdf"] = "pypdf"
    page_count: int
    has_text_layer: bool
    needs_ocr: bool
    pages: list[ParsedPdfPage]


class ParsedCell(ParserModel):
    coordinate: str
    row: int
    column: int
    raw_value: CellValue
    displayed_value: CellValue = None
    data_type: str
    is_formula: bool = False
    number_format: str | None = None


class ParsedSheet(ParserModel):
    name: str
    index: int
    state: str
    merged_ranges: list[str] = Field(default_factory=list)
    hidden_rows: list[int] = Field(default_factory=list)
    hidden_columns: list[str] = Field(default_factory=list)
    cells: list[ParsedCell] = Field(default_factory=list)


class ParsedWorkbook(ParserModel):
    document_id: str
    file_type: Literal["xlsx", "xls"]
    parser_used: Literal["openpyxl", "xlrd"]
    workbook_name: str
    sheet_count: int
    sheets: list[ParsedSheet]


ParsedDocument = ParsedPdfDocument | ParsedWorkbook
