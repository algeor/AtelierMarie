"""Inventory valuation and COGS service tests."""

import sqlite3

import pytest

from app.database import init_db
from app.models.inventory import (
    InventoryValuationSettingsRequest,
    MaterialAdjustmentRequest,
    MaterialCreateRequest,
    MaterialReceiptRequest,
    OpeningBalanceRequest,
)
from app.services import inventory_service


@pytest.fixture()
def valuation_db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "valuation.db")
    init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock) VALUES ('prod-value', 'Value Candle', 2500, 10)"
    )
    conn.commit()
    yield conn
    conn.close()


def test_valuation_settings_review_and_fifo_warning(valuation_db):
    settings = inventory_service.get_inventory_valuation_settings()
    assert settings.valuation_enabled is False
    assert settings.valuation_method == "weighted_average"

    updated = inventory_service.update_inventory_valuation_settings(
        InventoryValuationSettingsRequest(
            ledger_mode="setup",
            valuation_enabled=True,
            valuation_method="fifo",
            effective_date="2026-09-01",
            accountant_reviewed=True,
            reviewed_by_name="Accountant",
        ),
        actor_user_id="admin-1",
    )

    assert updated.settings_version == settings.settings_version + 1
    assert updated.accountant_reviewed is True
    exceptions = inventory_service.valuation_exceptions()
    assert "fifo_requires_lot_discipline" in {item["exception_type"] for item in exceptions}
    settings_exceptions = inventory_service.valuation_exceptions(
        target_type="inventory_settings",
        target_id="default",
    )
    assert {item["target_id"] for item in settings_exceptions} == {"default"}


def test_opening_balance_and_weighted_average_layers(valuation_db):
    inventory_service.update_inventory_valuation_settings(
        InventoryValuationSettingsRequest(
            ledger_mode="setup",
            valuation_enabled=True,
            valuation_method="weighted_average",
            effective_date="2026-09-01",
            accountant_reviewed=True,
        )
    )
    material = inventory_service.create_material(
        MaterialCreateRequest(sku="VAL-WAX", name="Valuation wax", category="wax", stock_uom="g")
    )
    inventory_service.create_material_receipt(
        material.id,
        MaterialReceiptRequest(
            quantity=1000,
            uom="g",
            total_cost_cents=1000,
            document_reference="VAL-INV",
        ),
    )
    inventory_service.create_material_adjustment(
        material.id,
        MaterialAdjustmentRequest(
            movement_type="write_off",
            quantity_delta=-100,
            reason="Spoiled wax sample",
        ),
    )

    generated = inventory_service.generate_valuation_layers()

    assert generated.total == 2
    assert [layer.total_value_cents for layer in generated.layers] == [1000, 100]
    assert generated.layers[0].review_state == "official"

    opening = inventory_service.record_opening_balance(
        OpeningBalanceRequest(
            item_type="finished_good",
            item_id="prod-value",
            quantity=10,
            uom="unit",
            unit_value_amount="2.00",
            reviewed=True,
        )
    )
    assert opening is not None
    assert opening.total_value_cents == 2000
    profile = valuation_db.execute(
        "SELECT opening_balance_state FROM product_inventory_profiles WHERE product_id = 'prod-value'"
    ).fetchone()
    assert profile[0] == "reviewed"


def test_cogs_generation_and_close_preview(valuation_db):
    inventory_service.update_inventory_valuation_settings(
        InventoryValuationSettingsRequest(
            ledger_mode="setup",
            valuation_enabled=True,
            valuation_method="weighted_average",
            effective_date="2026-09-01",
            accountant_reviewed=True,
        )
    )
    inventory_service.record_opening_balance(
        OpeningBalanceRequest(
            item_type="finished_good",
            item_id="prod-value",
            quantity=10,
            uom="unit",
            unit_value_amount="2.00",
            reviewed=True,
        )
    )
    valuation_db.execute(
        """
        INSERT INTO orders (id, session_id, total_cents, customer_email, order_number)
        VALUES ('order-value', 'session-value', 2500, 'buyer@example.com', 'AM-1')
        """
    )
    valuation_db.execute(
        """
        INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
        VALUES ('order-value', 'prod-value', 'Value Candle', 2500, 2)
        """
    )
    valuation_db.commit()

    cogs = inventory_service.generate_cogs_rows()

    assert cogs.total == 1
    assert cogs.rows[0].unit_cost_amount == "2.000000"
    assert cogs.rows[0].total_cost_cents == 400
    assert cogs.rows[0].review_state == "official"
    assert inventory_service.list_cogs_rows(product_id="prod-value").total == 1
    assert inventory_service.list_cogs_rows(order_id="order-value").total == 1
    assert inventory_service.list_cogs_rows(product_id="other-product").total == 0

    preview = inventory_service.inventory_close_preview("2000-01-01", "2999-12-31")
    assert preview.opening_value_cents == 2000
    assert preview.official is True


@pytest.mark.asyncio
async def test_valuation_admin_routes_no_store(admin_client):
    settings = await admin_client.get("/v1/admin/inventory/valuation/settings")
    assert settings.status_code == 200
    assert settings.headers["cache-control"] == "no-store, no-cache"

    update = await admin_client.put(
        "/v1/admin/inventory/valuation/settings",
        json={
            "ledger_mode": "setup",
            "valuation_enabled": True,
            "valuation_method": "weighted_average",
            "effective_date": "2026-09-01",
            "accountant_reviewed": True,
        },
    )
    assert update.status_code == 200
    assert update.json()["valuation_enabled"] is True
