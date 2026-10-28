"""Deterministic Commercial Invoice Header Extractor.

Extracts canonical Invoice header and Party fields from:
- ParsedPdfDocument
- ResolvedPdfDocument (respecting TASK-005A visual safety gates)
- ParsedWorkbook
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
import math
import re
from typing import Any

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, Invoice, Party
from customs_ai.extraction.config import (
    APPROVED_HEADER_PATHS,
    InvoiceExtractionConfig,
    load_invoice_extraction_config,
)
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.mapper import parse_date, parse_decimal
from customs_ai.extraction.models import (
    CandidateTypedValue,
    ExtractionCandidate,
    ExtractionIssue,
    InvoiceHeaderExtractionResult,
)
from customs_ai.parsers.models import (
    ParsedCell,
    ParsedPdfDocument,
    ParsedWorkbook,
)
from customs_ai.vision.enums import TextResolutionSource, VerificationLevel
from customs_ai.vision.models import ResolvedPdfDocument, ResolvedPdfPage

NUMERIC_HEADER_FIELDS = frozenset(
    {"total_amount", "freight", "insurance", "discount"}
)
DATE_HEADER_FIELDS = frozenset({"invoice_date"})

GENERIC_HEADER_ALIASES = frozenset(
    {"DATE", "NGÀY", "日期", "TOTAL", "TỔNG", "合计"}
)

# Known non-target label prefixes that must never be treated as values or approved headers
EXCLUDED_LABEL_PREFIXES = (
    # Non-invoice dates
    "DELIVERY DATE",
    "DELIVERY DT",
    "SHIPMENT DATE",
    "SHIPPING DATE",
    "SHIP DATE",
    "DUE DATE",
    "EXPIRY DATE",
    "EXPIRATION DATE",
    "PAYMENT DATE",
    "BL DATE",
    "B/L DATE",
    "ETA",
    "ETD",
    "NGÀY GIAO HÀNG",
    "NGÀY ĐÁO HẠN",
    "NGÀY HẾT HẠN",
    "交货日期",
    "发货日期",
    "到期日",
    # Non-target parties
    "SHIPPER",
    "EXPORTER",
    "CONSIGNEE",
    "IMPORTER",
    "NOTIFY PARTY",
    "FORWARDER",
    "CARRIER",
    "NGƯỜI GỬI HÀNG",
    "NGƯỜI XUẤT KHẨU",
    "NGƯỜI NHẬP KHẨU",
    "发货人",
    "出口商",
    "收货人",
    "进口商",
    "通知人",
    # Non-target commercial headers
    "SELLER BANK ACCOUNT",
    "BUYER BANK ACCOUNT",
    "BANK ACCOUNT",
    "BANK NAME",
    "BANK",
    "ACCOUNT NO",
    "SWIFT",
    "IBAN",
    "TEL",
    "FAX",
    "EMAIL",
    "WEBSITE",
    "ATTN",
    "CONTACT",
    "REMARKS",
    "NOTE",
    "NOTES",
)

DELIM_PATTERN = r"(?:(?P<colon>[ \t]*[:：][ \t]*)|(?P<dash>[ \t]+[-–—][ \t]+)|(?P<eq>[ \t]+=[ \t]+)|(?P<spaces>[ \t]{2,}|\t)|$)"


def is_generic_label_header(text: str) -> bool:
    """Check if text begins with a key-value label pattern like 'KEY:'."""
    s = text.strip()
    if not s:
        return False
    # Formulas starting with '=' are expressions, never label headers
    if s.startswith("="):
        return False
    # If it starts with an ISO date/timestamp like 2026-05-12 14:30, it is not a label header
    if re.match(r"^\d{4}[-/. ]\d{2}[-/. ]\d{2}", s):
        return False

    # Find first colon (ASCII ':' or full-width '：')
    pos_colon = s.find(":")
    pos_fw = s.find("：")
    positions = [p for p in (pos_colon, pos_fw) if p >= 0]
    if not positions:
        return False

    first_colon = min(positions)
    # Label key must be reasonable length (between 1 and 50 characters)
    if 0 < first_colon <= 50:
        key = s[:first_colon].strip()
        # Must contain at least one letter or CJK character
        if re.search(r"[A-Za-z\u00C0-\u024F\u1EA0-\u1EF9\u4E00-\u9FFF]", key):
            # Must not be an ISO date
            if not re.match(r"^\d{4}[-/.]\d{2}[-/.]\d{2}", key):
                return True
    return False


@dataclass(frozen=True)
class CompiledAlias:
    alias: str
    field_path: str
    is_generic: bool
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class LineBoundary:
    alias: CompiledAlias | None
    start: int
    val_start: int
    is_target: bool


class DeterministicInvoiceHeaderExtractor:
    """Extractor for commercial invoice headers and party fields.

    Design & Policies:
    - Longest/specific matching: longer aliases (e.g. 'SELLER ADDRESS') are matched
      before generic prefix aliases (e.g. 'SELLER') to avoid false captures.
    - Specific vs generic confidence: specific aliases yield 0.95 confidence,
      generic aliases yield 0.70 confidence.
    - Conflict policy: If multiple candidates for a field normalize to distinct material
      values, a conflict issue is raised and the field remains unresolved (None).
      A 2-to-1 candidate split remains strictly unresolved (no majority voting).
    - Repeated identical candidates: Candidates normalizing to the exact same typed value
      are deduplicated cleanly without generating conflict.
    - Safety gates: Unresolved visual pages or unverified OCR pages in ResolvedPdfDocument
      are flagged with NEEDS_REVIEW and excluded from header extraction.
    """

    def __init__(self, config: InvoiceExtractionConfig | None = None) -> None:
        self.config = config or load_invoice_extraction_config()
        self.compiled_aliases = self._compile_aliases()
        self._compiled_excluded = self._compile_excluded()

    def _compile_excluded(self) -> list[re.Pattern[str]]:
        patterns: list[re.Pattern[str]] = []
        sorted_excl = sorted(EXCLUDED_LABEL_PREFIXES, key=lambda x: len(x), reverse=True)
        for excl in sorted_excl:
            words = [re.escape(w) for w in excl.strip().split()]
            excl_regex = r"\s+".join(words)
            full_regex = rf"^(?:{excl_regex}){DELIM_PATTERN}"
            patterns.append(re.compile(full_regex, re.IGNORECASE))
        return patterns

    def _compile_aliases(self) -> list[CompiledAlias]:
        compiled: list[CompiledAlias] = []
        for path, aliases in self.config.headers.items():
            for alias in aliases:
                is_gen = alias.strip().upper() in GENERIC_HEADER_ALIASES
                words = [re.escape(w) for w in alias.strip().split()]
                alias_regex = r"\s+".join(words)
                full_regex = rf"^(?:{alias_regex}){DELIM_PATTERN}"
                compiled.append(
                    CompiledAlias(
                        alias=alias.strip(),
                        field_path=path,
                        is_generic=is_gen,
                        pattern=re.compile(full_regex, re.IGNORECASE),
                    )
                )
        # Sort by alias length descending so specific/longest aliases are tested first
        compiled.sort(key=lambda x: len(x.alias), reverse=True)
        return compiled

    def is_any_known_label(self, text: str) -> bool:
        """Check if a line or cell is a label rather than a value."""
        s = text.strip()
        if not s or s.startswith("="):
            return False

        for pat in self._compiled_excluded:
            if pat.match(s):
                return True

        for ca in self.compiled_aliases:
            if ca.pattern.match(s):
                return True

        # Generic pattern: ends with colon
        if s.endswith(":") or s.endswith("："):
            return True

        # Generic key-value label pattern: e.g. "CONTRACT NO: C-001", "PHONE: 012345"
        if is_generic_label_header(s):
            return True

        return False

    @staticmethod
    def _is_boundary_position(line: str, i: int) -> bool:
        """Check if index i in line represents a potential field boundary."""
        if i == 0:
            return True
        if line[i] in (" ", "\t", "|", ";"):
            return False
        sub = line[:i]
        # Only strip regular spaces ' ', leaving tabs, pipes, semicolons intact!
        sub_no_spaces = sub.rstrip(" ")
        if not sub_no_spaces:
            return True
        last_char = sub_no_spaces[-1]
        # If preceded by separator (pipe, semicolon, tab) with optional spaces in between:
        if last_char in ("|", ";", "\t"):
            return True
        # If separated by 2 or more consecutive spaces:
        if len(sub) - len(sub_no_spaces) >= 2:
            return True
        return False

    def _match_boundary_at_position(self, line: str, pos: int) -> tuple[LineBoundary | None, int]:
        """Match approved, excluded, or generic field boundary at position pos."""
        remainder = line[pos:]

        # 1. Excluded label check
        for pat in self._compiled_excluded:
            m = pat.match(remainder)
            if m:
                val_start = pos + m.end()
                return LineBoundary(
                    alias=None,
                    start=pos,
                    val_start=val_start,
                    is_target=False,
                ), val_start

        # 2. Approved target label check
        for ca in self.compiled_aliases:
            m = ca.pattern.match(remainder)
            if m:
                val_start = pos + m.end()
                return LineBoundary(
                    alias=ca,
                    start=pos,
                    val_start=val_start,
                    is_target=True,
                ), val_start

        # 3. Generic non-target label check (e.g. "CONTRACT-NO: C-001", "SHIPPER'S NAME: ...")
        if is_generic_label_header(remainder):
            pos_colon = remainder.find(":")
            pos_fw = remainder.find("：")
            positions = [p for p in (pos_colon, pos_fw) if p >= 0]
            first_colon = min(positions)
            after_colon = remainder[first_colon + 1:]
            val_offset = first_colon + 1 + (len(after_colon) - len(after_colon.lstrip(" \t")))
            val_start = pos + val_offset
            return LineBoundary(
                alias=None,
                start=pos,
                val_start=val_start,
                is_target=False,
            ), val_start

        return None, pos + 1

    def _find_boundaries_in_line(self, line: str) -> list[LineBoundary]:
        """Scan a line for all field boundaries (approved, excluded, and non-target)."""
        # If the line starts with an expression, it is opaque and cannot be a label source
        if line.strip().startswith("="):
            return []

        boundaries: list[LineBoundary] = []
        i = 0
        n = len(line)

        while i < n:
            if self._is_boundary_position(line, i):
                boundary, next_i = self._match_boundary_at_position(line, i)
                if boundary is not None:
                    boundaries.append(boundary)
                    # If the value following this boundary begins with an expression '=',
                    # it is opaque content: do not search for any further boundaries inside it.
                    val_remainder = line[boundary.val_start:].lstrip(" \t")
                    if val_remainder.startswith("="):
                        break
                    i = max(next_i, i + 1)
                    continue
            i += 1

        return boundaries

    def _is_resolved_page_unsafe(
        self,
        doc: ResolvedPdfDocument,
        page: ResolvedPdfPage,
    ) -> tuple[bool, str]:
        """Check if a resolved PDF page violates safety gates."""
        if page.requires_review:
            return True, "PAGE_REQUIRES_REVIEW"

        if page.page in doc.unresolved_pages:
            return True, "PAGE_IN_UNRESOLVED_LIST"

        if page.source == TextResolutionSource.UNRESOLVED:
            return True, "SOURCE_UNRESOLVED"

        if page.verification_level == VerificationLevel.CONFLICT:
            return True, "VERIFICATION_CONFLICT"

        # Non-native (OCR/VLM) page with unverified level
        if (
            page.source != TextResolutionSource.TEXT_LAYER
            and page.verification_level == VerificationLevel.UNVERIFIED
        ):
            return True, "UNVERIFIED_VISUAL_OCR"

        return False, ""

    def _extract_pdf(
        self,
        doc_id: str,
        pages_data: list[tuple[int, str, float | None, bool]],
    ) -> tuple[list[ExtractionCandidate], list[ExtractionIssue]]:
        candidates: list[ExtractionCandidate] = []
        issues: list[ExtractionIssue] = []

        for page_num, text, page_conf, is_unresolved in pages_data:
            if is_unresolved:
                issues.append(
                    ExtractionIssue(
                        code="UNRESOLVED_VISUAL_PAGE",
                        message=f"Page {page_num} has unresolved visual/OCR conflicts and requires human review",
                        is_review_required=True,
                    )
                )
                continue

            lines = text.splitlines()
            line_idx = 0

            while line_idx < len(lines):
                line = lines[line_idx]
                if not line.strip() or line.strip().startswith("="):
                    line_idx += 1
                    continue

                boundaries = self._find_boundaries_in_line(line)

                if boundaries:
                    for k, b in enumerate(boundaries):
                        # Determine raw value span terminated by next boundary or EOL
                        if k + 1 < len(boundaries):
                            raw_span = line[b.val_start : boundaries[k + 1].start]
                        else:
                            raw_span = line[b.val_start :]

                        # Strip whitespace and any trailing separators (| or ; or \t)
                        raw_val = (
                            raw_span.rstrip(" \t")
                            .rstrip("|;\t")
                            .rstrip(" \t")
                            .lstrip(" \t")
                        )

                        if b.is_target and b.alias is not None:
                            conf = 0.70 if b.alias.is_generic else 0.95
                            if page_conf is not None:
                                conf = round(min(conf, page_conf), 2)

                            if raw_val:
                                candidates.append(
                                    ExtractionCandidate(
                                        field_path=b.alias.field_path,
                                        raw_value=raw_val,
                                        source_document_id=doc_id,
                                        page=page_num,
                                        confidence=conf,
                                        extraction_method="deterministic_header",
                                    )
                                )
                            else:
                                # Next-line lookahead is ONLY allowed if:
                                # 1. Sole boundary on this line (len(boundaries) == 1)
                                # 2. Next line is not another label or generic header
                                if len(boundaries) == 1 and line_idx + 1 < len(lines):
                                    next_line = lines[line_idx + 1].strip()
                                    if next_line and not self.is_any_known_label(next_line):
                                        candidates.append(
                                            ExtractionCandidate(
                                                field_path=b.alias.field_path,
                                                raw_value=next_line,
                                                source_document_id=doc_id,
                                                page=page_num,
                                                confidence=conf,
                                                extraction_method="deterministic_header",
                                            )
                                        )
                                        line_idx += 1
                                        break
                line_idx += 1

        return candidates, issues

    @staticmethod
    def _format_cell_representation(cell: ParsedCell) -> tuple[str, Any]:
        """Returns (raw_value_str, typed_value) preserving full source evidence and native types."""
        raw = cell.raw_value
        disp = cell.displayed_value
        if cell.is_formula or (isinstance(raw, str) and raw.strip().startswith("=")):
            return (str(raw).strip() if raw is not None else ""), raw

        # String representation of raw evidence
        if disp is not None:
            raw_str = str(disp).strip()
        elif raw is not None:
            raw_str = str(raw).strip()
        else:
            raw_str = ""

        # Safe typed value for numeric and date conversions
        typed_val = raw
        if isinstance(raw, bool):
            typed_val = raw
        elif isinstance(raw, float):
            if math.isfinite(raw):
                typed_val = Decimal(str(raw))
            else:
                typed_val = None
        elif isinstance(raw, int):
            typed_val = Decimal(raw)
        elif isinstance(raw, Decimal):
            typed_val = raw if raw.is_finite() else None

        return raw_str, typed_val

    def _extract_workbook(
        self,
        workbook: ParsedWorkbook,
    ) -> tuple[list[ExtractionCandidate], list[ExtractionIssue]]:
        candidates: list[ExtractionCandidate] = []
        issues: list[ExtractionIssue] = []
        doc_id = workbook.document_id

        # Worksheet visibility policy:
        # Only worksheets with state == "visible" are considered active presentation sheets.
        # Hidden sheets (state in ("hidden", "veryHidden")) are excluded from extraction
        # unless the workbook contains no visible sheets at all.
        visible_sheets = [s for s in workbook.sheets if s.state == "visible"]
        sheets_to_process = visible_sheets if visible_sheets else workbook.sheets

        for sheet in sheets_to_process:
            grid: dict[tuple[int, int], ParsedCell] = {
                (c.row, c.column): c for c in sheet.cells
            }
            sorted_cells = sorted(sheet.cells, key=lambda c: (c.row, c.column))

            for cell in sorted_cells:
                # Formula cells or expression text must never act as a label source
                if cell.is_formula or (isinstance(cell.raw_value, str) and cell.raw_value.strip().startswith("=")):
                    continue

                text_clean, cell_typed = self._format_cell_representation(cell)
                if not text_clean or text_clean.startswith("="):
                    continue

                # Run exact same boundary scanner as PDF on cell text
                boundaries = self._find_boundaries_in_line(text_clean)
                if not boundaries:
                    continue

                for k, b in enumerate(boundaries):
                    if k + 1 < len(boundaries):
                        raw_span = text_clean[b.val_start : boundaries[k + 1].start]
                    else:
                        raw_span = text_clean[b.val_start :]

                    raw_val = (
                        raw_span.rstrip(" \t")
                        .rstrip("|;\t")
                        .rstrip(" \t")
                        .lstrip(" \t")
                    )

                    if b.is_target and b.alias is not None:
                        conf = 0.70 if b.alias.is_generic else 0.95

                        if raw_val:
                            # Label and value in the same cell (inline)
                            # Typed value must correspond to the parsed value span, not the entire cell text
                            inline_typed: CandidateTypedValue = None
                            if b.alias.field_path in NUMERIC_HEADER_FIELDS:
                                inline_typed = parse_decimal(raw_val)
                            elif b.alias.field_path in DATE_HEADER_FIELDS:
                                inline_typed = parse_date(raw_val)

                            candidates.append(
                                ExtractionCandidate(
                                    field_path=b.alias.field_path,
                                    raw_value=raw_val,
                                    source_document_id=doc_id,
                                    page=None,
                                    sheet=sheet.name,
                                    cell=cell.coordinate,
                                    confidence=conf,
                                    extraction_method="deterministic_header",
                                    typed_value=inline_typed,
                                )
                            )
                        else:
                            # Label only: next-cell search (right, then below) is ONLY permitted
                            # if this label is the SOLE boundary in the cell (len(boundaries) == 1)
                            if len(boundaries) == 1:
                                value_found = False

                                # 1. Check right on same row
                                for col_offset in (1, 2, 3):
                                    target = grid.get((cell.row, cell.column + col_offset))
                                    if target is not None:
                                        target_str, target_typed = self._format_cell_representation(target)
                                        if target_str:
                                            # If target cell is another label or generic header, STOP!
                                            if self.is_any_known_label(target_str):
                                                break

                                            candidates.append(
                                                ExtractionCandidate(
                                                    field_path=b.alias.field_path,
                                                    raw_value=target_str,
                                                    source_document_id=doc_id,
                                                    page=None,
                                                    sheet=sheet.name,
                                                    cell=target.coordinate,
                                                    confidence=conf,
                                                    extraction_method="deterministic_header",
                                                    typed_value=target_typed,
                                                )
                                            )
                                            value_found = True
                                            break

                                # 2. Check below in same column
                                if not value_found:
                                    for row_offset in (1, 2):
                                        target = grid.get((cell.row + row_offset, cell.column))
                                        if target is not None:
                                            target_str, target_typed = self._format_cell_representation(target)
                                            if target_str:
                                                # If target cell is another label or generic header, STOP!
                                                if self.is_any_known_label(target_str):
                                                    break

                                                candidates.append(
                                                    ExtractionCandidate(
                                                        field_path=b.alias.field_path,
                                                        raw_value=target_str,
                                                        source_document_id=doc_id,
                                                        page=None,
                                                        sheet=sheet.name,
                                                        cell=target.coordinate,
                                                        confidence=conf,
                                                        extraction_method="deterministic_header",
                                                        typed_value=target_typed,
                                                    )
                                                )
                                                value_found = True
                                                break

        return candidates, issues

    def _resolve_canonical_fields(
        self,
        candidates: list[ExtractionCandidate],
    ) -> tuple[dict[str, CanonicalField[Any]], list[ExtractionIssue]]:
        resolved_fields: dict[str, CanonicalField[Any]] = {}
        issues: list[ExtractionIssue] = []

        cands_by_path: dict[str, list[ExtractionCandidate]] = {}
        for c in candidates:
            cands_by_path.setdefault(c.field_path, []).append(c)

        for field_path in APPROVED_HEADER_PATHS:
            field_cands = cands_by_path.get(field_path, [])
            if not field_cands:
                continue

            parsed_list: list[tuple[ExtractionCandidate, Any]] = []
            has_unparseable = False

            for c in field_cands:
                raw = c.raw_value.strip()
                if not raw:
                    continue

                # Conservative formula policy: unexecuted formula expressions starting with '='
                # must not be treated as business values for ANY field.
                if raw.startswith("="):
                    has_unparseable = True
                    issues.append(
                        ExtractionIssue(
                            code="UNRESOLVED_FORMULA_FIELD",
                            message=f"Field '{field_path}' contains unexecuted formula expression",
                            field_path=field_path,
                            is_review_required=True,
                        )
                    )
                    continue

                if field_path in NUMERIC_HEADER_FIELDS:
                    # Boolean and time values must never be treated as numeric values
                    if isinstance(c.typed_value, (bool, time)) or raw.lower() in ("true", "false"):
                        has_unparseable = True
                        issues.append(
                            ExtractionIssue(
                                code="UNPARSEABLE_NUMERIC_FIELD",
                                message=f"Field '{field_path}' contains unparseable numeric value",
                                field_path=field_path,
                                is_review_required=True,
                            )
                        )
                        continue

                    val_to_parse = c.typed_value if c.typed_value is not None else raw
                    parsed_num = parse_decimal(val_to_parse)
                    if parsed_num is None:
                        has_unparseable = True
                        issues.append(
                            ExtractionIssue(
                                code="UNPARSEABLE_NUMERIC_FIELD",
                                message=f"Field '{field_path}' contains unparseable numeric value",
                                field_path=field_path,
                                is_review_required=True,
                            )
                        )
                    else:
                        parsed_list.append((c, parsed_num))

                elif field_path in DATE_HEADER_FIELDS:
                    # Boolean and time values must never be treated as calendar dates
                    if isinstance(c.typed_value, (bool, time)) or raw.lower() in ("true", "false"):
                        has_unparseable = True
                        issues.append(
                            ExtractionIssue(
                                code="UNPARSEABLE_DATE_FIELD",
                                message=f"Field '{field_path}' contains unparseable date value",
                                field_path=field_path,
                                is_review_required=True,
                            )
                        )
                        continue

                    val_to_parse = c.typed_value if c.typed_value is not None else raw
                    parsed_dt = parse_date(val_to_parse)
                    if parsed_dt is None:
                        has_unparseable = True
                        issues.append(
                            ExtractionIssue(
                                code="UNPARSEABLE_DATE_FIELD",
                                message=f"Field '{field_path}' contains unparseable date value",
                                field_path=field_path,
                                is_review_required=True,
                            )
                        )
                    else:
                        parsed_list.append((c, parsed_dt))

                else:
                    # String field
                    parsed_list.append((c, raw))

            if has_unparseable and not parsed_list:
                continue

            if not parsed_list:
                continue

            # Check distinct material values
            unique_typed_values = set(val for _, val in parsed_list)

            if len(unique_typed_values) > 1:
                # Material conflict
                issues.append(
                    ExtractionIssue(
                        code="CONFLICTING_FIELD_VALUES",
                        message=f"Conflicting values detected for field '{field_path}'",
                        field_path=field_path,
                        is_review_required=True,
                    )
                )
                continue

            # Exactly one distinct material value: all candidates agree or single candidate!
            # Select primary candidate (highest confidence, then earliest appearance)
            primary_c, final_norm_val = max(
                parsed_list,
                key=lambda item: (item[0].confidence or 0.0),
            )

            resolved_fields[field_path] = CanonicalField(
                origin=ValueOrigin.EXTRACTED,
                raw_value=primary_c.raw_value,
                normalized_value=final_norm_val,
                source_document_id=primary_c.source_document_id,
                page=primary_c.page,
                sheet=primary_c.sheet,
                cell=primary_c.cell,
                confidence=primary_c.confidence,
                extraction_method="deterministic_header",
            )

        return resolved_fields, issues

    def _assemble_invoice(self, fields: dict[str, CanonicalField[Any]]) -> Invoice:
        seller: Party | None = None
        seller_name = fields.get("seller.name")
        seller_tax_id = fields.get("seller.tax_id")
        seller_address = fields.get("seller.address")
        if seller_name or seller_tax_id or seller_address:
            seller = Party(name=seller_name, tax_id=seller_tax_id, address=seller_address)

        buyer: Party | None = None
        buyer_name = fields.get("buyer.name")
        buyer_tax_id = fields.get("buyer.tax_id")
        buyer_address = fields.get("buyer.address")
        if buyer_name or buyer_tax_id or buyer_address:
            buyer = Party(name=buyer_name, tax_id=buyer_tax_id, address=buyer_address)

        ship_to: Party | None = None
        ship_to_name = fields.get("ship_to.name")
        ship_to_address = fields.get("ship_to.address")
        if ship_to_name or ship_to_address:
            ship_to = Party(name=ship_to_name, address=ship_to_address)

        return Invoice(
            invoice_number=fields.get("invoice_number"),
            invoice_date=fields.get("invoice_date"),
            seller=seller,
            buyer=buyer,
            ship_to=ship_to,
            currency=fields.get("currency"),
            incoterm=fields.get("incoterm"),
            payment_term=fields.get("payment_term"),
            total_amount=fields.get("total_amount"),
            freight=fields.get("freight"),
            insurance=fields.get("insurance"),
            discount=fields.get("discount"),
            items=[],
        )

    def extract(
        self,
        document: ParsedPdfDocument | ResolvedPdfDocument | ParsedWorkbook,
    ) -> InvoiceHeaderExtractionResult:
        """Extract invoice header fields deterministically from parsed or resolved document."""
        if isinstance(document, ParsedPdfDocument):
            if not document.has_text_layer and document.needs_ocr:
                issue = ExtractionIssue(
                    code="PDF_NEEDS_OCR",
                    message="PDF document has no extractable text layer and requires OCR",
                    is_review_required=True,
                )
                return InvoiceHeaderExtractionResult(
                    invoice=Invoice(),
                    status=ExtractionStatus.NEEDS_REVIEW,
                    issues=[issue],
                    candidates=[],
                )
            pages_data = [(p.page, p.text, None, False) for p in document.pages]
            candidates, issues = self._extract_pdf(document.document_id, pages_data)

        elif isinstance(document, ResolvedPdfDocument):
            doc_issues: list[ExtractionIssue] = []
            if document.requires_review:
                doc_issues.append(
                    ExtractionIssue(
                        code="DOCUMENT_REQUIRES_REVIEW",
                        message="Document has visual resolution review flags and requires human review",
                        is_review_required=True,
                    )
                )

            pages_data = []
            for p in document.pages:
                is_unres, _ = self._is_resolved_page_unsafe(document, p)
                pages_data.append((p.page, p.text, p.confidence, is_unres))

            candidates, issues = self._extract_pdf(document.document_id, pages_data)
            issues = doc_issues + issues

        elif isinstance(document, ParsedWorkbook):
            candidates, issues = self._extract_workbook(document)

        else:
            issue = ExtractionIssue(
                code="UNSUPPORTED_DOCUMENT_TYPE",
                message=f"Unsupported document type for extraction: {type(document).__name__}",
                is_review_required=True,
            )
            return InvoiceHeaderExtractionResult(
                invoice=Invoice(),
                status=ExtractionStatus.FAILED,
                issues=[issue],
                candidates=[],
            )

        resolved_fields, resolution_issues = self._resolve_canonical_fields(candidates)
        all_issues = issues + resolution_issues

        invoice = self._assemble_invoice(resolved_fields)

        has_review_issue = any(iss.is_review_required for iss in all_issues)
        status = ExtractionStatus.NEEDS_REVIEW if has_review_issue else ExtractionStatus.EXTRACTED

        return InvoiceHeaderExtractionResult(
            invoice=invoice,
            status=status,
            issues=all_issues,
            candidates=candidates,
        )


def extract_invoice_headers(
    document: ParsedPdfDocument | ResolvedPdfDocument | ParsedWorkbook,
    config: InvoiceExtractionConfig | None = None,
) -> InvoiceHeaderExtractionResult:
    """Convenience function for deterministic invoice header extraction."""
    extractor = DeterministicInvoiceHeaderExtractor(config=config)
    return extractor.extract(document)
