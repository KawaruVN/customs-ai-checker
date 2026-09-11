import re
import unicodedata


def normalize_text(text: str) -> str:
    """Safely normalizes Unicode, casefolds, and squashes whitespace."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def build_clue_regex(clue: str) -> re.Pattern:
    """
    Builds a deterministic regex for a clue.
    Safely wraps short English acronyms in boundaries while avoiding
    boundary logic on CJK characters (which lack spaces).
    """
    norm_clue = normalize_text(clue)
    if not norm_clue:
        return re.compile(r"(?!)")  # Matches nothing

    # Handle requested punctuation variants dynamically
    if norm_clue in ("b/l", "b.l.", "b.l"):
        return re.compile(r"\bb[./]l\.?\b")

    escaped = re.escape(norm_clue)
    pattern = escaped

    # Apply word boundaries ONLY if the clue begins/ends with an ASCII alphanumeric.
    # This securely isolates 'AWB' from 'DRAWBACK' without breaking '商业发票' inside dense Chinese text.
    starts_with_ascii_alnum = bool(re.match(r"^[a-z0-9]", norm_clue))
    ends_with_ascii_alnum = bool(re.search(r"[a-z0-9]$", norm_clue))

    if starts_with_ascii_alnum:
        pattern = r"\b" + pattern
    if ends_with_ascii_alnum:
        pattern = pattern + r"\b"

    return re.compile(pattern)
