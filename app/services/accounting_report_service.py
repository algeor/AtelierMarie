"""Accounting-oriented return, refund, and settlement reports."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _latest_econt_cod_evidence(conn: sqlite3.Connection, order_id: str) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT id, action, response_json, created_at
        FROM order_courier_events
        WHERE order_id = ? AND courier = 'econt' AND response_json IS NOT NULL
        ORDER BY created_at DESC, id DESC
        """,
        (order_id,),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["response_json"])
        except json.JSONDecodeError:
            continue
        evidence = {
            "econt_cd_collected_amount": payload.get("cdCollectedAmount"),
            "econt_cd_collected_time": payload.get("cdCollectedTime"),
            "econt_cd_paid_amount": payload.get("cdPaidAmount"),
            "econt_cd_paid_time": payload.get("cdPaidTime"),
            "econt_evidence_event_id": row["id"],
            "econt_evidence_action": row["action"],
            "econt_evidence_recorded_at": row["created_at"],
        }
        if any(
            evidence[key] is not None
            for key in (
                "econt_cd_collected_amount",
                "econt_cd_collected_time",
                "econt_cd_paid_amount",
                "econt_cd_paid_time",
            )
        ):
            return evidence
    return {
        "econt_cd_collected_amount": None,
        "econt_cd_collected_time": None,
        "econt_cd_paid_amount": None,
        "econt_cd_paid_time": None,
        "econt_evidence_event_id": None,
        "econt_evidence_action": None,
        "econt_evidence_recorded_at": None,
    }


def stripe_refund_reconciliation_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return Stripe refund rows with order references for reconciliation."""
    rows = conn.execute(
        """
        SELECT
            pr.id AS refund_id,
            pr.order_id,
            o.order_number,
            o.customer_email,
            o.payment_status AS order_payment_status,
            o.total_cents AS order_total_cents,
            pr.payment_id,
            pr.provider,
            pr.provider_refund_id,
            pr.amount_cents,
            pr.status AS refund_status,
            pr.reason,
            pr.idempotency_key,
            pr.failure_reason,
            pr.created_by_admin_id,
            pr.created_at,
            pr.confirmed_at
        FROM payment_refunds pr
        JOIN orders o ON o.id = pr.order_id
        WHERE pr.provider = 'stripe'
        ORDER BY pr.created_at DESC, pr.id DESC
        """
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def cod_settlement_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return COD orders needing settlement reconciliation or already settled."""
    rows = conn.execute(
        """
        SELECT
            o.id AS order_id,
            o.order_number,
            o.customer_email,
            o.status AS order_status,
            o.delivery_courier,
            o.total_cents AS order_total_cents,
            o.courier_status,
            o.courier_last_synced_at,
            cs.id AS settlement_id,
            cs.amount_cents AS settlement_amount_cents,
            cs.settlement_date,
            cs.courier_reference,
            cs.mismatch_review,
            cs.notes AS settlement_notes,
            cs.created_by_admin_id,
            cs.created_at AS settlement_created_at,
            cs.updated_at AS settlement_updated_at,
            CASE
                WHEN cs.id IS NULL THEN 'unsettled'
                WHEN cs.mismatch_review = 1 THEN 'mismatch'
                ELSE 'settled'
            END AS settlement_state
        FROM orders o
        LEFT JOIN cod_settlements cs ON cs.order_id = o.id
        WHERE o.payment_method = 'cod'
          AND (o.status = 'delivered' OR cs.id IS NOT NULL)
        ORDER BY o.created_at DESC, o.id DESC
        """
    ).fetchall()
    report_rows: list[dict[str, Any]] = []
    for row in rows:
        item = _row_to_dict(row)
        item.update(_latest_econt_cod_evidence(conn, row["order_id"]))
        report_rows.append(item)
    return report_rows


def courier_fee_claim_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return courier return fees and manual claim records."""
    rows = conn.execute(
        """
        SELECT
            r.id AS return_id,
            r.order_id,
            o.order_number,
            o.customer_email,
            o.delivery_courier,
            r.reason,
            r.source,
            r.status AS return_status,
            r.courier_return_fee_cents,
            r.courier_claim_id,
            r.courier_claim_status,
            r.courier_claim_amount_cents,
            r.notes,
            r.created_at,
            r.updated_at
        FROM order_returns r
        JOIN orders o ON o.id = r.order_id
        WHERE r.courier_return_fee_cents > 0
           OR r.courier_claim_id IS NOT NULL
           OR r.courier_claim_status != 'none'
           OR r.courier_claim_amount_cents IS NOT NULL
        ORDER BY r.created_at DESC, r.id DESC
        """
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def return_reason_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return aggregate counts and amounts by return reason/source/status."""
    rows = conn.execute(
        """
        SELECT
            r.reason,
            r.source,
            r.status AS return_status,
            COUNT(*) AS return_count,
            COALESCE(SUM(r.refund_amount_cents), 0) AS refund_amount_cents,
            COALESCE(SUM(r.courier_return_fee_cents), 0) AS courier_return_fee_cents,
            SUM(
                CASE
                    WHEN r.courier_claim_status != 'none' OR r.courier_claim_id IS NOT NULL
                    THEN 1
                    ELSE 0
                END
            ) AS claim_count,
            MIN(r.created_at) AS first_created_at,
            MAX(r.created_at) AS last_created_at
        FROM order_returns r
        GROUP BY r.reason, r.source, r.status
        ORDER BY return_count DESC, r.reason ASC, r.source ASC, r.status ASC
        """
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def inventory_adjustment_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return inventory adjustments created by return inspection/restock decisions."""
    rows = conn.execute(
        """
        SELECT
            ia.id AS adjustment_id,
            ia.order_id,
            o.order_number,
            ia.order_return_id AS return_id,
            r.reason AS return_reason,
            r.restock_decision,
            ia.product_id,
            p.name_en AS product_name,
            ia.quantity,
            ia.reason AS adjustment_reason,
            ia.source,
            ia.notes,
            ia.created_by_admin_id,
            ia.created_at
        FROM inventory_adjustments ia
        LEFT JOIN orders o ON o.id = ia.order_id
        LEFT JOIN order_returns r ON r.id = ia.order_return_id
        JOIN products p ON p.id = ia.product_id
        WHERE ia.reason IN ('return_restock', 'return_partial_restock')
        ORDER BY ia.created_at DESC, ia.id DESC
        """
    ).fetchall()
    return [_row_to_dict(row) for row in rows]
