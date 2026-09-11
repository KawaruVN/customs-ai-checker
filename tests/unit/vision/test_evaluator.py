from customs_ai.config import VisionSettingsConfig
from customs_ai.vision.evaluator import TextQualityEvaluator


def evaluator(**overrides):
    config = VisionSettingsConfig(min_meaningful_chars=3, min_meaningful_ratio=0.4, **overrides)
    return TextQualityEvaluator(config)


def test_accepts_english_vietnamese_and_chinese():
    ev = evaluator()
    assert ev.evaluate_native_text("COMMERCIAL INVOICE 123")
    assert ev.evaluate_native_text("HÓA ĐƠN THƯƠNG MẠI 123")
    assert ev.evaluate_native_text("商业发票 123")


def test_rejects_blank_short_and_symbol_only_text():
    ev = evaluator()
    assert not ev.evaluate_native_text("")
    assert not ev.evaluate_native_text("A")
    assert not ev.evaluate_native_text("--- $$$ ###")


def test_rejects_control_and_replacement_garbage():
    ev = evaluator(max_control_ratio=0.01, max_replacement_ratio=0.01)
    assert not ev.evaluate_native_text("ABC\x00\x01\x02DEF")
    assert not ev.evaluate_native_text("ABC���DEF")


def test_provider_confidence_gate():
    ev = evaluator(min_confidence_threshold=0.8)
    assert not ev.evaluate_provider_result("COMMERCIAL INVOICE", 0.79)
    assert ev.evaluate_provider_result("COMMERCIAL INVOICE", 0.95)
    assert ev.evaluate_provider_result("COMMERCIAL INVOICE", None)
