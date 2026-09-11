import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

from customs_ai.classification.config import DocumentClassificationConfig, load_classification_config
from customs_ai.classification.text_utils import build_clue_regex, normalize_text
from customs_ai.config import VisionSettingsConfig, settings
from customs_ai.vision.enums import TextResolutionSource, VerificationLevel
from customs_ai.vision.models import ProviderTextResult, ResolvedPdfPage


_DATE_YMD = re.compile(r"(?<!\d)(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)")
_DATE_DMY = re.compile(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})(?!\d)")
_IDENTIFIER = re.compile(
    r"(?<![A-Za-z0-9])(?=[A-Za-z0-9/-]*[A-Za-z])(?=[A-Za-z0-9/-]*\d)"
    r"[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)*(?![A-Za-z0-9])"
)
_NUMBER = re.compile(r"(?<![A-Za-z0-9])[-+]?\d(?:[\d.,]*\d)?(?![A-Za-z0-9])")
_WORD = re.compile(r"\w+", re.UNICODE)


class HighSignalReconciler:
    def __init__(
        self,
        config: VisionSettingsConfig | None = None,
        classification_config: DocumentClassificationConfig | None = None,
    ) -> None:
        self.config = config or settings.vision
        self.classification_config = classification_config or load_classification_config()
        self._strong_clues = {
            doc_type: [build_clue_regex(clue) for clue in clue_cfg.strong]
            for doc_type, clue_cfg in self.classification_config.clues.items()
        }

    @staticmethod
    def _normalized_identifier(value: str) -> str:
        return unicodedata.normalize("NFKC", value).upper()

    @staticmethod
    def _normalize_date_ymd(year: int, month: int, day: int) -> str | None:
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    def _extract_dates(self, text: str) -> tuple[set[str], list[tuple[int, int]]]:
        tokens: set[str] = set()
        spans: list[tuple[int, int]] = []
        for match in _DATE_YMD.finditer(text):
            normalized = self._normalize_date_ymd(
                int(match.group(1)), int(match.group(2)), int(match.group(3))
            )
            if normalized:
                tokens.add(normalized)
                spans.append(match.span())
        for match in _DATE_DMY.finditer(text):
            day, month, year = map(int, match.groups())
            if day <= 12 and month <= 12:
                normalized = "AMBIG:" + match.group(0).replace(".", "/").replace("-", "/")
            else:
                normalized = self._normalize_date_ymd(year, month, day)
            if normalized:
                tokens.add(normalized)
                spans.append(match.span())
        return tokens, spans

    @staticmethod
    def _mask_spans(text: str, spans: list[tuple[int, int]]) -> str:
        chars = list(text)
        for start, end in spans:
            for idx in range(start, end):
                chars[idx] = " "
        return "".join(chars)

    @staticmethod
    def _normalize_number(raw: str) -> str:
        value = raw.strip()
        sign = ""
        if value.startswith(("+", "-")):
            sign, value = value[0], value[1:]
        if not value or not any(char.isdigit() for char in value):
            return "RAW:" + raw

        comma_count = value.count(",")
        dot_count = value.count(".")

        def _decimal_canonical(int_part: str, frac_part: str) -> str:
            digits = int_part.replace(",", "").replace(".", "") or "0"
            try:
                decimal_value = Decimal(f"{sign}{digits}.{frac_part}")
            except InvalidOperation:
                return "RAW:" + raw
            return format(decimal_value.normalize(), "f")

        if comma_count and dot_count:
            decimal_sep = "," if value.rfind(",") > value.rfind(".") else "."
            thousands_sep = "." if decimal_sep == "," else ","
            int_part, frac_part = value.rsplit(decimal_sep, 1)
            groups = int_part.split(thousands_sep)
            if len(groups) > 1 and not all(len(group) == 3 for group in groups[1:]):
                return "AMBIG:" + sign + value
            if not frac_part.isdigit() or not int_part.replace(thousands_sep, "").isdigit():
                return "AMBIG:" + sign + value
            return _decimal_canonical(int_part, frac_part)

        sep = "," if comma_count else "." if dot_count else None
        if sep is None:
            try:
                return str(int(f"{sign}{value}"))
            except ValueError:
                return "RAW:" + raw

        parts = value.split(sep)
        if not all(part.isdigit() for part in parts):
            return "AMBIG:" + sign + value

        if len(parts) > 2:
            if all(len(group) == 3 for group in parts[1:]):
                return str(int(sign + "".join(parts)))
            return "AMBIG:" + sign + value

        before, after = parts
        if len(after) in {1, 2, 4, 5, 6}:
            return _decimal_canonical(before, after)
        if len(after) == 3:
            if len(before) > 3:
                return _decimal_canonical(before, after)
            return "AMBIG:" + sign + value
        return _decimal_canonical(before, after)

    def _extract_identifiers(self, text: str) -> tuple[set[str], list[tuple[int, int]]]:
        tokens: set[str] = set()
        spans: list[tuple[int, int]] = []
        for match in _IDENTIFIER.finditer(text):
            tokens.add(self._normalized_identifier(match.group(0)))
            spans.append(match.span())
        return tokens, spans

    def _extract_numbers(self, text: str, excluded_spans: list[tuple[int, int]]) -> set[str]:
        masked = self._mask_spans(text, excluded_spans)
        return {self._normalize_number(match.group(0)) for match in _NUMBER.finditer(masked)}

    def _extract_document_types(self, text: str) -> set[str]:
        normalized = normalize_text(text)
        return {
            doc_type
            for doc_type, patterns in self._strong_clues.items()
            if any(pattern.search(normalized) for pattern in patterns)
        }

    @staticmethod
    def _soft_overlap(left: str, right: str) -> float:
        left_tokens = {token.casefold() for token in _WORD.findall(normalize_text(left))}
        right_tokens = {token.casefold() for token in _WORD.findall(normalize_text(right))}
        if not left_tokens and not right_tokens:
            return 1.0
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    def _signals(self, text: str) -> dict[str, set[str]]:
        dates, date_spans = self._extract_dates(text)
        identifiers, identifier_spans = self._extract_identifiers(text)
        numbers = self._extract_numbers(text, date_spans + identifier_spans)
        return {
            "dates": dates,
            "identifiers": identifiers,
            "numbers": numbers,
            "document_types": self._extract_document_types(text),
        }

    def reconcile(
        self,
        page_num: int,
        vlm_result: ProviderTextResult,
        vlm_usable: bool,
        ocr_result: ProviderTextResult,
        ocr_usable: bool,
    ) -> ResolvedPdfPage:
        provider_results = [vlm_result, ocr_result]

        if vlm_usable and ocr_usable:
            vlm_signals = self._signals(vlm_result.text)
            ocr_signals = self._signals(ocr_result.text)
            material_conflict = any(
                vlm_signals[key] != ocr_signals[key]
                for key in ("dates", "identifiers", "numbers", "document_types")
                if vlm_signals[key] or ocr_signals[key]
            )
            overlap = self._soft_overlap(vlm_result.text, ocr_result.text)
            if material_conflict or overlap < self.config.min_soft_text_overlap:
                return ResolvedPdfPage(
                    page=page_num,
                    text="",
                    source=TextResolutionSource.UNRESOLVED,
                    verification_level=VerificationLevel.CONFLICT,
                    agreement_score=overlap,
                    requires_review=True,
                    provider_results=provider_results,
                )
            return ResolvedPdfPage(
                page=page_num,
                text=vlm_result.text,
                source=TextResolutionSource.CROSS_VERIFIED_VISUAL,
                confidence=vlm_result.confidence,
                verification_level=VerificationLevel.CROSS_VERIFIED,
                agreement_score=overlap,
                requires_review=False,
                provider_results=provider_results,
            )

        if vlm_usable:
            return ResolvedPdfPage(
                page=page_num,
                text=vlm_result.text,
                source=TextResolutionSource.DOCUMENT_VISION_LOCAL,
                confidence=vlm_result.confidence,
                verification_level=VerificationLevel.SINGLE_PROVIDER,
                requires_review=False,
                provider_results=provider_results,
            )

        if ocr_usable:
            return ResolvedPdfPage(
                page=page_num,
                text=ocr_result.text,
                source=TextResolutionSource.OCR_LOCAL,
                confidence=ocr_result.confidence,
                verification_level=VerificationLevel.SINGLE_PROVIDER,
                requires_review=False,
                provider_results=provider_results,
            )

        return ResolvedPdfPage(
            page=page_num,
            text="",
            source=TextResolutionSource.UNRESOLVED,
            verification_level=VerificationLevel.UNVERIFIED,
            requires_review=True,
            provider_results=provider_results,
        )
