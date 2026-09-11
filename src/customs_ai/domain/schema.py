from datetime import date
from decimal import Decimal
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from customs_ai.domain.enums import ValueOrigin

T = TypeVar("T")


class BaseDomainModel(BaseModel):
    """Base model enforcing strict canonical schema policies."""

    model_config = ConfigDict(extra="forbid")


class CanonicalField(BaseDomainModel, Generic[T]):
    """Typed canonical value with raw value and provenance."""

    raw_value: str | None = None
    normalized_value: T | None = None
    origin: ValueOrigin
    source_document_id: str | None = None
    page: int | None = None
    sheet: str | None = None
    cell: str | None = None
    bounding_box: tuple[float, float, float, float] | None = None
    extraction_method: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def check_extracted_provenance(self) -> "CanonicalField[T]":
        if self.origin == ValueOrigin.EXTRACTED:
            if not self.raw_value:
                raise ValueError("raw_value is required when origin is EXTRACTED")
            if not self.source_document_id:
                raise ValueError(
                    "source_document_id is required when origin is EXTRACTED"
                )
        return self


class Evidence(BaseDomainModel):
    """Evidence reference used later by checks and reporting."""

    evidence_id: str
    document_id: str
    field_name: str
    raw_value: str
    normalized_value: Any | None = None
    page: int | None = None
    sheet: str | None = None
    cell: str | None = None
    bounding_box: tuple[float, float, float, float] | None = None
    extraction_id: str | None = None


class Party(BaseDomainModel):
    name: CanonicalField[str] | None = None
    tax_id: CanonicalField[str] | None = None
    address: CanonicalField[str] | None = None
    country_code: CanonicalField[str] | None = None


class InvoiceItem(BaseDomainModel):
    item_number: CanonicalField[str] | None = None
    item_code: CanonicalField[str] | None = None
    part_number: CanonicalField[str] | None = None
    model: CanonicalField[str] | None = None
    description: CanonicalField[str] | None = None
    brand: CanonicalField[str] | None = None
    manufacturer: CanonicalField[str] | None = None
    quantity: CanonicalField[Decimal] | None = None
    unit: CanonicalField[str] | None = None
    unit_price: CanonicalField[Decimal] | None = None
    amount: CanonicalField[Decimal] | None = None
    origin: CanonicalField[str] | None = None
    weight: CanonicalField[Decimal] | None = None
    package_information: CanonicalField[str] | None = None


class Invoice(BaseDomainModel):
    invoice_number: CanonicalField[str] | None = None
    invoice_date: CanonicalField[date] | None = None
    seller: Party | None = None
    buyer: Party | None = None
    ship_to: Party | None = None
    currency: CanonicalField[str] | None = None
    incoterm: CanonicalField[str] | None = None
    payment_term: CanonicalField[str] | None = None
    total_amount: CanonicalField[Decimal] | None = None
    freight: CanonicalField[Decimal] | None = None
    insurance: CanonicalField[Decimal] | None = None
    discount: CanonicalField[Decimal] | None = None
    items: list[InvoiceItem] = Field(default_factory=list)


class PackingItem(BaseDomainModel):
    item_code: CanonicalField[str] | None = None
    description: CanonicalField[str] | None = None
    quantity: CanonicalField[Decimal] | None = None
    unit: CanonicalField[str] | None = None
    package_number: CanonicalField[str] | None = None
    gross_weight: CanonicalField[Decimal] | None = None
    net_weight: CanonicalField[Decimal] | None = None


class PackingList(BaseDomainModel):
    packing_list_number: CanonicalField[str] | None = None
    date: CanonicalField[date] | None = None
    seller: Party | None = None
    buyer: Party | None = None
    shipment_reference: CanonicalField[str] | None = None
    invoice_references: list[CanonicalField[str]] = Field(default_factory=list)
    package_count: CanonicalField[Decimal] | None = None
    package_type: CanonicalField[str] | None = None
    gross_weight: CanonicalField[Decimal] | None = None
    net_weight: CanonicalField[Decimal] | None = None
    dimensions: CanonicalField[str] | None = None
    volume: CanonicalField[Decimal] | None = None
    items: list[PackingItem] = Field(default_factory=list)


class TransportDocument(BaseDomainModel):
    document_number: CanonicalField[str] | None = None
    shipper: Party | None = None
    consignee: Party | None = None
    notify_party: Party | None = None
    vessel: CanonicalField[str] | None = None
    voyage: CanonicalField[str] | None = None
    flight: CanonicalField[str] | None = None
    port_of_loading: CanonicalField[str] | None = None
    port_of_discharge: CanonicalField[str] | None = None
    place_of_receipt: CanonicalField[str] | None = None
    place_of_delivery: CanonicalField[str] | None = None
    etd: CanonicalField[date] | None = None
    eta: CanonicalField[date] | None = None
    package_count: CanonicalField[Decimal] | None = None
    package_type: CanonicalField[str] | None = None
    gross_weight: CanonicalField[Decimal] | None = None
    volume: CanonicalField[Decimal] | None = None
    container_numbers: list[CanonicalField[str]] = Field(default_factory=list)
    seal_numbers: list[CanonicalField[str]] = Field(default_factory=list)
    freight_term: CanonicalField[str] | None = None


class CustomsDeclarationItem(BaseDomainModel):
    line_reference: CanonicalField[str] | None = None
    description: CanonicalField[str] | None = None
    hs_code: CanonicalField[str] | None = None
    origin: CanonicalField[str] | None = None
    quantity: CanonicalField[Decimal] | None = None
    unit: CanonicalField[str] | None = None
    item_value: CanonicalField[Decimal] | None = None
    tax_fields: list[CanonicalField[str]] = Field(default_factory=list)
    permit_references: list[CanonicalField[str]] = Field(default_factory=list)


class CustomsDeclaration(BaseDomainModel):
    declaration_type: CanonicalField[str] | None = None
    customs_office: CanonicalField[str] | None = None
    importer: Party | None = None
    exporter: Party | None = None
    invoice_references: list[CanonicalField[str]] = Field(default_factory=list)
    transport_references: list[CanonicalField[str]] = Field(default_factory=list)
    currency: CanonicalField[str] | None = None
    exchange_rate: CanonicalField[Decimal] | None = None
    delivery_term: CanonicalField[str] | None = None
    total_value: CanonicalField[Decimal] | None = None
    freight: CanonicalField[Decimal] | None = None
    insurance: CanonicalField[Decimal] | None = None
    items: list[CustomsDeclarationItem] = Field(default_factory=list)


class CanonicalShipment(BaseDomainModel):
    schema_version: Literal["0.1"] = "0.1"
    invoices: list[Invoice] = Field(default_factory=list)
    packing_lists: list[PackingList] = Field(default_factory=list)
    transport_documents: list[TransportDocument] = Field(default_factory=list)
    customs_declarations: list[CustomsDeclaration] = Field(default_factory=list)
