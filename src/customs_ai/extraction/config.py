from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from customs_ai.config import BASE_DIR

APPROVED_HEADER_PATHS: frozenset[str] = frozenset(
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

APPROVED_ITEM_PATHS: frozenset[str] = frozenset(
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

DEFAULT_INVOICE_EXTRACTION_CONFIG_PATH = (
    BASE_DIR / "config" / "invoice_extraction.yaml"
)


def normalize_alias(alias: str) -> str:
    """Normalize alias for deterministic comparison.

    Collapses whitespace and converts to uppercase.
    """
    return " ".join(alias.strip().upper().split())


class InvoiceExtractionConfig(BaseModel):
    """Configuration for invoice header and item field extraction aliases.

    Note on Prefix Overlaps:
    Prefix overlaps such as 'SELLER' vs 'SELLER ADDRESS' are intentionally
    allowed at this configuration layer. Config validation only rejects exact
    duplicate conflicts within the same extraction context (headers or items).
    Longest/specific label resolution is handled downstream by TASK-006B.
    Config validation does not claim to solve document matching itself.
    """

    model_config = ConfigDict(extra="forbid")

    headers: dict[str, list[str]]
    items: dict[str, list[str]]

    @model_validator(mode="after")
    def validate_extraction_config(self) -> "InvoiceExtractionConfig":
        self._validate_context(
            context_name="headers",
            field_map=self.headers,
            approved_paths=APPROVED_HEADER_PATHS,
        )
        self._validate_context(
            context_name="items",
            field_map=self.items,
            approved_paths=APPROVED_ITEM_PATHS,
        )
        return self

    @classmethod
    def _validate_context(
        cls,
        context_name: str,
        field_map: dict[str, list[str]],
        approved_paths: frozenset[str],
    ) -> None:
        configured_paths = set(field_map.keys())

        # Check unknown paths
        unknown = configured_paths - approved_paths
        if unknown:
            unknown_str = ", ".join(sorted(unknown))
            raise ValueError(
                f"Unknown {context_name} field path(s) in extraction config: {unknown_str}"
            )

        # Check missing approved paths
        missing = approved_paths - configured_paths
        if missing:
            missing_str = ", ".join(sorted(missing))
            raise ValueError(
                f"Missing required {context_name} field path(s) in extraction config: {missing_str}"
            )

        # Validate aliases within this context
        seen_normalized: dict[str, str] = {}
        for path, aliases in field_map.items():
            if not isinstance(aliases, list) or len(aliases) == 0:
                raise ValueError(
                    f"Empty alias list for {context_name} path '{path}'. Each field must have at least one alias."
                )

            for alias in aliases:
                if not isinstance(alias, str) or not alias.strip():
                    raise ValueError(
                        f"Blank alias found in {context_name} for path '{path}'."
                    )

                norm = normalize_alias(alias)
                if norm in seen_normalized:
                    existing_path = seen_normalized[norm]
                    if existing_path == path:
                        raise ValueError(
                            f"Duplicate alias '{alias}' defined multiple times for {context_name} path '{path}'."
                        )
                    raise ValueError(
                        f"Conflicting duplicate alias '{alias}' in {context_name} for path '{path}' "
                        f"(already assigned to '{existing_path}')."
                    )
                seen_normalized[norm] = path


def load_invoice_extraction_config(
    config_path: Path | str | None = None,
) -> InvoiceExtractionConfig:
    """Load and validate invoice extraction alias config in a CWD-independent manner."""
    if config_path is None:
        resolved_path = DEFAULT_INVOICE_EXTRACTION_CONFIG_PATH
    else:
        resolved_path = Path(config_path).resolve()

    if not resolved_path.is_file():
        raise FileNotFoundError(
            f"Invoice extraction config not found at {resolved_path}"
        )

    with resolved_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invoice extraction config at {resolved_path} must be a YAML mapping"
        )

    return InvoiceExtractionConfig.model_validate(data)
