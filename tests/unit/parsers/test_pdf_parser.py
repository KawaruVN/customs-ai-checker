import hashlib
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from customs_ai.parsers.errors import FileCorruptedError, PdfEncryptedError
from customs_ai.parsers.pdf import PdfParser


def _write_text_pdf(path: Path, page_texts: list[str | None]) -> None:
    writer = PdfWriter()
    for text in page_texts:
        page = writer.add_blank_page(width=612, height=792)
        if text is None:
            continue
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_ref = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        stream = DecodedStreamObject()
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as handle:
        writer.write(handle)


def test_pdf_text_and_page_boundaries(tmp_path):
    path = tmp_path / "two-pages.pdf"
    _write_text_pdf(path, ["Page One", "Page Two"])

    parsed = PdfParser().parse("DOC-PDF", path)

    assert parsed.page_count == 2
    assert [page.page for page in parsed.pages] == [1, 2]
    assert "Page One" in parsed.pages[0].text
    assert "Page Two" in parsed.pages[1].text
    assert parsed.has_text_layer is True
    assert parsed.needs_ocr is False


def test_blank_pdf_is_flagged_for_later_ocr(tmp_path):
    path = tmp_path / "blank.pdf"
    _write_text_pdf(path, [None, None])

    parsed = PdfParser().parse("DOC-BLANK", path)

    assert parsed.page_count == 2
    assert all(page.text == "" for page in parsed.pages)
    assert parsed.has_text_layer is False
    assert parsed.needs_ocr is True


def test_encrypted_pdf_without_empty_password_is_rejected(tmp_path):
    path = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret-password")
    with path.open("wb") as handle:
        writer.write(handle)

    with pytest.raises(PdfEncryptedError) as exc:
        PdfParser().parse("DOC-ENC", path)
    assert exc.value.code == "PDF_ENCRYPTED"


def test_corrupt_pdf_is_deterministic(tmp_path):
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.7\nthis is not a valid pdf body")

    with pytest.raises(FileCorruptedError) as exc:
        PdfParser().parse("DOC-BAD", path)
    assert exc.value.code == "FILE_CORRUPTED"


def test_pdf_source_file_remains_unchanged(tmp_path):
    path = tmp_path / "immutable.pdf"
    _write_text_pdf(path, ["Immutable"])
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    PdfParser().parse("DOC-HASH", path)

    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert after == before
