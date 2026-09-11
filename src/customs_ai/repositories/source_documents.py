from typing import Optional

from customs_ai.ingestion.models import SourceDocument
from customs_ai.repositories.database import get_connection


class SourceDocumentRepository:
    def create(self, document: SourceDocument) -> None:
        query = """
            INSERT INTO source_documents (
                document_id,
                shipment_id,
                original_filename,
                file_type,
                mime_type,
                file_hash,
                file_size,
                stored_path,
                upload_time,
                processing_status,
                detected_document_type,
                classification_confidence,
                page_count,
                sheet_count,
                parser_used,
                extraction_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            document.document_id,
            document.shipment_id,
            document.original_filename,
            document.file_type,
            document.mime_type,
            document.file_hash,
            document.file_size,
            document.stored_path,
            document.upload_time.isoformat(),
            document.processing_status.value,
            document.detected_document_type,
            document.classification_confidence,
            document.page_count,
            document.sheet_count,
            document.parser_used,
            document.extraction_status,
        )
        with get_connection() as connection:
            connection.execute(query, values)
            connection.commit()

    def find_by_shipment_and_hash(
        self, shipment_id: str, file_hash: str
    ) -> Optional[SourceDocument]:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM source_documents WHERE shipment_id = ? AND file_hash = ?",
                (shipment_id, file_hash),
            ).fetchone()
        return SourceDocument(**dict(row)) if row else None

    def get_by_document_id(self, document_id: str) -> Optional[SourceDocument]:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM source_documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        return SourceDocument(**dict(row)) if row else None

    def update_parsing_metadata(
        self,
        document_id: str,
        processing_status,
        parser_used: str,
        page_count: int | None,
        sheet_count: int | None,
    ) -> None:
        query = """
            UPDATE source_documents
            SET processing_status = ?, parser_used = ?, page_count = ?, sheet_count = ?
            WHERE document_id = ?
        """
        status_value = getattr(processing_status, "value", processing_status)
        with get_connection() as connection:
            cursor = connection.execute(
                query,
                (status_value, parser_used, page_count, sheet_count, document_id),
            )
            if cursor.rowcount != 1:
                raise LookupError("SourceDocument not found during parser metadata update.")
            connection.commit()

    def update_classification_metadata(
        self,
        document_id: str,
        detected_document_type: str,
        classification_confidence: float,
        processing_status,
    ) -> None:
        query = """
            UPDATE source_documents
            SET detected_document_type = ?, classification_confidence = ?, processing_status = ?
            WHERE document_id = ?
        """
        status_value = getattr(processing_status, "value", processing_status)
        with get_connection() as connection:
            cursor = connection.execute(
                query,
                (detected_document_type, classification_confidence, status_value, document_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(
                    "SourceDocument not found during classification metadata update."
                )
            connection.commit()
