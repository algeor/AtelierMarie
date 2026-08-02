"""Accounting ledger query services for the finance hub."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Callable

from app.database import get_db
from app.models.accounting import AccountingLedgerName, AccountingLedgerResponse
from app.services import accounting_report_service
from app.services.finance_period_service import FinancePeriodError

_LEDGER_DEFAULT_DATE_BASIS: dict[str, str] = {
    "sales": "order_date",
    "payments": "event_date",
    "stripe_payouts": "provider_created_date",
    "cod_settlements": "order_date",
    "refunds": "created_date",
    "courier_claims": "created_date",
    "return_reasons": "last_created_date",
    "inventory_adjustments": "created_date",
    "inventory_movements": "occurred_date",
    "documents": "issue_date",
    "expenses": "purchase_date",
    "product_costs": "order_date",
}

_LEDGER_ALLOWED_DATE_BASIS: dict[str, set[str]] = {
    "sales": {"order_date"},
    "payments": {"event_date"},
    "stripe_payouts": {
        "provider_created_date",
        "available_date",
        "payout_effective_date",
        "payout_arrival_date",
    },
    "cod_settlements": {"order_date", "settlement_date"},
    "refunds": {"created_date", "confirmed_date"},
    "courier_claims": {"created_date", "updated_date"},
    "return_reasons": {"first_created_date", "last_created_date"},
    "inventory_adjustments": {"created_date"},
    "inventory_movements": {"occurred_date", "created_date"},
    "documents": {"issue_date"},
    "expenses": {"purchase_date", "document_date", "payment_date"},
    "product_costs": {"order_date", "effective_date"},
}


def _json_loads(value: str | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _get_period(conn: sqlite3.Connection, period_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM finance_periods WHERE id = %s", (period_id,)).fetchone()
    if row is None:
        raise FinancePeriodError(404, "FINANCE_PERIOD_NOT_FOUND", "Finance period not found.")
    return row


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {key: row[key] for key in row.keys()}


def _date_part(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:10] if len(text) >= 10 else text


def _filter_rows(
    rows: list[dict[str, object]],
    *,
    date_basis: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, object]]:
    filtered: list[dict[str, object]] = []
    for row in rows:
        row_date = _date_part(row.get(date_basis))
        if row_date is not None and start_date <= row_date <= end_date:
            filtered.append(row)
    return filtered


def _monetary_totals(rows: list[dict[str, object]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in rows:
        for key, value in row.items():
            if key.endswith("_cents") and isinstance(value, int):
                totals[key] = totals.get(key, 0) + value
    return totals


def _paginate(rows: list[dict[str, object]], *, page: int, limit: int) -> list[dict[str, object]]:
    start = (page - 1) * limit
    return rows[start : start + limit]


def _document_status(
    conn: sqlite3.Connection, *, order_id: str | None, refund_id: str | None = None
) -> str:
    if not order_id and not refund_id:
        return "not_applicable"
    clauses: list[str] = []
    params: list[str] = []
    if order_id:
        clauses.append("order_id = %s")
        params.append(order_id)
    if refund_id:
        clauses.append("refund_id = %s")
        params.append(refund_id)
    row = conn.execute(
        f"""
        SELECT status FROM accounting_documents
        WHERE ({" OR ".join(clauses)}) AND status NOT IN ('void', 'missing')
        ORDER BY issue_date DESC, created_at DESC
        LIMIT 1
        """,  # noqa: S608
        params,
    ).fetchone()
    return "recorded" if row is not None else "missing"


def _sales_rows(conn: sqlite3.Connection, period: sqlite3.Row) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT o.id AS order_id, o.order_number, substr(o.created_at, 1, 10) AS order_date,
               o.payment_method, o.accounting_currency AS currency,
               o.accounting_snapshot_json, o.invoice_profile_json,
               oi.product_id, oi.product_name, oi.price_cents, oi.quantity
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE substr(o.created_at, 1, 10) BETWEEN %s AND %s
          AND o.status != 'cancelled'
        ORDER BY o.created_at, o.id, oi.product_id
        """,
        (period["period_start"], period["period_end"]),
    ).fetchall()
    ledger: list[dict[str, object]] = []
    for row in rows:
        snapshot = _json_loads(row["accounting_snapshot_json"], {})
        if not isinstance(snapshot, dict):
            snapshot = {}
        gross = int(row["price_cents"] or 0) * int(row["quantity"] or 0)
        ledger.append(
            {
                "row_type": "order_line",
                "order_id": row["order_id"],
                "order_number": row["order_number"],
                "order_date": row["order_date"],
                "customer_country": snapshot.get("customer_country"),
                "delivery_country": snapshot.get("delivery_country"),
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "quantity": row["quantity"],
                "unit_amount_cents": row["price_cents"],
                "discount_amount_cents": 0,
                "net_amount_cents": gross,
                "vat_tax_rate": None,
                "vat_tax_amount_cents": 0,
                "gross_amount_cents": gross,
                "currency": row["currency"] or period["currency"],
                "payment_method": row["payment_method"],
                "document_reference_status": _document_status(conn, order_id=row["order_id"]),
                "source_row_id": f"{row['order_id']}:{row['product_id']}",
            }
        )

    shipping_rows = conn.execute(
        """
        SELECT id AS order_id, order_number, substr(created_at, 1, 10) AS order_date,
               payment_method, accounting_currency AS currency, shipping_cents,
               accounting_snapshot_json
        FROM orders
        WHERE substr(created_at, 1, 10) BETWEEN %s AND %s
          AND status != 'cancelled'
          AND shipping_cents > 0
        ORDER BY created_at, id
        """,
        (period["period_start"], period["period_end"]),
    ).fetchall()
    for row in shipping_rows:
        snapshot = _json_loads(row["accounting_snapshot_json"], {})
        if not isinstance(snapshot, dict):
            snapshot = {}
        ledger.append(
            {
                "row_type": "shipping",
                "order_id": row["order_id"],
                "order_number": row["order_number"],
                "order_date": row["order_date"],
                "customer_country": snapshot.get("customer_country"),
                "delivery_country": snapshot.get("delivery_country"),
                "product_id": None,
                "product_name": "Shipping",
                "quantity": 1,
                "unit_amount_cents": row["shipping_cents"],
                "discount_amount_cents": 0,
                "net_amount_cents": row["shipping_cents"],
                "vat_tax_rate": None,
                "vat_tax_amount_cents": 0,
                "gross_amount_cents": row["shipping_cents"],
                "currency": row["currency"] or period["currency"],
                "payment_method": row["payment_method"],
                "document_reference_status": _document_status(conn, order_id=row["order_id"]),
                "source_row_id": f"{row['order_id']}:shipping",
            }
        )

    refund_rows = conn.execute(
        """
        SELECT r.id AS refund_id, r.order_id, o.order_number,
               substr(COALESCE(r.confirmed_at, r.created_at), 1, 10) AS order_date,
               o.payment_method, o.accounting_currency AS currency, r.amount_cents
        FROM payment_refunds r
        JOIN orders o ON o.id = r.order_id
        WHERE substr(o.created_at, 1, 10) BETWEEN %s AND %s
          AND r.status = 'succeeded'
        ORDER BY COALESCE(r.confirmed_at, r.created_at), r.id
        """,
        (period["period_start"], period["period_end"]),
    ).fetchall()
    for row in refund_rows:
        amount = -int(row["amount_cents"] or 0)
        ledger.append(
            {
                "row_type": "refund_reversal",
                "order_id": row["order_id"],
                "order_number": row["order_number"],
                "order_date": row["order_date"],
                "customer_country": None,
                "delivery_country": None,
                "product_id": None,
                "product_name": "Refund reversal",
                "quantity": 1,
                "unit_amount_cents": amount,
                "discount_amount_cents": 0,
                "net_amount_cents": amount,
                "vat_tax_rate": None,
                "vat_tax_amount_cents": 0,
                "gross_amount_cents": amount,
                "currency": row["currency"] or period["currency"],
                "payment_method": row["payment_method"],
                "document_reference_status": _document_status(
                    conn, order_id=row["order_id"], refund_id=row["refund_id"]
                ),
                "source_row_id": row["refund_id"],
            }
        )
    return ledger


def _payment_rows(conn: sqlite3.Connection, period: sqlite3.Row) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT p.id AS source_event_id, substr(p.created_at, 1, 10) AS event_date,
               p.order_id, o.order_number, p.provider, o.payment_method,
               p.stripe_payment_intent_id, p.stripe_checkout_session_id,
               p.amount_cents AS gross_amount_cents, NULL AS fee_amount_cents,
               NULL AS net_amount_cents, p.currency, p.provider_status AS status,
               'payment' AS row_type, 'unreviewed' AS reconciliation_status
        FROM payments p
        JOIN orders o ON o.id = p.order_id
        WHERE substr(p.created_at, 1, 10) BETWEEN %s AND %s
        ORDER BY p.created_at, p.id
        """,
        (period["period_start"], period["period_end"]),
    ).fetchall()
    ledger = [_row_to_dict(row) for row in rows]
    refund_rows = conn.execute(
        """
        SELECT r.id AS source_event_id, substr(COALESCE(r.confirmed_at, r.created_at), 1, 10)
                   AS event_date,
               r.order_id, o.order_number, r.provider, o.payment_method,
               NULL AS stripe_payment_intent_id, NULL AS stripe_checkout_session_id,
               -r.amount_cents AS gross_amount_cents, NULL AS fee_amount_cents,
               NULL AS net_amount_cents, o.accounting_currency AS currency, r.status,
               'refund' AS row_type, 'unreviewed' AS reconciliation_status
        FROM payment_refunds r
        JOIN orders o ON o.id = r.order_id
        WHERE substr(COALESCE(r.confirmed_at, r.created_at), 1, 10) BETWEEN %s AND %s
        ORDER BY COALESCE(r.confirmed_at, r.created_at), r.id
        """,
        (period["period_start"], period["period_end"]),
    ).fetchall()
    ledger.extend(_row_to_dict(row) for row in refund_rows)
    return ledger


def _stripe_payout_rows(conn: sqlite3.Connection, _period: sqlite3.Row) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT id, balance_transaction_id, reporting_category, transaction_type,
               substr(provider_created_at, 1, 10) AS provider_created_date,
               substr(available_on, 1, 10) AS available_date,
               gross_amount_cents, fee_amount_cents, net_amount_cents, currency,
               payment_intent_id, charge_id, provider_refund_id, dispute_id,
               payout_id, substr(payout_effective_at, 1, 10) AS payout_effective_date,
               substr(payout_arrival_at, 1, 10) AS payout_arrival_date,
               payout_status, trace_id, status, match_status
        FROM stripe_balance_transactions
        ORDER BY COALESCE(provider_created_at, payout_effective_at, imported_at), id
        """
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _cod_rows(conn: sqlite3.Connection, _period: sqlite3.Row) -> list[dict[str, object]]:
    order_dates = {
        row["id"]: _date_part(row["created_at"])
        for row in conn.execute("SELECT id, created_at FROM orders").fetchall()
    }
    rows: list[dict[str, object]] = []
    for row in accounting_report_service.cod_settlement_rows(conn):
        item = dict(row)
        item["order_date"] = order_dates.get(str(item.get("order_id")))
        item["settlement_date"] = _date_part(item.get("settlement_date"))
        rows.append(item)
    return rows


def _report_rows(
    report_func: Callable[[sqlite3.Connection], list[dict[str, Any]]],
) -> Callable[[sqlite3.Connection, sqlite3.Row], list[dict[str, object]]]:
    def adapter(conn: sqlite3.Connection, _period: sqlite3.Row) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for row in report_func(conn):
            item = dict(row)
            for key in list(item):
                if key.endswith("_at") and item[key] is not None:
                    item[f"{key[:-3]}_date"] = _date_part(item[key])
            rows.append(item)
        return rows

    return adapter


def _document_rows(conn: sqlite3.Connection, _period: sqlite3.Row) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT d.id, d.document_type, d.document_number, d.source_system,
               substr(d.issue_date, 1, 10) AS issue_date, d.order_id, o.order_number,
               d.refund_id, d.period_id, d.currency, d.net_amount_cents,
               d.tax_amount_cents, d.gross_amount_cents, d.status, d.file_reference,
               d.original_document_id, d.notes, d.created_by_admin_id,
               d.updated_by_admin_id, d.created_at, d.updated_at
        FROM accounting_documents d
        LEFT JOIN orders o ON o.id = d.order_id
        ORDER BY d.issue_date, d.id
        """
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _expense_rows(conn: sqlite3.Connection, _period: sqlite3.Row) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT id AS expense_id, supplier_name, supplier_identifier, document_number,
               substr(document_date, 1, 10) AS document_date,
               substr(purchase_date, 1, 10) AS purchase_date,
               substr(payment_date, 1, 10) AS payment_date,
               payment_status, category_key, net_amount_cents, tax_amount_cents,
               gross_amount_cents, currency, attachment_reference,
               CASE WHEN attachment_reference IS NULL OR attachment_reference = ''
                    THEN 'missing' ELSE 'recorded' END AS attachment_reference_status,
               linked_product_id, linked_material_name, linked_courier, linked_order_id,
               review_status, created_by_admin_id, updated_by_admin_id, created_at, updated_at
        FROM expense_evidence
        ORDER BY purchase_date, id
        """
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _product_cost_rows(conn: sqlite3.Connection, period: sqlite3.Row) -> list[dict[str, object]]:
    settings = conn.execute("SELECT * FROM product_cost_settings WHERE id = 'default'").fetchone()
    if settings is not None and not bool(settings["enabled"]):
        return []
    rows = conn.execute(
        """
        SELECT o.id AS order_id, o.order_number, substr(o.created_at, 1, 10) AS order_date,
               oi.product_id, oi.product_name, oi.quantity, oi.price_cents AS unit_revenue_cents,
               pc.id AS effective_cost_version_id,
               substr(pc.effective_date, 1, 10) AS effective_date,
               pc.costing_basis, pc.material_cost_cents, pc.packaging_cost_cents,
               pc.labor_cost_cents, pc.overhead_cost_cents,
               pc.estimated_unit_cost_cents, pc.currency, pc.review_status,
               pc.accountant_reviewed
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN product_cost_versions pc ON pc.id = (
            SELECT pc2.id
            FROM product_cost_versions pc2
            WHERE pc2.product_id = oi.product_id
              AND pc2.effective_date <= substr(o.created_at, 1, 10)
              AND pc2.review_status != 'archived'
            ORDER BY pc2.effective_date DESC, pc2.created_at DESC
            LIMIT 1
        )
        WHERE substr(o.created_at, 1, 10) BETWEEN %s AND %s
          AND o.status != 'cancelled'
        ORDER BY o.created_at, o.id, oi.product_id
        """,
        (period["period_start"], period["period_end"]),
    ).fetchall()
    ledger: list[dict[str, object]] = []
    for row in rows:
        estimated_unit_cost = int(row["estimated_unit_cost_cents"] or 0)
        quantity = int(row["quantity"] or 0)
        total_cost = estimated_unit_cost * quantity
        revenue = int(row["unit_revenue_cents"] or 0) * quantity
        reviewed = bool(row["accountant_reviewed"] or False)
        ledger.append(
            {
                "order_id": row["order_id"],
                "order_number": row["order_number"],
                "order_date": row["order_date"],
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "quantity": quantity,
                "effective_cost_version_id": row["effective_cost_version_id"],
                "effective_date": row["effective_date"],
                "costing_basis": row["costing_basis"],
                "material_cost_cents": row["material_cost_cents"] or 0,
                "packaging_cost_cents": row["packaging_cost_cents"] or 0,
                "labor_cost_cents": row["labor_cost_cents"] or 0,
                "overhead_cost_cents": row["overhead_cost_cents"] or 0,
                "estimated_unit_cost_cents": estimated_unit_cost,
                "estimated_total_cost_cents": total_cost,
                "estimated_gross_margin_cents": revenue - total_cost,
                "currency": row["currency"] or period["currency"],
                "review_status": row["review_status"] or "missing",
                "accountant_reviewed": reviewed,
                "estimate_label": "accountant_reviewed" if reviewed else "management_estimate",
                "missing_cost_warning": row["effective_cost_version_id"] is None,
            }
        )
    return ledger


def _inventory_movement_rows(
    conn: sqlite3.Connection, period: sqlite3.Row
) -> list[dict[str, object]]:
    settings = conn.execute("SELECT * FROM inventory_settings WHERE id = 'default'").fetchone()
    official = bool(settings and settings["valuation_enabled"] and settings["accountant_reviewed"])
    rows = conn.execute(
        """
        SELECT im.id AS movement_id, substr(im.occurred_at, 1, 10) AS occurred_date,
               substr(im.created_at, 1, 10) AS created_date,
               im.item_type, im.item_id,
               COALESCE(m.name, p.name_en, im.item_id) AS item_name,
               im.movement_type, im.quantity_delta, im.uom,
               im.source_type, im.source_id, im.product_id, im.order_id,
               im.order_item_key, im.material_lot_id, im.reversal_of_movement_id,
               im.review_state, vl.id AS valuation_layer_id,
               vl.unit_value_amount, vl.total_value_cents,
               vl.review_state AS valuation_review_state
        FROM inventory_movements im
        LEFT JOIN materials m ON im.item_type = 'material' AND m.id = im.item_id
        LEFT JOIN products p ON im.item_type = 'finished_good' AND p.id = im.item_id
        LEFT JOIN inventory_valuation_layers vl ON vl.movement_id = im.id
        WHERE substr(im.occurred_at, 1, 10) BETWEEN %s AND %s
        ORDER BY im.occurred_at, im.created_at, im.id
        """,
        (period["period_start"], period["period_end"]),
    ).fetchall()
    return [
        {
            **_row_to_dict(row),
            "currency": period["currency"],
            "valuation_method": settings["valuation_method"] if settings else None,
            "export_label": "official" if official else "estimate_only",
            "official_inventory_value": official,
        }
        for row in rows
    ]


_LEDGER_BUILDERS: dict[
    str, Callable[[sqlite3.Connection, sqlite3.Row], list[dict[str, object]]]
] = {
    "sales": _sales_rows,
    "payments": _payment_rows,
    "stripe_payouts": _stripe_payout_rows,
    "cod_settlements": _cod_rows,
    "refunds": _report_rows(accounting_report_service.stripe_refund_reconciliation_rows),
    "courier_claims": _report_rows(accounting_report_service.courier_fee_claim_rows),
    "return_reasons": _report_rows(accounting_report_service.return_reason_rows),
    "inventory_adjustments": _report_rows(accounting_report_service.inventory_adjustment_rows),
    "inventory_movements": _inventory_movement_rows,
    "documents": _document_rows,
    "expenses": _expense_rows,
    "product_costs": _product_cost_rows,
}


def get_ledger(
    period_id: str,
    ledger: AccountingLedgerName,
    *,
    date_basis: str | None = None,
    page: int = 1,
    limit: int = 100,
) -> AccountingLedgerResponse:
    """Return one accounting ledger for a selected period."""
    ledger_name = str(ledger)
    if ledger_name not in _LEDGER_BUILDERS:
        raise FinancePeriodError(422, "INVALID_LEDGER", "Unknown accounting ledger.")
    basis = date_basis or _LEDGER_DEFAULT_DATE_BASIS[ledger_name]
    if basis not in _LEDGER_ALLOWED_DATE_BASIS[ledger_name]:
        raise FinancePeriodError(
            422,
            "INVALID_LEDGER_DATE_BASIS",
            f"Invalid date_basis '{basis}' for ledger '{ledger_name}'.",
            {"allowed_date_basis": sorted(_LEDGER_ALLOWED_DATE_BASIS[ledger_name])},
        )
    with get_db() as conn:
        period = _get_period(conn, period_id)
        rows = _LEDGER_BUILDERS[ledger_name](conn, period)
        filtered = _filter_rows(
            rows,
            date_basis=basis,
            start_date=period["period_start"],
            end_date=period["period_end"],
        )
        return AccountingLedgerResponse(
            period_id=period_id,
            ledger=ledger,
            date_basis=basis,
            rows=_paginate(filtered, page=page, limit=limit),
            totals=_monetary_totals(filtered),
            total=len(filtered),
            page=page,
            limit=limit,
        )
