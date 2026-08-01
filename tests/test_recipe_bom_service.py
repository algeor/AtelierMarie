"""Recipe/BOM service tests."""

import sqlite3

import pytest

from app.database import init_db
from app.models.inventory import (
    MaterialCreateRequest,
    MaterialReceiptRequest,
    MaterialUpdateRequest,
    RecipeComponentRequest,
    RecipeCostSnapshotRequest,
    RecipeReviewRequest,
    RecipeVersionCreateRequest,
)
from app.services import inventory_service
from app.services.inventory_service import InventoryValidationError


@pytest.fixture()
def recipe_db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "recipe.db")
    init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock) VALUES ('prod-candle', 'Candle', 2500, 0)"
    )
    conn.commit()
    yield conn
    conn.close()


def _material_with_cost(
    *,
    sku: str,
    name: str,
    category: str,
    stock_uom: str,
    quantity: float,
    total_cost_cents: int,
) -> str:
    material = inventory_service.create_material(
        MaterialCreateRequest(
            sku=sku,
            name=name,
            category=category,
            stock_uom=stock_uom,
        )
    )
    inventory_service.create_material_receipt(
        material.id,
        MaterialReceiptRequest(
            quantity=quantity,
            uom=stock_uom,
            total_cost_cents=total_cost_cents,
            supplier_lot=f"{sku}-LOT",
            document_reference=f"{sku}-INV",
        ),
    )
    return material.id


def test_recipe_lifecycle_active_lookup_and_conflict_archiving(recipe_db):
    wax_id = _material_with_cost(
        sku="WAX-RECIPE",
        name="Recipe wax",
        category="wax",
        stock_uom="g",
        quantity=1000,
        total_cost_cents=1000,
    )

    first = inventory_service.create_recipe_version(
        RecipeVersionCreateRequest(
            product_id="prod-candle",
            version_label="v1",
            effective_date="2026-09-01",
            output_quantity=2,
            components=[
                RecipeComponentRequest(material_id=wax_id, quantity=100, uom="g"),
            ],
        ),
        actor_user_id="admin-1",
    )
    active_first = inventory_service.activate_recipe_version(first.id)
    assert active_first.status == "active"

    second = inventory_service.create_recipe_version(
        RecipeVersionCreateRequest(
            product_id="prod-candle",
            version_label="v2",
            effective_date="2026-10-01",
            output_quantity=2,
            components=[
                RecipeComponentRequest(material_id=wax_id, quantity=120, uom="g"),
            ],
        )
    )
    inventory_service.activate_recipe_version(second.id)

    assert inventory_service.get_recipe_version(first.id).status == "archived"
    active = inventory_service.get_active_recipe_for_product(
        "prod-candle",
        as_of_date="2026-10-15",
    )
    assert active.id == second.id


def test_recipe_cost_snapshot_review_and_diagnostics(recipe_db):
    wax_id = _material_with_cost(
        sku="WAX-COST",
        name="Cost wax",
        category="wax",
        stock_uom="g",
        quantity=1000,
        total_cost_cents=1000,
    )
    jar_id = _material_with_cost(
        sku="JAR-COST",
        name="Cost jar",
        category="packaging",
        stock_uom="piece",
        quantity=10,
        total_cost_cents=1000,
    )

    recipe = inventory_service.create_recipe_version(
        RecipeVersionCreateRequest(
            product_id="prod-candle",
            version_label="costed",
            effective_date="2026-09-01",
            output_quantity=2,
            components=[
                RecipeComponentRequest(material_id=wax_id, quantity=100, uom="g"),
                RecipeComponentRequest(material_id=jar_id, quantity=2, uom="piece"),
            ],
        )
    )
    reviewed = inventory_service.review_recipe_version(
        recipe.id,
        RecipeReviewRequest(review_state="accountant_reviewed", review_note="Reviewed"),
        actor_user_id="admin-1",
    )
    assert reviewed.accountant_reviewed is True

    snapshot = inventory_service.create_recipe_cost_snapshot(
        recipe.id,
        RecipeCostSnapshotRequest(),
    )
    assert snapshot.material_cost_cents == 100
    assert snapshot.packaging_cost_cents == 200
    assert snapshot.batch_cost_cents == 300
    assert snapshot.expected_unit_cost_cents == 150
    assert snapshot.review_state == "accountant_reviewed"

    diagnostics = inventory_service.recipe_diagnostics(recipe.id).diagnostics
    assert diagnostics == []

    inventory_service.update_material(wax_id, MaterialUpdateRequest(active=False))
    inactive_diagnostics = inventory_service.recipe_diagnostics(recipe.id).diagnostics
    assert "inactive_material" in {item.code for item in inactive_diagnostics}


def test_recipe_validation_and_missing_cost_diagnostics(recipe_db):
    material = inventory_service.create_material(
        MaterialCreateRequest(
            sku="NO-COST",
            name="No cost material",
            category="wax",
            stock_uom="g",
        )
    )
    recipe = inventory_service.create_recipe_version(
        RecipeVersionCreateRequest(
            product_id="prod-candle",
            version_label="needs-cost",
            effective_date="2026-09-01",
            output_quantity=1,
            components=[
                RecipeComponentRequest(
                    material_id=material.id,
                    quantity=10,
                    uom="g",
                    wastage_percent=30,
                ),
            ],
        )
    )

    diagnostics = inventory_service.recipe_diagnostics(recipe.id).diagnostics
    assert {item.code for item in diagnostics} == {
        "missing_material_cost",
        "excessive_wastage",
    }

    with pytest.raises(InventoryValidationError):
        inventory_service.create_recipe_version(
            RecipeVersionCreateRequest(
                product_id="prod-candle",
                version_label="bad-uom",
                effective_date="2026-09-01",
                output_quantity=1,
                components=[
                    RecipeComponentRequest(material_id=material.id, quantity=1, uom="kg"),
                ],
            )
        )


def test_product_missing_recipe_diagnostic(recipe_db):
    diagnostics = inventory_service.product_recipe_diagnostics("prod-candle").diagnostics

    assert diagnostics[0].code == "missing_active_recipe"
