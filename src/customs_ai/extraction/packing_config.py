"""Packing-only alias configuration; no document interpretation or extraction.

The shared normalization policy is case/whitespace normalization only. Colons,
other punctuation and Unicode compatibility characters remain literal aliases.
Separate header/item namespaces allow document and item weights to reuse labels;
future extractors must establish context and longest/specific label boundaries.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
import yaml

from customs_ai.config import BASE_DIR
from customs_ai.extraction.config import normalize_alias

APPROVED_PACKING_HEADER_PATHS = frozenset({
    "packing_list_number", "date",
    "seller.name", "seller.tax_id", "seller.address",
    "buyer.name", "buyer.tax_id", "buyer.address",
    "shipment_reference", "invoice_references", "package_count", "package_type",
    "gross_weight", "net_weight", "dimensions", "volume",
})
APPROVED_PACKING_ITEM_PATHS = frozenset({
    "item_code", "description", "quantity", "unit", "package_number",
    "gross_weight", "net_weight",
})
DEFAULT_PACKING_EXTRACTION_CONFIG_PATH = BASE_DIR / "config" / "packing_extraction.yaml"


class PackingExtractionConfig(BaseModel):
    """Complete strict canonical-path alias maps in two independent contexts."""

    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True, revalidate_instances="always")

    headers: dict[str, list[str]]
    items: dict[str, list[str]]

    @field_validator("headers", "items", mode="before")
    @classmethod
    def require_map_of_alias_lists(cls, value):
        if type(value) is not dict:
            raise ValueError("Alias context must be a mapping.")
        if any(type(key) is not str or type(aliases) is not list for key, aliases in value.items()):
            raise ValueError("Alias paths must map to lists of strings.")
        return value

    @model_validator(mode="after")
    def validate_paths_and_aliases(self) -> "PackingExtractionConfig":
        for context, paths in (
            ("headers", APPROVED_PACKING_HEADER_PATHS),
            ("items", APPROVED_PACKING_ITEM_PATHS),
        ):
            field_map = getattr(self, context)
            if field_map.keys() - paths:
                raise ValueError(f"Unknown {context} field path(s).")
            if paths - field_map.keys():
                raise ValueError(f"Missing required {context} field path(s).")
            seen = set()
            for aliases in field_map.values():
                if not aliases:
                    raise ValueError(f"Empty alias list in {context}.")
                for alias in aliases:
                    normalized = normalize_alias(alias)
                    if not normalized:
                        raise ValueError(f"Blank alias in {context}.")
                    if normalized in seen:
                        raise ValueError(f"Duplicate normalized alias in {context}.")
                    seen.add(normalized)
        return self


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML without silent duplicate-key overwrite or merge-key expansion."""

    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if type(key) is not str or key in mapping:
                raise ValueError("YAML mapping keys must be unique strings.")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def load_packing_extraction_config(
    config_path: Path | str | None = None,
) -> PackingExtractionConfig:
    """Load the default independently of CWD; explicit relative paths use CWD."""
    path = DEFAULT_PACKING_EXTRACTION_CONFIG_PATH if config_path is None else Path(config_path).resolve()
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.load(handle, Loader=_UniqueKeySafeLoader)
    except FileNotFoundError:
        raise FileNotFoundError("Packing extraction config file not found.") from None
    except (yaml.YAMLError, ValueError, TypeError, RecursionError):
        raise ValueError("Invalid packing extraction YAML.") from None
    if type(data) is not dict:
        raise ValueError("Packing extraction config must be a YAML mapping.")
    return PackingExtractionConfig.model_validate(data)
