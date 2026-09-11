from pathlib import Path

from PIL import Image

from customs_ai.config import VisionSettingsConfig, settings
from customs_ai.vision.errors import PdfRenderFailedError, PdfRenderLimitExceededError


class PdfRenderer:
    def __init__(self, config: VisionSettingsConfig | None = None) -> None:
        self.config = config or settings.vision
        self.scale = self.config.render_dpi / 72.0

    def render_page(self, pdf_path: Path, page_index_zero_based: int) -> Image.Image:
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:  # pragma: no cover - installation guard
            raise PdfRenderFailedError() from exc

        pdf = None
        page = None
        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
            page = pdf[page_index_zero_based]
            width, height = page.get_size()
            scaled_w = max(1, int(width * self.scale))
            scaled_h = max(1, int(height * self.scale))
            if scaled_w * scaled_h > self.config.max_render_pixels:
                raise PdfRenderLimitExceededError()
            return page.render(scale=self.scale).to_pil().convert("RGB")
        except PdfRenderLimitExceededError:
            raise
        except Exception as exc:
            raise PdfRenderFailedError() from exc
        finally:
            if page is not None and hasattr(page, "close"):
                page.close()
            if pdf is not None:
                pdf.close()
