from enum import Enum


class ValueOrigin(str, Enum):
    EXTRACTED = "EXTRACTED"
    INFERRED = "INFERRED"
    MANUAL = "MANUAL"
