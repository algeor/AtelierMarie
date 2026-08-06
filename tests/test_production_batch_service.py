"""Production batch service tests."""

import pytest

from app.models.inventory import (
    MaterialCreateRequest,
    MaterialReceiptRequest,
    ProductionBatchActualConsumptionRequest,
    ProductionBatchCorrectionRequest,
    ProductionBatchCreateRequest,
    ProductionBatchPostRequest,
    RecipeComponentRequest,
    RecipeVersionCreateRequest,
)
from app.services import inventory_service


@pytest.fixture()
def batch_db(db):
    db.execute(
        "INSERT INTO products (id, name_en, price_cents, stock) "
        "VALUES ('prod-batch', 'Batch Candle', 2500, 0)"
    )
    db.commit()
    return db


def _material(
    sku: str, name: str, category: str, stock_uom: str, quantity: float, cost: int
) -> str:
    material = inventory_service.create_material(
        MaterialCreateRequest(sku=sku, name=name, category=category, stock_uom=stock_uom)
    )
    inventory_service.create_material_receipt(
        material.id,
        MaterialReceiptRequest(
            quantity=quantity,
            uom=stock_uom,
            total_cost_cents=cost,
            supplier_lot=f"{sku}-LOT",
            document_reference=f"{sku}-INV",
        ),
    )
    return material.id


def _active_recipe(wax_id: str, wick_id: str) -> str:
    recipe = inventory_service.create_recipe_version(
        RecipeVersionCreateRequest(
            product_id="prod-batch",
            version_label="batch-v1",
            effective_date="2026-09-01",
            output_quantity=10,
            components=[
                RecipeComponentRequest(material_id=wax_id, quantity=100, uom="g"),
                RecipeComponentRequest(
                    material_id=wick_id,
                    quantity=1,
                    uom="piece",
                    quantity_basis="per_unit",
                ),
            ],
        )
    )
    return inventory_service.activate_recipe_version(recipe.id).id


def test_batch_create_post_correct_and_traceability(batch_db):
    wax_id = _material("BATCH-WAX", "Batch wax", "wax", "g", 1000, 1000)
    wick_id = _material("BATCH-WICK", "Batch wick", "wick", "piece", 100, 500)
    recipe_id = _active_recipe(wax_id, wick_id)

    batch = inventory_service.create_production_batch(
        ProductionBatchCreateRequest(
            batch_number="B-001",
            product_id="prod-batch",
            recipe_version_id=recipe_id,
            planned_output_quantity=10,
            production_date="2026-09-05",
        )
    )
    assert batch.status == "draft"
    assert {line.material_id: line.expected_quantity for line in batch.consumption} == {
        wax_id: 100,
        wick_id: 10,
    }

    consumption_by_material = {line.material_id: line for line in batch.consumption}
    posted = inventory_service.post_production_batch(
        batch.id,
        ProductionBatchPostRequest(
            actual_output_quantity=9,
            variance_tolerance_percent=10,
            actual_consumption=[
                ProductionBatchActualConsumptionRequest(
                    batch_consumption_id=consumption_by_material[wax_id].id,
                    material_id=wax_id,
                    actual_quantity=120,
                ),
                ProductionBatchActualConsumptionRequest(
                    batch_consumption_id=consumption_by_material[wick_id].id,
                    material_id=wick_id,
                    actual_quantity=10,
                ),
            ],
        ),
    )

    assert posted.status == "produced"
    assert posted.actual_output_quantity == 9
    assert posted.outputs[0].quantity == 9
    assert posted.outputs[0].unit_cost_amount == "0.188889"
    assert {item.exception_type for item in posted.exceptions} == {
        "material_usage_variance",
        "produced_quantity_variance",
    }
    product_stock = batch_db.execute(
        "SELECT stock FROM products WHERE id = 'prod-batch'"
    ).fetchone()["stock"]
    assert product_stock == 9
    wax_on_hand = inventory_service.get_material(wax_id).on_hand_quantity
    assert wax_on_hand == 880

    correction = inventory_service.correct_production_batch(
        batch.id,
        ProductionBatchCorrectionRequest(
            item_type="finished_good",
            item_id="prod-batch",
            quantity_delta=-1,
            uom="unit",
            reason="One candle failed curing inspection",
        ),
    )
    assert correction.quantity_delta == -1
    assert (
        batch_db.execute("SELECT stock FROM products WHERE id = 'prod-batch'").fetchone()["stock"]
        == 8
    )

    trace = inventory_service.production_traceability(batch.id)
    assert len(trace.source_movements) == 2
    assert len(trace.finished_movements) == 1


def test_draft_batch_can_be_cancelled(batch_db):
    wax_id = _material("BATCH-WAX-2", "Batch wax", "wax", "g", 1000, 1000)
    wick_id = _material("BATCH-WICK-2", "Batch wick", "wick", "piece", 100, 500)
    recipe_id = _active_recipe(wax_id, wick_id)
    batch = inventory_service.create_production_batch(
        ProductionBatchCreateRequest(
            batch_number="B-002",
            product_id="prod-batch",
            recipe_version_id=recipe_id,
            planned_output_quantity=10,
            production_date="2026-09-05",
        )
    )

    cancelled = inventory_service.cancel_production_batch(batch.id)

    assert cancelled.status == "cancelled"


def test_batch_post_records_insufficient_material_exception(batch_db):
    wax_id = _material("BATCH-WAX-3", "Batch wax", "wax", "g", 50, 500)
    wick_id = _material("BATCH-WICK-3", "Batch wick", "wick", "piece", 100, 500)
    recipe_id = _active_recipe(wax_id, wick_id)
    batch = inventory_service.create_production_batch(
        ProductionBatchCreateRequest(
            batch_number="B-003",
            product_id="prod-batch",
            recipe_version_id=recipe_id,
            planned_output_quantity=10,
            production_date="2026-09-05",
        )
    )

    result = inventory_service.post_production_batch(
        batch.id,
        ProductionBatchPostRequest(actual_output_quantity=10),
    )

    assert result.status == "draft"
    assert result.exceptions[0].exception_type == "insufficient_materials"
    assert (
        batch_db.execute("SELECT stock FROM products WHERE id = 'prod-batch'").fetchone()["stock"]
        == 0
    )


def test_posted_batch_decrements_lot_and_values_finished_output(batch_db):
    material = inventory_service.create_material(
        MaterialCreateRequest(
            sku="BATCH-LOT-WAX",
            name="Lot wax",
            category="wax",
            stock_uom="g",
            lot_tracked=True,
        )
    )
    receipt = inventory_service.create_material_receipt(
        material.id,
        MaterialReceiptRequest(
            quantity=200,
            uom="g",
            total_cost_cents=2000,
            supplier_lot="LOT-WAX-1",
            document_reference="LOT-INV",
        ),
    )
    recipe = inventory_service.create_recipe_version(
        RecipeVersionCreateRequest(
            product_id="prod-batch",
            version_label="lot-v1",
            effective_date="2026-09-01",
            output_quantity=10,
            components=[RecipeComponentRequest(material_id=material.id, quantity=100, uom="g")],
        )
    )
    active_recipe_id = inventory_service.activate_recipe_version(recipe.id).id
    batch = inventory_service.create_production_batch(
        ProductionBatchCreateRequest(
            batch_number="B-LOT-001",
            product_id="prod-batch",
            recipe_version_id=active_recipe_id,
            planned_output_quantity=10,
            production_date="2026-09-05",
        )
    )

    posted = inventory_service.post_production_batch(
        batch.id,
        ProductionBatchPostRequest(
            actual_output_quantity=10,
            actual_consumption=[
                ProductionBatchActualConsumptionRequest(
                    batch_consumption_id=batch.consumption[0].id,
                    material_id=material.id,
                    material_lot_id=receipt.lot_id,
                    actual_quantity=100,
                )
            ],
        ),
    )

    assert posted.outputs[0].unit_cost_amount == "1.000000"
    remaining = batch_db.execute(
        "SELECT remaining_quantity_snapshot FROM material_lots WHERE id = %s",
        (receipt.lot_id,),
    ).fetchone()["remaining_quantity_snapshot"]
    assert remaining == 100

    layers = inventory_service.generate_valuation_layers()
    output_layers = [
        layer
        for layer in layers.layers
        if layer.item_type == "finished_good" and layer.item_id == "prod-batch"
    ]
    assert output_layers[0].total_value_cents == 1000


def test_batch_post_rejects_lot_for_different_material(batch_db):
    wax_id = _material("BATCH-WAX-LOT-MISMATCH", "Batch wax", "wax", "g", 1000, 1000)
    wick = inventory_service.create_material(
        MaterialCreateRequest(
            sku="BATCH-WICK-LOT-MISMATCH", name="Batch wick", category="wick", stock_uom="piece"
        )
    )
    wick_receipt = inventory_service.create_material_receipt(
        wick.id,
        MaterialReceiptRequest(
            quantity=100, uom="piece", total_cost_cents=500, supplier_lot="WICK-LOT"
        ),
    )
    recipe = inventory_service.create_recipe_version(
        RecipeVersionCreateRequest(
            product_id="prod-batch",
            version_label="lot-mismatch-v1",
            effective_date="2026-09-01",
            output_quantity=10,
            components=[RecipeComponentRequest(material_id=wax_id, quantity=100, uom="g")],
        )
    )
    batch = inventory_service.create_production_batch(
        ProductionBatchCreateRequest(
            batch_number="B-LOT-MISMATCH",
            product_id="prod-batch",
            recipe_version_id=inventory_service.activate_recipe_version(recipe.id).id,
            planned_output_quantity=10,
            production_date="2026-09-05",
        )
    )

    with pytest.raises(inventory_service.InventoryValidationError):
        inventory_service.post_production_batch(
            batch.id,
            ProductionBatchPostRequest(
                actual_output_quantity=10,
                actual_consumption=[
                    ProductionBatchActualConsumptionRequest(
                        batch_consumption_id=batch.consumption[0].id,
                        material_id=wax_id,
                        material_lot_id=wick_receipt.lot_id,
                        actual_quantity=100,
                    )
                ],
            ),
        )
