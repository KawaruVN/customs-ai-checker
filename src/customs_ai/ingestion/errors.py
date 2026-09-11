class IngestionError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class InvalidShipmentIdError(IngestionError):
    def __init__(self):
        super().__init__(
            "INVALID_SHIPMENT_ID",
            "Shipment ID contains invalid characters or path traversal.",
        )


class FileEmptyError(IngestionError):
    def __init__(self):
        super().__init__("FILE_EMPTY", "Uploaded file is empty.")


class FileTooLargeError(IngestionError):
    def __init__(self, limit_mb: int):
        super().__init__(
            "FILE_TOO_LARGE",
            f"File size exceeds the {limit_mb} MiB limit.",
        )


class FileUnsupportedError(IngestionError):
    def __init__(self, ext: str):
        display = ext or "<missing>"
        super().__init__("FILE_UNSUPPORTED", f"Extension '{display}' is not supported.")


class FileMimeMismatchError(IngestionError):
    def __init__(self, client_mime: str, expected: str):
        super().__init__(
            "FILE_MIME_MISMATCH",
            f"Client-declared MIME '{client_mime}' does not match '{expected}'.",
        )


class FileInvalidContentError(IngestionError):
    def __init__(self, message: str):
        super().__init__("FILE_INVALID_CONTENT", message)


class InternalIngestionError(IngestionError):
    def __init__(self, code: str = "INGESTION_FAILED", message: str = "Failed to persist document."):
        super().__init__(code, message, http_status=500)
