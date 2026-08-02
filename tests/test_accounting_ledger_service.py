"""Accounting ledger service and API tests."""

import sqlite3

import pytest


def _seed_settings(db: sqlite3.Connection) -> tuple[int, int]:
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
            effective_date, reviewed, vat_mode, fiscal_document_mode
        ) VALUES ('2026-08-01', 1, 'registered', 'external_reference')
        """
    )
    vat_id = int(db.execute("SELECT last_insert_rowid()").fetchone()[0])
    db.commit()
    return seller_id, vat_id


def _insert_order(
    db: sqlite3.Connection,
    app,
    *,
    order_id: str,
    product_id: str,
    product_name: str,
    created_at: str,
    status: str = "confirmed",
    payment_method: str = "card",
    payment_status: str = "paid",
    total_cents: int = 1000,
    shipping_cents: int = 100,
    price_cents: int = 900,
    seller_id: int,
    vat_id: int,
) -> None:
    db.execute(
        "INSERT OR IGNORE INTO products (id, name_en, price_cents, stock) VALUES (?, ?, ?, 10)",
        (product_id, product_name, price_cents),
    )
    db.execute(
        """
        INSERT INTO orders (
            id, order_number, session_id, status, total_cents, customer_email,
            customer_name, shipping_cents, payment_method, payment_status,
            seller_legal_profile_version_id, vat_fiscal_settings_version_id,
            accounting_classification_state, accounting_readiness_status,
            accounting_snapshot_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'Ledger Buyer', ?, ?, ?, ?, ?,
                  'domestic_default', 'ready', ?, ?, ?)
        """,
        (
            order_id,
            order_id.upper(),
            app._test_session_id,
            status,
            total_cents,
            f"{order_id}@example.com",
            shipping_cents,
            payment_method,
            payment_status,
            seller_id,
            vat_id,
            '{"delivery_country":"BG","customer_country":"BG"}',
            created_at,
            created_at,
        ),
    )
    db.execute(
        """
        INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
        VALUES (?, ?, ?, ?, 1)
        """,
        (order_id, product_id, product_name, price_cents),
    )
    db.commit()


@pytest.mark.asyncio
async def test_accounting_ledger_endpoint_returns_core_ledgers(admin_client, db, app):
    seller_id, vat_id = _seed_settings(db)
    _insert_order(
        db,
        app,
        order_id="ledger-card-order",
        product_id="ledger-candle",
        product_name="Ledger Candle",
        created_at="2026-08-10 10:00:00",
        seller_id=seller_id,
        vat_id=vat_id,
    )
    _insert_order(
        db,
        app,
        order_id="ledger-cod-order",
        product_id="ledger-cod-candle",
        product_name="Ledger COD Candle",
        created_at="2026-08-12 10:00:00",
        status="delivered",
        payment_method="cod",
        payment_status="paid",
        seller_id=seller_id,
        vat_id=vat_id,
    )
    db.execute(
        """
        INSERT INTO payments (
            id, order_id, provider, amount_cents, currency, stripe_payment_intent_id,
            provider_status, created_at, updated_at
        ) VALUES ('ledger-payment', 'ledger-card-order', 'stripe', 1000, 'EUR',
                  'pi_ledger', 'paid', '2026-08-10 10:01:00', '2026-08-10 10:01:00')
        """
    )
    db.execute(
        """
        INSERT INTO payment_refunds (
            id, order_id, payment_id, provider, provider_refund_id, amount_cents,
            status, created_at, confirmed_at
        ) VALUES ('ledger-refund', 'ledger-card-order', 'ledger-payment', 'stripe',
                  're_ledger', 300, 'succeeded', '2026-08-11 10:00:00',
                  '2026-08-11 11:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO stripe_balance_transactions (
            id, balance_transaction_id, provider_created_at, available_on,
            gross_amount_cents, fee_amount_cents, net_amount_cents, currency,
            payment_intent_id, payout_id, match_status
        ) VALUES ('ledger-btxn', 'txn_ledger', '2026-08-10 10:02:00', '2026-08-12',
                  1000, 50, 950, 'EUR', 'pi_ledger', 'po_ledger', 'matched')
        """
    )
    db.execute(
        """
        INSERT INTO accounting_documents (
            id, document_type, document_number, issue_date, order_id, currency,
            gross_amount_cents
        ) VALUES ('ledger-doc', 'invoice', 'INV-LEDGER', '2026-08-10',
                  'ledger-card-order', 'EUR', 1000)
        """
    )
    db.execute(
        """
        INSERT INTO expense_evidence (
            id, supplier_name, document_number, document_date, purchase_date,
            payment_date, payment_status, category_key, net_amount_cents,
            tax_amount_cents, gross_amount_cents, currency, attachment_reference,
            review_status
        ) VALUES ('ledger-expense', 'Wax Supplier', 'SUP-1', '2026-08-04',
                  '2026-08-05', '2026-09-01', 'paid', 'materials', 10000,
                  2000, 12000, 'EUR', 'file://supplier.pdf', 'reviewed')
        """
    )
    db.execute(
        """
        INSERT INTO product_cost_versions (
            id, product_id, product_name, effective_date, costing_basis,
            material_cost_cents, packaging_cost_cents, estimated_unit_cost_cents,
            currency, reviewed, accountant_reviewed, review_status
        ) VALUES ('ledger-cost', 'ledger-candle', 'Ledger Candle', '2026-08-01',
                  'manual_snapshot', 300, 100, 400, 'EUR', 1, 1,
                  'accountant_reviewed')
        """
    )
    db.execute(
        """
        INSERT INTO materials (id, sku, name, category, stock_uom)
        VALUES ('ledger-wax', 'WAX-LEDGER', 'Ledger Wax', 'wax', 'g')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_movements (
            id, item_type, item_id, movement_type, quantity_delta, uom,
            source_type, source_id, review_state, occurred_at
        ) VALUES ('ledger-inventory-move', 'material', 'ledger-wax', 'receipt',
                  1000, 'g', 'material_receipt', 'receipt-ledger', 'reviewed',
                  '2026-08-06 09:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO inventory_valuation_layers (
            id, movement_id, item_type, item_id, quantity, unit_value_amount,
            total_value_cents, currency, valuation_method, source_type, source_id,
            valuation_date, review_state
        ) VALUES ('ledger-inventory-layer', 'ledger-inventory-move', 'material',
                  'ledger-wax', 1000, '0.010000', 1000, 'EUR', 'weighted_average',
                  'material_receipt', 'receipt-ledger', '2026-08-06 09:00:00', 'reviewed')
        """
    )
    db.commit()

    period_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "EUR"},
    )
    period_id = period_resp.json()["id"]

    sales_resp = await admin_client.get(f"/v1/admin/accounting/periods/{period_id}/ledgers/sales")
    assert sales_resp.status_code == 200
    assert sales_resp.headers["cache-control"] == "no-store, no-cache"
    sales = sales_resp.json()
    assert sales["ledger"] == "sales"
    assert {row["row_type"] for row in sales["rows"]} >= {
        "order_line",
        "shipping",
        "refund_reversal",
    }
    assert sales["totals"]["gross_amount_cents"] == 1700

    payments_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/ledgers/payments"
    )
    assert payments_resp.status_code == 200
    assert payments_resp.json()["totals"]["gross_amount_cents"] == 700

    payout_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/ledgers/stripe_payouts"
    )
    assert payout_resp.status_code == 200
    assert payout_resp.json()["rows"][0]["balance_transaction_id"] == "txn_ledger"

    cod_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/ledgers/cod_settlements"
    )
    assert cod_resp.status_code == 200
    assert cod_resp.json()["rows"][0]["settlement_state"] == "unsettled"

    documents_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/ledgers/documents"
    )
    assert documents_resp.status_code == 200
    assert documents_resp.json()["rows"][0]["document_number"] == "INV-LEDGER"

    expenses_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/ledgers/expenses"
    )
    assert expenses_resp.status_code == 200
    assert expenses_resp.json()["rows"][0]["attachment_reference_status"] == "recorded"
    assert expenses_resp.json()["totals"]["gross_amount_cents"] == 12000

    paid_expenses_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/ledgers/expenses?date_basis=payment_date"
    )
    assert paid_expenses_resp.status_code == 200
    assert paid_expenses_resp.json()["total"] == 0

    product_cost_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/ledgers/product_costs"
    )
    assert product_cost_resp.status_code == 200
    rows = product_cost_resp.json()["rows"]
    assert any(row["effective_cost_version_id"] == "ledger-cost" for row in rows)
    assert any(row["missing_cost_warning"] is True for row in rows)

    inventory_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/ledgers/inventory_movements"
    )
    assert inventory_resp.status_code == 200
    inventory = inventory_resp.json()
    assert inventory["ledger"] == "inventory_movements"
    assert inventory["total"] == 1
    assert inventory["rows"][0]["movement_id"] == "ledger-inventory-move"
    assert inventory["rows"][0]["item_name"] == "Ledger Wax"
    assert inventory["totals"]["total_value_cents"] == 1000

    invalid_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/ledgers/sales?date_basis=payment_date"
    )
    assert invalid_resp.status_code == 422
    assert invalid_resp.json()["error"]["code"] == "INVALID_LEDGER_DATE_BASIS"
