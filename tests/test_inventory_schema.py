"""Schema coverage for inventory, recipe/BOM, production, valuation, and COGS tables."""

import psycopg
import pytest

from app.database import IntegrityError


def _table_names(conn: psycopg.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT tablename AS name FROM pg_tables WHERE schemaname = 'public'"
    ).fetchall()
    return {row["name"] for row in rows}


def _index_names(conn: psycopg.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT indexname AS name FROM pg_indexes WHERE schemaname = 'public'"
    ).fetchall()
    return {row["name"] for row in rows}


def test_inventory_schema_tables_exist(db: psycopg.Connection):
    expected_tables = {
        "inventory_settings",
        "product_inventory_profiles",
        "materials",
        "material_receipts",
        "material_lots",
        "inventory_movements",
        "recipe_versions",
        "recipe_components",
        "recipe_cost_snapshots",
        "production_batches",
        "production_batch_consumption",
        "production_batch_outputs",
        "inventory_valuation_layers",
        "cogs_ledger",
        "inventory_closes",
        "stock_counts",
        "stock_count_lines",
        "inventory_exceptions",
    }

    assert expected_tables <= _table_names(db)


def test_inventory_settings_bootstrap_is_disabled_by_default(db: psycopg.Connection):
    row = db.execute(
        """
        SELECT ledger_mode, valuation_enabled, valuation_method, cogs_date_basis,
               missing_cost_behavior, accountant_reviewed
        FROM inventory_settings
        WHERE id = 'default'
        """
    ).fetchone()

    assert dict(row) == {
        "ledger_mode": "setup",
        "valuation_enabled": 0,
        "valuation_method": "weighted_average",
        "cogs_date_basis": "order_date",
        "missing_cost_behavior": "block_official",
        "accountant_reviewed": 0,
    }
    # Alembic's ``alembic_version`` proves the initial migration ran and seeded
    # the default settings row above.
    marker = db.execute("SELECT 1 FROM alembic_version WHERE version_num IS NOT NULL").fetchone()
    assert marker is not None


def test_material_receipt_and_movement_constraints(db: psycopg.Connection):
    db.execute(
        """
        INSERT INTO materials (
            id, sku, name, category, stock_uom, purchase_uom,
            purchase_to_stock_factor, reorder_threshold, lot_tracked, expiry_tracked
        ) VALUES ('mat-wax', 'WAX-SOY', 'Soy wax', 'wax', 'g', 'kg', 1000, 500, 1, 0)
        """
    )
    db.execute(
        """
        INSERT INTO material_receipts (
            id, material_id, quantity, uom, stock_quantity, stock_uom,
            unit_cost_amount, total_cost_cents, supplier_name, supplier_lot,
            document_reference, review_state
        ) VALUES (
            'receipt-wax-1', 'mat-wax', 5, 'kg', 5000, 'g',
            '0.0120', 6000, 'Wax Supplier', 'LOT-1', 'INV-1', 'reviewed'
        )
        """
    )
    db.execute(
        """
        INSERT INTO material_lots (
            id, material_id, receipt_id, supplier_lot, received_quantity,
            stock_uom, remaining_quantity_snapshot, unit_cost_amount, supplier_name,
            review_state
        ) VALUES (
            'lot-wax-1', 'mat-wax', 'receipt-wax-1', 'LOT-1', 5000,
            'g', 5000, '0.0120', 'Wax Supplier', 'reviewed'
        )
        """
    )
    db.execute(
        """
        INSERT INTO inventory_movements (
            id, item_type, item_id, movement_type, quantity_delta, uom,
            source_type, source_id, material_lot_id, actor_user_id, review_state
        ) VALUES (
            'move-receipt-1', 'material', 'mat-wax', 'receipt', 5000, 'g',
            'material_receipt', 'receipt-wax-1', 'lot-wax-1', 'admin-1', 'reviewed'
        )
        """
    )
    db.commit()

    on_hand = db.execute(
        "SELECT SUM(quantity_delta) AS total FROM inventory_movements WHERE item_id = 'mat-wax'"
    ).fetchone()["total"]
    assert on_hand == 5000

    with pytest.raises(IntegrityError):
        db.execute(
            """
            INSERT INTO inventory_movements (id, item_type, item_id, movement_type,
                                             quantity_delta, uom)
            VALUES ('bad-movement', 'material', 'mat-wax', 'silent_edit', 1, 'g')
            """
        )
    db.rollback()


def test_recipe_batch_valuation_and_cogs_tables_accept_linked_rows(db: psycopg.Connection):
    db.execute(
        "INSERT INTO products (id, name_en, price_cents, stock) "
        "VALUES ('prod-candle', 'Candle', 2500, 0)"
    )
    db.execute(
        "INSERT INTO materials (id, sku, name, category, stock_uom) "
        "VALUES ('mat-wick', 'WICK', 'Wick', 'wick', 'piece')"
    )
    db.execute(
        """
        INSERT INTO recipe_versions (
            id, product_id, version_label, status, effective_date,
            output_quantity, output_uom, review_state
        ) VALUES ('recipe-1', 'prod-candle', 'v1', 'active', '2026-09-01', 24, 'unit', 'reviewed')
        """
    )
    db.execute(
        """
        INSERT INTO recipe_components (
            id, recipe_version_id, material_id, quantity, uom,
            quantity_basis, wastage_percent, required, sort_order
        ) VALUES ('component-1', 'recipe-1', 'mat-wick', 24, 'piece', 'per_batch', 0, 1, 1)
        """
    )
    db.execute(
        """
        INSERT INTO recipe_cost_snapshots (
            id, recipe_version_id, material_cost_cents, packaging_cost_cents,
            batch_cost_cents, expected_unit_cost_cents, review_state
        ) VALUES ('cost-1', 'recipe-1', 240, 0, 240, 10, 'reviewed')
        """
    )
    db.execute(
        """
        INSERT INTO production_batches (
            id, batch_number, product_id, recipe_version_id, planned_output_quantity,
            actual_output_quantity, production_date, cost_snapshot_id, status
        ) VALUES ('batch-1', 'B-2026-001', 'prod-candle', 'recipe-1', 24, 24,
                  '2026-09-02', 'cost-1', 'produced')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_movements (
            id, item_type, item_id, movement_type, quantity_delta, uom,
            source_type, source_id, product_id, review_state
        ) VALUES ('move-output-1', 'finished_good', 'prod-candle', 'production_output', 24, 'unit',
                  'production_batch', 'batch-1', 'prod-candle', 'reviewed')
        """
    )
    db.execute(
        """
        INSERT INTO production_batch_consumption (
            id, production_batch_id, recipe_component_id, material_id,
            expected_quantity, actual_quantity, waste_quantity, uom, movement_id,
            review_state
        ) VALUES ('consume-1', 'batch-1', 'component-1', 'mat-wick', 24, 24, 0,
                  'piece', NULL, 'reviewed')
        """
    )
    db.execute(
        """
        INSERT INTO production_batch_outputs (
            id, production_batch_id, product_id, batch_number, quantity, uom,
            unit_cost_amount, movement_id, valuation_review_state
        ) VALUES ('output-1', 'batch-1', 'prod-candle', 'B-2026-001', 24, 'unit',
                  '0.10', 'move-output-1', 'reviewed')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_valuation_layers (
            id, movement_id, item_type, item_id, quantity, unit_value_amount,
            total_value_cents, valuation_method, source_type, source_id,
            valuation_date, review_state
        ) VALUES ('value-1', 'move-output-1', 'finished_good', 'prod-candle', 24, '0.10',
                  240, 'weighted_average', 'production_batch', 'batch-1', '2026-09-02', 'reviewed')
        """
    )
    db.execute(
        """
        INSERT INTO cogs_ledger (
            id, product_id, quantity_sold, cogs_date, unit_cost_amount,
            total_cost_cents, valuation_method, source_movement_id,
            source_valuation_layer_id, source_finished_batch_id, review_state
        ) VALUES ('cogs-1', 'prod-candle', 1, '2026-09-03', '0.10', 10,
                  'weighted_average', 'move-output-1', 'value-1', 'batch-1', 'reviewed')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_closes (
            id, period_start, period_end, valuation_method, ending_value_cents, status
        ) VALUES ('close-1', '2026-09-01', '2026-09-30', 'weighted_average', 230, 'draft')
        """
    )
    db.execute("INSERT INTO stock_counts (id, count_date) VALUES ('count-1', '2026-09-30')")
    db.execute(
        """
        INSERT INTO stock_count_lines (
            id, stock_count_id, item_type, item_id, counted_quantity, uom, review_state
        ) VALUES ('count-line-1', 'count-1', 'finished_good', 'prod-candle', 23, 'unit', 'draft')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_exceptions (
            id, exception_type, severity, target_type, target_id, message
        ) VALUES ('inv-ex-1', 'missing_opening_balance_review', 'blocking',
                  'product', 'prod-candle', 'Review opening value')
        """
    )
    db.commit()

    assert db.execute("SELECT COUNT(*) AS n FROM production_batches").fetchone()["n"] == 1
    assert db.execute("SELECT COUNT(*) AS n FROM cogs_ledger").fetchone()["n"] == 1
    assert db.execute("SELECT COUNT(*) AS n FROM inventory_exceptions").fetchone()["n"] == 1


def test_inventory_schema_indexes_exist(db: psycopg.Connection):
    expected_indexes = {
        "idx_inventory_movements_item_date",
        "idx_inventory_movements_source",
        "idx_inventory_movements_type_date",
        "idx_materials_category_active",
        "idx_recipe_versions_product_effective_status",
        "idx_production_batches_product_status_date",
        "idx_inventory_valuation_layers_item_date",
        "idx_cogs_ledger_order_product_date",
    }

    assert expected_indexes <= _index_names(db)
