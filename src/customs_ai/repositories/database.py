import sqlite3

from customs_ai.config import settings


def get_connection() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(settings.db_path))
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_documents (
                document_id TEXT PRIMARY KEY,
                shipment_id TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                stored_path TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                processing_status TEXT NOT NULL,
                detected_document_type TEXT,
                classification_confidence REAL,
                page_count INTEGER,
                sheet_count INTEGER,
                parser_used TEXT,
                extraction_status TEXT,
                UNIQUE(shipment_id, file_hash)
            )
            """
        )
        connection.commit()
