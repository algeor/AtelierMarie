"""Admin accounting access-control and order readiness integration tests."""

import sqlite3

import pytest


def _seed_period(db: sqlite3.Connection, period_id: str = "period-order-flags") -> str:
    db.execute(
        """
        INSERT INTO finance_periods (id, period_start, period_end, currency, status)
        VALUES (?, '2026-08-01', '2026-08-31', 'EUR', 'review')
        """,
        (period_id,),
    )
    db.commit()
    return period_id


def _seed_order(
    db: sqlite3.Connection,
    app,
    *,
    order_id: str,
    period_id: str | None = None,
    status: str = "delivered",
    payment_method: str = "cod",
    payment_status: str = "paid",
    classification: str = "domestic_default",
    stripe_payment_intent_id: str | None = None,
) -> None:
    db.execute(
        """
        INSERT OR IGNORE INTO products (id, name_en, price_cents, stock)
        VALUES ('accounting-order-product', 'Accounting Candle', 2500, 10)
        """
    )
    db.execute(
        """
        INSERT INTO orders (
            id, session_id, status, total_cents, customer_email, customer_name,
            shipping_cents, payment_method, payment_status, stripe_payment_intent_id,
            accounting_classification_state, accounting_readiness_status,
            finance_period_id, created_at, updated_at
        ) VALUES (?, ?, ?, 2500, ?, 'Accounting Buyer', 0, ?, ?, ?, ?, 'ready', ?,
                  '2026-08-10 10:00:00', '2026-08-10 10:00:00')
        """,
        (
            order_id,
            app._test_session_id,
            status,
            f"{order_id}@example.com",
            payment_method,
            payment_status,
            stripe_payment_intent_id,
            classification,
            period_id,
        ),
    )
    db.execute(
        """
        INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
        VALUES (?, 'accounting-order-product', 'Accounting Candle', 2500, 1)
        """,
        (order_id,),
    )
    db.commit()


def _seed_order_exception(
    db: sqlite3.Connection,
    *,
    order_id: str,
    period_id: str,
    exception_type: str = "missing_document_reference",
) -> None:
    db.execute(
        """
        INSERT INTO finance_exceptions (
            id, period_id, exception_type, severity, target_type, target_id, status, message
        ) VALUES (?, ?, ?, 'blocking', 'order', ?, 'open', 'Missing accounting evidence')
        """,
        (f"exception-{order_id}-{exception_type}", period_id, exception_type, order_id),
    )
    db.commit()


@pytest.mark.asyncio
async def test_admin_order_responses_include_accounting_flags(admin_client, db, app):
    period_id = _seed_period(db)
    _seed_order(db, app, order_id="acct-order-cod", period_id=period_id)
    _seed_order_exception(db, order_id="acct-order-cod", period_id=period_id)

    list_resp = await admin_client.get("/v1/admin/orders?accounting_filter=unresolved_exception")

    assert list_resp.status_code == 200
    order = list_resp.json()["items"][0]
    assert order["id"] == "acct-order-cod"
    assert order["accounting_readiness_status"] == "blocked"
    assert order["document_reference_status"] == "missing"
    assert order["payment_reconciliation_status"] == "pending"
    assert order["cod_settlement_status"] == "pending"
    assert order["blocking_exception_count"] == 1
    assert order["finance_hub_links"]["period_id"] == period_id

    detail_resp = await admin_client.get("/v1/admin/orders/acct-order-cod")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["finance_hub_links"]["exceptions_href"].endswith("tab=exceptions")


@pytest.mark.asyncio
async def test_admin_order_accounting_filters(admin_client, db, app):
    period_id = _seed_period(db, "period-order-filters")
    _seed_order(db, app, order_id="acct-order-missing-doc", period_id=period_id)
    _seed_order(db, app, order_id="acct-order-clean", period_id=period_id, payment_status="pending")
    _seed_order_exception(db, order_id="acct-order-missing-doc", period_id=period_id)

    missing_resp = await admin_client.get(
        "/v1/admin/orders?accounting_filter=missing_document_reference"
    )
    assert missing_resp.status_code == 200
    assert [item["id"] for item in missing_resp.json()["items"]] == ["acct-order-missing-doc"]

    period_resp = await admin_client.get(f"/v1/admin/orders?finance_period_id={period_id}")
    assert period_resp.status_code == 200
    assert {item["id"] for item in period_resp.json()["items"]} == {
        "acct-order-missing-doc",
        "acct-order-clean",
    }

    invalid_resp = await admin_client.get("/v1/admin/orders?accounting_filter=nope")
    assert invalid_resp.status_code == 422
    assert invalid_resp.json()["error"]["code"] == "INVALID_ACCOUNTING_FILTER"


@pytest.mark.asyncio
async def test_admin_order_payout_mismatch_filter(admin_client, db, app):
    period_id = _seed_period(db, "period-payout-filter")
    _seed_order(
        db,
        app,
        order_id="acct-card-mismatch",
        period_id=period_id,
        payment_method="card",
        payment_status="paid",
        stripe_payment_intent_id="pi_mismatch",
    )
    db.execute(
        """
        INSERT INTO stripe_balance_transactions (
            id, balance_transaction_id, gross_amount_cents, fee_amount_cents,
            net_amount_cents, currency, payment_intent_id, match_status
        ) VALUES ('sbt-mismatch', 'txn_mismatch', 2500, 100, 2400, 'EUR', 'pi_mismatch',
                  'mismatch')
        """
    )
    db.commit()

    resp = await admin_client.get("/v1/admin/orders?accounting_filter=payout_mismatch")

    assert resp.status_code == 200
    assert [item["id"] for item in resp.json()["items"]] == ["acct-card-mismatch"]
    assert resp.json()["items"][0]["payout_reconciliation_status"] == "mismatch"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/v1/admin/accounting/config", None),
        ("POST", "/v1/admin/accounting/config/seller-profile", {"effective_date": "2026-08-01"}),
        ("GET", "/v1/admin/accounting/periods", None),
        ("GET", "/v1/admin/accounting/periods/fake/ledgers/sales", None),
        ("POST", "/v1/admin/accounting/periods/fake/exports", None),
        ("GET", "/v1/admin/accounting/exports/fake/download", None),
    ],
)
async def test_accounting_admin_routes_require_admin(client, method, path, body):
    response = await client.request(method, path, json=body)

    assert response.status_code == 401
