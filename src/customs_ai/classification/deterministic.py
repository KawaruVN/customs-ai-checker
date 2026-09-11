
import re

from customs_ai.classification.config import DocumentClassificationConfig
from customs_ai.classification.enums import ClassificationMethod, DocumentType
from customs_ai.classification.models import (
    ClassificationEvidence,
    DocumentClassificationResult,
)
from customs_ai.classification.text_utils import build_clue_regex, normalize_text
from customs_ai.parsers.models import ParsedDocument, ParsedPdfDocument, ParsedWorkbook
from customs_ai.vision.models import ResolvedPdfDocument


class DeterministicClassifier:
    def __init__(self, config: DocumentClassificationConfig):
        self.config = config
        self._compiled_clues: dict[str, dict[str, list[tuple[str, float, re.Pattern]]]] = {
            dt.value: {"strong": [], "supporting": []} for dt in DocumentType
        }

        # Precompile all clue regular expressions
        for dt_key, clue_config in self.config.clues.items():
            for clue in clue_config.strong:
                pattern = build_clue_regex(clue)
                self._compiled_clues[dt_key]["strong"].append(
                    (clue, self.config.settings.strong_weight, pattern)
                )
            for clue in clue_config.supporting:
                pattern = build_clue_regex(clue)
                self._compiled_clues[dt_key]["supporting"].append(
                    (clue, self.config.settings.supporting_weight, pattern)
                )

    def classify(
        self, parsed_doc: ParsedDocument | ResolvedPdfDocument, filename: str | None = None
    ) -> DocumentClassificationResult:
        # Note: filename is explicitly accepted for signature compatibility but ignored for scoring.
        scores: dict[str, float] = {dt.value: 0.0 for dt in DocumentType}
        evidences: list[ClassificationEvidence] = []
        found_clues: set[tuple[str, str]] = set()

        def _evaluate_text(
            text: str, page: int | None = None, sheet: str | None = None, cell: str | None = None
        ) -> None:
            if not text:
                return
            norm_text = normalize_text(text)
            for dt_key, compiled_groups in self._compiled_clues.items():
                for clue, weight, pattern in compiled_groups["strong"] + compiled_groups["supporting"]:
                    if pattern.search(norm_text):
                        # Ensure deduplication: a specific clue only contributes to a type's score once
                        dedup_key = (dt_key, clue)
                        if dedup_key in found_clues:
                            continue
                        found_clues.add(dedup_key)
                        
                        scores[dt_key] = min(1.0, round(scores[dt_key] + weight, 10))
                        evidences.append(
                            ClassificationEvidence(
                                target_document_type=DocumentType(dt_key),
                                clue=clue,
                                weight=weight,
                                page=page,
                                sheet=sheet,
                                cell=cell,
                            )
                        )

        # 1. Evaluate PDF Text
        if isinstance(parsed_doc, (ParsedPdfDocument, ResolvedPdfDocument)):
            for page in parsed_doc.pages:
                _evaluate_text(page.text, page=page.page)

        # 2. Evaluate Excel Cells
        elif isinstance(parsed_doc, ParsedWorkbook):
            for sheet in parsed_doc.sheets:
                for cell in sheet.cells:
                    if isinstance(cell.raw_value, str):
                        _evaluate_text(cell.raw_value, sheet=sheet.name, cell=cell.coordinate)

        # 3. Resolve Document Type
        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_dt_key, top_score = sorted_scores[0]
        second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0

        if top_score < self.config.settings.threshold:
            final_dt = DocumentType.UNKNOWN
            final_conf = round(top_score, 10)
        elif (top_score - second_score) < self.config.settings.conflict_margin:
            final_dt = DocumentType.UNKNOWN
            final_conf = round(top_score, 10)
        else:
            final_dt = DocumentType(top_dt_key)
            final_conf = round(top_score, 10)

        # Return evidence (Retain all evidence if UNKNOWN so humans can review conflicting clues)
        filtered_evidence = (
            evidences
            if final_dt == DocumentType.UNKNOWN
            else [e for e in evidences if e.target_document_type == final_dt]
        )

        return DocumentClassificationResult(
            document_id=parsed_doc.document_id,
            document_type=final_dt,
            confidence=final_conf,
            method=ClassificationMethod.DETERMINISTIC,
            evidence=filtered_evidence,
        )
