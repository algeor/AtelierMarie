"""Admin accounting report exports for returns, refunds, and settlements."""

import csv
import io
import json
import sqlite3

import pytest


def _rows(response) -> list[dict[str, str]]:
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    return list(csv.DictReader(io.StringIO(response.text)))


def _seed_session(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute(
        """
        INSERT INTO sessions (id, created_at, expires_at)
        VALUES (?, datetime('now'), datetime('now', '+30 days'))
        """,
        (session_id,),
    )


def _seed_product(conn: sqlite3.Connection, product_id: str = "report-candle") -> None:
    conn.execute(
        """
        INSERT INTO products (id, name_en, price_cents, stock, is_active, created_at, updated_at)
        VALUES (?, 'Report Candle', 2500, 5, 1, datetime('now'), datetime('now'))
        """,
        (product_id,),
    )


def _seed_order(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    session_id: str,
    order_number: str,
    status: str = "delivered",
    payment_method: str = "cod",
    payment_status: str = "cod_pending",
    total_cents: int = 5500,
    delivery_courier: str = "econt",
) -> None:
    conn.execute(
        """
        INSERT INTO orders (
            id, session_id, order_number, status, total_cents, customer_email,
            payment_method, payment_status, delivery_courier, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            order_id,
            session_id,
            order_number,
            status,
            total_cents,
            f"{order_id}@example.com",
            payment_method,
            payment_status,
            delivery_courier,
        ),
    )


@pytest.mark.asyncio
async def test_refund_and_cod_settlement_reports_export_accounting_rows(admin_client, db_path):
    conn = sqlite3.connect(db_path)
    try:
        for session_id in (
            "report-session-1",
            "report-session-2",
            "report-session-3",
            "report-session-4",
        ):
            _seed_session(conn, session_id)
        _seed_order(
            conn,
            "refund-order",
            session_id="report-session-1",
            order_number="AM-REFUND",
            payment_method="card",
            payment_status="refund_pending",
            delivery_courier="speedy",
        )
        _seed_order(
            conn,
            "cod-unsettled",
            session_id="report-session-2",
            order_number="AM-COD-OPEN",
        )
        _seed_order(
            conn,
            "cod-settled",
            session_id="report-session-3",
            order_number="AM-COD-SETTLED",
        )
        _seed_order(
            conn,
            "cod-mismatch",
            session_id="report-session-4",
            order_number="AM-COD-MISMATCH",
        )
        conn.execute(
            """
            INSERT INTO payment_refunds (
                id, order_id, provider, provider_refund_id, amount_cents, status,
                reason, idempotency_key, created_at
            ) VALUES ('refund-report-1', 'refund-order', 'stripe', 're_123', 1200, 'pending',
                'Customer return', 'idem-123', datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO cod_settlements (
                id, order_id, amount_cents, settlement_date, courier_reference, mismatch_review
            )
            VALUES ('cod-settlement-1', 'cod-settled', 5500, '2026-08-01', 'COD-SETTLED', 0)
            """
        )
        conn.execute(
            """
            INSERT INTO cod_settlements (
                id, order_id, amount_cents, settlement_date, courier_reference, mismatch_review
            )
            VALUES ('cod-settlement-2', 'cod-mismatch', 5000, '2026-08-02', 'COD-MISMATCH', 1)
            """
        )
        conn.execute(
            """
            INSERT INTO order_courier_events (order_id, courier, action, status, response_json)
            VALUES ('cod-unsettled', 'econt', 'refresh_trace', 'trace_synced', ?)
            """,
            (json.dumps({"cdCollectedAmount": 55.0, "cdCollectedTime": "2026-08-01T10:00:00Z"}),),
        )
        conn.commit()
    finally:
        conn.close()

    refund_resp = await admin_client.get("/v1/admin/reports/refunds.csv")
    refund_rows = _rows(refund_resp)
    assert refund_rows[0]["refund_id"] == "refund-report-1"
    assert refund_rows[0]["order_number"] == "AM-REFUND"
    assert refund_rows[0]["provider_refund_id"] == "re_123"
    assert refund_rows[0]["amount_cents"] == "1200"
    assert refund_rows[0]["refund_status"] == "pending"

    cod_resp = await admin_client.get("/v1/admin/reports/cod-settlements.csv")
    cod_rows = {row["order_id"]: row for row in _rows(cod_resp)}
    assert cod_rows["cod-unsettled"]["settlement_state"] == "unsettled"
    assert cod_rows["cod-unsettled"]["econt_cd_collected_amount"] == "55.0"
    assert cod_rows["cod-settled"]["settlement_state"] == "settled"
    assert cod_rows["cod-mismatch"]["settlement_state"] == "mismatch"
    assert cod_rows["cod-mismatch"]["mismatch_review"] == "1"


@pytest.mark.asyncio
async def test_return_claim_reason_and_inventory_reports_export_rows(admin_client, db_path):
    conn = sqlite3.connect(db_path)
    try:
        _seed_session(conn, "report-session-return")
        _seed_product(conn)
        _seed_order(
            conn,
            "return-report-order",
            session_id="report-session-return",
            order_number="AM-RETURN-REPORT",
            status="return_in_transit",
            payment_method="card",
            payment_status="paid",
            delivery_courier="speedy",
        )
        conn.execute(
            """
            INSERT INTO order_returns (
                id, order_id, reason, source, status, courier_return_fee_cents,
                courier_claim_id, courier_claim_status, courier_claim_amount_cents,
                restock_decision, created_at, updated_at
            ) VALUES (
                'return-report-1', 'return-report-order', 'damaged_by_courier',
                'admin', 'inspected',
                650, 'CLM-123', 'filed', 3000, 'partial', datetime('now'), datetime('now')
            )
            """
        )
        conn.execute(
            """
            INSERT INTO inventory_adjustments (
                id, order_id, order_return_id, product_id, quantity, reason, source,
                notes, created_by_admin_id
            ) VALUES (
                'adjustment-report-1', 'return-report-order', 'return-report-1', 'report-candle',
                1, 'return_partial_restock', 'admin', 'Box damaged', 'admin-1'
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    claim_rows = _rows(await admin_client.get("/v1/admin/reports/courier-claims.csv"))
    assert claim_rows[0]["return_id"] == "return-report-1"
    assert claim_rows[0]["courier_return_fee_cents"] == "650"
    assert claim_rows[0]["courier_claim_id"] == "CLM-123"
    assert claim_rows[0]["courier_claim_amount_cents"] == "3000"

    reason_rows = _rows(await admin_client.get("/v1/admin/reports/return-reasons.csv"))
    assert reason_rows[0]["reason"] == "damaged_by_courier"
    assert reason_rows[0]["return_count"] == "1"
    assert reason_rows[0]["courier_return_fee_cents"] == "650"
    assert reason_rows[0]["claim_count"] == "1"

    inventory_rows = _rows(await admin_client.get("/v1/admin/reports/inventory-adjustments.csv"))
    assert inventory_rows[0]["adjustment_id"] == "adjustment-report-1"
    assert inventory_rows[0]["order_number"] == "AM-RETURN-REPORT"
    assert inventory_rows[0]["return_reason"] == "damaged_by_courier"
    assert inventory_rows[0]["restock_decision"] == "partial"
    assert inventory_rows[0]["adjustment_reason"] == "return_partial_restock"
