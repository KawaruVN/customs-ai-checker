import hashlib
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
import uuid

from fastapi import UploadFile

from customs_ai.config import settings
from customs_ai.ingestion.enums import ProcessingStatus
from customs_ai.ingestion.errors import (
    FileEmptyError,
    FileTooLargeError,
    InternalIngestionError,
    InvalidShipmentIdError,
)
from customs_ai.ingestion.models import SourceDocument, UploadResponse
from customs_ai.ingestion.validator import (
    SUPPORTED_EXTENSIONS,
    normalize_extension,
    validate_client_mime,
    validate_content_signature,
)
from customs_ai.logger import logger
from customs_ai.repositories.source_documents import SourceDocumentRepository

SHIPMENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
CHUNK_SIZE = 64 * 1024


class IngestionService:
    def __init__(self, repository: SourceDocumentRepository):
        self.repo = repository

    def _sanitize_filename(self, raw_filename: str | None) -> str:
        if not raw_filename:
            return ""
        basename = raw_filename.replace("\\", "/").split("/")[-1]
        cleaned = "".join(char for char in basename if ord(char) >= 32 and char != "\x7f")
        return cleaned.strip()

    def _validate_shipment_id(self, shipment_id: str) -> None:
        if not SHIPMENT_ID_PATTERN.fullmatch(shipment_id):
            raise InvalidShipmentIdError()

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False

    @staticmethod
    def _cleanup_final(final_path: Path | None, document_dir: Path | None) -> None:
        if final_path is not None:
            try:
                final_path.unlink(missing_ok=True)
            except OSError:
                pass
        if document_dir is not None:
            try:
                document_dir.rmdir()
            except OSError:
                pass

    async def ingest(self, shipment_id: str, upload: UploadFile) -> tuple[UploadResponse, int]:
        self._validate_shipment_id(shipment_id)

        original_filename = self._sanitize_filename(upload.filename)
        ext = normalize_extension(original_filename)
        canonical_mime = SUPPORTED_EXTENSIONS[ext]
        validate_client_mime(upload.content_type, ext)

        limit_bytes = settings.max_upload_size_mb * 1024 * 1024
        upload_root = settings.upload_root.resolve()

        try:
            upload_root.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(dir=upload_root, prefix="ingest_")
        except Exception as exc:
            logger.error("Could not initialize ingestion temporary storage.", exc_info=True)
            raise InternalIngestionError() from exc

        temp_path = Path(temp_name)
        final_path: Path | None = None
        document_dir: Path | None = None
        hasher = hashlib.sha256()
        file_size = 0

        try:
            with os.fdopen(fd, "wb") as temp_file:
                while True:
                    chunk = await upload.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    file_size += len(chunk)
                    if file_size > limit_bytes:
                        raise FileTooLargeError(settings.max_upload_size_mb)
                    hasher.update(chunk)
                    temp_file.write(chunk)

            if file_size == 0:
                raise FileEmptyError()

            file_hash = hasher.hexdigest()

            # Validate the current request before duplicate short-circuiting.
            validate_content_signature(temp_path, ext)

            existing = self.repo.find_by_shipment_and_hash(shipment_id, file_hash)
            if existing is not None:
                return self._build_duplicate_response(existing), 200

            document_id = f"DOC-{uuid.uuid4().hex}"
            document_dir = upload_root / shipment_id / document_id
            final_path = document_dir / f"original{ext}"

            if not self._is_within(final_path, upload_root):
                raise InternalIngestionError(
                    code="PATH_ESCAPE",
                    message="Resolved storage path is outside the configured upload root.",
                )

            try:
                document_dir.mkdir(parents=True, exist_ok=False)
                os.replace(temp_path, final_path)
            except Exception as exc:
                self._cleanup_final(final_path, document_dir)
                logger.error("Could not finalize uploaded file storage.", exc_info=True)
                raise InternalIngestionError() from exc

            document = SourceDocument(
                document_id=document_id,
                shipment_id=shipment_id,
                original_filename=original_filename,
                file_type=ext.lstrip("."),
                mime_type=canonical_mime,
                file_hash=file_hash,
                file_size=file_size,
                stored_path=str(final_path.resolve()),
                upload_time=datetime.now(timezone.utc),
                processing_status=ProcessingStatus.UPLOADED,
            )

            try:
                self.repo.create(document)
            except sqlite3.IntegrityError:
                self._cleanup_final(final_path, document_dir)
                winner = self.repo.find_by_shipment_and_hash(shipment_id, file_hash)
                if winner is None:
                    raise InternalIngestionError(
                        code="INGESTION_FAILED",
                        message="Duplicate constraint was raised but no existing document could be resolved.",
                    )
                return self._build_duplicate_response(winner), 200
            except Exception as exc:
                self._cleanup_final(final_path, document_dir)
                logger.error("Could not persist SourceDocument metadata.", exc_info=True)
                raise InternalIngestionError() from exc

            return (
                UploadResponse(
                    document_id=document.document_id,
                    shipment_id=document.shipment_id,
                    status=document.processing_status,
                    sha256=document.file_hash,
                    mime_type=document.mime_type,
                    file_size=document.file_size,
                    is_duplicate=False,
                ),
                201,
            )
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _build_duplicate_response(existing: SourceDocument) -> UploadResponse:
        return UploadResponse(
            document_id=existing.document_id,
            shipment_id=existing.shipment_id,
            status=existing.processing_status,
            sha256=existing.file_hash,
            mime_type=existing.mime_type,
            file_size=existing.file_size,
            is_duplicate=True,
        )
