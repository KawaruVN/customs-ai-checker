from contextlib import closing
import sqlite3

from customs_ai.config import settings


def get_connection() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(settings.db_path))
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise sqlite3.OperationalError("SQLite foreign-key enforcement unavailable.")
    except BaseException:
        connection.close()
        raise
    return connection


def init_db() -> None:
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS document_extractions (
                extraction_id TEXT PRIMARY KEY NOT NULL,
                document_id TEXT NOT NULL
                    REFERENCES source_documents(document_id) ON DELETE RESTRICT,
                attempt_number INTEGER NOT NULL CHECK(attempt_number > 0),
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK(status IN ('EXTRACTED', 'NEEDS_REVIEW', 'FAILED')),
                is_active INTEGER NOT NULL CHECK(is_active IN (0, 1)),
                created_at TEXT NOT NULL,
                schema_version TEXT NOT NULL CHECK(schema_version = '0.1'),
                extraction_method TEXT,
                source_file_hash TEXT NOT NULL,
                supersedes_extraction_id TEXT
                    REFERENCES document_extractions(extraction_id) ON DELETE RESTRICT,
                UNIQUE(document_id, attempt_number),
                CHECK(status != 'FAILED' OR is_active = 0)
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_extraction_per_document
            ON document_extractions(document_id) WHERE is_active = 1
            """
        )
