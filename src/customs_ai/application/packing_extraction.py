"""Packing-only orchestration with source, evidence and transactional boundaries."""

from hashlib import sha256
from datetime import date
from decimal import Decimal
import math
import re

from pydantic import BaseModel

from customs_ai.application.packing_models import PackingExtractionOutcome, PackingExtractionRequest
from customs_ai.application.parsing import DocumentParsingService
from customs_ai.application.paths import resolve_source_path
from customs_ai.classification.config import load_classification_config
from customs_ai.classification.deterministic import DeterministicClassifier
from customs_ai.classification.enums import DocumentType
from customs_ai.classification.models import DocumentClassificationResult
from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField, PackingList
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.models import ExtractionIssue
from customs_ai.extraction.mapper import parse_date, parse_decimal
from customs_ai.extraction.packing_headers import DeterministicPackingHeaderExtractor
from customs_ai.extraction.packing_items import DeterministicPackingItemExtractor
from customs_ai.extraction.packing_models import PackingItemExtractionResult, PackingListHeaderExtractionResult
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.models import SourceDocument
from customs_ai.parsers.models import ParsedPdfDocument, ParsedWorkbook
from customs_ai.repositories.document_extractions import DocumentExtractionRepository, ExtractionConflictError
from customs_ai.repositories.extraction_models import ExtractionAttempt, ExtractionRecord, ExtractionReplacement, deserialize_result, serialize_result
from customs_ai.repositories.source_documents import SourceDocumentRepository
from customs_ai.vision.enums import TextResolutionSource
from customs_ai.vision.models import ResolvedPdfDocument


def _issue(code):
    return ExtractionIssue(code=code, message="Packing extraction requires review.", is_review_required=True)


def _empty(status, code):
    return PackingListHeaderExtractionResult(packing_list=PackingList(), status=status, issues=[_issue(code)])


def _fields(value):
    if isinstance(value, CanonicalField):
        yield value
    elif isinstance(value, BaseModel):
        for _, child in value:
            yield from _fields(child)
    elif isinstance(value, list):
        for child in value:
            yield from _fields(child)


class PackingExtractionService:
    def __init__(self, repository: SourceDocumentRepository, parsing_service=None, classifier=None,
                 extraction_repository=None, header_extractor=None, item_extractor=None, vision_service=None):
        self.repository = repository
        self.parsing = parsing_service if parsing_service is not None else DocumentParsingService(repository)
        config = load_classification_config()
        self._authoritative_classifier = DeterministicClassifier(config)
        self.classifier = classifier if classifier is not None else self._authoritative_classifier
        self.classification_threshold = config.settings.threshold
        self.extractions = extraction_repository if extraction_repository is not None else DocumentExtractionRepository()
        self._pdf_policy = DeterministicPackingHeaderExtractor()
        self.headers = header_extractor if header_extractor is not None else self._pdf_policy
        self.items = item_extractor if item_extractor is not None else DeterministicPackingItemExtractor()
        self.vision = vision_service

    @staticmethod
    def _fingerprint(source):
        path = resolve_source_path(source.stored_path)
        if path.stat().st_size != source.file_size:
            raise ValueError("Invalid source size")
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _source_unchanged(self, source):
        return self.repository.get_by_document_id(source.document_id) == source and self._fingerprint(source) == source.file_hash

    def _stored_classification_safe(self, source):
        confidence = source.classification_confidence
        return (source.detected_document_type == DocumentType.PACKING_LIST.value
                and isinstance(confidence, (float, int)) and not isinstance(confidence, bool)
                and math.isfinite(confidence) and self.classification_threshold <= confidence <= 1
                and source.processing_status in {ProcessingStatus.CLASSIFIED, ProcessingStatus.EXTRACTED,
                    ProcessingStatus.NEEDS_REVIEW, ProcessingStatus.FAILED, ProcessingStatus.NORMALIZED})

    @staticmethod
    def _classification_context(document):
        if not isinstance(document, ParsedWorkbook):
            return document
        data = document.model_dump(mode="python", warnings="error")
        sheets = []
        for original, sheet in zip(document.sheets, data["sheets"], strict=True):
            grid = DeterministicPackingItemExtractor._grid(original)
            if sheet["state"] != "visible":
                continue
            visible_cells = {cell.coordinate for cell in original.cells if grid.visible(cell)}
            sheet["cells"] = [cell for cell in sheet["cells"] if not (
                cell["coordinate"] not in visible_cells
                or cell["is_formula"] or cell["data_type"].lower() == "f"
                or isinstance(cell["raw_value"], str) and cell["raw_value"].lstrip().startswith("="))]
            sheets.append(sheet)
        data.update(sheets=sheets, sheet_count=len(sheets))
        return ParsedWorkbook.model_validate(data)

    def _classifies_as_packing(self, document):
        context = self._classification_context(document)
        try:
            output = self.classifier.classify(context)
            classification = DocumentClassificationResult.model_validate(output.model_dump(mode="python", warnings="error"))
        except Exception:
            return False
        grounded = (classification if self.classifier is self._authoritative_classifier
                    else self._authoritative_classifier.classify(context))
        return (classification == grounded and classification.document_id == document.document_id
                and classification.document_type == DocumentType.PACKING_LIST
                and classification.confidence >= self.classification_threshold
                and bool(classification.evidence))

    def _safe_pdf(self, document):
        expected = set(range(1, document.page_count + 1))
        if not expected or len(document.pages) != document.page_count or {p.page for p in document.pages} != expected:
            return None
        if self._pdf_policy._safe_pdf(document):
            return document
        if self.vision is None:
            return None
        try:
            output = self.vision.resolve_document(document.document_id, document)
            if not isinstance(output, ResolvedPdfDocument):
                return None
            resolved = ResolvedPdfDocument.model_validate(output.model_dump(mode="python", warnings="error"))
            originals = {p.page: p.text for p in document.pages}
            if (resolved.document_id != document.document_id or resolved.file_type != document.file_type
                    or resolved.page_count != document.page_count or not self._pdf_policy._safe_pdf(resolved)
                    or any(page.source == TextResolutionSource.TEXT_LAYER and page.text != originals[page.page]
                           for page in resolved.pages)):
                return None
            return resolved
        except Exception:
            return None

    def _grounding(self, result, document):
        """Check source identity/location/raw evidence, including injected outputs."""
        cells = {}
        if isinstance(document, ParsedWorkbook):
            for sheet in document.sheets:
                grid = DeterministicPackingItemExtractor._grid(sheet)
                for cell in sheet.cells:
                    key = (sheet.name, cell.coordinate)
                    if key in cells:
                        raise ValueError("Ambiguous evidence location")
                    visible = grid.visible(cell)
                    safe = visible and cell.raw_value is not None and not (cell.is_formula or cell.data_type.lower() in {"f", "e", "error"}
                                            or isinstance(cell.raw_value, str) and cell.raw_value.lstrip().startswith("="))
                    cells[key] = (str(cell.raw_value), safe, cell.raw_value)
        else:
            pages = {page.page: page.text for page in document.pages}
        for value in list(_fields(result.packing_list)) + list(result.candidates):
            if value.source_document_id != document.document_id or not value.raw_value:
                # Empty missing-label candidates are legitimate unresolved evidence.
                if isinstance(value, CanonicalField) or value.source_document_id != document.document_id:
                    raise ValueError("Invalid evidence identity")
            accepted = isinstance(value, CanonicalField)
            if accepted and value.origin != ValueOrigin.EXTRACTED:
                raise ValueError("Non-extracted pipeline value")
            if isinstance(document, ParsedWorkbook):
                raw, safe, native = cells.get((value.sheet, value.cell), (None, False, None))
                exact = (value.raw_value == raw or isinstance(native, str)
                         and any(span == value.raw_value for _, span in self._pdf_policy._spans(native)))
                if value.page is not None or raw is None or not exact or accepted and not safe:
                    raise ValueError("Invalid cell evidence")
            else:
                if value.sheet is not None or value.cell is not None or value.page not in pages:
                    raise ValueError("Invalid page evidence")
                lines = pages[value.page].splitlines()
                if not any(value.raw_value == line or any(span == value.raw_value for _, span in self._pdf_policy._spans(line))
                           for line in lines):
                    raise ValueError("Invalid raw page evidence")
                native = value.raw_value
            if accepted:
                original = native if not isinstance(native, str) else value.raw_value
                normalized = value.normalized_value
                if isinstance(normalized, Decimal):
                    expected = Decimal(str(original)) if type(original) is float and math.isfinite(original) else parse_decimal(original)
                elif type(normalized) is date:
                    expected = parse_date(original)
                elif type(normalized) is str:
                    expected = value.raw_value.strip() if isinstance(original, str) else None
                else:
                    raise ValueError("Unsupported canonical value")
                if expected is None or normalized != expected:
                    raise ValueError("Canonical value differs from source evidence")

    def _header_context(self, document, item_result):
        """Route proven goods rows away from shared document-weight aliases.

        Only a clean supported item result can identify rows to omit. Footer
        candidates are not goods: use actual accepted fields plus header evidence.
        No component issue is discarded; reviewable tables retain full context.
        """
        if item_result.status != ExtractionStatus.EXTRACTED:
            return document
        rows = set()
        mapped_columns = {}
        for item in item_result.items:
            for value in _fields(item):
                match = re.fullmatch(r"[A-Z]+([1-9][0-9]*)", value.cell or "")
                if match and value.source_document_id == document.document_id:
                    rows.add((value.sheet, int(match[1])))
        for candidate in item_result.candidates:
            if candidate.field_path.startswith("headers.tables["):
                column = re.search(r"\.columns\[([0-9]+)\]\.", candidate.field_path)
                if column:
                    mapped_columns.setdefault(candidate.sheet, set()).add(int(column[1]))
                match = re.fullmatch(r"[A-Z]+([1-9][0-9]*)", candidate.cell or "")
                if match and candidate.source_document_id == document.document_id:
                    rows.add((candidate.sheet, int(match[1])))
        for sheet in document.sheets:
            for cell in sheet.cells:
                if ((sheet.name, cell.row) in rows and cell.column not in mapped_columns.get(sheet.name, set())
                        and isinstance(cell.raw_value, str)
                        and any(label.path is not None for label, _ in self._pdf_policy._spans(cell.raw_value))):
                    return document  # Mixed header/goods row needs the complete conservative context.
        data = document.model_dump(mode="python", warnings="error")
        for sheet in data["sheets"]:
            sheet["cells"] = [cell for cell in sheet["cells"] if (sheet["name"], cell["row"]) not in rows]
        return ParsedWorkbook.model_validate(data)

    def _assemble(self, document):
        item_result = None
        header_context = document
        if isinstance(document, ParsedWorkbook):
            item_output = self.items.extract(document)
            if not isinstance(item_output, PackingItemExtractionResult):
                raise ValueError("Invalid Packing item contract")
            item_result = PackingItemExtractionResult.model_validate(item_output.model_dump(mode="python", warnings="error"))
            header_context = self._header_context(document, item_result)
        output = self.headers.extract(header_context)
        if not isinstance(output, PackingListHeaderExtractionResult):
            raise ValueError("Invalid Packing header contract")
        headers = PackingListHeaderExtractionResult.model_validate(output.model_dump(mode="python", warnings="error"))
        if headers.packing_list.items:
            raise ValueError("Header extractor supplied unsupported items")
        data = headers.model_dump(mode="python", warnings="error")
        issues, candidates, statuses = list(headers.issues), [], [headers.status]
        for candidate in headers.candidates:
            candidates.append(candidate.model_copy(update={"field_path": "header." + candidate.field_path}))
        if isinstance(document, ParsedWorkbook):
            data["packing_list"]["items"] = [item.model_dump(mode="python") for item in item_result.items]
            statuses.append(item_result.status)
            issues.extend(item_result.issues)
            candidates.extend(candidate.model_copy(update={"field_path": "items." + candidate.field_path}) for candidate in item_result.candidates)
        else:
            issues.append(_issue("PDF_PACKING_ITEMS_UNSUPPORTED"))
        if not any(_fields(headers.packing_list)):
            issues.append(_issue("PACKING_HEADERS_UNRESOLVED"))
        if isinstance(document, ParsedWorkbook) and not data["packing_list"]["items"]:
            issues.append(_issue("PACKING_ITEMS_UNRESOLVED"))
        status = (ExtractionStatus.FAILED if ExtractionStatus.FAILED in statuses else
                  ExtractionStatus.NEEDS_REVIEW if ExtractionStatus.NEEDS_REVIEW in statuses or any(i.is_review_required for i in issues)
                  else ExtractionStatus.EXTRACTED)
        data.update(status=status, issues=issues, candidates=candidates)
        result = PackingListHeaderExtractionResult.model_validate(data)
        self._grounding(result, document)
        return result

    def extract_document(self, document_id, *, expected_active_extraction_id=None,
                         expected_source_file_hash=None, expected_processing_status=None):
        try:
            request = PackingExtractionRequest(document_id=document_id, expected_active_extraction_id=expected_active_extraction_id,
                expected_source_file_hash=expected_source_file_hash, expected_processing_status=expected_processing_status)
        except Exception:
            return PackingExtractionOutcome(document_id=None, result=_empty(ExtractionStatus.FAILED, "INVALID_EXTRACTION_REQUEST"))
        active = None

        def refuse(code, status=ExtractionStatus.NEEDS_REVIEW):
            return PackingExtractionOutcome(document_id=request.document_id, result=_empty(status, code), active_record=active)

        try:
            stored = self.repository.get_by_document_id(request.document_id)
            if stored is None:
                return refuse("SOURCE_DOCUMENT_NOT_FOUND", ExtractionStatus.FAILED)
            source = SourceDocument.model_validate(stored.model_dump(mode="python", warnings="error"))
            if source.document_id != request.document_id or source.file_type not in {"pdf", "xlsx", "xls"}:
                return refuse("UNSUPPORTED_PACKING_SOURCE")
            if not self._stored_classification_safe(source):
                return refuse("UNSAFE_PACKING_CLASSIFICATION")
            if (request.expected_source_file_hash is not None and request.expected_source_file_hash != source.file_hash
                    or request.expected_processing_status is not None and request.expected_processing_status != source.processing_status):
                return refuse("STALE_EXTRACTION_SOURCE")
            observed = self.extractions.get_active(source.document_id)
            if observed is not None:
                observed = ExtractionRecord.model_validate(observed.model_dump(mode="python", warnings="error"))
                if (observed.document_id != source.document_id or not observed.is_active
                        or not isinstance(observed.result, PackingListHeaderExtractionResult)):
                    return refuse("INCOMPATIBLE_ACTIVE_EXTRACTION")
                active = observed
            if active is not None and request.expected_active_extraction_id is None:
                return refuse("ACTIVE_EXTRACTION_EXISTS")
            if request.expected_active_extraction_id is not None and (active is None or active.extraction_id != request.expected_active_extraction_id):
                return refuse("STALE_ACTIVE_EXTRACTION")
            if self._fingerprint(source) != source.file_hash:
                return refuse("SOURCE_HASH_MISMATCH")
        except Exception:
            return refuse("SOURCE_PREFLIGHT_FAILED", ExtractionStatus.FAILED)
        try:
            parsed = self.parsing.parse_document_readonly(source.document_id)
            if not isinstance(parsed, (ParsedPdfDocument, ParsedWorkbook)):
                raise ValueError("Unsupported parser result")
            parsed = type(parsed).model_validate(parsed.model_dump(mode="python", warnings="error"))
            if parsed.document_id != source.document_id or parsed.file_type != source.file_type:
                raise ValueError("Invalid parser identity")
            document = self._safe_pdf(parsed) if isinstance(parsed, ParsedPdfDocument) else parsed
            if document is None:
                result = _empty(ExtractionStatus.NEEDS_REVIEW, "UNSAFE_VISUAL_DOCUMENT")
                result.issues.append(_issue("PDF_PACKING_ITEMS_UNSUPPORTED"))
            elif not self._classifies_as_packing(document):
                return refuse("CLASSIFICATION_EVIDENCE_MISMATCH")
            else:
                result = self._assemble(document)
        except Exception:
            result = _empty(ExtractionStatus.FAILED, "PACKING_EXTRACTION_FAILED")
        try:
            if not self._source_unchanged(source):
                return refuse("SOURCE_CHANGED_DURING_EXTRACTION")
            validated = deserialize_result(serialize_result(result))
            if not isinstance(validated, PackingListHeaderExtractionResult):
                raise ValueError("Invalid composed Packing result")
            values = dict(document_id=source.document_id, source_file_hash=source.file_hash,
                          expected_processing_status=source.processing_status, expected_source_document=source,
                          result=validated, extraction_method="packing_extraction_service")
            record = (self.extractions.save_attempt(ExtractionAttempt(**values)) if request.expected_active_extraction_id is None
                      else self.extractions.replace_active(ExtractionReplacement(**values,
                           expected_active_extraction_id=request.expected_active_extraction_id)))
            return PackingExtractionOutcome(document_id=source.document_id, result=validated, record=record,
                                            active_record=record if record.is_active else active)
        except ExtractionConflictError:
            return refuse("EXTRACTION_PERSISTENCE_CONFLICT", ExtractionStatus.FAILED)
        except Exception:
            return refuse("EXTRACTION_PERSISTENCE_FAILED", ExtractionStatus.FAILED)
