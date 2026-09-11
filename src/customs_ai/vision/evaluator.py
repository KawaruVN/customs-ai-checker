import unicodedata

from customs_ai.config import VisionSettingsConfig, settings


class TextQualityEvaluator:
    def __init__(self, config: VisionSettingsConfig | None = None) -> None:
        self.config = config or settings.vision

    @staticmethod
    def _stats(text: str) -> tuple[int, int, int, int, int]:
        content = text.strip()
        length = len(content)
        if length == 0:
            return 0, 0, 0, 0, 0

        replacement = content.count("\ufffd")
        control = sum(
            1
            for char in content
            if unicodedata.category(char).startswith("C") and char not in {"\n", "\r", "\t"}
        )
        non_space = sum(1 for char in content if not char.isspace())
        meaningful = sum(
            1 for char in content if unicodedata.category(char).startswith(("L", "N"))
        )
        return length, replacement, control, non_space, meaningful

    def _text_is_usable(self, text: str | None) -> bool:
        if not text or not text.strip():
            return False

        length, replacement, control, non_space, meaningful = self._stats(text)
        if length == 0 or non_space == 0:
            return False
        if meaningful < self.config.min_meaningful_chars:
            return False
        if replacement / length > self.config.max_replacement_ratio:
            return False
        if control / length > self.config.max_control_ratio:
            return False
        if meaningful / non_space < self.config.min_meaningful_ratio:
            return False
        return True

    def evaluate_native_text(self, text: str | None) -> bool:
        return self._text_is_usable(text)

    def evaluate_provider_result(
        self, text: str | None, confidence: float | None
    ) -> bool:
        if confidence is not None and confidence < self.config.min_confidence_threshold:
            return False
        return self._text_is_usable(text)
