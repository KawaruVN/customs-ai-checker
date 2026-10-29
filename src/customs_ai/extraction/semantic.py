"""Optional header proposals with independently verified, role-labelled evidence.

This boundary never supplies an AI implementation. It accepts only whole-label
adjacent Excel values or explicit ``LABEL: value`` PDF lines. Other layouts,
unlabelled prose, semantic item matching and inferred business values abstain.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
import math
import re
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, Invoice
from customs_ai.extraction.config import APPROVED_HEADER_PATHS, load_invoice_extraction_config, normalize_alias
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.mapper import parse_date, parse_decimal
from customs_ai.extraction.models import ExtractionCandidate, ExtractionIssue, InvoiceHeaderExtractionResult
from customs_ai.parsers.models import ParsedPdfDocument, ParsedWorkbook
from customs_ai.repositories.extraction_models import deserialize_result, serialize_result
from customs_ai.vision.enums import TextResolutionSource, VerificationLevel
from customs_ai.vision.evaluator import TextQualityEvaluator
from customs_ai.vision.models import ResolvedPdfDocument

NUMERIC_PATHS = frozenset({"total_amount", "freight", "insurance", "discount"})


class SemanticSource(BaseModel):
    """A single independently role-labelled source span, with no stored paths."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    field_path: StrictStr
    raw_value: StrictStr
    page: int | None = Field(default=None, ge=1)
    sheet: StrictStr | None = None
    cell: StrictStr | None = None


class SemanticInvoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_id: StrictStr
    sources: list[SemanticSource]

    @field_validator("document_id")
    @classmethod
    def validate_document_id(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("Invalid semantic document identifier.")
        return value


class SemanticInvoiceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: StrictStr
    candidates: list[ExtractionCandidate]


class SemanticInvoiceProvider(Protocol):
    def extract(self, request: SemanticInvoiceRequest) -> SemanticInvoiceResponse:
        """Propose typed values using only request sources; no trust is implied."""
        ...


@dataclass(frozen=True)
class _Grounded:
    source: SemanticSource
    value: str | date | Decimal


def _issue(code: str, path: str | None = None) -> ExtractionIssue:
    return ExtractionIssue(
        code=code, message="Semantic proposal requires independent review.",
        field_path=path, is_review_required=True,
    )


def _parse(path: str, raw):
    if isinstance(raw, (bool, time)):
        return None
    if isinstance(raw, str) and (not raw.strip() or raw.lstrip().startswith("=")):
        return None
    if path in NUMERIC_PATHS:
        if isinstance(raw, (date, datetime)):
            return None
        if type(raw) is float:
            return Decimal(str(raw)) if math.isfinite(raw) else None
        return parse_decimal(raw)
    if path == "invoice_date":
        return parse_date(raw)
    if isinstance(raw, (date, datetime, float)):
        return None
    return str(raw).strip() if raw is not None else None


def _sources(document) -> list[_Grounded]:
    aliases = {
        normalize_alias(alias).rstrip(":：").rstrip(): path
        for path, labels in load_invoice_extraction_config().headers.items()
        for alias in labels
    }
    # Long/specific aliases precede generic labels; fullmatch prevents substrings.
    labels = sorted(aliases, key=len, reverse=True)
    expressions = [
        (aliases[label], re.compile(r"^\s*" + r"\s+".join(re.escape(word) for word in label.split()) + r"\s*[:：](?P<value>.*)$", re.IGNORECASE))
        for label in labels
    ]
    embedded = re.compile(
        r"(?:^|[\s|;])(?:" + "|".join(r"\s+".join(re.escape(word) for word in label.split()) for label in labels) + r")\s*[:：]",
        re.IGNORECASE,
    )
    grounded: list[_Grounded] = []

    def add(path, raw, **location):
        value = _parse(path, raw)
        if value is not None:
            grounded.append(_Grounded(SemanticSource(field_path=path, raw_value=str(raw), **location), value))

    def inline(text, **location):
        if not isinstance(text, str) or text.lstrip().startswith("="):
            return
        for path, pattern in expressions:
            match = pattern.fullmatch(text)
            if match:
                raw = match["value"]
                if raw.strip() and not embedded.search(raw):
                    add(path, raw, **location)
                return

    if isinstance(document, ParsedWorkbook):
        names = [sheet.name for sheet in document.sheets]
        if len(names) != len(set(names)):
            return []
        for sheet in document.sheets:
            if sheet.state != "visible":
                continue
            grid = {(cell.row, cell.column): cell for cell in sheet.cells}
            if len(grid) != len(sheet.cells):
                continue
            for cell in sheet.cells:
                if not _eligible_cell(cell, sheet):
                    continue
                inline(cell.raw_value, sheet=sheet.name, cell=cell.coordinate)
                if not isinstance(cell.raw_value, str):
                    continue
                label = normalize_alias(cell.raw_value).rstrip(":：").rstrip()
                path = aliases.get(label)
                target = grid.get((cell.row, cell.column + 1))
                if path is None or target is None or not _eligible_cell(target, sheet):
                    continue
                if isinstance(target.raw_value, str):
                    if normalize_alias(target.raw_value).rstrip(":：").rstrip() in aliases or embedded.search(target.raw_value):
                        continue
                add(path, target.raw_value, sheet=sheet.name, cell=target.coordinate)
    else:
        for page in document.pages:
            for line in page.text.splitlines():
                inline(line, page=page.page)
    return grounded


def _eligible_cell(cell, sheet) -> bool:
    if cell.row in sheet.hidden_rows or cell.is_formula or cell.data_type == "f":
        return False
    if isinstance(cell.raw_value, str) and cell.raw_value.lstrip().startswith("="):
        return False
    address = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", cell.coordinate)
    if not address or int(address[2]) != cell.row:
        return False
    col = 0
    for letter in address[1]:
        col = col * 26 + ord(letter) - ord("A") + 1
    if col != cell.column or address[1] in {value.upper() for value in sheet.hidden_columns}:
        return False
    # Merged cells cannot establish a unique label/value role in this policy.
    for merged in sheet.merged_ranges:
        match = re.fullmatch(r"([A-Z]+)([0-9]+):([A-Z]+)([0-9]+)", merged)
        if not match:
            return False
        def column(text):
            value = 0
            for char in text:
                value = value * 26 + ord(char) - ord("A") + 1
            return value
        if int(match[2]) <= cell.row <= int(match[4]) and column(match[1]) <= cell.column <= column(match[3]):
            return False
    return True


def _safe_document(document) -> bool:
    if not isinstance(document, (ParsedWorkbook, ParsedPdfDocument, ResolvedPdfDocument)):
        return False
    if isinstance(document, ParsedWorkbook):
        return True
    if document.page_count != len(document.pages) or [page.page for page in document.pages] != list(range(1, document.page_count + 1)):
        return False
    evaluator = TextQualityEvaluator()
    if isinstance(document, ParsedPdfDocument):
        return not document.needs_ocr and document.has_text_layer and all(evaluator.evaluate_native_text(page.text) for page in document.pages)
    if document.requires_review or document.unresolved_pages:
        return False
    for page in document.pages:
        if page.requires_review or page.source == TextResolutionSource.UNRESOLVED or page.verification_level == VerificationLevel.CONFLICT:
            return False
        if page.source == TextResolutionSource.TEXT_LAYER:
            if not evaluator.evaluate_native_text(page.text):
                return False
        elif page.verification_level == VerificationLevel.UNVERIFIED or not evaluator.evaluate_provider_result(page.text, page.confidence):
            return False
    return True


def _get(invoice: Invoice, path: str):
    value = invoice
    for part in path.split("."):
        value = getattr(value, part, None)
        if value is None:
            return None
    return value


def merge_semantic(document, deterministic: InvoiceHeaderExtractionResult, provider: SemanticInvoiceProvider) -> InvoiceHeaderExtractionResult:
    """Validate proposals independently, fill missing headers, keep review sticky."""
    base = deserialize_result(serialize_result(deterministic))
    if not isinstance(base, InvoiceHeaderExtractionResult):
        raise ValueError("Semantic merge requires an invoice result.")
    issues = list(base.issues)

    def finish():
        status = base.status
        if status != ExtractionStatus.FAILED and any(issue.is_review_required for issue in issues):
            status = ExtractionStatus.NEEDS_REVIEW
        return InvoiceHeaderExtractionResult.model_validate({
            "invoice": base.invoice.model_dump(mode="python"), "status": status,
            "issues": [issue.model_dump(mode="python") for issue in issues],
            "candidates": [candidate.model_dump(mode="python") for candidate in base.candidates],
        })

    if not _safe_document(document) or base.status == ExtractionStatus.FAILED:
        issues.append(_issue("UNSAFE_SEMANTIC_CONTEXT"))
        return finish()
    trusted = _sources(document)
    if not trusted:
        return finish()
    request = SemanticInvoiceRequest(document_id=document.document_id, sources=[value.source.model_copy(deep=True) for value in trusted])
    try:
        response = provider.extract(request)
        raw_response = response.model_dump(mode="python", warnings="error") if isinstance(response, BaseModel) else response
        response = SemanticInvoiceResponse.model_validate(raw_response)
    except Exception:
        issues.append(_issue("SEMANTIC_PROVIDER_FAILED"))
        return finish()
    if response.document_id != document.document_id:
        issues.append(_issue("SEMANTIC_DOCUMENT_MISMATCH"))
        return finish()

    blocked = {issue.field_path for issue in issues if issue.is_review_required}
    blocked.update(candidate.field_path for candidate in base.candidates if _get(base.invoice, candidate.field_path) is None)
    source_values: dict[str, set] = {}
    for source in trusted:
        source_values.setdefault(source.source.field_path, set()).add((type(source.value), source.value))
    source_conflicts = {path for path, values in source_values.items() if len(values) > 1}
    accepted: dict[str, list[tuple[ExtractionCandidate, _Grounded]]] = {}
    for candidate in response.candidates:
        path = candidate.field_path
        if path not in APPROVED_HEADER_PATHS:
            issues.append(_issue("SEMANTIC_UNSUPPORTED_FIELD"))
            continue
        if path in source_conflicts:
            issues.append(_issue("SEMANTIC_CONFLICTING_VALUES", path))
            continue
        matches = [item for item in trusted if (
            item.source.field_path == path and item.source.raw_value == candidate.raw_value
            and item.source.page == candidate.page and item.source.sheet == candidate.sheet
            and item.source.cell == candidate.cell
        )]
        if candidate.source_document_id != document.document_id or not matches or candidate.bounding_box is not None:
            issues.append(_issue("SEMANTIC_UNGROUNDED_FIELD", path))
            continue
        grounded = matches[0]
        if type(candidate.typed_value) is not type(grounded.value) or candidate.typed_value != grounded.value:
            issues.append(_issue("SEMANTIC_INVALID_TYPED_VALUE", path))
            continue
        if path in blocked:
            issues.append(_issue("SEMANTIC_BLOCKED_DETERMINISTIC_FIELD", path))
            continue
        current = _get(base.invoice, path)
        if current is not None:
            if current.normalized_value != grounded.value:
                issues.append(_issue("SEMANTIC_OVERWRITE_REJECTED", path))
            continue
        accepted.setdefault(path, []).append((candidate, grounded))

    invoice = base.invoice.model_dump(mode="python")
    for path, proposals in accepted.items():
        if len({(type(value.value), value.value) for _, value in proposals}) != 1:
            issues.append(_issue("SEMANTIC_CONFLICTING_VALUES", path))
            continue
        candidate, value = proposals[0]
        field = CanonicalField(
            raw_value=value.source.raw_value, normalized_value=value.value,
            origin=ValueOrigin.EXTRACTED, source_document_id=document.document_id,
            page=value.source.page, sheet=value.source.sheet, cell=value.source.cell,
            confidence=None, extraction_method="semantic_grounded_header",
        )
        target = invoice
        parts = path.split(".")
        if len(parts) == 2:
            target = invoice.setdefault(parts[0], {})
            if target is None:
                target = invoice[parts[0]] = {}
        target[parts[-1]] = field.model_dump(mode="python")
        base.candidates.append(ExtractionCandidate(
            field_path=path, raw_value=value.source.raw_value,
            source_document_id=document.document_id, page=value.source.page,
            sheet=value.source.sheet, cell=value.source.cell,
            extraction_method="semantic_grounded_header", typed_value=value.value,
        ))
    base.invoice = Invoice.model_validate(invoice)
    return finish()
