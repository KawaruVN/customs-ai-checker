from customs_ai.application.paths import resolve_source_path
from customs_ai.config import VisionSettingsConfig, settings
from customs_ai.logger import logger
from customs_ai.parsers.models import ParsedDocument, ParsedPdfDocument
from customs_ai.repositories.source_documents import SourceDocumentRepository
from customs_ai.vision.enums import TextResolutionSource, VerificationLevel
from customs_ai.vision.errors import (
    DocumentVisionUnavailableError,
    OcrEngineUnavailableError,
    PdfRenderFailedError,
    VisualPageLimitExceededError,
    VisionError,
)
from customs_ai.vision.evaluator import TextQualityEvaluator
from customs_ai.vision.models import ProviderTextResult, ResolvedPdfDocument, ResolvedPdfPage
from customs_ai.vision.providers.base import LocalDocumentVisionProvider, LocalOcrProvider
from customs_ai.vision.reconciler import HighSignalReconciler
from customs_ai.vision.renderer import PdfRenderer


class VisualResolutionService:
    def __init__(
        self,
        repository: SourceDocumentRepository,
        vlm_provider: LocalDocumentVisionProvider,
        ocr_provider: LocalOcrProvider,
        config: VisionSettingsConfig | None = None,
        evaluator: TextQualityEvaluator | None = None,
        renderer: PdfRenderer | None = None,
        reconciler: HighSignalReconciler | None = None,
    ) -> None:
        self.repository = repository
        self.config = config or settings.vision
        self.vlm = vlm_provider
        self.ocr = ocr_provider
        self.evaluator = evaluator or TextQualityEvaluator(self.config)
        self.renderer = renderer or PdfRenderer(self.config)
        self.reconciler = reconciler or HighSignalReconciler(self.config)

    @staticmethod
    def _empty_provider(provider: str) -> ProviderTextResult:
        return ProviderTextResult(provider=provider, text="", confidence=None)

    def _run_vlm(self, image, document_id: str, page: int) -> ProviderTextResult:
        try:
            return self.vlm.process(image)
        except DocumentVisionUnavailableError:
            logger.warning(
                "Visual provider unavailable: document_id=%s page=%s provider=PaddleOCR-VL error_code=DOCUMENT_VISION_UNAVAILABLE",
                document_id,
                page,
            )
        except VisionError as exc:
            logger.warning(
                "Visual provider failed: document_id=%s page=%s provider=PaddleOCR-VL error_code=%s",
                document_id,
                page,
                exc.code,
            )
        except Exception:
            logger.warning(
                "Visual provider failed: document_id=%s page=%s provider=PaddleOCR-VL error_code=DOCUMENT_VISION_FAILED",
                document_id,
                page,
            )
        return self._empty_provider("PaddleOCR-VL-1.6")

    def _run_ocr(self, image, document_id: str, page: int) -> ProviderTextResult:
        try:
            return self.ocr.process(image)
        except OcrEngineUnavailableError:
            logger.warning(
                "OCR provider unavailable: document_id=%s page=%s provider=RapidOCR error_code=OCR_ENGINE_UNAVAILABLE",
                document_id,
                page,
            )
        except VisionError as exc:
            logger.warning(
                "OCR provider failed: document_id=%s page=%s provider=RapidOCR error_code=%s",
                document_id,
                page,
                exc.code,
            )
        except Exception:
            logger.warning(
                "OCR provider failed: document_id=%s page=%s provider=RapidOCR error_code=OCR_FAILED",
                document_id,
                page,
            )
        return self._empty_provider("RapidOCR")

    def resolve_document(
        self, document_id: str, parsed_doc: ParsedDocument
    ) -> ParsedDocument | ResolvedPdfDocument:
        if not isinstance(parsed_doc, ParsedPdfDocument):
            return parsed_doc

        source_document = self.repository.get_by_document_id(document_id)
        if source_document is None:
            return parsed_doc
        pdf_path = resolve_source_path(source_document.stored_path)

        resolved_pages: list[ResolvedPdfPage] = []
        visual_pages: list[int] = []
        unresolved_pages: list[int] = []

        for parsed_page in parsed_doc.pages:
            if self.evaluator.evaluate_native_text(parsed_page.text):
                resolved_pages.append(
                    ResolvedPdfPage(
                        page=parsed_page.page,
                        text=parsed_page.text,
                        source=TextResolutionSource.TEXT_LAYER,
                        confidence=None,
                        verification_level=VerificationLevel.UNVERIFIED,
                        requires_review=False,
                    )
                )
                continue

            visual_pages.append(parsed_page.page)
            if len(visual_pages) > self.config.max_visual_pages:
                raise VisualPageLimitExceededError()

            try:
                image = self.renderer.render_page(pdf_path, parsed_page.page - 1)
            except PdfRenderFailedError as exc:
                logger.warning(
                    "PDF render failed: document_id=%s page=%s error_code=%s",
                    document_id,
                    parsed_page.page,
                    exc.code,
                )
                resolved_pages.append(
                    ResolvedPdfPage(
                        page=parsed_page.page,
                        text="",
                        source=TextResolutionSource.UNRESOLVED,
                        verification_level=VerificationLevel.UNVERIFIED,
                        requires_review=True,
                    )
                )
                unresolved_pages.append(parsed_page.page)
                continue

            vlm_result = self._run_vlm(image, document_id, parsed_page.page)
            vlm_usable = self.evaluator.evaluate_provider_result(
                vlm_result.text, vlm_result.confidence
            )

            if self.config.accuracy_mode:
                ocr_result = self._run_ocr(image, document_id, parsed_page.page)
                ocr_usable = self.evaluator.evaluate_provider_result(
                    ocr_result.text, ocr_result.confidence
                )
            else:
                ocr_result = self._empty_provider("RapidOCR")
                ocr_usable = False

            resolved_page = self.reconciler.reconcile(
                parsed_page.page,
                vlm_result,
                vlm_usable,
                ocr_result,
                ocr_usable,
            )
            resolved_pages.append(resolved_page)
            if resolved_page.requires_review:
                unresolved_pages.append(parsed_page.page)

        return ResolvedPdfDocument(
            document_id=document_id,
            page_count=parsed_doc.page_count,
            pages=resolved_pages,
            visual_pages=visual_pages,
            unresolved_pages=unresolved_pages,
            requires_review=bool(unresolved_pages),
            vision_fallback_recommended=bool(unresolved_pages),
        )
