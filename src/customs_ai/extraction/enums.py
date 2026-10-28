from enum import Enum


class ExtractionStatus(str, Enum):
    """Lifecycle status of document extraction."""

    EXTRACTED = "EXTRACTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"
