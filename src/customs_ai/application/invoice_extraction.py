"""Local-first invoice orchestration with explicit safety and write boundaries.

Preconditions/refusals do not write. Verified-source technical extraction failures
are persisted as FAILED attempts; unsafe visual content becomes NEEDS_REVIEW.
Persistence failures are returned without retrying or writing a second attempt.
"""

from hashlib import sha256
import math

from customs_ai.application.invoice_models import InvoiceExtractionOutcome, InvoiceExtractionRequest
from customs_ai.application.parsing import DocumentParsingService
from customs_ai.application.paths import resolve_source_path
from customs_ai.classification.config import load_classification_config
from customs_ai.classification.deterministic import DeterministicClassifier
from customs_ai.classification.enums import DocumentType
from customs_ai.classification.models import DocumentClassificationResult
from customs_ai.domain.schema import Invoice
from customs_ai.extraction.config import APPROVED_HEADER_PATHS
from customs_ai.extraction.enums import ExtractionStatus
from customs_ai.extraction.headers import DeterministicInvoiceHeaderExtractor
from customs_ai.extraction.items import DeterministicInvoiceItemExtractor
from customs_ai.extraction.models import ExtractionIssue, InvoiceHeaderExtractionResult, InvoiceItemExtractionResult
from customs_ai.extraction.semantic import SemanticInvoiceProvider, merge_semantic
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.models import SourceDocument
from customs_ai.parsers.models import ParsedPdfDocument, ParsedWorkbook
from customs_ai.repositories.document_extractions import DocumentExtractionRepository, ExtractionConflictError
from customs_ai.repositories.extraction_models import ExtractionAttempt, ExtractionReplacement, deserialize_result, serialize_result
from customs_ai.repositories.source_documents import SourceDocumentRepository
from customs_ai.vision.enums import TextResolutionSource, VerificationLevel
from customs_ai.vision.evaluator import TextQualityEvaluator
from customs_ai.vision.models import ResolvedPdfDocument


def _issue(code: str, message: str) -> ExtractionIssue:
    return ExtractionIssue(code=code, message=message, is_review_required=True)


def _empty(status: ExtractionStatus, code: str, message: str) -> InvoiceHeaderExtractionResult:
    return InvoiceHeaderExtractionResult(invoice=Invoice(), status=status, issues=[_issue(code, message)])


def _value(invoice: Invoice, path: str):
    node = invoice
    for part in path.split("."):
        node = getattr(node, part, None)
        if node is None:
            break
    return node


class InvoiceExtractionService:
    def __init__(
        self,
        repository: SourceDocumentRepository,
        parsing_service=None,
        classifier=None,
        extraction_repository=None,
        header_extractor=None,
        item_extractor=None,
        vision_service=None,
        semantic_provider: SemanticInvoiceProvider | None = None,
    ) -> None:
        self.repository = repository
        self.parsing = parsing_service if parsing_service is not None else DocumentParsingService(repository)
        self.classifier = classifier if classifier is not None else DeterministicClassifier(load_classification_config())
        self.extractions = extraction_repository if extraction_repository is not None else DocumentExtractionRepository()
        self.headers = header_extractor if header_extractor is not None else DeterministicInvoiceHeaderExtractor()
        self.items = item_extractor if item_extractor is not None else DeterministicInvoiceItemExtractor()
        self.vision = vision_service
        self.semantic = semantic_provider
        self.quality = TextQualityEvaluator()
        self.classification_threshold = load_classification_config().settings.threshold

    @staticmethod
    def _fingerprint(source: SourceDocument) -> str:
        path = resolve_source_path(source.stored_path)
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _source_unchanged(self, source: SourceDocument) -> bool:
        current = self.repository.get_by_document_id(source.document_id)
        return current == source and self._fingerprint(source) == source.file_hash

    def _stored_classification_safe(self, source: SourceDocument) -> bool:
        confidence = source.classification_confidence
        return (
            source.detected_document_type == DocumentType.COMMERCIAL_INVOICE.value
            and isinstance(confidence, (int, float))
            and not isinstance(confidence, bool)
            and math.isfinite(confidence)
            and self.classification_threshold <= confidence <= 1
            and source.processing_status in {
                ProcessingStatus.CLASSIFIED, ProcessingStatus.EXTRACTED,
                ProcessingStatus.NEEDS_REVIEW, ProcessingStatus.FAILED, ProcessingStatus.NORMALIZED,
            }
        )

    @staticmethod
    def _visible_workbook(document: ParsedWorkbook) -> tuple[ParsedWorkbook, bool]:
        data = document.model_dump(mode="python", warnings="error")
        sheets = []
        omitted = False
        for sheet in data["sheets"]:
            if sheet["state"] != "visible":
                omitted |= bool(sheet["cells"])
                continue
            kept = []
            for cell in sheet["cells"]:
                letters = "".join(c for c in cell["coordinate"] if c.isalpha()).upper()
                if cell["row"] in sheet["hidden_rows"] or letters in {c.upper() for c in sheet["hidden_columns"]}:
                    omitted |= cell["raw_value"] is not None
                    continue
                kept.append(cell)
            sheet["cells"] = kept
            sheets.append(sheet)
        data["sheets"] = sheets
        data["sheet_count"] = len(sheets)
        return ParsedWorkbook.model_validate(data), omitted

    def _classification_context(self, document):
        if not isinstance(document, ParsedWorkbook):
            return document
        visible, _ = self._visible_workbook(document)
        data = visible.model_dump(mode="python")
        for sheet in data["sheets"]:
            sheet["cells"] = [cell for cell in sheet["cells"] if not (
                cell["is_formula"] or cell["data_type"] == "f"
                or isinstance(cell["raw_value"], str) and cell["raw_value"].lstrip().startswith("=")
            )]
        return ParsedWorkbook.model_validate(data)

    def _safe_pdf(self, document: ParsedPdfDocument):
        expected = set(range(1, document.page_count + 1))
        if not expected or len(document.pages) != document.page_count or {p.page for p in document.pages} != expected:
            return None
        needs_vision = document.needs_ocr or not document.has_text_layer or any(
            not self.quality.evaluate_native_text(page.text) for page in document.pages
        )
        if not needs_vision:
            return document
        if self.vision is None:
            return None
        try:
            output = self.vision.resolve_document(document.document_id, document)
            if not isinstance(output, ResolvedPdfDocument):
                return None
            resolved = ResolvedPdfDocument.model_validate(output.model_dump(mode="python", warnings="error"))
            if (
                resolved.document_id != document.document_id
                or resolved.page_count != document.page_count
                or resolved.requires_review or resolved.unresolved_pages
                or len(resolved.pages) != document.page_count
                or {p.page for p in resolved.pages} != expected
            ):
                return None
            originals = {p.page: p.text for p in document.pages}
            for page in resolved.pages:
                if page.requires_review or page.verification_level == VerificationLevel.CONFLICT:
                    return None
                if page.source == TextResolutionSource.TEXT_LAYER:
                    if page.text != originals[page.page] or not self.quality.evaluate_native_text(page.text):
                        return None
                elif (
                    page.source == TextResolutionSource.UNRESOLVED
                    or page.verification_level not in {VerificationLevel.SINGLE_PROVIDER, VerificationLevel.CROSS_VERIFIED}
                    or not self.quality.evaluate_provider_result(page.text, page.confidence)
                ):
                    return None
            return resolved
        except Exception:
            return None

    def _assemble(self, document) -> InvoiceHeaderExtractionResult:
        header_context = document
        omitted = False
        if isinstance(document, ParsedWorkbook):
            header_context, omitted = self._visible_workbook(document)
        output = self.headers.extract(header_context)
        headers = deserialize_result(serialize_result(output))
        if not isinstance(headers, InvoiceHeaderExtractionResult):
            raise ValueError("Invalid header extraction contract")
        data = headers.model_dump(mode="python", warnings="error")
        issues = list(headers.issues)
        candidates = list(headers.candidates)
        statuses = [headers.status]
        if isinstance(document, ParsedWorkbook):
            item_output = self.items.extract(document)
            item_result = deserialize_result(serialize_result(item_output))
            if not isinstance(item_result, InvoiceItemExtractionResult):
                raise ValueError("Invalid item extraction contract")
            data["invoice"]["items"] = [item.model_dump(mode="python") for item in item_result.items]
            issues.extend(item_result.issues)
            candidates.extend(item_result.candidates)
            statuses.append(item_result.status)
            if omitted:
                issues.append(_issue("HIDDEN_INVOICE_CONTENT", "Hidden workbook content was excluded from header interpretation."))
        else:
            issues.append(_issue("PDF_ITEMS_UNSUPPORTED", "PDF item tables require independent extraction or human review."))
        if not data["invoice"]["items"] and isinstance(document, ParsedWorkbook):
            issues.append(_issue("INVOICE_ITEMS_UNRESOLVED", "No unambiguous invoice item list was established."))
        if not any(_value(headers.invoice, path) is not None for path in APPROVED_HEADER_PATHS):
            issues.append(_issue("INVOICE_HEADERS_UNRESOLVED", "No invoice header values were established."))
        status = (
            ExtractionStatus.FAILED if ExtractionStatus.FAILED in statuses
            else ExtractionStatus.NEEDS_REVIEW if ExtractionStatus.NEEDS_REVIEW in statuses or any(i.is_review_required for i in issues)
            else ExtractionStatus.EXTRACTED
        )
        data.update(status=status, issues=issues, candidates=candidates)
        return InvoiceHeaderExtractionResult.model_validate(data)

    def extract_document(
        self, document_id: str, *, expected_active_extraction_id: str | None = None,
        expected_source_file_hash: str | None = None,
        expected_processing_status: ProcessingStatus | None = None,
    ) -> InvoiceExtractionOutcome:
        try:
            request = InvoiceExtractionRequest(
                document_id=document_id, expected_active_extraction_id=expected_active_extraction_id,
                expected_source_file_hash=expected_source_file_hash,
                expected_processing_status=expected_processing_status,
            )
        except Exception:
            return InvoiceExtractionOutcome(document_id=None, result=_empty(ExtractionStatus.FAILED, "INVALID_EXTRACTION_REQUEST", "Extraction request is invalid."))

        def refuse(code: str, message: str, status=ExtractionStatus.NEEDS_REVIEW):
            return InvoiceExtractionOutcome(document_id=request.document_id, result=_empty(status, code, message))

        try:
            stored = self.repository.get_by_document_id(request.document_id)
            if stored is None:
                return refuse("SOURCE_DOCUMENT_NOT_FOUND", "SourceDocument was not found.", ExtractionStatus.FAILED)
            source = SourceDocument.model_validate(stored.model_dump(mode="python", warnings="error"))
            if source.document_id != request.document_id or source.file_type not in {"pdf", "xlsx", "xls"}:
                return refuse("UNSUPPORTED_INVOICE_SOURCE", "Source identity or document format is unsupported.")
            if not self._stored_classification_safe(source):
                return refuse("UNSAFE_INVOICE_CLASSIFICATION", "A safely classified Commercial Invoice is required.")
            if (
                request.expected_source_file_hash is not None and request.expected_source_file_hash != source.file_hash
                or request.expected_processing_status is not None and request.expected_processing_status != source.processing_status
            ):
                return refuse("STALE_EXTRACTION_SOURCE", "SourceDocument no longer matches the requested state.")
            active = self.extractions.get_active(source.document_id)
            if active is not None and request.expected_active_extraction_id is None:
                return refuse("ACTIVE_EXTRACTION_EXISTS", "Explicit replacement of the active extraction is required.")
            if request.expected_active_extraction_id is not None and (
                active is None or active.extraction_id != request.expected_active_extraction_id
            ):
                return refuse("STALE_ACTIVE_EXTRACTION", "The requested active extraction is stale or missing.")
            if self._fingerprint(source) != source.file_hash:
                return refuse("SOURCE_HASH_MISMATCH", "Source bytes do not match the stored fingerprint.")
        except Exception:
            return refuse("SOURCE_PREFLIGHT_FAILED", "Source preconditions could not be verified.", ExtractionStatus.FAILED)

        try:
            parsed = self.parsing.parse_document_readonly(source.document_id)
            model = ParsedPdfDocument if isinstance(parsed, ParsedPdfDocument) else ParsedWorkbook
            parsed = model.model_validate(parsed.model_dump(mode="python", warnings="error"))
            if parsed.document_id != source.document_id or parsed.file_type != source.file_type:
                raise ValueError("Invalid parser identity")
            document = self._safe_pdf(parsed) if isinstance(parsed, ParsedPdfDocument) else parsed
            if document is None:
                result = _empty(ExtractionStatus.NEEDS_REVIEW, "UNSAFE_VISUAL_DOCUMENT", "PDF visual content is unresolved and requires human review.")
            else:
                classified_output = self.classifier.classify(self._classification_context(document))
                classification = DocumentClassificationResult.model_validate(classified_output.model_dump(mode="python", warnings="error"))
                if (
                    classification.document_id != source.document_id
                    or classification.document_type != DocumentType.COMMERCIAL_INVOICE
                    or classification.confidence < self.classification_threshold
                    or not any(e.target_document_type == DocumentType.COMMERCIAL_INVOICE for e in classification.evidence)
                ):
                    return refuse("CLASSIFICATION_EVIDENCE_MISMATCH", "Current source content does not safely establish a Commercial Invoice.")
                result = self._assemble(document)
                if self.semantic is not None and result.status != ExtractionStatus.FAILED and any(
                    _value(result.invoice, path) is None for path in APPROVED_HEADER_PATHS
                ):
                    result = merge_semantic(document, result, self.semantic)
        except Exception:
            result = _empty(ExtractionStatus.FAILED, "INVOICE_EXTRACTION_FAILED", "Invoice parsing or deterministic extraction failed.")

        try:
            if not self._source_unchanged(source):
                return refuse("SOURCE_CHANGED_DURING_EXTRACTION", "SourceDocument changed during extraction; no result was saved.")
            validated = deserialize_result(serialize_result(result))
            if not isinstance(validated, InvoiceHeaderExtractionResult):
                raise ValueError("Invalid assembled result")
            values = dict(
                document_id=source.document_id, source_file_hash=source.file_hash,
                expected_processing_status=source.processing_status, result=validated,
                expected_source_document=source,
                extraction_method="invoice_extraction_service",
            )
            if request.expected_active_extraction_id is None:
                record = self.extractions.save_attempt(ExtractionAttempt(**values))
            else:
                record = self.extractions.replace_active(ExtractionReplacement(
                    **values, expected_active_extraction_id=request.expected_active_extraction_id,
                ))
            return InvoiceExtractionOutcome(document_id=source.document_id, result=validated, record=record)
        except ExtractionConflictError:
            # 006D uses this safe exception for both optimistic conflicts and
            # SQLite integrity/trigger failures. No commit means application
            # persistence failed; do not disguise a technical DB failure as
            # successfully extracted data needing business review.
            return refuse("EXTRACTION_PERSISTENCE_CONFLICT", "Extraction state or constraints prevented persistence.", ExtractionStatus.FAILED)
        except Exception:
            return refuse("EXTRACTION_PERSISTENCE_FAILED", "Extraction could not be persisted.", ExtractionStatus.FAILED)
