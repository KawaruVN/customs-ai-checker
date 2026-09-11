class ParserError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class SourceDocumentNotFoundError(ParserError):
    def __init__(self):
        super().__init__("SOURCE_DOCUMENT_NOT_FOUND", "Source document was not found.")


class SourceFileNotFoundError(ParserError):
    def __init__(self):
        super().__init__("SOURCE_FILE_NOT_FOUND", "Stored source file was not found.")


class SourceFilePathInvalidError(ParserError):
    def __init__(self):
        super().__init__("SOURCE_FILE_PATH_INVALID", "Stored source file path is outside the configured upload root.")


class ParserUnsupportedError(ParserError):
    def __init__(self, file_type: str):
        super().__init__("PARSER_UNSUPPORTED", f"No local parser is available for file type '{file_type}'.")


class PdfEncryptedError(ParserError):
    def __init__(self):
        super().__init__("PDF_ENCRYPTED", "PDF requires a password and cannot be parsed locally.")


class FileCorruptedError(ParserError):
    def __init__(self, file_type: str):
        super().__init__("FILE_CORRUPTED", f"Stored {file_type.upper()} file is malformed or unreadable.")


class ParserFailedError(ParserError):
    def __init__(self):
        super().__init__("PARSER_FAILED", "Local document parsing failed.")
