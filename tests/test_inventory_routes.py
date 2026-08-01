"""Admin inventory route tests."""

import pytest


@pytest.mark.asyncio
async def test_inventory_material_routes_require_admin(client):
    resp = await client.get("/v1/admin/inventory/materials")

    assert resp.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/v1/admin/inventory/materials", None),
        ("POST", "/v1/admin/inventory/materials", {"name": "Wax", "stock_uom": "g"}),
        ("GET", "/v1/admin/inventory/reorder", None),
        ("GET", "/v1/admin/inventory/movements", None),
        ("GET", "/v1/admin/inventory/materials/mat-1", None),
        ("PATCH", "/v1/admin/inventory/materials/mat-1", {"name": "Wax updated"}),
        ("POST", "/v1/admin/inventory/materials/mat-1/receipts", {"quantity": 1, "uom": "g"}),
        ("POST", "/v1/admin/inventory/materials/mat-1/adjustments", {"movement_type": "adjustment", "quantity_delta": 1, "reason": "count"}),
        ("GET", "/v1/admin/inventory/materials/mat-1/lots", None),
        ("GET", "/v1/admin/inventory/materials/mat-1/movements", None),
        ("GET", "/v1/admin/inventory/recipes", None),
        ("POST", "/v1/admin/inventory/recipes", {"product_id": "p-1", "version_label": "v1", "effective_date": "2026-09-01", "output_quantity": 1}),
        ("GET", "/v1/admin/inventory/recipes/recipe-1", None),
        ("PATCH", "/v1/admin/inventory/recipes/recipe-1", {"version_label": "v2"}),
        ("POST", "/v1/admin/inventory/recipes/recipe-1/activate", {}),
        ("POST", "/v1/admin/inventory/recipes/recipe-1/archive", {}),
        ("POST", "/v1/admin/inventory/recipes/recipe-1/cost-snapshots", {}),
        ("POST", "/v1/admin/inventory/recipes/recipe-1/review", {"review_state": "reviewed"}),
        ("GET", "/v1/admin/inventory/recipes/recipe-1/diagnostics", None),
        ("GET", "/v1/admin/inventory/products/product-1/active-recipe", None),
        ("GET", "/v1/admin/inventory/products/product-1/recipe-diagnostics", None),
        ("GET", "/v1/admin/inventory/batches", None),
        ("POST", "/v1/admin/inventory/batches", {"batch_number": "B-1", "product_id": "p-1", "planned_output_quantity": 1, "production_date": "2026-09-01"}),
        ("GET", "/v1/admin/inventory/batches/batch-1", None),
        ("PATCH", "/v1/admin/inventory/batches/batch-1", {"planned_output_quantity": 2}),
        ("POST", "/v1/admin/inventory/batches/batch-1/post", {"actual_output_quantity": 1}),
        ("POST", "/v1/admin/inventory/batches/batch-1/cancel", {}),
        ("POST", "/v1/admin/inventory/batches/batch-1/correct", {"item_type": "material", "item_id": "mat-1", "quantity_delta": -1, "uom": "g", "reason": "count"}),
        ("GET", "/v1/admin/inventory/batches/batch-1/traceability", None),
        ("GET", "/v1/admin/inventory/valuation/settings", None),
        ("PUT", "/v1/admin/inventory/valuation/settings", {"effective_date": "2026-09-01"}),
        ("POST", "/v1/admin/inventory/valuation/opening-balances", {"item_type": "material", "item_id": "mat-1", "quantity": 1, "uom": "g"}),
        ("POST", "/v1/admin/inventory/valuation/layers/generate", {}),
        ("GET", "/v1/admin/inventory/valuation/layers", None),
        ("POST", "/v1/admin/inventory/valuation/cogs/generate", {}),
        ("GET", "/v1/admin/inventory/valuation/cogs", None),
        ("GET", "/v1/admin/inventory/valuation/close-preview?period_start=2026-09-01&period_end=2026-09-30", None),
        ("GET", "/v1/admin/inventory/valuation/exceptions", None),
    ],
)
async def test_inventory_recipe_production_valuation_and_cogs_endpoints_require_admin(
    client, method, path, payload
):
    resp = await client.request(method, path, json=payload) if payload is not None else await client.request(method, path)

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_inventory_material_admin_workflow_no_store(admin_client):
    create_resp = await admin_client.post(
        "/v1/admin/inventory/materials",
        json={
            "sku": "WAX-API",
            "name": "API soy wax",
            "category": "wax",
            "stock_uom": "g",
            "purchase_uom": "kg",
            "purchase_to_stock_factor": 1000,
            "reorder_threshold": 250,
            "lot_tracked": True,
            "expiry_tracked": False,
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.headers["cache-control"] == "no-store, no-cache"
    material = create_resp.json()

    receipt_resp = await admin_client.post(
        f"/v1/admin/inventory/materials/{material['id']}/receipts",
        json={
            "quantity": 1,
            "uom": "kg",
            "total_cost_cents": 900,
            "supplier_name": "Wax Supplier",
            "supplier_lot": "API-LOT-1",
            "document_reference": "INV-API-1",
        },
    )
    assert receipt_resp.status_code == 201
    assert receipt_resp.headers["cache-control"] == "no-store, no-cache"
    assert receipt_resp.json()["stock_quantity"] == 1000

    list_resp = await admin_client.get("/v1/admin/inventory/materials")
    assert list_resp.status_code == 200
    assert list_resp.headers["cache-control"] == "no-store, no-cache"
    listed = list_resp.json()["materials"]
    assert listed[0]["on_hand_quantity"] == 1000

    writeoff_resp = await admin_client.post(
        f"/v1/admin/inventory/materials/{material['id']}/adjustments",
        json={
            "movement_type": "write_off",
            "quantity_delta": -50,
            "reason": "Test write-off",
        },
    )
    assert writeoff_resp.status_code == 201
    assert writeoff_resp.json()["movement_type"] == "write_off"

    detail_resp = await admin_client.get(f"/v1/admin/inventory/materials/{material['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["on_hand_quantity"] == 950

    lots_resp = await admin_client.get(
        f"/v1/admin/inventory/materials/{material['id']}/lots?production_date=2026-09-01"
    )
    assert lots_resp.status_code == 200
    assert lots_resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_inventory_material_validation_errors(admin_client):
    resp = await admin_client.post(
        "/v1/admin/inventory/materials",
        json={
            "sku": "BAD-UOM",
            "name": "Bad material",
            "category": "wax",
            "stock_uom": "g",
            "purchase_uom": "kg",
        },
    )

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_INVENTORY"


@pytest.mark.asyncio
async def test_recipe_admin_workflow_and_product_inventory_context(admin_client):
    product_resp = await admin_client.post(
        "/v1/admin/products",
        json={
            "id": "api-recipe-product",
            "name_en": "API Recipe Candle",
            "price_cents": 2500,
            "stock": 0,
        },
    )
    assert product_resp.status_code == 201

    material_resp = await admin_client.post(
        "/v1/admin/inventory/materials",
        json={
            "sku": "API-WICK",
            "name": "API wick",
            "category": "wick",
            "stock_uom": "piece",
        },
    )
    assert material_resp.status_code == 201
    material_id = material_resp.json()["id"]

    await admin_client.post(
        f"/v1/admin/inventory/materials/{material_id}/receipts",
        json={
            "quantity": 100,
            "uom": "piece",
            "total_cost_cents": 500,
            "supplier_lot": "WICK-LOT",
            "document_reference": "WICK-INV",
        },
    )

    recipe_resp = await admin_client.post(
        "/v1/admin/inventory/recipes",
        json={
            "product_id": "api-recipe-product",
            "version_label": "v1",
            "effective_date": "2026-09-01",
            "output_quantity": 10,
            "components": [
                {
                    "material_id": material_id,
                    "quantity": 10,
                    "uom": "piece",
                    "quantity_basis": "per_batch",
                }
            ],
        },
    )
    assert recipe_resp.status_code == 201
    assert recipe_resp.headers["cache-control"] == "no-store, no-cache"
    recipe_id = recipe_resp.json()["id"]

    activate_resp = await admin_client.post(f"/v1/admin/inventory/recipes/{recipe_id}/activate")
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "active"

    snapshot_resp = await admin_client.post(
        f"/v1/admin/inventory/recipes/{recipe_id}/cost-snapshots",
        json={},
    )
    assert snapshot_resp.status_code == 201
    assert snapshot_resp.json()["expected_unit_cost_cents"] == 5

    active_resp = await admin_client.get(
        "/v1/admin/inventory/products/api-recipe-product/active-recipe?as_of_date=2026-09-02"
    )
    assert active_resp.status_code == 200
    assert active_resp.json()["id"] == recipe_id

    product_detail = await admin_client.get("/v1/admin/products/api-recipe-product")
    assert product_detail.status_code == 200
    body = product_detail.json()
    assert body["active_recipe_id"] == recipe_id
    assert body["active_recipe_status"] == "active"


@pytest.mark.asyncio
async def test_production_batch_admin_workflow(admin_client):
    product_resp = await admin_client.post(
        "/v1/admin/products",
        json={
            "id": "api-batch-product",
            "name_en": "API Batch Candle",
            "price_cents": 3000,
            "stock": 0,
        },
    )
    assert product_resp.status_code == 201

    material_resp = await admin_client.post(
        "/v1/admin/inventory/materials",
        json={
            "sku": "API-BATCH-WAX",
            "name": "API batch wax",
            "category": "wax",
            "stock_uom": "g",
        },
    )
    material_id = material_resp.json()["id"]
    await admin_client.post(
        f"/v1/admin/inventory/materials/{material_id}/receipts",
        json={
            "quantity": 1000,
            "uom": "g",
            "total_cost_cents": 1000,
            "document_reference": "WAX-BATCH-INV",
        },
    )
    recipe_resp = await admin_client.post(
        "/v1/admin/inventory/recipes",
        json={
            "product_id": "api-batch-product",
            "version_label": "batch-v1",
            "effective_date": "2026-09-01",
            "output_quantity": 10,
            "components": [{"material_id": material_id, "quantity": 100, "uom": "g"}],
        },
    )
    recipe_id = recipe_resp.json()["id"]
    await admin_client.post(f"/v1/admin/inventory/recipes/{recipe_id}/activate")

    batch_resp = await admin_client.post(
        "/v1/admin/inventory/batches",
        json={
            "batch_number": "API-B-001",
            "product_id": "api-batch-product",
            "recipe_version_id": recipe_id,
            "planned_output_quantity": 10,
            "production_date": "2026-09-05",
        },
    )
    assert batch_resp.status_code == 201
    assert batch_resp.headers["cache-control"] == "no-store, no-cache"
    batch = batch_resp.json()

    post_resp = await admin_client.post(
        f"/v1/admin/inventory/batches/{batch['id']}/post",
        json={"actual_output_quantity": 10},
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["status"] == "produced"

    trace_resp = await admin_client.get(f"/v1/admin/inventory/batches/{batch['id']}/traceability")
    assert trace_resp.status_code == 200
    assert len(trace_resp.json()["source_movements"]) == 1

    product_detail = await admin_client.get("/v1/admin/products/api-batch-product")
    assert product_detail.json()["latest_batch_number"] == "API-B-001"
    assert product_detail.json()["stock"] == 10
