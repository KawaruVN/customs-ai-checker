class VisionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class OcrEngineUnavailableError(VisionError):
    def __init__(self):
        super().__init__("OCR_ENGINE_UNAVAILABLE", "Local OCR engine is unavailable.")


class OcrFailedError(VisionError):
    def __init__(self):
        super().__init__("OCR_FAILED", "Local OCR processing failed.")


class DocumentVisionUnavailableError(VisionError):
    def __init__(self):
        super().__init__("DOCUMENT_VISION_UNAVAILABLE", "Local document-vision service is unavailable.")


class DocumentVisionFailedError(VisionError):
    def __init__(self):
        super().__init__("DOCUMENT_VISION_FAILED", "Local document-vision processing failed.")


class PdfRenderFailedError(VisionError):
    def __init__(self):
        super().__init__("PDF_RENDER_FAILED", "Failed to render PDF page.")


class PdfRenderLimitExceededError(VisionError):
    def __init__(self):
        super().__init__("PDF_RENDER_LIMIT_EXCEEDED", "PDF render exceeds configured safety limit.")


class VisualPageLimitExceededError(VisionError):
    def __init__(self):
        super().__init__("VISUAL_PAGE_LIMIT_EXCEEDED", "Document exceeds configured visual-page limit.")


class VisualResultConflictError(VisionError):
    def __init__(self):
        super().__init__("VISUAL_RESULT_CONFLICT", "Local visual providers materially disagree.")
