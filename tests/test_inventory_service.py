"""Material inventory service tests."""

import sqlite3

import pytest

from app.database import init_db
from app.models.inventory import (
    MaterialAdjustmentRequest,
    MaterialCreateRequest,
    MaterialReceiptRequest,
    MaterialUpdateRequest,
)
from app.services import inventory_service
from app.services.inventory_service import InventoryValidationError


@pytest.fixture()
def inventory_db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "inventory.db")
    init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    yield conn
    conn.close()


def test_material_catalog_crud_validation_and_reorder(inventory_db):
    material = inventory_service.create_material(
        MaterialCreateRequest(
            sku="WAX-SOY",
            name="Soy wax",
            category="wax",
            stock_uom="g",
            purchase_uom="kg",
            purchase_to_stock_factor=1000,
            reorder_threshold=500,
            lot_tracked=True,
        ),
        actor_user_id="admin-1",
    )

    assert material.sku == "WAX-SOY"
    assert material.active is True
    assert material.on_hand_quantity == 0
    assert material.reorder_status == "below_threshold"

    updated = inventory_service.update_material(
        material.id,
        MaterialUpdateRequest(name="Soy wax flakes", active=False),
        actor_user_id="admin-2",
    )

    assert updated.name == "Soy wax flakes"
    assert updated.active is False
    assert updated.reorder_status == "inactive"

    listed = inventory_service.list_materials(active=False)
    assert [item.id for item in listed.materials] == [material.id]

    with pytest.raises(InventoryValidationError):
        inventory_service.create_material(
            MaterialCreateRequest(
                sku="BAD",
                name="Bad conversion",
                category="wax",
                stock_uom="g",
                purchase_uom="kg",
            )
        )


def test_reorder_filter_total_matches_filtered_materials(inventory_db):
    low = inventory_service.create_material(
        MaterialCreateRequest(
            sku="LOW-WAX",
            name="Low wax",
            category="wax",
            stock_uom="g",
            reorder_threshold=100,
        )
    )
    ok = inventory_service.create_material(
        MaterialCreateRequest(
            sku="OK-WAX",
            name="OK wax",
            category="wax",
            stock_uom="g",
            reorder_threshold=100,
        )
    )
    inventory_service.create_material_receipt(
        ok.id,
        MaterialReceiptRequest(quantity=250, uom="g", total_cost_cents=2500),
    )

    listed = inventory_service.list_materials(needs_reorder=True)

    assert listed.total == 1
    assert [item.id for item in listed.materials] == [low.id]


def test_material_receipt_creates_lot_movement_and_review_exceptions(inventory_db):
    material = inventory_service.create_material(
        MaterialCreateRequest(
            sku="FRAG-LAV",
            name="Lavender fragrance oil",
            category="fragrance",
            stock_uom="ml",
            purchase_uom="l",
            purchase_to_stock_factor=1000,
            lot_tracked=True,
            expiry_tracked=True,
            evidence_required=True,
        )
    )

    receipt = inventory_service.create_material_receipt(
        material.id,
        MaterialReceiptRequest(quantity=1.5, uom="l", supplier_name="Fragrance Supplier"),
        actor_user_id="admin-1",
        actor_email="admin@example.com",
    )

    assert receipt.stock_quantity == 1500
    assert receipt.stock_uom == "ml"
    assert receipt.review_state == "needs_review"
    assert {item.exception_type for item in receipt.exceptions} == {
        "missing_receipt_evidence",
        "missing_supplier_lot",
        "missing_expiry_metadata",
        "missing_unit_cost",
    }

    detail = inventory_service.get_material(material.id)
    assert detail.on_hand_quantity == 1500
    assert detail.open_exception_count == 4
    assert detail.lots[0].supplier_lot is None
    assert detail.recent_movements[0].movement_type == "receipt"


def test_reviewed_receipt_adjustment_writeoff_and_stock_count_correction(inventory_db):
    material = inventory_service.create_material(
        MaterialCreateRequest(
            sku="JAR-120",
            name="120 ml amber jar",
            category="packaging",
            stock_uom="piece",
            purchase_uom="piece",
            reorder_threshold=10,
            evidence_required=True,
        )
    )

    receipt = inventory_service.create_material_receipt(
        material.id,
        MaterialReceiptRequest(
            quantity=100,
            uom="piece",
            total_cost_cents=12000,
            supplier_name="Jar Supplier",
            document_reference="INV-JAR-1",
            supplier_lot="JAR-LOT-1",
        ),
    )
    assert receipt.review_state == "reviewed"
    assert receipt.unit_cost_amount == "1.200000"

    writeoff = inventory_service.create_material_adjustment(
        material.id,
        MaterialAdjustmentRequest(
            movement_type="write_off",
            quantity_delta=-2,
            reason="Two jars cracked during unpacking",
        ),
    )
    assert writeoff.quantity_delta == -2

    correction = inventory_service.create_material_adjustment(
        material.id,
        MaterialAdjustmentRequest(
            movement_type="stock_count_correction",
            quantity_delta=-1,
            reason="Month-end count variance",
        ),
    )
    assert correction.movement_type == "stock_count_correction"

    detail = inventory_service.get_material(material.id)
    assert detail.on_hand_quantity == 97
    assert detail.open_exception_count == 0

    with pytest.raises(ValueError):
        MaterialAdjustmentRequest(
            movement_type="spoilage",
            quantity_delta=1,
            reason="wrong sign",
        )


def test_lot_expiry_diagnostics(inventory_db):
    material = inventory_service.create_material(
        MaterialCreateRequest(
            sku="OIL-ORANGE",
            name="Orange oil",
            category="fragrance",
            stock_uom="ml",
            lot_tracked=True,
            expiry_tracked=True,
        )
    )
    inventory_service.create_material_receipt(
        material.id,
        MaterialReceiptRequest(
            quantity=100,
            uom="ml",
            unit_cost_amount="0.05",
            supplier_lot="OIL-1",
            expiry_date="2026-09-10",
        ),
    )

    lots = inventory_service.list_material_lots(
        material.id,
        production_date="2026-09-12",
    )
    assert lots.lots[0].lot_status == "expired"

    near = inventory_service.list_material_lots(
        material.id,
        production_date="2026-09-01",
        near_expiry_days=14,
    )
    assert near.lots[0].lot_status == "near_expiry"
