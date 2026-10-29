"""Conservative Packing item tables from approved parsed workbooks only.

A header needs identity plus quantity/weight columns; a credible region also
needs safe identity AND numeric evidence on the same body row. Only contiguous
identical headers continue a region. Other credible regions compete, never vote
or concatenate. See TASK-007C for row, geometry and source-boundary policies.
"""

from dataclasses import dataclass, field
from decimal import Decimal
import math
import re
from typing import Any
import unicodedata

from openpyxl.utils.cell import column_index_from_string, get_column_letter, range_boundaries

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, PackingItem
from customs_ai.extraction.config import normalize_alias
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.mapper import parse_decimal
from customs_ai.extraction.models import ExtractionCandidate, ExtractionIssue
from customs_ai.extraction.packing_config import PackingExtractionConfig, load_packing_extraction_config
from customs_ai.extraction.packing_models import PackingItemExtractionResult
from customs_ai.parsers.models import ParsedCell, ParsedSheet, ParsedWorkbook

IDENTITY_FIELDS = frozenset({"item_code", "description"})
NUMERIC_FIELDS = frozenset({"quantity", "gross_weight", "net_weight"})
SUMMARY_MARKERS = frozenset({
    "TOTAL", "GRAND TOTAL", "SUBTOTAL", "SUB TOTAL", "TỔNG", "TỔNG CỘNG",
    "CỘNG", "小计", "合计", "总计", "SUMMARY",
})
SUBTOTAL_MARKERS = frozenset({"SUBTOTAL", "SUB TOTAL", "小计"})
FOOTER_MARKERS = frozenset({"NOTE", "NOTES", "REMARK", "REMARKS", "GHI CHÚ", "备注"})
METHOD = "deterministic_packing_item_table"
CONFIDENCE = 0.95  # Approved specific-label policy; not proof of completeness.


def _label(text: str) -> str:
    label = normalize_alias(text)
    return label[:-1].rstrip() if label.endswith((":", "：")) else label


def _present(cell: ParsedCell | None) -> bool:
    return cell is not None and cell.raw_value is not None and (
        not isinstance(cell.raw_value, str) or bool(cell.raw_value.strip()))


def _formula(cell: ParsedCell) -> bool:
    return (cell.is_formula or cell.data_type.lower() == "f"
            or isinstance(cell.raw_value, str) and cell.raw_value.lstrip().startswith("="))


def _issue(code: str, path: str | None = None) -> ExtractionIssue:
    return ExtractionIssue(code=code, message="Packing item evidence requires review.",
                           field_path=path, is_review_required=True)


@dataclass
class _Grid:
    sheet: ParsedSheet
    rows: dict[int, dict[int, ParsedCell]]
    merges: list[tuple[int, int, int, int]]
    hidden_columns: set[int]

    def visible(self, cell: ParsedCell) -> bool:
        if (self.sheet.state != "visible" or cell.row in self.sheet.hidden_rows
                or cell.column in self.hidden_columns):
            return False
        for left, top, right, bottom in self.merges:
            if left <= cell.column <= right and top <= cell.row <= bottom:
                if (any(top <= row <= bottom for row in self.sheet.hidden_rows)
                        or any(left <= col <= right for col in self.hidden_columns)):
                    return False
        return True


@dataclass
class _Header:
    row: int
    bindings: dict[int, set[str]]
    errors: list[ExtractionIssue] = field(default_factory=list)

    @property
    def paths(self) -> set[str]:
        return set().union(*self.bindings.values())


@dataclass
class _Region:
    grid: _Grid
    header: _Header
    rows: list[tuple[int, dict[int, ParsedCell]]] = field(default_factory=list)
    unresolved: list[tuple[int, dict[int, ParsedCell]]] = field(default_factory=list)
    repeated: set[int] = field(default_factory=set)
    issues: list[ExtractionIssue] = field(default_factory=list)
    credible: bool = False


class DeterministicPackingItemExtractor:
    """Pure workbook -> canonical PackingItems with explicit abstention."""

    def __init__(self, config: PackingExtractionConfig | None = None) -> None:
        supplied = config if config is not None else load_packing_extraction_config()
        self.config = PackingExtractionConfig.model_validate(supplied.model_dump(mode="python", warnings="error"))
        self.aliases = {}
        for path, aliases in self.config.items.items():
            for alias in aliases:
                key = _label(alias)
                if key in self.aliases and self.aliases[key] != path:
                    raise ValueError("Ambiguous Packing table alias vocabulary.")
                self.aliases[key] = path
        self.summary_markers = SUMMARY_MARKERS | {
            _label(alias) for path in ("package_count", "gross_weight", "net_weight", "volume")
            for alias in self.config.headers[path]
            if path == "package_count" or _label(alias).startswith(("TOTAL ", "TỔNG ", "总"))
        }

    @staticmethod
    def _note_context(cells) -> bool:
        present = [cell for cell in cells.values() if _present(cell)]
        if (len(present) == 1 and isinstance(present[0].raw_value, str)
                and not _formula(present[0]) and _label(present[0].raw_value) in FOOTER_MARKERS):
            return True
        return any(isinstance(cell.raw_value, str) and not _formula(cell)
                   and re.match(r"^(?:NOTE|NOTES|REMARK|REMARKS|GHI CHÚ|备注)\s*[:：]\s*\S", normalize_alias(cell.raw_value))
                   for cell in present)

    def _paths(self, cell: ParsedCell) -> set[str]:
        if _formula(cell) or not isinstance(cell.raw_value, str):
            return set()
        exact = self.aliases.get(_label(cell.raw_value))
        if exact:
            return {exact}
        parts = re.split(r"\s*(?:/|\||\r?\n|\r|&|;)\s*", cell.raw_value)
        combined = {self.aliases[_label(part)] for part in parts if _label(part) in self.aliases}
        return combined if len(combined) > 1 else set()

    @staticmethod
    def _grid(sheet: ParsedSheet) -> _Grid:
        if not sheet.name.strip() or sheet.index < 0 or sheet.state not in {"visible", "hidden", "veryHidden"}:
            raise ValueError("Invalid sheet metadata")
        rows: dict[int, dict[int, ParsedCell]] = {}
        for cell in sheet.cells:
            if (not 1 <= cell.row <= 1048576 or not 1 <= cell.column <= 16384
                    or cell.coordinate != f"{get_column_letter(cell.column)}{cell.row}"
                    or cell.column in rows.setdefault(cell.row, {})):
                raise ValueError("Invalid cell metadata")
            rows[cell.row][cell.column] = cell
        merges = []
        for address in sheet.merged_ranges:
            left, top, right, bottom = range_boundaries(address)
            if (None in (left, top, right, bottom) or not 1 <= left <= right <= 16384
                    or not 1 <= top <= bottom <= 1048576):
                raise ValueError("Invalid merged metadata")
            if left == right and top == bottom:
                continue
            if any(left <= r and right >= l and top <= b and bottom >= t for l, t, r, b in merges):
                raise ValueError("Overlapping merges")
            merges.append((left, top, right, bottom))
            for row, cells in rows.items():
                if top <= row <= bottom:
                    if any(left <= col <= right and (row, col) != (top, left) and _present(cell)
                           for col, cell in cells.items()):
                        raise ValueError("Populated merged interior")
        hidden = {column_index_from_string(col) for col in sheet.hidden_columns}
        if (any(not 1 <= col <= 16384 for col in hidden)
                or any(not 1 <= row <= 1048576 for row in sheet.hidden_rows)):
            raise ValueError("Invalid visibility metadata")
        return _Grid(sheet, rows, merges, hidden)

    def _header(self, grid: _Grid, row: int, cells: dict[int, ParsedCell]) -> _Header | None:
        bindings = {col: paths for col, cell in sorted(cells.items()) if (paths := self._paths(cell))}
        if not bindings:
            return None
        paths = set().union(*bindings.values())
        if not (paths & IDENTITY_FIELDS and paths & NUMERIC_FIELDS):
            return None
        header = _Header(row, bindings)
        assigned = [path for found in bindings.values() for path in found]
        if len(assigned) != len(set(assigned)) or any(len(found) != 1 for found in bindings.values()):
            header.errors.append(_issue("AMBIGUOUS_PACKING_COLUMNS"))
        groups: list[set[str]] = []
        previous = None
        for col, found in bindings.items():
            if previous is None or col != previous + 1:
                groups.append(set())
            groups[-1].update(found)
            previous = col
        if sum(bool(group & IDENTITY_FIELDS and group & NUMERIC_FIELDS) for group in groups) > 1:
            header.errors.append(_issue("COMPETING_COLUMN_GROUPS"))
        if any(not grid.visible(cells[col]) for col in bindings):
            header.errors.append(_issue("HIDDEN_PACKING_HEADER"))
        if any(top <= row <= bottom and any(left <= col <= right for col in bindings)
               for left, top, right, bottom in grid.merges):
            header.errors.append(_issue("MERGED_PACKING_HEADER"))
        if self._note_context(cells):
            header.errors.append(_issue("NON_GOODS_HEADER_CONTEXT"))
        return header

    @staticmethod
    def _value(path: str, cell: ParsedCell) -> Any:
        if _formula(cell) or cell.data_type.lower() in {"e", "error"}:
            return None
        raw = cell.raw_value
        if path in NUMERIC_FIELDS:
            if type(raw) is float:
                return Decimal(str(raw)) if math.isfinite(raw) else None
            return parse_decimal(raw)
        if not isinstance(raw, str) or not raw.strip():
            return None  # No numeric-ID formatting, bool/date/time coercion.
        if any(unicodedata.category(char).startswith("C") and
               not (path == "description" and char in "\r\n\t") for char in raw):
            return None
        if path == "item_code" and not any(char.isalnum() for char in raw):
            return None
        if path == "description" and not any(char.isalpha() for char in raw):
            return None
        if path == "package_number" and (
                re.search(r"[\s,;|&，；、]", raw.strip())
                or re.fullmatch(r"\d+[-–—/]\d+", raw.strip())):
            return None  # One opaque identifier; never split/associate packages.
        return raw.strip()

    @staticmethod
    def _bad_merge(grid: _Grid, header: _Header, row: int) -> bool:
        for left, top, right, bottom in grid.merges:
            mapped = [col for col in header.bindings if left <= col <= right]
            if top <= row <= bottom and mapped:
                # Single-row, single-field, actual-anchor evidence is unambiguous.
                if top != bottom or len(mapped) != 1 or mapped[0] != left:
                    return True
        return False

    def _grounded(self, grid: _Grid, header: _Header, row: int, cells) -> bool:
        if self._bad_merge(grid, header, row):
            return False
        safe = {path for col, paths in header.bindings.items() for path in paths
                if _present(cell := cells.get(col)) and grid.visible(cell)
                and self._value(path, cell) is not None}
        return bool(safe & IDENTITY_FIELDS and safe & NUMERIC_FIELDS)

    def _boundary(self, header: _Header, cells) -> tuple[str | None, bool]:
        identity = [(path, cell) for col, paths in header.bindings.items() for path in paths
                    if path in IDENTITY_FIELDS and _present(cell := cells.get(col))
                    and isinstance(cell.raw_value, str) and not _formula(cell)]
        markers = []
        for path, cell in identity:
            text = _label(cell.raw_value)
            for marker in self.summary_markers | FOOTER_MARKERS:
                if text == marker or re.match(rf"^{re.escape(marker)}\s*[:：]", text):
                    markers.append((path, marker))
                    break
        if not markers:
            return None, False
        independent = any(path not in {p for p, _ in markers} for path, _ in identity)
        kind = "subtotal" if any(marker in SUBTOTAL_MARKERS for _, marker in markers) else "footer"
        return kind, independent

    def _scan(self, grid: _Grid, header: _Header, headers: dict[int, _Header]) -> _Region:
        region = _Region(grid, header)
        previous = header.row
        for row, cells in sorted(grid.rows.items()):
            if row <= header.row:
                continue
            if row != previous + 1:
                if any(previous < hidden < row for hidden in grid.sheet.hidden_rows):
                    region.issues.append(_issue("HIDDEN_PACKING_ROW_BOUNDARY"))
                    region.unresolved.append((row, cells))
                break
            previous = row
            repeated = headers.get(row)
            if repeated is not None:
                if repeated.bindings == header.bindings and not repeated.errors:
                    region.repeated.add(row)
                    continue
                break
            present = [cells.get(col) for col in header.bindings if _present(cells.get(col))]
            if not present:
                break  # Unmapped notes cannot bridge a blank business row.
            boundary, independent = self._boundary(header, cells)
            if boundary:
                region.unresolved.append((row, cells))
                if boundary == "subtotal" or independent:
                    region.issues.append(_issue("AMBIGUOUS_PACKING_BOUNDARY"))
                break
            if row in grid.sheet.hidden_rows:
                region.unresolved.append((row, cells))
                region.issues.append(_issue("HIDDEN_PACKING_ROW"))
                continue
            if self._bad_merge(grid, header, row):
                region.unresolved.append((row, cells))
                bottom = max(bottom for left, top, right, bottom in grid.merges
                             if top <= row <= bottom and any(left <= col <= right for col in header.bindings))
                region.unresolved.extend((following, body) for following, body in sorted(grid.rows.items())
                                         if row < following <= bottom and following not in headers)
                region.issues.append(_issue("AMBIGUOUS_PACKING_MERGE"))
                break
            region.rows.append((row, cells))
            region.credible |= self._grounded(grid, header, row, cells)
        return region

    @staticmethod
    def _path(region: _Region, row: int, col: int, path: str) -> str:
        return f"tables[{region.grid.sheet.index}:{region.header.row}].rows[{row}].columns[{col}].{path}"

    def _candidate(self, doc_id: str, grid: _Grid, path: str, cell: ParsedCell, value=None) -> ExtractionCandidate:
        return ExtractionCandidate(
            field_path=path, raw_value=str(cell.raw_value), typed_value=value,
            source_document_id=doc_id, sheet=grid.sheet.name, cell=cell.coordinate,
            extraction_method=METHOD, confidence=CONFIDENCE,
        )

    def _evidence(self, doc_id: str, region: _Region) -> list[ExtractionCandidate]:
        candidates = []
        for row, cells in [(region.header.row, region.grid.rows[region.header.row])] + region.rows + region.unresolved:
            for col, paths in region.header.bindings.items():
                cell = cells.get(col)
                if _present(cell):
                    for path in sorted(paths):
                        prefix = self._path(region, row, col, path)
                        if row == region.header.row:
                            prefix = "headers." + prefix
                        value = self._value(path, cell) if region.grid.visible(cell) else None
                        candidates.append(self._candidate(doc_id, region.grid, prefix, cell, value))
        return candidates

    def _items(self, doc_id: str, region: _Region, issues) -> list[PackingItem]:
        items = []
        for row, cells in region.rows:
            fields = {}
            paths = set()
            for col, found in region.header.bindings.items():
                path = next(iter(found))  # Only an unambiguous selected header reaches here.
                cell = cells.get(col)
                if not _present(cell):
                    continue
                source_path = self._path(region, row, col, path)
                value = self._value(path, cell) if region.grid.visible(cell) else None
                if value is None:
                    issues.append(_issue("UNRESOLVED_PACKING_FIELD", source_path))
                    continue
                paths.add(path)
                fields[path] = CanonicalField(
                    raw_value=str(cell.raw_value), normalized_value=value, origin=ValueOrigin.EXTRACTED,
                    source_document_id=doc_id, sheet=region.grid.sheet.name, cell=cell.coordinate,
                    extraction_method=METHOD, confidence=CONFIDENCE,
                )
            if not (paths & IDENTITY_FIELDS and paths & NUMERIC_FIELDS):
                issues.append(_issue("INCOMPLETE_PACKING_ROW", f"tables[{region.grid.sheet.index}:{region.header.row}].rows[{row}]"))
            if fields:
                items.append(PackingItem(**fields))
        return items

    def extract(self, workbook: ParsedWorkbook) -> PackingItemExtractionResult:
        if not isinstance(workbook, ParsedWorkbook):
            return PackingItemExtractionResult(status=ExtractionStatus.FAILED,
                                               issues=[_issue("UNSUPPORTED_PACKING_ITEM_DOCUMENT")])
        issues: list[ExtractionIssue] = []
        try:
            workbook = ParsedWorkbook.model_validate(workbook.model_dump(mode="python", warnings="error"))
            if (not workbook.document_id.strip() or workbook.sheet_count != len(workbook.sheets)
                    or len({s.name for s in workbook.sheets}) != len(workbook.sheets)
                    or len({s.index for s in workbook.sheets}) != len(workbook.sheets)):
                raise ValueError("Invalid workbook identity")
            grids = [self._grid(sheet) for sheet in workbook.sheets]
        except (ValueError, TypeError, OverflowError):
            return PackingItemExtractionResult(status=ExtractionStatus.NEEDS_REVIEW,
                                               issues=[_issue("INVALID_PACKING_GRID")])
        regions = []
        candidates = []
        for grid in sorted(grids, key=lambda g: g.sheet.index):
            headers = {}
            notes = False
            previous_row = None
            for row, cells in sorted(grid.rows.items()):
                visible_gap = (previous_row is not None and row > previous_row + 1
                               and row - previous_row - 1 > len({hidden for hidden in grid.sheet.hidden_rows
                                                                 if previous_row < hidden < row}))
                visible_blank = row not in grid.sheet.hidden_rows and not any(_present(c) for c in cells.values())
                if visible_gap or visible_blank:
                    notes = False
                previous_row = row
                notes |= self._note_context(cells)
                header = self._header(grid, row, cells)
                if header is not None:
                    if notes:
                        header.errors.append(_issue("NON_GOODS_HEADER_CONTEXT"))
                    headers[row] = header
            for row, cells in grid.rows.items():
                for col, cell in cells.items():
                    if _present(cell) and not grid.visible(cell):
                        issues.append(_issue("HIDDEN_WORKBOOK_CONTENT"))
                    if _formula(cell):
                        issues.append(_issue("OPAQUE_PACKING_FORMULA"))
                        candidates.append(self._candidate(workbook.document_id, grid,
                            f"unresolved.sheets[{grid.sheet.index}].rows[{row}].columns[{col}]", cell))
            covered = set()
            for row, header in headers.items():
                if row in covered:
                    continue
                region = self._scan(grid, header, headers)
                covered.update(region.repeated)
                issues.extend(header.errors)
                issues.extend(region.issues)
                # Hidden/ambiguous regions retain evidence but cannot be chosen.
                regions.append(region)
                if not region.credible:
                    issues.append(_issue("UNSUPPORTED_PACKING_REGION"))
        credible = [region for region in regions if region.credible and not region.header.errors]
        if len(credible) > 1:
            issues.append(_issue("MULTIPLE_PACKING_TABLES"))
        for region in regions:
            candidates.extend(self._evidence(workbook.document_id, region))
        items = []
        if len(credible) == 1 and not credible[0].header.errors:
            items = self._items(workbook.document_id, credible[0], issues)
        if not items and not issues:
            issues.append(_issue("NO_PACKING_ITEM_TABLE"))
        return PackingItemExtractionResult(
            items=items, candidates=candidates, issues=issues,
            status=ExtractionStatus.NEEDS_REVIEW if issues else ExtractionStatus.EXTRACTED,
        )


def extract_packing_items(workbook: ParsedWorkbook, config: PackingExtractionConfig | None = None) -> PackingItemExtractionResult:
    return DeterministicPackingItemExtractor(config).extract(workbook)
