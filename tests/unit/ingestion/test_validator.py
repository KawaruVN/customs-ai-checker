from pathlib import Path
import zipfile

import pytest

from customs_ai.ingestion.errors import (
    FileInvalidContentError,
    FileMimeMismatchError,
    FileUnsupportedError,
)
from customs_ai.ingestion.validator import (
    normalize_extension,
    validate_client_mime,
    validate_content_signature,
)


def write_bytes(tmp_path: Path, content: bytes, name: str = "sample.bin") -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def make_ooxml(tmp_path: Path, entries: list[str], name: str = "sample.zip") -> Path:
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as archive:
        for entry in entries:
            archive.writestr(entry, "synthetic")
    return path


def test_extension_normalization_and_unsupported():
    assert normalize_extension("invoice.PDF") == ".pdf"
    assert normalize_extension("archive.v2.XLSX") == ".xlsx"
    with pytest.raises(FileUnsupportedError):
        normalize_extension("payload.exe")


def test_client_mime_validation():
    validate_client_mime("application/pdf", ".pdf")
    validate_client_mime("application/octet-stream", ".pdf")
    validate_client_mime("text/csv; charset=utf-8", ".csv")
    validate_client_mime("application/x-csv", ".csv")
    validate_client_mime("image/pjpeg", ".jpg")
    with pytest.raises(FileMimeMismatchError):
        validate_client_mime("text/plain", ".pdf")


@pytest.mark.parametrize(
    ("ext", "valid", "invalid"),
    [
        (".pdf", b"%PDF-1.7\nsynthetic", b"not-pdf"),
        (".png", b"\x89PNG\r\n\x1a\nsynthetic", b"not-png"),
        (".jpg", b"\xff\xd8\xff\xe0synthetic", b"not-jpeg"),
        (".jpeg", b"\xff\xd8\xff\xe1synthetic", b"not-jpeg"),
        (".xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1synthetic", b"not-ole"),
    ],
)
def test_signature_valid_and_invalid(tmp_path, ext, valid, invalid):
    validate_content_signature(write_bytes(tmp_path, valid), ext)
    with pytest.raises(FileInvalidContentError):
        validate_content_signature(write_bytes(tmp_path, invalid), ext)


def test_ooxml_xlsx_and_docx_valid(tmp_path):
    xlsx = make_ooxml(tmp_path, ["[Content_Types].xml", "xl/workbook.xml"], "a.xlsx")
    docx = make_ooxml(tmp_path, ["[Content_Types].xml", "word/document.xml"], "a.docx")
    validate_content_signature(xlsx, ".xlsx")
    validate_content_signature(docx, ".docx")


def test_ooxml_cross_rename_rejected(tmp_path):
    xlsx = make_ooxml(tmp_path, ["xl/workbook.xml"], "a.xlsx")
    docx = make_ooxml(tmp_path, ["word/document.xml"], "a.docx")
    with pytest.raises(FileInvalidContentError):
        validate_content_signature(xlsx, ".docx")
    with pytest.raises(FileInvalidContentError):
        validate_content_signature(docx, ".xlsx")


def test_ooxml_ambiguous_rejected(tmp_path):
    ambiguous = make_ooxml(
        tmp_path,
        ["xl/workbook.xml", "word/document.xml"],
        "ambiguous.zip",
    )
    with pytest.raises(FileInvalidContentError):
        validate_content_signature(ambiguous, ".xlsx")
    with pytest.raises(FileInvalidContentError):
        validate_content_signature(ambiguous, ".docx")


def test_csv_text_valid_and_binary_rejected(tmp_path):
    validate_content_signature(
        write_bytes(tmp_path, "mã hàng,số lượng\nA01,10\n".encode("utf-8")),
        ".csv",
    )

    with pytest.raises(FileInvalidContentError):
        validate_content_signature(write_bytes(tmp_path, b"a,b\x00binary"), ".csv")

    # Binary without NUL bytes.
    with pytest.raises(FileInvalidContentError):
        validate_content_signature(write_bytes(tmp_path, b"X" * 20 + b"\x01\x02\x03\x04"), ".csv")


def test_csv_rejects_known_other_document_signature(tmp_path):
    with pytest.raises(FileInvalidContentError):
        validate_content_signature(write_bytes(tmp_path, b"%PDF-1.7\nsynthetic"), ".csv")
