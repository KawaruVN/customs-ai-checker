from decimal import Decimal

import pytest
from pydantic import ValidationError

from customs_ai.domain import (
    CanonicalField,
    CanonicalShipment,
    CustomsDeclaration,
    CustomsDeclarationItem,
    Invoice,
    InvoiceItem,
    PackingItem,
    PackingList,
    Party,
    TransportDocument,
    ValueOrigin,
)


def test_canonical_field_provenance_success():
    field = CanonicalField[Decimal](
        raw_value="1,000.50",
        normalized_value=Decimal("1000.50"),
        origin=ValueOrigin.EXTRACTED,
        source_document_id="DOC-123",
        page=1,
        confidence=0.95,
    )
    assert field.normalized_value == Decimal("1000.50")
    assert field.origin == ValueOrigin.EXTRACTED
    assert field.source_document_id == "DOC-123"


def test_canonical_field_provenance_invariant_failure():
    with pytest.raises(ValidationError) as exc:
        CanonicalField[str](
            normalized_value="Missing Raw",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="DOC-123",
        )
    assert "raw_value is required" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        CanonicalField[str](
            raw_value="Missing Doc ID",
            origin=ValueOrigin.EXTRACTED,
        )
    assert "source_document_id is required" in str(exc.value)


def test_canonical_field_inferred_preservation():
    field = CanonicalField[str](
        normalized_value="SET",
        origin=ValueOrigin.INFERRED,
        confidence=0.7,
    )
    assert field.origin == ValueOrigin.INFERRED
    assert field.raw_value is None


def test_manual_origin_preservation():
    field = CanonicalField[str](
        normalized_value="User Override",
        origin=ValueOrigin.MANUAL,
    )
    dumped = field.model_dump_json()
    reloaded = CanonicalField[str].model_validate_json(dumped)

    assert reloaded.origin == ValueOrigin.MANUAL
    assert reloaded.normalized_value == "User Override"


def test_confidence_boundaries():
    CanonicalField[str](
        raw_value="A",
        origin=ValueOrigin.EXTRACTED,
        source_document_id="D1",
        confidence=0.0,
    )
    CanonicalField[str](
        raw_value="B",
        origin=ValueOrigin.EXTRACTED,
        source_document_id="D1",
        confidence=1.0,
    )

    with pytest.raises(ValidationError):
        CanonicalField[str](
            raw_value="C",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="D1",
            confidence=-0.01,
        )
    with pytest.raises(ValidationError):
        CanonicalField[str](
            raw_value="D",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="D1",
            confidence=1.01,
        )


def test_missing_data_remains_none():
    invoice = Invoice()
    assert invoice.insurance is None
    assert invoice.payment_term is None


def test_strict_extra_field_rejection():
    with pytest.raises(ValidationError) as exc:
        Invoice(customer_specific_field="Should Fail")
    assert "Extra inputs are not permitted" in str(exc.value)


def test_invalid_decimal_normalized_value_rejected():
    with pytest.raises(ValidationError):
        CanonicalField[Decimal](
            normalized_value={"not": "a decimal"},
            origin=ValueOrigin.INFERRED,
        )


def test_decimal_precision_preservation():
    exact_val = Decimal("123456789.987654321")
    field = CanonicalField[Decimal](
        raw_value="123456789.987654321",
        normalized_value=exact_val,
        origin=ValueOrigin.EXTRACTED,
        source_document_id="1",
    )
    dumped = field.model_dump_json()
    reloaded = CanonicalField[Decimal].model_validate_json(dumped)
    assert reloaded.normalized_value == exact_val
    assert isinstance(reloaded.normalized_value, Decimal)


def test_hs_code_leading_zero_in_declaration():
    decl_item = CustomsDeclarationItem(
        hs_code=CanonicalField[str](
            raw_value="01012100",
            normalized_value="01012100",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="1",
        )
    )
    decl = CustomsDeclaration(items=[decl_item])
    dumped = decl.model_dump_json()
    reloaded = CustomsDeclaration.model_validate_json(dumped)
    assert reloaded.items[0].hs_code.normalized_value == "01012100"


def test_source_locations():
    pdf_field = CanonicalField[str](
        raw_value="A",
        origin=ValueOrigin.EXTRACTED,
        source_document_id="1",
        page=2,
    )
    excel_field = CanonicalField[str](
        raw_value="B",
        origin=ValueOrigin.EXTRACTED,
        source_document_id="2",
        sheet="Sheet1",
        cell="A1",
    )
    assert pdf_field.page == 2
    assert pdf_field.bounding_box is None
    assert excel_field.sheet == "Sheet1"
    assert excel_field.cell == "A1"


def test_populated_invoice():
    item = InvoiceItem(
        quantity=CanonicalField[Decimal](
            raw_value="10.5",
            normalized_value=Decimal("10.5"),
            origin=ValueOrigin.EXTRACTED,
            source_document_id="D1",
        )
    )
    invoice = Invoice(
        invoice_number=CanonicalField[str](
            raw_value="INV1",
            normalized_value="INV1",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="D1",
        ),
        items=[item],
    )
    assert len(invoice.items) == 1
    assert invoice.invoice_number.normalized_value == "INV1"
    assert invoice.items[0].quantity.normalized_value == Decimal("10.5")


def test_populated_packing_list():
    item = PackingItem(
        net_weight=CanonicalField[Decimal](
            raw_value="5.2",
            normalized_value=Decimal("5.2"),
            origin=ValueOrigin.EXTRACTED,
            source_document_id="D2",
        )
    )
    packing_list = PackingList(
        packing_list_number=CanonicalField[str](
            raw_value="PL1",
            normalized_value="PL1",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="D2",
        ),
        items=[item],
    )
    assert len(packing_list.items) == 1
    assert packing_list.items[0].net_weight.normalized_value == Decimal("5.2")


def test_transport_document_containers_seals():
    transport = TransportDocument(
        container_numbers=[
            CanonicalField[str](
                raw_value="CONT1",
                normalized_value="CONT1",
                origin=ValueOrigin.EXTRACTED,
                source_document_id="D3",
            ),
            CanonicalField[str](
                raw_value="CONT2",
                normalized_value="CONT2",
                origin=ValueOrigin.EXTRACTED,
                source_document_id="D3",
            ),
        ],
        seal_numbers=[
            CanonicalField[str](
                raw_value="SEAL1",
                normalized_value="SEAL1",
                origin=ValueOrigin.EXTRACTED,
                source_document_id="D3",
            ),
            CanonicalField[str](
                raw_value="SEAL2",
                normalized_value="SEAL2",
                origin=ValueOrigin.EXTRACTED,
                source_document_id="D3",
            ),
        ],
    )
    dumped = transport.model_dump_json()
    reloaded = TransportDocument.model_validate_json(dumped)
    assert len(reloaded.container_numbers) == 2
    assert len(reloaded.seal_numbers) == 2
    assert reloaded.container_numbers[1].normalized_value == "CONT2"


def test_ac05_multiple_documents():
    shipment = CanonicalShipment(
        invoices=[Invoice(), Invoice()],
        packing_lists=[PackingList(), PackingList()],
    )
    assert len(shipment.invoices) == 2
    assert len(shipment.packing_lists) == 2
    assert shipment.schema_version == "0.1"


def test_json_schema_generation():
    schema = CanonicalShipment.model_json_schema()
    assert schema["title"] == "CanonicalShipment"
    assert "invoices" in schema["properties"]


def test_customs_declaration_nested_populated():
    item = CustomsDeclarationItem(
        hs_code=CanonicalField[str](
            raw_value="850110",
            normalized_value="850110",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="DECL1",
        )
    )
    declaration = CustomsDeclaration(
        declaration_type=CanonicalField[str](
            raw_value="E13",
            normalized_value="E13",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="DECL1",
        ),
        items=[item],
    )

    assert declaration.declaration_type.normalized_value == "E13"
    assert len(declaration.items) == 1
    assert declaration.items[0].hs_code.normalized_value == "850110"


def test_unicode_party_support():
    party = Party(
        name=CanonicalField[str](
            raw_value="CÔNG TY TNHH HÀ NỘI / 北京有限公司",
            normalized_value="CÔNG TY TNHH HÀ NỘI / 北京有限公司",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="D1",
        )
    )
    dumped = party.model_dump_json()
    reloaded = Party.model_validate_json(dumped)
    assert reloaded.name.normalized_value == "CÔNG TY TNHH HÀ NỘI / 北京有限公司"


def test_top_level_shipment_roundtrip():
    invoice = Invoice(
        invoice_number=CanonicalField[str](
            raw_value="I1",
            normalized_value="I1",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="1",
        )
    )
    packing_list = PackingList(
        packing_list_number=CanonicalField[str](
            raw_value="P1",
            normalized_value="P1",
            origin=ValueOrigin.EXTRACTED,
            source_document_id="2",
        )
    )

    shipment = CanonicalShipment(
        invoices=[invoice],
        packing_lists=[packing_list],
    )

    dumped = shipment.model_dump_json()
    reloaded = CanonicalShipment.model_validate_json(dumped)

    assert reloaded.schema_version == "0.1"
    assert len(reloaded.invoices) == 1
    assert reloaded.invoices[0].invoice_number.normalized_value == "I1"
    assert reloaded.invoices[0].invoice_number.origin == ValueOrigin.EXTRACTED
    assert len(reloaded.packing_lists) == 1
