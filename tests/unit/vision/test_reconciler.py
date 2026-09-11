from customs_ai.config import VisionSettingsConfig
from customs_ai.vision.enums import TextResolutionSource, VerificationLevel
from customs_ai.vision.models import ProviderTextResult
from customs_ai.vision.reconciler import HighSignalReconciler


def result(provider, text):
    return ProviderTextResult(provider=provider, text=text, confidence=0.99)


def reconciler():
    return HighSignalReconciler(VisionSettingsConfig(min_soft_text_overlap=0.2))


def test_cross_verified_when_high_signals_agree():
    rec = reconciler()
    page = rec.reconcile(
        1,
        result("VLM", "COMMERCIAL INVOICE INV-001 total 1,200.50 date 2026-09-11"),
        True,
        result("OCR", "COMMERCIAL INVOICE INV-001 total 1200.50 date 2026-09-11"),
        True,
    )
    assert page.source == TextResolutionSource.CROSS_VERIFIED_VISUAL
    assert page.verification_level == VerificationLevel.CROSS_VERIFIED
    assert not page.requires_review


def test_single_numeric_difference_forces_conflict():
    rec = reconciler()
    common = "COMMERCIAL INVOICE INV-001 seller buyer goods quantity price amount " * 4
    page = rec.reconcile(
        1,
        result("VLM", common + " total 12500.50"),
        True,
        result("OCR", common + " total 125000.50"),
        True,
    )
    assert page.source == TextResolutionSource.UNRESOLVED
    assert page.requires_review


def test_date_difference_forces_conflict():
    rec = reconciler()
    page = rec.reconcile(1, result("VLM", "Date 2026-09-11"), True, result("OCR", "Date 2026-09-12"), True)
    assert page.requires_review


def test_identifier_difference_forces_conflict():
    rec = reconciler()
    page = rec.reconcile(1, result("VLM", "Invoice INV-001"), True, result("OCR", "Invoice INV-002"), True)
    assert page.requires_review


def test_identifier_case_only_difference_is_equal():
    rec = reconciler()
    page = rec.reconcile(1, result("VLM", "Invoice inv-001"), True, result("OCR", "Invoice INV-001"), True)
    assert not page.requires_review


def test_ordinary_words_are_not_identifiers():
    rec = reconciler()
    left = rec._signals("Invoice Amount Container")
    assert left["identifiers"] == set()


def test_number_extraction_supports_plain_and_decimal_values():
    rec = reconciler()
    assert "12500" in rec._signals("Amount 12500")["numbers"]
    assert "1200.5" in rec._signals("Amount 1200.50")["numbers"]


def test_safe_thousands_decimal_equivalence():
    rec = reconciler()
    left = rec._signals("Amount 1,200.50")["numbers"]
    right = rec._signals("Amount 1200.50")["numbers"]
    assert left == right == {"1200.5"}


def test_ambiguous_single_separator_is_not_silently_normalized():
    rec = reconciler()
    assert rec._signals("Amount 1,200")["numbers"] != rec._signals("Amount 1200")["numbers"]


def test_strong_document_type_conflict_forces_review():
    rec = reconciler()
    page = rec.reconcile(
        1,
        result("VLM", "COMMERCIAL INVOICE INV-001"),
        True,
        result("OCR", "PACKING LIST INV-001"),
        True,
    )
    assert page.requires_review


def test_single_provider_fallbacks_and_both_failed():
    rec = reconciler()
    empty = result("X", "")
    vlm = result("VLM", "COMMERCIAL INVOICE INV-001")
    ocr = result("OCR", "COMMERCIAL INVOICE INV-001")
    assert rec.reconcile(1, vlm, True, empty, False).source == TextResolutionSource.DOCUMENT_VISION_LOCAL
    assert rec.reconcile(1, empty, False, ocr, True).source == TextResolutionSource.OCR_LOCAL
    assert rec.reconcile(1, empty, False, empty, False).requires_review
