import copy

import pytest
from pydantic import ValidationError

from customs_ai.extraction.config import (
    APPROVED_HEADER_PATHS,
    APPROVED_ITEM_PATHS,
    InvoiceExtractionConfig,
    load_invoice_extraction_config,
)

# Independent spec declarations to protect against drift in implementation constants
SPEC_APPROVED_HEADER_PATHS = frozenset(
    {
        "invoice_number",
        "invoice_date",
        "seller.name",
        "seller.tax_id",
        "seller.address",
        "buyer.name",
        "buyer.tax_id",
        "buyer.address",
        "ship_to.name",
        "ship_to.address",
        "currency",
        "incoterm",
        "payment_term",
        "total_amount",
        "freight",
        "insurance",
        "discount",
    }
)

SPEC_APPROVED_ITEM_PATHS = frozenset(
    {
        "item_number",
        "item_code",
        "part_number",
        "model",
        "description",
        "brand",
        "manufacturer",
        "quantity",
        "unit",
        "unit_price",
        "amount",
        "origin",
        "weight",
        "package_information",
    }
)


def _valid_payload() -> dict:
    return load_invoice_extraction_config().model_dump(mode="python")


def test_valid_extraction_config_loads_normally():
    config = load_invoice_extraction_config()
    assert isinstance(config.headers, dict)
    assert isinstance(config.items, dict)
    assert "invoice_number" in config.headers
    assert "description" in config.items
    assert len(config.headers["invoice_number"]) > 0


def test_cwd_independent_extraction_config_loading(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = load_invoice_extraction_config()
    assert "invoice_number" in config.headers
    assert "quantity" in config.items


def test_complete_approved_path_coverage():
    config = load_invoice_extraction_config()
    # Check against independent spec path definitions
    assert set(config.headers.keys()) == SPEC_APPROVED_HEADER_PATHS
    assert set(config.items.keys()) == SPEC_APPROVED_ITEM_PATHS
    # Check implementation constants match spec definitions
    assert APPROVED_HEADER_PATHS == SPEC_APPROVED_HEADER_PATHS
    assert APPROVED_ITEM_PATHS == SPEC_APPROVED_ITEM_PATHS


def test_party_role_separation_guarantee():
    """Per MASTER_SPEC.md:499, distinct Party roles must not be conflated."""
    config = load_invoice_extraction_config()

    # Seller must not map to Shipper or Exporter
    seller_aliases = set(config.headers["seller.name"])
    assert "SHIPPER" not in seller_aliases
    assert "EXPORTER" not in seller_aliases
    assert "发货人" not in seller_aliases

    # Buyer must not map to Consignee or Importer
    buyer_aliases = set(config.headers["buyer.name"])
    assert "CONSIGNEE" not in buyer_aliases
    assert "IMPORTER" not in buyer_aliases
    assert "收货人" not in buyer_aliases

    # Ship to must not conflate with general Consignee
    ship_to_aliases = set(config.headers["ship_to.name"])
    assert "CONSIGNEE" not in ship_to_aliases


def test_unknown_header_and_item_paths_rejected():
    payload = _valid_payload()
    payload["headers"]["unapproved_header"] = ["ALIAS"]
    with pytest.raises(ValidationError) as exc_info:
        InvoiceExtractionConfig.model_validate(payload)
    assert "Unknown headers field path(s)" in str(exc_info.value)

    payload = _valid_payload()
    payload["items"]["unapproved_item"] = ["ALIAS"]
    with pytest.raises(ValidationError) as exc_info:
        InvoiceExtractionConfig.model_validate(payload)
    assert "Unknown items field path(s)" in str(exc_info.value)


def test_missing_required_paths_rejected():
    payload = _valid_payload()
    del payload["headers"]["invoice_date"]
    with pytest.raises(ValidationError) as exc_info:
        InvoiceExtractionConfig.model_validate(payload)
    assert "Missing required headers field path(s)" in str(exc_info.value)

    payload = _valid_payload()
    del payload["items"]["unit_price"]
    with pytest.raises(ValidationError) as exc_info:
        InvoiceExtractionConfig.model_validate(payload)
    assert "Missing required items field path(s)" in str(exc_info.value)


def test_empty_and_blank_aliases_rejected():
    # Empty alias list rejected
    payload = _valid_payload()
    payload["headers"]["currency"] = []
    with pytest.raises(ValidationError) as exc_info:
        InvoiceExtractionConfig.model_validate(payload)
    assert "Empty alias list" in str(exc_info.value)

    # Blank alias string rejected
    payload = _valid_payload()
    payload["headers"]["currency"] = ["   "]
    with pytest.raises(ValidationError) as exc_info:
        InvoiceExtractionConfig.model_validate(payload)
    assert "Blank alias found" in str(exc_info.value)


def test_conflicting_duplicate_alias_rejected_inside_same_context():
    # Duplicate inside same context (e.g. buyer.name and seller.name sharing an alias)
    payload = _valid_payload()
    payload["headers"]["buyer.name"].append("SELLER")
    with pytest.raises(ValidationError) as exc_info:
        InvoiceExtractionConfig.model_validate(payload)
    assert "Conflicting duplicate alias" in str(exc_info.value)

    # Duplicate under same path
    payload = _valid_payload()
    payload["headers"]["invoice_number"].append("INVOICE NO")
    with pytest.raises(ValidationError) as exc_info:
        InvoiceExtractionConfig.model_validate(payload)
    assert "Duplicate alias" in str(exc_info.value)


def test_harmless_alias_reuse_across_separate_contexts_allowed():
    # Separate contexts (headers vs items) are independent namespaces.
    # An alias appearing in headers can also safely appear in items.
    payload = _valid_payload()
    payload["headers"]["currency"].append("SHARED_TAG")
    payload["items"]["unit"].append("SHARED_TAG")
    config = InvoiceExtractionConfig.model_validate(payload)
    assert "SHARED_TAG" in config.headers["currency"]
    assert "SHARED_TAG" in config.items["unit"]
