from pathlib import Path
import zipfile

from customs_ai.ingestion.errors import (
    FileInvalidContentError,
    FileMimeMismatchError,
    FileUnsupportedError,
)

SUPPORTED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

VALID_MIME_ALIASES = {
    ".csv": {
        "text/csv",
        "application/csv",
        "application/x-csv",
        "text/comma-separated-values",
        "application/vnd.ms-excel",
    },
    ".jpg": {"image/jpeg", "image/jpg", "image/pjpeg"},
    ".jpeg": {"image/jpeg", "image/jpg", "image/pjpeg"},
}

GENERIC_MIME_TYPES = {"application/octet-stream"}


def normalize_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise FileUnsupportedError(ext)
    return ext


def validate_client_mime(client_mime: str | None, ext: str) -> None:
    if not client_mime:
        return

    normalized = client_mime.split(";", 1)[0].strip().lower()
    if not normalized or normalized in GENERIC_MIME_TYPES:
        return

    expected = SUPPORTED_EXTENSIONS[ext]
    allowed = VALID_MIME_ALIASES.get(ext, {expected})
    if normalized not in allowed:
        raise FileMimeMismatchError(normalized, expected)


def _read_prefix(file_path: Path, size: int = 4096) -> bytes:
    with file_path.open("rb") as file:
        return file.read(size)


def _reject_known_non_csv_signature(sample: bytes) -> None:
    known_signatures = (
        b"%PDF-",
        b"\x89PNG\r\n\x1a\n",
        b"\xff\xd8\xff",
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
        b"PK\x03\x04",
    )
    if sample.startswith(known_signatures):
        raise FileInvalidContentError(
            "CSV payload matches a known non-CSV document/binary signature."
        )


def validate_content_signature(file_path: Path, ext: str) -> None:
    sample = _read_prefix(file_path)
    if not sample:
        raise FileInvalidContentError("Uploaded file has no content.")

    if ext == ".pdf":
        if not sample.startswith(b"%PDF-"):
            raise FileInvalidContentError("PDF signature is invalid.")
        return

    if ext == ".png":
        if not sample.startswith(b"\x89PNG\r\n\x1a\n"):
            raise FileInvalidContentError("PNG signature is invalid.")
        return

    if ext in {".jpg", ".jpeg"}:
        if not sample.startswith(b"\xff\xd8\xff"):
            raise FileInvalidContentError("JPEG signature is invalid.")
        return

    if ext == ".xls":
        if not sample.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            raise FileInvalidContentError("XLS/OLE signature is invalid.")
        return

    if ext in {".xlsx", ".docx"}:
        if not sample.startswith(b"PK\x03\x04"):
            raise FileInvalidContentError(f"{ext} is not a ZIP/OOXML container.")
        try:
            with zipfile.ZipFile(file_path, "r") as archive:
                names = archive.namelist()
        except (zipfile.BadZipFile, OSError) as exc:
            raise FileInvalidContentError(
                f"{ext} is not a valid OOXML ZIP container."
            ) from exc

        has_xl = any(name.startswith("xl/") for name in names)
        has_word = any(name.startswith("word/") for name in names)
        if has_xl and has_word:
            raise FileInvalidContentError(
                "Ambiguous OOXML container contains both spreadsheet and Word content."
            )
        if ext == ".xlsx" and not has_xl:
            raise FileInvalidContentError("XLSX spreadsheet content is missing.")
        if ext == ".docx" and not has_word:
            raise FileInvalidContentError("DOCX Word content is missing.")
        return

    if ext == ".csv":
        _reject_known_non_csv_signature(sample)
        if b"\x00" in sample:
            raise FileInvalidContentError("CSV contains NUL bytes indicating binary data.")

        control_count = sum(
            1 for byte in sample if byte < 32 and byte not in (9, 10, 13)
        )
        if control_count / len(sample) > 0.05:
            raise FileInvalidContentError(
                "CSV contains too many binary control characters."
            )
        return

    raise FileUnsupportedError(ext)
