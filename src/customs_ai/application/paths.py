from pathlib import Path

from customs_ai.config import settings
from customs_ai.parsers.errors import SourceFileNotFoundError, SourceFilePathInvalidError


def resolve_source_path(stored_path: str) -> Path:
    """Resolve a persisted source path and enforce upload-root containment."""
    root = settings.upload_root.resolve()
    candidate = Path(stored_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SourceFilePathInvalidError() from exc
    if not resolved.is_file():
        raise SourceFileNotFoundError()
    return resolved
