class ClassificationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ClassificationFailedError(ClassificationError):
    def __init__(self, message: str = "Document classification failed."):
        super().__init__("CLASSIFICATION_FAILED", message)
