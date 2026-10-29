"""Packing config validation tests; no document extraction is implemented."""

import pytest
from pydantic import ValidationError
import yaml

from customs_ai.domain.schema import PackingItem, PackingList, Party
from customs_ai.extraction.config import load_invoice_extraction_config, normalize_alias
from customs_ai.extraction.packing_config import (
    APPROVED_PACKING_HEADER_PATHS,
    APPROVED_PACKING_ITEM_PATHS,
    PackingExtractionConfig,
    load_packing_extraction_config,
)

HEADER_PATHS = {
    "packing_list_number", "date", "seller.name", "seller.tax_id", "seller.address",
    "buyer.name", "buyer.tax_id", "buyer.address", "shipment_reference", "invoice_references",
    "package_count", "package_type", "gross_weight", "net_weight", "dimensions", "volume",
}
ITEM_PATHS = {"item_code", "description", "quantity", "unit", "package_number", "gross_weight", "net_weight"}


def payload():
    return load_packing_extraction_config().model_dump(mode="python")


def normalized(aliases):
    return {normalize_alias(alias) for alias in aliases}


def test_complete_paths_match_handoff_and_existing_canonical_models():
    config = load_packing_extraction_config()
    assert set(config.headers) == HEADER_PATHS == APPROVED_PACKING_HEADER_PATHS
    assert set(config.items) == ITEM_PATHS == APPROVED_PACKING_ITEM_PATHS
    for path in HEADER_PATHS:
        parts = path.split(".")
        assert parts[0] in PackingList.model_fields
        if len(parts) == 2:
            assert parts[1] in Party.model_fields
    assert ITEM_PATHS == set(PackingItem.model_fields)


@pytest.mark.parametrize("labels", [
    ("PACKING LIST NO", "TOTAL PACKAGES", "QUANTITY", "GROSS WEIGHT", "NET WEIGHT"),
    ("SỐ PHIẾU ĐÓNG GÓI", "TỔNG SỐ KIỆN", "SỐ LƯỢNG", "TRỌNG LƯỢNG CẢ BÌ", "TRỌNG LƯỢNG TỊNH"),
    ("装箱单号", "总件数", "数量", "毛重", "净重"),
])
def test_default_vocabulary_covers_english_vietnamese_and_chinese_roles(labels):
    config = load_packing_extraction_config()
    number, packages, quantity, gross, net = labels
    assert number in config.headers["packing_list_number"]
    assert packages in config.headers["package_count"]
    assert quantity in config.items["quantity"]
    assert gross in config.headers["gross_weight"] and gross in config.items["gross_weight"]
    assert net in config.headers["net_weight"] and net in config.items["net_weight"]


def test_default_loading_is_cwd_independent(monkeypatch, tmp_path):
    expected = payload()
    monkeypatch.chdir(tmp_path)
    assert load_packing_extraction_config().model_dump() == expected


def test_explicit_yaml_path_and_relative_path_follow_documented_cwd_policy(tmp_path, monkeypatch):
    expected = payload()
    path = tmp_path / "synthetic.yaml"
    path.write_text(yaml.safe_dump(expected, allow_unicode=True), encoding="utf-8")
    assert load_packing_extraction_config(path).model_dump() == expected
    monkeypatch.chdir(tmp_path)
    assert load_packing_extraction_config("synthetic.yaml").model_dump() == expected


@pytest.mark.parametrize("context", ["headers", "items"])
def test_unknown_and_missing_paths_rejected(context):
    value = payload()
    value[context]["customer.layout.field"] = ["SYNTHETIC ALIAS"]
    with pytest.raises(ValidationError, match="Unknown"):
        PackingExtractionConfig.model_validate(value)
    value = payload()
    value[context].pop(next(iter(value[context])))
    with pytest.raises(ValidationError, match="Missing required"):
        PackingExtractionConfig.model_validate(value)


@pytest.mark.parametrize("context", ["headers", "items"])
def test_missing_context_and_unexpected_root_keys_rejected(context):
    value = payload()
    del value[context]
    with pytest.raises(ValidationError):
        PackingExtractionConfig.model_validate(value)
    value = payload()
    value["extra"] = {}
    with pytest.raises(ValidationError):
        PackingExtractionConfig.model_validate(value)


@pytest.mark.parametrize("alias", [" gross   weight ", "gRoSs WeIgHt", "\tGROSS\nWEIGHT\t", "毛重", "\t毛重 "])
def test_duplicate_normalized_aliases_in_same_field_rejected(alias):
    value = payload()
    value["headers"]["gross_weight"].append(alias)
    with pytest.raises(ValidationError, match="Duplicate normalized alias"):
        PackingExtractionConfig.model_validate(value)


@pytest.mark.parametrize("context,field,alias", [
    ("headers", "buyer.name", " seller "),
    ("headers", "net_weight", "g.w."),
    ("items", "net_weight", "毛重"),
    ("items", "package_number", " quantity "),
    ("headers", "volume", "dimensions"),
    ("headers", "packing_list_number", " invoice no "),
])
def test_cross_field_conflicts_rejected_within_each_context(context, field, alias):
    value = payload()
    value[context][field].append(alias)
    with pytest.raises(ValidationError, match="Duplicate normalized alias"):
        PackingExtractionConfig.model_validate(value)


@pytest.mark.parametrize("aliases", [[], [""], [" \t\n"], [None], [12], [True], "GROSS WEIGHT", None, ("GROSS WEIGHT",), {"GROSS WEIGHT"}, {"alias": "GROSS WEIGHT"}])
def test_empty_blank_nonstring_or_nonlist_alias_shapes_rejected(aliases):
    value = payload()
    value["headers"]["gross_weight"] = aliases
    with pytest.raises(ValidationError):
        PackingExtractionConfig.model_validate(value)


@pytest.mark.parametrize("shape", [None, [], "headers", 12, True])
def test_context_must_be_a_mapping(shape):
    value = payload()
    value["headers"] = shape
    with pytest.raises(ValidationError):
        PackingExtractionConfig.model_validate(value)


@pytest.mark.parametrize("text", [
    "headers: [", "", "null", "[]", "synthetic scalar", "12", "true",
    "headers: {}\nheaders: {}\nitems: {}",
    "headers:\n  date: [DATE]\n  date: [OTHER]\nitems: {}",
    "headers: {1: [DATE]}\nitems: {}",
    "!!python/object/apply:os.system ['echo forbidden']",
    "headers: &aliases {<<: *aliases}\nitems: {}",
])
def test_invalid_yaml_unsupported_shapes_and_duplicate_keys_fail_closed(tmp_path, text):
    path = tmp_path / "synthetic-invalid.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load_packing_extraction_config(path)


def test_nonexistent_configuration_file_fails_explicitly(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_packing_extraction_config(tmp_path / "not-present.yaml")


def test_context_isolation_intentionally_allows_repeated_weight_labels():
    config = load_packing_extraction_config()
    assert normalized(config.headers["gross_weight"]) & normalized(config.items["gross_weight"])
    assert normalized(config.headers["net_weight"]) & normalized(config.items["net_weight"])
    value = payload()
    value["headers"]["package_type"].append("SYNTHETIC SHARED LABEL")
    value["items"]["unit"].append(" synthetic   shared label ")
    assert PackingExtractionConfig.model_validate(value)


def test_roles_counts_weights_dimensions_and_references_are_not_conflated():
    config = load_packing_extraction_config()
    headers, items = config.headers, config.items
    party_labels = set().union(*(normalized(headers[path]) for path in headers if path.startswith(("seller.", "buyer."))))
    assert party_labels.isdisjoint({"SHIPPER", "CONSIGNEE", "EXPORTER", "IMPORTER", "发货人", "收货人", "出口商", "进口商"})
    assert normalized(headers["seller.name"]).isdisjoint(normalized(headers["buyer.name"]))
    assert normalized(headers["package_count"]).isdisjoint(normalized(items["quantity"]))
    assert {"QUANTITY", "QTY", "数量"}.isdisjoint(normalized(headers["package_count"]))
    assert {"TOTAL PACKAGES", "NO. OF PACKAGES", "件数", "总件数"}.isdisjoint(normalized(items["quantity"]))
    assert normalized(headers["gross_weight"]).isdisjoint(normalized(headers["net_weight"]))
    assert normalized(items["gross_weight"]).isdisjoint(normalized(items["net_weight"]))
    assert normalized(headers["package_type"]).isdisjoint(normalized(items["package_number"]))
    assert {"CARTON", "PALLET", "CASE"}.isdisjoint(normalized(headers["package_type"]))
    assert normalized(headers["dimensions"]).isdisjoint(normalized(headers["volume"]))
    assert "MEASUREMENT" not in normalized(headers["dimensions"] + headers["volume"])
    assert normalized(headers["packing_list_number"]).isdisjoint(normalized(headers["invoice_references"]))


def test_normalization_reuses_approved_helper_and_preserves_punctuation_policy():
    from customs_ai.extraction import packing_config
    assert packing_config.normalize_alias is normalize_alias
    assert normalize_alias("  người\t bán ") == "NGƯỜI BÁN"
    assert normalize_alias("  毛重  ") == "毛重"
    assert normalize_alias("G.W.") != normalize_alias("GW")
    assert normalize_alias("SELLER:") != normalize_alias("SELLER：")
    value = payload()
    value["headers"]["seller.name"].extend(["SELLER:", "SELLER："])
    assert PackingExtractionConfig.model_validate(value)


def test_model_revalidation_detects_nested_mutation_instead_of_trusting_instances():
    config = load_packing_extraction_config()
    config.items["unit"].append(" quantity ")
    with pytest.raises(ValidationError, match="Duplicate normalized alias"):
        PackingExtractionConfig.model_validate(config)


def test_packing_load_is_independent_of_invoice_vocabulary_and_preserves_invoice_config(monkeypatch):
    import customs_ai.extraction.config as invoice_config
    before = load_invoice_extraction_config().model_dump()
    with monkeypatch.context() as patch:
        patch.setattr(invoice_config, "load_invoice_extraction_config", lambda *args: (_ for _ in ()).throw(AssertionError("Invoice loader must not be called")))
        assert load_packing_extraction_config().headers["invoice_references"]
    assert load_invoice_extraction_config().model_dump() == before
