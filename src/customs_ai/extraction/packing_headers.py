"""Evidence-grounded Packing List headers; no items, providers or persistence.

Only explicit configured labels establish fields. A whole unsafe PDF abstains;
workbooks retain visible evidence with review flags for omitted unsafe content.
Scalar conflicts are sticky, while independently labelled invoice references
form an exact-string-deduplicated list. See TASK-007B for bounded layout policy.
"""

from dataclasses import dataclass
from decimal import Decimal
import math
import re
from typing import Any

from openpyxl.utils.cell import column_index_from_string, get_column_letter, range_boundaries
from pydantic import ValidationError

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, PackingList, Party
from customs_ai.extraction.config import normalize_alias
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.mapper import parse_date, parse_decimal
from customs_ai.extraction.models import ExtractionCandidate, ExtractionIssue
from customs_ai.extraction.packing_config import PackingExtractionConfig, load_packing_extraction_config
from customs_ai.extraction.packing_models import PackingListHeaderExtractionResult
from customs_ai.parsers.models import ParsedCell, ParsedPdfDocument, ParsedSheet, ParsedWorkbook
from customs_ai.vision.enums import TextResolutionSource, VerificationLevel
from customs_ai.vision.evaluator import TextQualityEvaluator
from customs_ai.vision.models import ResolvedPdfDocument

NUMERIC_FIELDS = frozenset({"package_count", "gross_weight", "net_weight", "volume"})
METHOD = "deterministic_packing_header"
LABEL_CONFIDENCE = 0.95  # Same specific-label policy as approved TASK-006B.
_DELIMITER = r"(?:[ \t]*[:：][ \t]*|[ \t]+[-–—][ \t]+|[ \t]{2,}|\t|[ \t]*(?=[|;])|$)"
_SEPARATORS = re.compile(r"[|;\t]| {2,}")
_GENERIC = re.compile(r"^[^:：\n]{1,60}[:：][ \t]*")
_GENERIC_IDENTIFIERS = frozenset({"NO", "DATE", "TOTAL", "QTY", "WEIGHT", "NGÀY", "日期", "数量"})
_NON_HEADER_LABELS = (
    "SHIPPER", "EXPORTER", "CONSIGNEE", "IMPORTER", "NOTIFY PARTY",
    "NGƯỜI GỬI HÀNG", "NGƯỜI NHẬN HÀNG", "NGƯỜI XUẤT KHẨU", "NGƯỜI NHẬP KHẨU",
    "发货人", "收货人", "出口商", "进口商", "SHIPMENT DATE", "DELIVERY DATE",
    "DATE", "NO", "TOTAL", "WEIGHT", "NOTES", "REMARKS",
)


def _issue(code: str, path: str | None = None) -> ExtractionIssue:
    # Codes/paths only: never interpolate source text, sheet names or identifiers.
    return ExtractionIssue(code=code, message="Packing header evidence requires review.",
                           field_path=path, is_review_required=True)


@dataclass(frozen=True)
class _Label:
    path: str | None
    alias: str
    pattern: re.Pattern[str]
    item: bool = False


@dataclass
class _Observation:
    candidate: ExtractionCandidate
    value: Any
    blocked: bool = False


class DeterministicPackingHeaderExtractor:
    def __init__(self, config: PackingExtractionConfig | None = None) -> None:
        supplied = config if config is not None else load_packing_extraction_config()
        self.config = PackingExtractionConfig.model_validate(supplied.model_dump(mode="python", warnings="error"))
        self.quality = TextQualityEvaluator()
        targets = {normalize_alias(a) for aliases in self.config.headers.values() for a in aliases}
        self.labels: list[_Label] = []
        for path, aliases in self.config.headers.items():
            for alias in aliases:
                # A custom config cannot turn generic identifiers into semantics.
                if normalize_alias(alias) not in _GENERIC_IDENTIFIERS:
                    self.labels.append(self._compile(path, alias))
        for aliases in self.config.items.values():
            for alias in aliases:
                if normalize_alias(alias) not in targets:
                    self.labels.append(self._compile(None, alias, item=True))
        for alias in _NON_HEADER_LABELS:
            if normalize_alias(alias) not in targets:
                self.labels.append(self._compile(None, alias))
        self.labels.sort(key=lambda label: len(normalize_alias(label.alias)), reverse=True)

    @staticmethod
    def _compile(path: str | None, alias: str, item: bool = False) -> _Label:
        words = r"[ \t]+".join(re.escape(word) for word in alias.split())
        return _Label(path, alias, re.compile(rf"^(?:{words}){_DELIMITER}", re.IGNORECASE), item)

    def _match(self, text: str) -> tuple[_Label | None, int]:
        if text.lstrip().startswith("="):
            return None, 0
        for label in self.labels:
            match = label.pattern.match(text)
            if match:
                return label, match.end()
        match = _GENERIC.match(text)
        if match and any(c.isalpha() for c in match.group()):
            return _Label(None, "", _GENERIC), match.end()
        return None, 0

    def _spans(self, text: str) -> list[tuple[_Label, str]]:
        """Only start at a label; split later spans at explicit label boundaries.

        Unlabelled prose is opaque, including labels mentioned within descriptions.
        Unknown key/value boundaries shield their values from target extraction.
        """
        text = text.lstrip(" \t")
        label, end = self._match(text)
        if label is None:
            return []
        if label.path is None:
            # Everything after an unknown/item label is opaque value content,
            # even when a description mentions target labels after separators.
            return [(label, text[end:])]
        boundaries = [(0, label, end)]
        search_from = end
        while search_from < len(text):
            if boundaries[-1][1].path is None:
                break
            # Formula contents are opaque even if they contain plausible labels.
            if text[search_from:].lstrip().startswith("="):
                break
            found = False
            for sep in _SEPARATORS.finditer(text, search_from):
                start = sep.end()
                while start < len(text) and text[start] in " \t":
                    start += 1
                next_label, next_end = self._match(text[start:])
                if next_label is not None:
                    boundaries.append((sep.start(), next_label, start + next_end))
                    search_from = start + next_end
                    found = True
                    break
            if not found:
                break
        return [(label, text[end:boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)])
                for i, (_, label, end) in enumerate(boundaries)]

    @staticmethod
    def _formula(cell: ParsedCell) -> bool:
        return (cell.is_formula or cell.data_type.lower() == "f"
                or isinstance(cell.raw_value, str) and cell.raw_value.lstrip().startswith("="))

    @staticmethod
    def _raw(value: Any) -> str:
        return "" if value is None else str(value)

    def _observe(self, path: str, raw: str, value: Any, doc_id: str,
                 observations: list[_Observation], issues: list[ExtractionIssue],
                 *, page: int | None = None, sheet: str | None = None,
                 cell: str | None = None, confidence: float = LABEL_CONFIDENCE,
                 blocked: bool = False) -> None:
        parsed: Any = None
        code = None
        if blocked or raw.lstrip().startswith("="):
            code = "UNRESOLVED_FORMULA_FIELD" if raw.lstrip().startswith("=") else "UNSAFE_CELL_EVIDENCE"
        elif not raw.strip():
            code = "MISSING_LABEL_VALUE"
        elif any(self._match(line.lstrip(" \t"))[0] is not None for line in raw.splitlines()[1:]):
            # Multiline cells may contain several business labels. Do not merge
            # them into one identifier/party or guess an intra-cell layout.
            code = "AMBIGUOUS_MULTILINE_VALUE"
        elif path in NUMERIC_FIELDS:
            # Only native finite numbers or strict lexical forms; never bool/time.
            numeric = Decimal(str(value)) if type(value) is float and math.isfinite(value) else value
            parsed = parse_decimal(numeric)
            if parsed is None:
                code = "UNPARSEABLE_NUMERIC_FIELD"
        elif path == "date":
            parsed = parse_date(value)
            if parsed is None:
                code = "UNPARSEABLE_DATE_FIELD"
        elif not isinstance(value, str):
            code = "UNPARSEABLE_STRING_FIELD"
        elif path == "invoice_references" and (
                re.search(r"[\s,;|&，；、]", raw.strip())
                or re.fullmatch(r"\d+[-–—/]\d+", raw.strip())):
            # One atomic token per explicit label. No guessed splitting/ranges.
            code = "AMBIGUOUS_INVOICE_REFERENCE"
        else:
            parsed = raw.strip()
        if code:
            issues.append(_issue(code, path))
        candidate = ExtractionCandidate(
            field_path=path, raw_value=raw, typed_value=parsed if parsed is not None else value,
            source_document_id=doc_id, page=page, sheet=sheet, cell=cell,
            extraction_method=METHOD, confidence=confidence,
        )
        observations.append(_Observation(candidate, parsed, bool(code)))

    def _safe_pdf(self, document: ParsedPdfDocument | ResolvedPdfDocument) -> bool:
        if (document.page_count < 1 or len(document.pages) != document.page_count
                or {p.page for p in document.pages} != set(range(1, document.page_count + 1))):
            return False
        if isinstance(document, ParsedPdfDocument):
            return (document.has_text_layer and not document.needs_ocr
                    and all(self.quality.evaluate_native_text(p.text) for p in document.pages))
        visual = {p.page for p in document.pages if p.source != TextResolutionSource.TEXT_LAYER}
        if (document.file_type != "pdf" or document.requires_review or document.unresolved_pages
                or document.vision_fallback_recommended
                or len(document.visual_pages) != len(set(document.visual_pages))
                or set(document.visual_pages) != visual):
            return False
        allowed = {
            TextResolutionSource.TEXT_LAYER: VerificationLevel.UNVERIFIED,
            TextResolutionSource.OCR_LOCAL: VerificationLevel.SINGLE_PROVIDER,
            TextResolutionSource.DOCUMENT_VISION_LOCAL: VerificationLevel.SINGLE_PROVIDER,
            TextResolutionSource.CROSS_VERIFIED_VISUAL: VerificationLevel.CROSS_VERIFIED,
        }
        for page in document.pages:
            if page.requires_review or allowed.get(page.source) != page.verification_level:
                return False
            if page.source == TextResolutionSource.TEXT_LAYER:
                if not self.quality.evaluate_native_text(page.text):
                    return False
            elif not self.quality.evaluate_provider_result(page.text, page.confidence):
                return False
            if (page.source == TextResolutionSource.CROSS_VERIFIED_VISUAL
                    and page.agreement_score is not None
                    and page.agreement_score < self.quality.config.min_soft_text_overlap):
                return False
        return True

    def _pdf(self, document, observations, issues) -> None:
        if not self._safe_pdf(document):
            issues.append(_issue("UNSAFE_PDF_EVIDENCE"))
            return
        item_context = False
        for page in sorted(document.pages, key=lambda p: p.page):
            lines = page.text.splitlines()
            consumed = False
            for index, line in enumerate(lines):
                if consumed:
                    consumed = False
                    continue
                if not line.strip():
                    item_context = False
                    continue
                spans = self._spans(line)
                if not spans:
                    continue
                if spans[0][0].path is None:
                    item_context |= spans[0][0].item
                    continue
                if item_context:
                    issues.append(_issue("UNSUPPORTED_ITEM_CONTEXT"))
                    continue
                # A row of labels is column evidence, not a header value lookup.
                if len(spans) > 1 and any(not raw.strip() for _, raw in spans):
                    issues.append(_issue("AMBIGUOUS_COLUMN_LABELS"))
                    continue
                for label, raw in spans:
                    if label.path is None:
                        item_context |= label.item
                        continue
                    if not raw.strip() and len(spans) == 1 and index + 1 < len(lines):
                        next_line = lines[index + 1]
                        if next_line.strip() and not self._spans(next_line):
                            raw = next_line
                            consumed = True
                    confidence = LABEL_CONFIDENCE
                    if isinstance(document, ResolvedPdfDocument) and page.confidence is not None:
                        confidence = min(confidence, page.confidence)
                    self._observe(label.path, raw, raw, document.document_id, observations, issues,
                                  page=page.page, confidence=confidence)

    @staticmethod
    def _sheet_grid(sheet: ParsedSheet):
        """Reject internally inconsistent coordinates/merges before any selection."""
        grid = {}
        for cell in sheet.cells:
            if (cell.row < 1 or cell.column < 1 or cell.row > 1048576 or cell.column > 16384
                    or cell.coordinate != f"{get_column_letter(cell.column)}{cell.row}"
                    or (cell.row, cell.column) in grid):
                raise ValueError("Invalid cell metadata")
            grid[cell.row, cell.column] = cell
        ranges = []
        for raw_range in sheet.merged_ranges:
            left, top, right, bottom = range_boundaries(raw_range)
            if (None in (left, top, right, bottom) or not 1 <= left <= right <= 16384
                    or not 1 <= top <= bottom <= 1048576):
                raise ValueError("Invalid merged metadata")
            rect = left, top, right, bottom
            if any(left <= r and right >= l and top <= b and bottom >= t for l, t, r, b in ranges):
                raise ValueError("Overlapping merged metadata")
            ranges.append(rect)
            for (row, col), cell in grid.items():
                if (left <= col <= right and top <= row <= bottom and (row, col) != (top, left)
                        and cell.raw_value is not None):
                    raise ValueError("Populated merged interior")
        hidden = {column_index_from_string(col) for col in sheet.hidden_columns}
        if any(not 1 <= col <= 16384 for col in hidden) or any(row < 1 for row in sheet.hidden_rows):
            raise ValueError("Invalid visibility metadata")
        return grid, ranges, hidden

    @staticmethod
    def _right_column(cell: ParsedCell, ranges) -> int:
        for left, top, right, _ in ranges:
            if (cell.row, cell.column) == (top, left):
                return right + 1
        return cell.column + 1

    def _workbook(self, document, observations, issues) -> None:
        if (document.sheet_count != len(document.sheets)
                or len({s.name for s in document.sheets}) != len(document.sheets)
                or len({s.index for s in document.sheets}) != len(document.sheets)):
            raise ValueError("Invalid workbook metadata")
        prepared = [(sheet, *self._sheet_grid(sheet)) for sheet in document.sheets]
        for sheet, grid, ranges, hidden_cols in prepared:
            def hidden(cell):
                if sheet.state != "visible" or cell.row in sheet.hidden_rows or cell.column in hidden_cols:
                    return True
                # A partially hidden merged region is not unambiguously visible.
                for left, top, right, bottom in ranges:
                    if left <= cell.column <= right and top <= cell.row <= bottom:
                        return (any(top <= row <= bottom for row in sheet.hidden_rows)
                                or any(left <= col <= right for col in hidden_cols))
                return False

            if any(hidden(cell) and cell.raw_value is not None for cell in sheet.cells):
                issues.append(_issue("HIDDEN_WORKBOOK_CONTENT"))
            cells = [cell for cell in sorted(sheet.cells, key=lambda c: (c.row, c.column)) if not hidden(cell)]
            rows: dict[int, list[tuple[ParsedCell, list]]] = {}
            for cell in cells:
                if self._formula(cell):
                    issues.append(_issue("OPAQUE_FORMULA_CELL"))
                    continue
                if isinstance(cell.raw_value, str):
                    spans = self._spans(cell.raw_value)
                    if spans:
                        rows.setdefault(cell.row, []).append((cell, spans))
            item_context = False
            previous_row = None
            occupied_rows = {cell.row for cell in sheet.cells if cell.raw_value is not None}
            # Inspect context only, never recognize/extract PackingItem rows.
            for row in sorted({cell.row for cell in cells}):
                if (previous_row is not None and row > previous_row + 1
                        and not any(previous_row < occupied < row for occupied in occupied_rows)
                        and not any(previous_row < hidden_row < row for hidden_row in sheet.hidden_rows)):
                    item_context = False
                previous_row = row
                entries = rows.get(row, [])
                standalone = sum(1 for _, spans in entries for _, raw in spans if not raw.strip())
                has_item_label = any(label.item for _, spans in entries for label, _ in spans)
                prior_item_context = item_context
                inline_before_opaque = len(entries) == 1 and entries[0][1][0][0].path is not None
                if has_item_label:
                    item_context = True
                column_row = standalone > 1 and any(
                    (target := grid.get((cell.row, self._right_column(cell, ranges)))) is None
                    or target.raw_value is None
                    or isinstance(target.raw_value, str) and bool(self._spans(target.raw_value))
                    for cell, spans in entries if len(spans) == 1 and not spans[0][1].strip()
                )
                if column_row:
                    issues.append(_issue("AMBIGUOUS_COLUMN_LABELS"))
                    item_context = True
                for cell, spans in entries:
                    for label, inline in spans:
                        if label.path is None:
                            continue
                        if item_context and not (inline_before_opaque and not prior_item_context):
                            issues.append(_issue("UNSUPPORTED_ITEM_CONTEXT", label.path))
                            continue
                        if inline.strip():
                            self._observe(label.path, inline, inline, document.document_id, observations, issues,
                                          sheet=sheet.name, cell=cell.coordinate)
                            continue
                        if column_row or len(spans) != 1:
                            continue
                        right_col = self._right_column(cell, ranges)
                        target = grid.get((cell.row, right_col))
                        if target is None or target.raw_value is None:
                            issues.append(_issue("MISSING_LABEL_VALUE", label.path))
                            continue
                        raw = self._raw(target.raw_value)
                        blocked = hidden(target) or self._formula(target) or target.data_type.lower() in {"e", "error"}
                        if not blocked and isinstance(target.raw_value, str) and self._spans(target.raw_value):
                            issues.append(_issue("AMBIGUOUS_LABEL_VALUE", label.path))
                            continue
                        self._observe(label.path, raw, target.raw_value, document.document_id, observations, issues,
                                      sheet=sheet.name, cell=target.coordinate, blocked=blocked)

    @staticmethod
    def _resolve(observations, issues) -> PackingList:
        grouped: dict[str, list[_Observation]] = {}
        for observation in observations:
            grouped.setdefault(observation.candidate.field_path, []).append(observation)
        fields = {}
        for path, group in grouped.items():
            good = [o for o in group if not o.blocked]
            if path != "invoice_references":
                if len({o.value for o in good}) > 1:
                    issues.append(_issue("CONFLICTING_FIELD_VALUES", path))
                    continue
                if len(good) != len(group):
                    continue  # Invalid evidence cannot be outvoted by valid evidence.
            seen = set()
            accepted = []
            for observation in good:
                if observation.value in seen:
                    continue
                seen.add(observation.value)
                data = observation.candidate.model_dump(exclude={"field_path", "typed_value"})
                accepted.append(CanonicalField(origin=ValueOrigin.EXTRACTED,
                                               normalized_value=observation.value, **data))
            if accepted:
                fields[path] = accepted if path == "invoice_references" else accepted[0]
        for role in ("seller", "buyer"):
            party = {key.split(".")[1]: fields.pop(key) for key in list(fields) if key.startswith(role + ".")}
            if party:
                fields[role] = Party(**party)
        return PackingList(**fields, items=[])

    def extract(self, document: ParsedPdfDocument | ResolvedPdfDocument | ParsedWorkbook) -> PackingListHeaderExtractionResult:
        observations: list[_Observation] = []
        issues: list[ExtractionIssue] = []
        if not isinstance(document, (ParsedPdfDocument, ResolvedPdfDocument, ParsedWorkbook)):
            return PackingListHeaderExtractionResult(packing_list=PackingList(), status=ExtractionStatus.FAILED,
                                                     issues=[_issue("UNSUPPORTED_DOCUMENT_TYPE")])
        try:
            # Parsers are permissive; revalidate mutated/constructed nested inputs.
            document = type(document).model_validate(document.model_dump(mode="python", warnings="error"))
            if not document.document_id.strip():
                raise ValueError("Missing document identity")
            if isinstance(document, ParsedWorkbook):
                self._workbook(document, observations, issues)
            else:
                self._pdf(document, observations, issues)
        except (ValidationError, ValueError, TypeError, OverflowError):
            return PackingListHeaderExtractionResult(packing_list=PackingList(), status=ExtractionStatus.NEEDS_REVIEW,
                                                     issues=[_issue("INVALID_SOURCE_METADATA")])
        packing = self._resolve(observations, issues)
        if not observations and not issues:
            issues.append(_issue("NO_HEADER_EVIDENCE"))
        return PackingListHeaderExtractionResult(
            packing_list=packing,
            status=ExtractionStatus.NEEDS_REVIEW if issues else ExtractionStatus.EXTRACTED,
            issues=issues, candidates=[o.candidate for o in observations],
        )


def extract_packing_headers(document, config: PackingExtractionConfig | None = None) -> PackingListHeaderExtractionResult:
    return DeterministicPackingHeaderExtractor(config).extract(document)
