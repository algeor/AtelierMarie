"""Finance period lifecycle and exception engine tests."""

import json
import sqlite3

import pytest


def _seed_reviewed_settings(
    db: sqlite3.Connection,
    *,
    document_rules: dict[str, object] | None = None,
) -> tuple[int, int]:
    db.execute(
        """
        INSERT INTO seller_legal_profile_versions (
            effective_date, reviewed, legal_name, default_currency
        ) VALUES ('2026-08-01', 1, 'Atelier Marie OOD', 'EUR')
        """
    )
    seller_id = int(db.execute("SELECT last_insert_rowid()").fetchone()[0])
    db.execute(
        """
        INSERT INTO vat_fiscal_settings_versions (
            effective_date, reviewed, vat_mode, fiscal_document_mode,
            document_rules_json, tolerance_cents
        ) VALUES ('2026-08-01', 1, 'registered', 'external_reference', ?, 1)
        """,
        (json.dumps(document_rules or {}),),
    )
    vat_id = int(db.execute("SELECT last_insert_rowid()").fetchone()[0])
    db.commit()
    return seller_id, vat_id


def _insert_order(
    db: sqlite3.Connection,
    app,
    *,
    order_id: str,
    created_at: str = "2026-08-10 10:00:00",
    status: str = "confirmed",
    payment_method: str = "card",
    payment_status: str = "paid",
    total_cents: int = 1000,
    shipping_cents: int = 100,
    product_id: str = "finance-candle",
    product_name: str = "Finance Candle",
    price_cents: int = 900,
    quantity: int = 1,
    seller_id: int | None = None,
    vat_id: int | None = None,
    readiness: str = "ready",
    classification: str = "domestic_default",
) -> None:
    db.execute(
        """
        INSERT OR IGNORE INTO products (id, name_en, price_cents, stock)
        VALUES (?, ?, ?, 10)
        """,
        (product_id, product_name, price_cents),
    )
    db.execute(
        """
        INSERT INTO orders (
            id, session_id, status, total_cents, customer_email, customer_name,
            shipping_cents, payment_method, payment_status,
            seller_legal_profile_version_id, vat_fiscal_settings_version_id,
            accounting_classification_state, accounting_readiness_status,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'Finance Buyer', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            app._test_session_id,
            status,
            total_cents,
            f"{order_id}@example.com",
            shipping_cents,
            payment_method,
            payment_status,
            seller_id,
            vat_id,
            classification,
            readiness,
            created_at,
            created_at,
        ),
    )
    db.execute(
        """
        INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
        VALUES (?, ?, ?, ?, ?)
        """,
        (order_id, product_id, product_name, price_cents, quantity),
    )
    db.commit()


@pytest.mark.asyncio
async def test_finance_period_lifecycle_close_export_accept_reopen(admin_client, db, app):
    seller_id, vat_id = _seed_reviewed_settings(db)
    _insert_order(db, app, order_id="period-happy-order", seller_id=seller_id, vat_id=vat_id)
    db.execute(
        """
        INSERT INTO payments (
            id, order_id, provider, amount_cents, provider_status, created_at, updated_at
        ) VALUES ('payment-happy', 'period-happy-order', 'stripe', 1000, 'paid',
                  '2026-08-10 10:01:00', '2026-08-10 10:01:00')
        """
    )
    db.commit()

    create_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "eur"},
    )
    assert create_resp.status_code == 200
    assert create_resp.headers["cache-control"] == "no-store, no-cache"
    period_id = create_resp.json()["id"]

    review_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/review")
    assert review_resp.status_code == 200
    reviewed = review_resp.json()
    assert reviewed["status"] == "review"
    assert reviewed["summary_totals"]["gross_sales_cents"] == 1000
    assert reviewed["open_exception_count"] == 0

    close_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/close")
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"
    assert close_resp.json()["closed_at"] is not None

    exported_resp = await admin_client.post(
        f"/v1/admin/accounting/periods/{period_id}/mark-exported"
    )
    assert exported_resp.status_code == 200
    assert exported_resp.json()["status"] == "exported"

    accept_resp = await admin_client.post(
        f"/v1/admin/accounting/periods/{period_id}/accept",
        json={"reason": "Accountant confirmed August package."},
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "accepted"

    reopen_resp = await admin_client.post(
        f"/v1/admin/accounting/periods/{period_id}/reopen",
        json={"reason": "Late correction from accountant."},
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["status"] == "reopened"
    assert reopen_resp.json()["reopen_reason"] == "Late correction from accountant."

    actions = [
        row["action"]
        for row in db.execute(
            "SELECT action FROM finance_audit_events WHERE target_id = ? ORDER BY created_at",
            (period_id,),
        ).fetchall()
    ]
    assert actions == [
        "finance_period.create",
        "finance_period.start_review",
        "finance_period.close",
        "finance_period.mark_exported",
        "finance_period.accept",
        "finance_period.reopen",
    ]


@pytest.mark.asyncio
async def test_finance_period_close_blocks_until_exception_waived(admin_client, db, app):
    _insert_order(
        db,
        app,
        order_id="period-blocked-cod",
        status="delivered",
        payment_method="cod",
        payment_status="paid",
        readiness="review_required",
        classification="unreviewed",
    )

    create_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "EUR"},
    )
    period_id = create_resp.json()["id"]

    review_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/review")
    assert review_resp.json()["blocking_exception_count"] >= 1

    close_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/close")
    assert close_resp.status_code == 409
    assert close_resp.json()["error"]["code"] == "FINANCE_PERIOD_CLOSE_BLOCKED"

    exceptions_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/exceptions?status=open"
    )
    exception_ids = [item["id"] for item in exceptions_resp.json()["items"]]
    assert exception_ids

    for exception_id in exception_ids:
        waive_resp = await admin_client.post(
            f"/v1/admin/accounting/exceptions/{exception_id}/waive",
            json={"reason": "Accountant accepted this known startup gap."},
        )
        assert waive_resp.status_code == 200
        assert waive_resp.json()["status"] == "waived"

    close_after_waiver = await admin_client.post(
        f"/v1/admin/accounting/periods/{period_id}/close"
    )
    assert close_after_waiver.status_code == 200
    assert close_after_waiver.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_exception_engine_flags_accounting_risks(admin_client, db, app):
    seller_id, vat_id = _seed_reviewed_settings(
        db,
        document_rules={"card": "invoice_reference", "cod": "fiscal_receipt_reference"},
    )
    _insert_order(
        db,
        app,
        order_id="risk-card-no-payment",
        payment_method="card",
        payment_status="paid",
        seller_id=seller_id,
        vat_id=vat_id,
        product_id="risk-product-card",
    )
    _insert_order(
        db,
        app,
        order_id="risk-cod-unsettled",
        status="delivered",
        payment_method="cod",
        payment_status="paid",
        seller_id=seller_id,
        vat_id=vat_id,
        product_id="risk-product-cod",
    )
    db.execute(
        """
        INSERT INTO payment_refunds (
            id, order_id, provider, amount_cents, status, created_at
        ) VALUES ('refund-missing-doc', 'risk-card-no-payment', 'stripe', 300,
                  'succeeded', '2026-08-11 12:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO stripe_balance_transactions (
            id, balance_transaction_id, provider_created_at, gross_amount_cents,
            fee_amount_cents, net_amount_cents, match_status
        ) VALUES ('stripe-mismatch', 'txn_mismatch', '2026-08-11 10:00:00',
                  1000, 50, 950, 'mismatch')
        """
    )
    db.execute(
        """
        INSERT INTO stripe_balance_transactions (
            id, balance_transaction_id, provider_created_at, gross_amount_cents,
            fee_amount_cents, net_amount_cents, match_status
        ) VALUES ('stripe-duplicate', 'txn_duplicate', '2026-08-12 10:00:00',
                  1000, 50, 950, 'duplicate')
        """
    )
    db.execute(
        """
        INSERT INTO expense_evidence_settings (
            id, required_document_categories_json, close_behavior
        ) VALUES ('default', '["materials"]', 'block')
        """
    )
    db.execute(
        """
        INSERT INTO expense_evidence (
            id, supplier_name, purchase_date, category_key, gross_amount_cents,
            tax_amount_cents
        ) VALUES ('expense-missing-doc', 'Wax Supplier', '2026-08-05',
                  'materials', 12000, 2000)
        """
    )
    db.execute(
        """
        INSERT INTO product_cost_settings (id, enabled, missing_cost_policy)
        VALUES ('default', 1, 'blocking')
        """
    )
    db.commit()

    create_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "EUR"},
    )
    period_id = create_resp.json()["id"]
    review_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/review")
    assert review_resp.status_code == 200

    exceptions_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/exceptions?status=open"
    )
    exception_types = {item["exception_type"] for item in exceptions_resp.json()["items"]}
    assert {
        "missing_document_reference",
        "payment_evidence_missing",
        "cod_settlement_missing",
        "refund_document_missing",
        "stripe_payout_mismatch",
        "stripe_payout_duplicate",
        "expense_document_missing",
        "missing_product_cost",
    }.issubset(exception_types)


@pytest.mark.asyncio
async def test_inventory_readiness_exceptions_block_official_period(admin_client, db, app):
    seller_id, vat_id = _seed_reviewed_settings(db)
    _insert_order(
        db,
        app,
        order_id="inventory-readiness-order",
        seller_id=seller_id,
        vat_id=vat_id,
        product_id="inventory-readiness-candle",
    )
    db.execute(
        """
        INSERT INTO product_inventory_profiles (
            product_id, inventory_mode, stock_source, opening_balance_state
        ) VALUES ('inventory-readiness-candle', 'ledger_managed', 'inventory_ledger', 'unreviewed')
        """
    )
    db.execute(
        """
        UPDATE inventory_settings
        SET valuation_enabled = 1, accountant_reviewed = 0
        WHERE id = 'default'
        """
    )
    db.commit()

    create_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "EUR"},
    )
    period_id = create_resp.json()["id"]
    review_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/review")
    assert review_resp.status_code == 200

    exceptions_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/exceptions?status=open"
    )
    exception_types = {item["exception_type"] for item in exceptions_resp.json()["items"]}
    assert {
        "inventory_settings_unreviewed",
        "inventory_opening_balance_unreviewed",
        "inventory_sale_movement_missing",
    }.issubset(exception_types)

    close_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/close")
    assert close_resp.status_code == 409


@pytest.mark.asyncio
async def test_finance_summary_includes_inventory_valuation_totals(admin_client, db, app):
    seller_id, vat_id = _seed_reviewed_settings(db)
    _insert_order(
        db,
        app,
        order_id="inventory-summary-order",
        seller_id=seller_id,
        vat_id=vat_id,
        product_id="inventory-summary-candle",
    )
    db.execute(
        """
        INSERT INTO product_inventory_profiles (
            product_id, inventory_mode, stock_source, opening_balance_state, valuation_readiness
        ) VALUES ('inventory-summary-candle', 'ledger_managed', 'inventory_ledger', 'reviewed', 'ready')
        """
    )
    db.execute(
        """
        UPDATE inventory_settings
        SET valuation_enabled = 1, accountant_reviewed = 1, valuation_method = 'weighted_average'
        WHERE id = 'default'
        """
    )
    db.execute(
        """
        INSERT INTO materials (id, sku, name, category, stock_uom)
        VALUES ('summary-wax', 'SUM-WAX', 'Summary Wax', 'wax', 'g')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_movements (
            id, item_type, item_id, movement_type, quantity_delta, uom,
            product_id, order_id, order_item_key, review_state, occurred_at
        ) VALUES ('summary-sale-move', 'finished_good', 'inventory-summary-candle',
                  'sale_issue', -1, 'unit', 'inventory-summary-candle',
                  'inventory-summary-order', 'inventory-summary-order:inventory-summary-candle',
                  'reviewed', '2026-08-10 10:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_movements (
            id, item_type, item_id, movement_type, quantity_delta, uom,
            review_state, occurred_at
        ) VALUES ('summary-writeoff-move', 'material', 'summary-wax', 'write_off',
                  -100, 'g', 'reviewed', '2026-08-12 10:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_valuation_layers (
            id, movement_id, item_type, item_id, quantity, unit_value_amount,
            total_value_cents, currency, valuation_method, valuation_date, review_state
        ) VALUES ('summary-material-layer', NULL, 'material', 'summary-wax', 1000,
                  '0.010000', 1000, 'EUR', 'weighted_average', '2026-08-01', 'official')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_valuation_layers (
            id, movement_id, item_type, item_id, quantity, unit_value_amount,
            total_value_cents, currency, valuation_method, valuation_date, review_state
        ) VALUES ('summary-finished-layer', NULL, 'finished_good',
                  'inventory-summary-candle', 5, '2.000000', 1000, 'EUR',
                  'weighted_average', '2026-08-01', 'official')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_valuation_layers (
            id, movement_id, item_type, item_id, quantity, unit_value_amount,
            total_value_cents, currency, valuation_method, valuation_date, review_state
        ) VALUES ('summary-writeoff-layer', 'summary-writeoff-move', 'material',
                  'summary-wax', -100, '0.010000', 100, 'EUR', 'weighted_average',
                  '2026-08-12', 'official')
        """
    )
    db.execute(
        """
        INSERT INTO cogs_ledger (
            id, order_id, order_number, order_item_key, product_id, quantity_sold,
            cogs_date, unit_cost_amount, total_cost_cents, currency, valuation_method,
            source_movement_id, review_state
        ) VALUES ('summary-cogs', 'inventory-summary-order', 'INV-SUMMARY',
                  'inventory-summary-order:inventory-summary-candle',
                  'inventory-summary-candle', 1, '2026-08-10', '2.000000', 200,
                  'EUR', 'weighted_average', 'summary-sale-move', 'official')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_exceptions (
            id, exception_type, severity, target_type, target_id, status, message
        ) VALUES ('summary-inventory-exception', 'sample_warning', 'warning', 'product',
                  'inventory-summary-candle', 'open', 'Sample warning')
        """
    )
    db.commit()

    create_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "EUR"},
    )
    period_id = create_resp.json()["id"]
    review_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/review")
    summary = review_resp.json()["summary_totals"]

    assert summary["inventory_valuation_enabled"] is True
    assert summary["inventory_valuation_reviewed"] is True
    assert summary["material_on_hand_value_cents"] == 900
    assert summary["finished_goods_on_hand_value_cents"] == 1000
    assert summary["inventory_cogs_cents"] == 200
    assert summary["inventory_writeoffs_cents"] == 100
    assert summary["inventory_exception_count"] == 1
