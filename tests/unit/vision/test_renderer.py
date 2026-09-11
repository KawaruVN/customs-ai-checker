import hashlib

import pytest
from pypdf import PdfWriter

from customs_ai.config import VisionSettingsConfig
from customs_ai.vision.errors import PdfRenderFailedError, PdfRenderLimitExceededError
from customs_ai.vision.renderer import PdfRenderer


def _pdf(path, width=200, height=200):
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=height)
    with path.open("wb") as handle:
        writer.write(handle)


def test_renderer_respects_pixel_limit_and_uses_dedicated_error(tmp_path):
    path = tmp_path / "large.pdf"
    _pdf(path, width=2000, height=2000)
    renderer = PdfRenderer(VisionSettingsConfig(render_dpi=600, max_render_pixels=1_000_000))
    with pytest.raises(PdfRenderLimitExceededError) as exc:
        renderer.render_page(path, 0)
    assert exc.value.code == "PDF_RENDER_LIMIT_EXCEEDED"


def test_renderer_does_not_modify_source(tmp_path):
    path = tmp_path / "page.pdf"
    _pdf(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    image = PdfRenderer(VisionSettingsConfig(render_dpi=100)).render_page(path, 0)
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert image.size[0] > 0 and image.size[1] > 0
    assert before == after


def test_renderer_maps_missing_file_to_safe_error(tmp_path):
    renderer = PdfRenderer(VisionSettingsConfig())
    with pytest.raises(PdfRenderFailedError) as exc:
        renderer.render_page(tmp_path / "missing.pdf", 0)
    assert exc.value.code == "PDF_RENDER_FAILED"
