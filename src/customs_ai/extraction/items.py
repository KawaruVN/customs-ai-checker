"""Conservative Excel item tables; no parsing, calculation, or orchestration.

Headers match whole configured aliases (case/whitespace insensitive, optional
terminal colon). A table needs a product identity/content column and a numeric
column, plus grounded identity in its body. NO + QTY alone is insufficient.
Only contiguous, identical repeated headers are continuations. Other tables
compete; they are never appended or selected by position.

Blank mapped business rows (including implicit gaps) and summaries terminate a
region. Unmapped notes cannot extend it. Exact summary markers are distinct from
TOTALIZER/TOTAL CONTROL/TOTAL LOSS. Ambiguous summary/footer rows retain evidence
and require review. Subtotal sections are not automatically concatenated.

Only visible sheets are eligible. Material hidden rows are omitted with review;
hidden table headers, mapped hidden columns and merged headers also force review.
Formula/expression values are always unresolved, even if a displayed cache exists.
Source representations are kept separately from typed conversions. No source is
modified, no missing fact is inferred, and no customer content is logged.
"""

from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal
import math
import re

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, InvoiceItem
from customs_ai.extraction.config import (
    InvoiceExtractionConfig,
    load_invoice_extraction_config,
    normalize_alias,
)
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.mapper import parse_decimal
from customs_ai.extraction.models import (
    ExtractionCandidate,
    ExtractionIssue,
    InvoiceItemExtractionResult,
)
from customs_ai.parsers.models import ParsedCell, ParsedSheet, ParsedWorkbook

IDENTITY_FIELDS = frozenset({"description", "item_code", "part_number", "model"})
NUMERIC_FIELDS = frozenset({"quantity", "unit_price", "amount", "weight"})
IDENTIFIER_FIELDS = frozenset({"item_number", "item_code", "part_number", "model"})
SUMMARY_MARKERS = frozenset({
    "TOTAL", "TOTAL PRICE", "SUBTOTAL", "SUB TOTAL", "GRAND TOTAL", "TỔNG", "TỔNG CỘNG",
    "CỘNG", "小计", "合计", "总计", "总金额",
})
SUBTOTAL_MARKERS = frozenset({"SUBTOTAL", "SUB TOTAL", "小计"})
FOOTER_MARKERS = frozenset({
    "NOTE", "NOTES", "REMARK", "REMARKS", "PAYMENT TERMS", "BANK DETAILS",
    "BANK ACCOUNT", "THANK YOU", "GHI CHÚ", "备注",
})
FIELD_CONFIDENCE = 0.95


def _label(value: str) -> str:
    return normalize_alias(value).rstrip(":：").rstrip()


def _present(cell: ParsedCell | None) -> bool:
    return cell is not None and cell.raw_value is not None and (
        not isinstance(cell.raw_value, str) or bool(cell.raw_value.strip())
    )


def _expression(cell: ParsedCell) -> bool:
    return cell.is_formula or cell.data_type == "f" or (
        isinstance(cell.raw_value, str) and cell.raw_value.lstrip().startswith("=")
    )


def _issue(code: str, message: str, path: str | None = None) -> ExtractionIssue:
    return ExtractionIssue(
        code=code, message=message, field_path=path, is_review_required=True,
    )


def _col_index(letters: str) -> int:
    if not letters:
        raise ValueError("Invalid column metadata")
    result = 0
    for letter in letters.upper():
        if letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            raise ValueError("Invalid column metadata")
        result = result * 26 + ord(letter) - ord("A") + 1
    return result


def _bounds(address: str) -> tuple[int, int, int, int]:
    parts = address.replace("$", "").split(":")
    if len(parts) != 2:
        raise ValueError("Invalid merged range metadata")
    cells = [re.fullmatch(r"([A-Za-z]+)([1-9][0-9]*)", part) for part in parts]
    if any(match is None for match in cells):
        raise ValueError("Invalid merged range metadata")
    start, end = cells
    bounds = _col_index(start[1]), int(start[2]), _col_index(end[1]), int(end[2])
    if bounds[2] < bounds[0] or bounds[3] < bounds[1]:
        raise ValueError("Invalid merged range metadata")
    return bounds


@dataclass
class _Header:
    row: int
    columns: dict[str, int]
    errors: list[ExtractionIssue] = field(default_factory=list)


@dataclass
class _Region:
    sheet: ParsedSheet
    header: _Header
    rows: list[tuple[int, dict[int, ParsedCell]]] = field(default_factory=list)
    unresolved: list[tuple[int, dict[int, ParsedCell]]] = field(default_factory=list)
    repeated: set[int] = field(default_factory=set)
    issues: list[ExtractionIssue] = field(default_factory=list)


class DeterministicInvoiceItemExtractor:
    """Pure ParsedWorkbook -> canonical items with explicit abstention policies."""

    def __init__(self, config: InvoiceExtractionConfig | None = None) -> None:
        self.config = config if config is not None else load_invoice_extraction_config()
        self.summary_markers = SUMMARY_MARKERS | {
            _label(alias) for alias in self.config.headers["total_amount"]
        }
        self.aliases: dict[str, set[str]] = {}
        for path, aliases in self.config.items.items():
            for alias in aliases:
                self.aliases.setdefault(_label(alias), set()).add(path)

    def _paths(self, cell: ParsedCell) -> set[str]:
        if _expression(cell) or not isinstance(cell.raw_value, str):
            return set()
        text = cell.raw_value
        exact = self.aliases.get(_label(text))
        if exact:
            return exact
        parts = re.split(r"\s*(?:/|\||\n)\s*", text)
        combined = set().union(*(self.aliases.get(_label(part), set()) for part in parts))
        return combined if len(combined) > 1 else set()

    def _header(
        self,
        row: int,
        cells: dict[int, ParsedCell],
        hidden_cols: set[int],
        merged: list[tuple[int, int, int, int]],
    ) -> _Header | None:
        columns: dict[str, int] = {}
        ambiguous = False
        for col, cell in sorted(cells.items()):
            paths = self._paths(cell)
            ambiguous |= len(paths) > 1
            for path in sorted(paths):
                if path in columns:
                    ambiguous = True
                columns.setdefault(path, col)
        if not (IDENTITY_FIELDS & columns.keys() and NUMERIC_FIELDS & columns.keys()):
            return None
        header = _Header(row, columns)
        if ambiguous:
            header.errors.append(_issue("AMBIGUOUS_ITEM_COLUMNS", "Item column interpretation is ambiguous."))
        # Two separated blocks that independently establish identity + numeric
        # columns may be different tables, even if their canonical paths differ.
        groups: list[set[str]] = []
        previous_col = None
        for col in sorted(set(columns.values())):
            if previous_col is None or col != previous_col + 1:
                groups.append(set())
            groups[-1].update(p for p, c in columns.items() if c == col)
            previous_col = col
        if sum(bool(IDENTITY_FIELDS & group and NUMERIC_FIELDS & group) for group in groups) > 1:
            header.errors.append(_issue("AMBIGUOUS_ITEM_COLUMN_GROUPS", "Separated item column groups may belong to competing tables."))
        if hidden_cols & set(columns.values()):
            header.errors.append(_issue("HIDDEN_ITEM_COLUMN", "A mapped item column is hidden."))
        if any(
            r1 <= row <= r2 and any(c1 <= col <= c2 for col in columns.values())
            for c1, r1, c2, r2 in merged
        ):
            header.errors.append(_issue("MERGED_ITEM_HEADER", "Merged item headers do not establish unique columns."))
        return header

    @staticmethod
    def _grounded_identity(header: _Header, cells: dict[int, ParsedCell]) -> bool:
        for path in IDENTITY_FIELDS & header.columns.keys():
            cell = cells.get(header.columns[path])
            if (
                _present(cell)
                and not _expression(cell)
                and not isinstance(cell.raw_value, (bool, date, time))
            ):
                if path == "description" and (
                    not isinstance(cell.raw_value, str)
                    or not any(char.isalpha() for char in cell.raw_value)
                ):
                    continue
                if not isinstance(cell.raw_value, float) or math.isfinite(cell.raw_value):
                    return True
        return False

    def _row_kind(self, header: _Header, cells: dict[int, ParsedCell]) -> str:
        populated = {
            p: cells[c] for p, c in header.columns.items() if _present(cells.get(c))
        }
        if not populated:
            return "blank"
        markers = {
            p: _label(c.raw_value)
            for p, c in populated.items()
            if p in IDENTITY_FIELDS | {"item_number"}
            and isinstance(c.raw_value, str)
            and not _expression(c)
        }
        summary = {p: value for p, value in markers.items() if value in self.summary_markers}
        if summary:
            other_identity = any(p in IDENTITY_FIELDS and p not in summary for p in populated)
            if other_identity:
                return "ambiguous_item"
            # A label plus amount alone is a summary. Product-like numbers make
            # the interpretation uncertain, not a reason to invent a total row.
            if not ({"quantity", "unit_price", "unit"} & populated.keys()) and "amount" in populated:
                return "subtotal" if any(v in SUBTOTAL_MARKERS for v in summary.values()) else "summary"
            return "ambiguous_summary"
        footer_paths = {
            p for p, value in markers.items()
            if any(
                value == marker
                or value.startswith((marker + ":", marker + "：", marker + " "))
                for marker in FOOTER_MARKERS
            )
        }
        if footer_paths:
            independent_identity = any(
                p in IDENTITY_FIELDS and p not in footer_paths for p in populated
            )
            return "ambiguous_item" if independent_identity else "footer"
        if not (IDENTITY_FIELDS | NUMERIC_FIELDS) & populated.keys():
            return "uncertain"
        return "item"

    def _scan(
        self,
        sheet: ParsedSheet,
        header: _Header,
        rows: dict[int, dict[int, ParsedCell]],
        headers: dict[int, _Header],
        merged: list[tuple[int, int, int, int]],
    ) -> _Region:
        region = _Region(sheet, header)
        previous = header.row
        for row in sorted(r for r in rows if r > header.row):
            if row != previous + 1:
                break  # implicit blank business row
            previous = row
            cells = rows[row]
            if row in sheet.hidden_rows:
                if any(_present(cells.get(col)) for col in header.columns.values()):
                    region.issues.append(_issue("HIDDEN_ITEM_ROW", "A material hidden row was excluded from the item table."))
                    if row in headers and headers[row].columns == header.columns:
                        region.repeated.add(row)
                    elif row in headers:
                        break
                    if self._row_kind(header, cells) in {"summary", "subtotal", "ambiguous_summary", "footer", "uncertain"}:
                        break
                    continue
                break
            repeated = headers.get(row)
            if repeated is not None:
                if repeated.columns == header.columns and not repeated.errors:
                    region.repeated.add(row)
                    continue
                break
            kind = self._row_kind(header, cells)
            if kind == "blank" or kind == "summary":
                break
            if kind == "subtotal":
                region.issues.append(_issue("ITEM_SUBTOTAL_BOUNDARY", "Subtotal sections require review before continuation."))
                break
            if kind in {"ambiguous_summary", "footer", "uncertain"}:
                region.unresolved.append((row, cells))
                region.issues.append(_issue("AMBIGUOUS_ITEM_ROW", "An item-region boundary requires human interpretation."))
                break
            if any(
                r1 <= row <= r2
                and any(c1 <= col <= c2 for col in header.columns.values())
                for c1, r1, c2, r2 in merged
            ):
                region.unresolved.append((row, cells))
                region.issues.append(_issue("MERGED_ITEM_ROW", "Merged business cells require manual row interpretation."))
                break
            if kind == "ambiguous_item":
                region.issues.append(_issue("AMBIGUOUS_ITEM_SUMMARY", "A boundary marker also has independent product identity evidence."))
            region.rows.append((row, cells))
        return region

    @staticmethod
    def _candidate(
        doc_id: str, sheet: ParsedSheet, path: str, cell: ParsedCell,
    ) -> ExtractionCandidate:
        return ExtractionCandidate(
            field_path=path,
            raw_value=str(cell.raw_value),
            source_document_id=doc_id,
            sheet=sheet.name,
            cell=cell.coordinate,
            extraction_method="deterministic_item_table",
            confidence=FIELD_CONFIDENCE,
        )

    def _evidence(
        self, workbook: ParsedWorkbook, region: _Region, prefix: str,
    ) -> list[ExtractionCandidate]:
        result = []
        for row, cells in region.rows + region.unresolved:
            for path, col in sorted(region.header.columns.items()):
                cell = cells.get(col)
                if _present(cell):
                    result.append(self._candidate(workbook.document_id, region.sheet, f"{prefix}.rows[{row}].{path}", cell))
        return result

    @staticmethod
    def _number(cell: ParsedCell) -> Decimal | None:
        raw = cell.raw_value
        if isinstance(raw, (bool, date, time)):
            return None
        if isinstance(raw, float):
            return Decimal(str(raw)) if math.isfinite(raw) else None
        return parse_decimal(raw)

    @staticmethod
    def _text(path: str, cell: ParsedCell) -> str | None:
        raw = cell.raw_value
        if isinstance(raw, (bool, date, time)):
            return None
        if isinstance(raw, float) and not math.isfinite(raw):
            return None
        if (
            path in IDENTIFIER_FIELDS
            and cell.number_format
            and re.fullmatch(r"0+", cell.number_format)
            and isinstance(raw, (int, float))
        ):
            if isinstance(raw, float) and not raw.is_integer():
                return None
            number = int(raw)
            return ("-" if number < 0 else "") + str(abs(number)).zfill(len(cell.number_format))
        return str(raw).strip()

    def extract(self, workbook: ParsedWorkbook) -> InvoiceItemExtractionResult:
        if not isinstance(workbook, ParsedWorkbook):
            return InvoiceItemExtractionResult(items=[], status=ExtractionStatus.FAILED, issues=[_issue("UNSUPPORTED_ITEM_DOCUMENT", "Item tables require a parsed Excel workbook.")])
        if not workbook.document_id.strip():
            return InvoiceItemExtractionResult(items=[], status=ExtractionStatus.FAILED, issues=[_issue("MISSING_SOURCE_DOCUMENT_ID", "Item extraction requires a source document identifier.")])

        issues: list[ExtractionIssue] = []
        regions: list[_Region] = []
        header_evidence: list[ExtractionCandidate] = []
        blocked = False
        sheet_names: set[str] = set()
        for sheet in workbook.sheets:
            rows: dict[int, dict[int, ParsedCell]] = {}
            try:
                if not sheet.name or sheet.name in sheet_names:
                    raise ValueError("Ambiguous sheet metadata")
                sheet_names.add(sheet.name)
                for cell in sheet.cells:
                    if cell.row < 1 or cell.column < 1 or cell.column in rows.setdefault(cell.row, {}):
                        raise ValueError("Ambiguous cell metadata")
                    address = re.fullmatch(r"([A-Za-z]+)([1-9][0-9]*)", cell.coordinate)
                    if not address or (_col_index(address[1]), int(address[2])) != (cell.column, cell.row):
                        raise ValueError("Inconsistent cell provenance")
                    rows[cell.row][cell.column] = cell
                merged = [_bounds(address) for address in sheet.merged_ranges]
                merged = [b for b in merged if (b[0], b[1]) != (b[2], b[3])]
                hidden_cols = {_col_index(col) for col in sheet.hidden_columns}
            except ValueError:
                issues.append(_issue("INVALID_ITEM_GRID", "Workbook grid metadata is ambiguous."))
                blocked = True
                continue
            headers = {}
            for row, cells in sorted(rows.items()):
                header = self._header(row, cells, hidden_cols, merged)
                if header is not None:
                    headers[row] = header
            if sheet.state != "visible":
                if headers:
                    issues.append(_issue("HIDDEN_ITEM_TABLE", "A hidden worksheet contains item-table header evidence and was excluded."))
                continue
            covered: set[int] = set()
            for row, header in headers.items():
                if row in covered:
                    continue
                if row in sheet.hidden_rows:
                    issues.append(_issue("HIDDEN_ITEM_HEADER", "A hidden item-table header was excluded."))
                    continue
                if header.errors:
                    issues.extend(header.errors)
                    for cell in rows[row].values():
                        for path in sorted(self._paths(cell)):
                            header_evidence.append(self._candidate(workbook.document_id, sheet, f"headers[{sheet.index}:{row}].{path}", cell))
                    blocked = True
                    continue
                region = self._scan(sheet, header, rows, headers, merged)
                covered.update(region.repeated)
                issues.extend(region.issues)
                if region.rows:
                    regions.append(region)
                else:
                    issues.append(_issue("EMPTY_ITEM_TABLE", "Item header evidence did not establish any business rows."))
                    if region.unresolved:
                        regions.append(region)

        credible = [
            r for r in regions
            if any(self._grounded_identity(r.header, cells) for _, cells in r.rows)
        ]
        if any(r not in credible for r in regions):
            blocked = True
            issues.append(_issue("UNVERIFIED_ITEM_TABLE", "Item-region evidence does not establish grounded product identity."))
        if len(credible) > 1:
            blocked = True
            issues.append(_issue("MULTIPLE_ITEM_TABLES", "Multiple credible item tables require independent review."))
        if blocked or len(credible) != 1:
            if not regions and not issues:
                issues.append(_issue("NO_ITEM_TABLE", "No supported item-table evidence was found."))
            candidates = list(header_evidence)
            for index, region in enumerate(regions):
                candidates.extend(self._evidence(workbook, region, f"tables[{index}]"))
            return InvoiceItemExtractionResult(items=[], status=ExtractionStatus.NEEDS_REVIEW, issues=issues, candidates=candidates)

        region = credible[0]
        items: list[InvoiceItem] = []
        candidates: list[ExtractionCandidate] = []
        for _, cells in region.rows:
            index = len(items)
            fields = {}
            has_identity = self._grounded_identity(region.header, cells)
            has_numeric = any(
                _present(cells.get(region.header.columns[p]))
                for p in NUMERIC_FIELDS & region.header.columns.keys()
            )
            if not has_identity or not has_numeric:
                issues.append(_issue("INCOMPLETE_ITEM_ROW", "An incomplete item row requires review.", f"items[{index}]"))
            for path, col in sorted(region.header.columns.items()):
                cell = cells.get(col)
                if not _present(cell):
                    continue
                field_path = f"items[{index}].{path}"
                candidate = self._candidate(workbook.document_id, region.sheet, field_path, cell)
                candidates.append(candidate)
                if _expression(cell):
                    issues.append(_issue("UNRESOLVED_ITEM_FORMULA", "An item expression was preserved without evaluation.", field_path))
                    continue
                value = self._number(cell) if path in NUMERIC_FIELDS else self._text(path, cell)
                if value is None:
                    issues.append(_issue("UNPARSEABLE_ITEM_FIELD", "An item field cannot be converted safely.", field_path))
                    continue
                fields[path] = CanonicalField(
                    origin=ValueOrigin.EXTRACTED,
                    raw_value=candidate.raw_value,
                    normalized_value=value,
                    source_document_id=workbook.document_id,
                    sheet=region.sheet.name,
                    cell=cell.coordinate,
                    extraction_method="deterministic_item_table",
                    confidence=FIELD_CONFIDENCE,
                )
            items.append(InvoiceItem(**fields))
        if region.unresolved:
            evidence_region = _Region(region.sheet, region.header, unresolved=region.unresolved)
            candidates.extend(self._evidence(workbook, evidence_region, "unresolved"))
        return InvoiceItemExtractionResult(
            items=items,
            status=ExtractionStatus.NEEDS_REVIEW if issues else ExtractionStatus.EXTRACTED,
            issues=issues,
            candidates=candidates,
        )


def extract_invoice_items(
    workbook: ParsedWorkbook, config: InvoiceExtractionConfig | None = None,
) -> InvoiceItemExtractionResult:
    return DeterministicInvoiceItemExtractor(config).extract(workbook)
