"""Finance period lifecycle and exception engine services."""

from __future__ import annotations

from datetime import date
import json
import sqlite3
import uuid
from typing import Any

from app.database import get_db
from app.models.accounting import (
    FinanceExceptionActionRequest,
    FinanceExceptionListResponse,
    FinanceExceptionResponse,
    FinancePeriodActionRequest,
    FinancePeriodCreateRequest,
    FinancePeriodListResponse,
    FinancePeriodResponse,
)
from app.services import accounting_config_service, pricing

_ENGINE_MARKER = "finance_period_service"
_PAID_PAYMENT_STATUSES = ("paid", "partially_refunded", "refunded")


class FinancePeriodError(ValueError):
    """HTTP-mappable finance period service error."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: object | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.details = details


def _json_dumps(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _json_loads(value: str | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _validate_date_range(period_start: str, period_end: str) -> None:
    try:
        start = date.fromisoformat(period_start)
        end = date.fromisoformat(period_end)
    except ValueError as exc:
        raise FinancePeriodError(
            422,
            "INVALID_PERIOD_DATE",
            "period_start and period_end must use YYYY-MM-DD dates.",
        ) from exc
    if start > end:
        raise FinancePeriodError(
            422,
            "INVALID_PERIOD_RANGE",
            "period_start must be on or before period_end.",
        )


def _period_counts(conn: sqlite3.Connection, period_id: str) -> tuple[int, int]:
    row = conn.execute(
        """
        SELECT
            SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_count,
            SUM(CASE WHEN status = 'open' AND severity = 'blocking' THEN 1 ELSE 0 END)
                AS blocking_count
        FROM finance_exceptions
        WHERE period_id = ?
        """,
        (period_id,),
    ).fetchone()
    return int(row["open_count"] or 0), int(row["blocking_count"] or 0)


def _period_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> FinancePeriodResponse:
    open_count, blocking_count = _period_counts(conn, row["id"])
    return FinancePeriodResponse(
        id=row["id"],
        period_start=row["period_start"],
        period_end=row["period_end"],
        currency=row["currency"],
        status=row["status"],
        summary_totals=_json_loads(row["summary_totals_json"], None),
        open_exception_count=open_count,
        blocking_exception_count=blocking_count,
        created_by_admin_id=row["created_by_admin_id"],
        updated_by_admin_id=row["updated_by_admin_id"],
        closed_by_admin_id=row["closed_by_admin_id"],
        closed_at=row["closed_at"],
        accepted_at=row["accepted_at"],
        reopened_from_export_id=row["reopened_from_export_id"],
        reopen_reason=row["reopen_reason"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _exception_from_row(row: sqlite3.Row) -> FinanceExceptionResponse:
    return FinanceExceptionResponse(
        id=row["id"],
        period_id=row["period_id"],
        exception_type=row["exception_type"],
        severity=row["severity"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        status=row["status"],
        message=row["message"],
        details=_json_loads(row["details_json"], None),
        waived_by_admin_id=row["waived_by_admin_id"],
        waiver_reason=row["waiver_reason"],
        waived_at=row["waived_at"],
        resolved_at=row["resolved_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_period_row(conn: sqlite3.Connection, period_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM finance_periods WHERE id = ?", (period_id,)).fetchone()
    if row is None:
        raise FinancePeriodError(404, "FINANCE_PERIOD_NOT_FOUND", "Finance period not found.")
    return row


def _get_exception_row(conn: sqlite3.Connection, exception_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM finance_exceptions WHERE id = ?", (exception_id,)
    ).fetchone()
    if row is None:
        raise FinancePeriodError(404, "FINANCE_EXCEPTION_NOT_FOUND", "Finance exception not found.")
    return row


def _ensure_transition(row: sqlite3.Row, allowed: set[str], action: str) -> None:
    if row["status"] not in allowed:
        raise FinancePeriodError(
            409,
            "INVALID_FINANCE_PERIOD_STATUS",
            f"Cannot {action} a period with status '{row['status']}'.",
            {"current_status": row["status"], "allowed_statuses": sorted(allowed)},
        )


def _assign_orders_to_period(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    conn.execute(
        """
        UPDATE orders
        SET finance_period_id = ?
        WHERE substr(created_at, 1, 10) BETWEEN ? AND ?
          AND (finance_period_id IS NULL OR finance_period_id = ?)
        """,
        (row["id"], row["period_start"], row["period_end"], row["id"]),
    )


def _latest_settings_row(conn: sqlite3.Connection, table: str) -> sqlite3.Row | None:
    return conn.execute(
        f"SELECT * FROM {table} ORDER BY effective_date DESC, id DESC LIMIT 1"  # noqa: S608
    ).fetchone()


def _settings_exception_specs(conn: sqlite3.Connection) -> list[dict[str, object]]:
    seller = _latest_settings_row(conn, "seller_legal_profile_versions")
    vat = _latest_settings_row(conn, "vat_fiscal_settings_versions")
    issues: list[dict[str, object]] = []
    if seller is None:
        issues.append(
            {
                "exception_type": "seller_profile_missing",
                "severity": "blocking",
                "target_type": "settings",
                "target_id": "seller_legal_profile",
                "message": "Seller legal profile is missing.",
            }
        )
    elif not bool(seller["reviewed"]):
        issues.append(
            {
                "exception_type": "seller_profile_unreviewed",
                "severity": "blocking",
                "target_type": "settings",
                "target_id": str(seller["id"]),
                "message": "Seller legal profile has not been accountant-reviewed.",
            }
        )

    if vat is None:
        issues.append(
            {
                "exception_type": "vat_fiscal_settings_missing",
                "severity": "blocking",
                "target_type": "settings",
                "target_id": "vat_fiscal_settings",
                "message": "VAT/fiscal settings are missing.",
            }
        )
    elif not bool(vat["reviewed"]):
        issues.append(
            {
                "exception_type": "vat_fiscal_settings_unreviewed",
                "severity": "blocking",
                "target_type": "settings",
                "target_id": str(vat["id"]),
                "message": "VAT/fiscal settings have not been accountant-reviewed.",
            }
        )
    return issues


def _document_rules(conn: sqlite3.Connection) -> dict[str, object]:
    row = _latest_settings_row(conn, "vat_fiscal_settings_versions")
    if row is None:
        return {}
    rules = _json_loads(row["document_rules_json"], {})
    return rules if isinstance(rules, dict) else {}


def _expense_settings(conn: sqlite3.Connection) -> tuple[set[str], str]:
    row = conn.execute("SELECT * FROM expense_evidence_settings WHERE id = 'default'").fetchone()
    if row is None:
        return set(), "warn"
    categories = _json_loads(row["required_document_categories_json"], [])
    if not isinstance(categories, list):
        categories = []
    return {str(category) for category in categories}, row["close_behavior"]


def _product_cost_settings(conn: sqlite3.Connection) -> tuple[bool, str]:
    row = conn.execute("SELECT * FROM product_cost_settings WHERE id = 'default'").fetchone()
    if row is None:
        return False, "none"
    return bool(row["enabled"]), row["missing_cost_policy"]


def _inventory_settings(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM inventory_settings WHERE id = 'default'").fetchone()


def _tolerance_cents(conn: sqlite3.Connection) -> int:
    row = _latest_settings_row(conn, "vat_fiscal_settings_versions")
    return int(row["tolerance_cents"] or 0) if row is not None else 1


def _period_order_clause() -> str:
    return "substr(o.created_at, 1, 10) BETWEEN ? AND ? AND o.status != 'cancelled'"


def _collect_exception_specs(conn: sqlite3.Connection, period: sqlite3.Row) -> list[dict[str, object]]:
    period_start = period["period_start"]
    period_end = period["period_end"]
    specs = _settings_exception_specs(conn)

    order_rows = conn.execute(
        f"""
        SELECT o.*
        FROM orders o
        WHERE {_period_order_clause()}
        """,
        (period_start, period_end),
    ).fetchall()
    for order in order_rows:
        if (
            order["accounting_readiness_status"] != "ready"
            or order["seller_legal_profile_version_id"] is None
            or order["vat_fiscal_settings_version_id"] is None
        ):
            specs.append(
                {
                    "exception_type": "order_accounting_review_required",
                    "severity": "blocking",
                    "target_type": "order",
                    "target_id": order["id"],
                    "message": f"Order {order['order_number'] or order['id']} is missing reviewed accounting settings.",
                    "details": {"payment_method": order["payment_method"]},
                }
            )
        if order["accounting_classification_state"] in {"unreviewed", "manual_review_required"}:
            specs.append(
                {
                    "exception_type": "vat_classification_review_required",
                    "severity": "blocking",
                    "target_type": "order",
                    "target_id": order["id"],
                    "message": f"Order {order['order_number'] or order['id']} needs VAT/accounting classification review.",
                    "details": {"classification": order["accounting_classification_state"]},
                }
            )

    required_document_methods = {
        str(method)
        for method, requirement in _document_rules(conn).items()
        if requirement not in {None, False, "", "not_required"}
    }
    if required_document_methods:
        rows = conn.execute(
            f"""
            SELECT o.id, o.order_number, o.payment_method
            FROM orders o
            WHERE {_period_order_clause()}
              AND o.payment_method IN ({','.join('?' for _ in required_document_methods)})
              AND NOT EXISTS (
                  SELECT 1 FROM accounting_documents d
                  WHERE d.order_id = o.id
                    AND d.status NOT IN ('void', 'missing')
              )
            """,
            (period_start, period_end, *sorted(required_document_methods)),
        ).fetchall()
        for row in rows:
            specs.append(
                {
                    "exception_type": "missing_document_reference",
                    "severity": "blocking",
                    "target_type": "order",
                    "target_id": row["id"],
                    "message": f"Order {row['order_number'] or row['id']} is missing a required accounting document reference.",
                    "details": {"payment_method": row["payment_method"]},
                }
            )

    rows = conn.execute(
        f"""
        SELECT o.id, o.order_number, o.payment_method, o.payment_status
        FROM orders o
        WHERE {_period_order_clause()}
          AND o.payment_method IN ('card', 'bank_transfer')
          AND o.payment_status IN ({','.join('?' for _ in _PAID_PAYMENT_STATUSES)})
          AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.order_id = o.id)
        """,
        (period_start, period_end, *_PAID_PAYMENT_STATUSES),
    ).fetchall()
    for row in rows:
        specs.append(
            {
                "exception_type": "payment_evidence_missing",
                "severity": "blocking",
                "target_type": "order",
                "target_id": row["id"],
                "message": f"Order {row['order_number'] or row['id']} is marked paid without payment evidence.",
                "details": {"payment_method": row["payment_method"], "payment_status": row["payment_status"]},
            }
        )

    rows = conn.execute(
        f"""
        SELECT o.id, o.order_number, o.total_cents
        FROM orders o
        WHERE {_period_order_clause()}
          AND o.payment_method = 'cod'
          AND o.status = 'delivered'
          AND NOT EXISTS (SELECT 1 FROM cod_settlements c WHERE c.order_id = o.id)
        """,
        (period_start, period_end),
    ).fetchall()
    for row in rows:
        specs.append(
            {
                "exception_type": "cod_settlement_missing",
                "severity": "blocking",
                "target_type": "order",
                "target_id": row["id"],
                "message": f"Delivered COD order {row['order_number'] or row['id']} has no settlement record.",
                "details": {"order_total_cents": row["total_cents"]},
            }
        )

    rows = conn.execute(
        f"""
        SELECT o.id, o.order_number, o.total_cents, c.amount_cents, c.mismatch_review
        FROM orders o
        JOIN cod_settlements c ON c.order_id = o.id
        WHERE {_period_order_clause()}
          AND o.payment_method = 'cod'
          AND (c.amount_cents != o.total_cents OR c.mismatch_review = 1)
        """,
        (period_start, period_end),
    ).fetchall()
    for row in rows:
        specs.append(
            {
                "exception_type": "cod_settlement_mismatch",
                "severity": "blocking",
                "target_type": "order",
                "target_id": row["id"],
                "message": f"COD settlement for order {row['order_number'] or row['id']} does not match the order total.",
                "details": {
                    "order_total_cents": row["total_cents"],
                    "settlement_amount_cents": row["amount_cents"],
                },
            }
        )

    rows = conn.execute(
        """
        SELECT id, balance_transaction_id, match_status, gross_amount_cents, net_amount_cents
        FROM stripe_balance_transactions
        WHERE match_status IN ('unmatched', 'mismatch', 'duplicate')
          AND COALESCE(substr(provider_created_at, 1, 10), substr(payout_effective_at, 1, 10), substr(imported_at, 1, 10))
              BETWEEN ? AND ?
        """,
        (period_start, period_end),
    ).fetchall()
    for row in rows:
        severity = "blocking" if row["match_status"] in {"mismatch", "duplicate"} else "warning"
        specs.append(
            {
                "exception_type": f"stripe_payout_{row['match_status']}",
                "severity": severity,
                "target_type": "stripe_balance_transaction",
                "target_id": row["id"],
                "message": f"Stripe balance transaction {row['balance_transaction_id']} is {row['match_status']}.",
                "details": {
                    "gross_amount_cents": row["gross_amount_cents"],
                    "net_amount_cents": row["net_amount_cents"],
                },
            }
        )

    rows = conn.execute(
        f"""
        SELECT r.id, r.order_id, o.order_number, r.amount_cents
        FROM payment_refunds r
        JOIN orders o ON o.id = r.order_id
        WHERE {_period_order_clause()}
          AND r.status = 'succeeded'
          AND NOT EXISTS (
              SELECT 1 FROM accounting_documents d
              WHERE d.refund_id = r.id AND d.status NOT IN ('void', 'missing')
          )
        """,
        (period_start, period_end),
    ).fetchall()
    for row in rows:
        specs.append(
            {
                "exception_type": "refund_document_missing",
                "severity": "blocking",
                "target_type": "refund",
                "target_id": row["id"],
                "message": f"Refund for order {row['order_number'] or row['order_id']} is missing a credit/document reference.",
                "details": {"amount_cents": row["amount_cents"], "order_id": row["order_id"]},
            }
        )

    required_expense_categories, close_behavior = _expense_settings(conn)
    if required_expense_categories:
        rows = conn.execute(
            f"""
            SELECT id, supplier_name, category_key, gross_amount_cents
            FROM expense_evidence
            WHERE purchase_date BETWEEN ? AND ?
              AND category_key IN ({','.join('?' for _ in required_expense_categories)})
              AND COALESCE(document_number, '') = ''
              AND COALESCE(attachment_reference, '') = ''
            """,
            (period_start, period_end, *sorted(required_expense_categories)),
        ).fetchall()
        for row in rows:
            specs.append(
                {
                    "exception_type": "expense_document_missing",
                    "severity": "blocking" if close_behavior == "block" else "warning",
                    "target_type": "expense",
                    "target_id": row["id"],
                    "message": f"Expense from {row['supplier_name']} is missing required invoice/receipt evidence.",
                    "details": {
                        "category_key": row["category_key"],
                        "gross_amount_cents": row["gross_amount_cents"],
                    },
                }
            )

    costing_enabled, missing_cost_policy = _product_cost_settings(conn)
    if costing_enabled and missing_cost_policy != "none":
        rows = conn.execute(
            f"""
            SELECT DISTINCT o.id AS order_id, o.order_number, oi.product_id, oi.product_name,
                   substr(o.created_at, 1, 10) AS order_date
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE {_period_order_clause()}
              AND NOT EXISTS (
                  SELECT 1 FROM product_cost_versions pc
                  WHERE pc.product_id = oi.product_id
                    AND pc.effective_date <= substr(o.created_at, 1, 10)
                    AND pc.review_status != 'archived'
              )
            """,
            (period_start, period_end),
        ).fetchall()
        for row in rows:
            specs.append(
                {
                    "exception_type": "missing_product_cost",
                    "severity": "blocking" if missing_cost_policy == "blocking" else "warning",
                    "target_type": "order_item",
                    "target_id": f"{row['order_id']}:{row['product_id']}",
                    "message": f"Sold product {row['product_name']} has no effective product-cost estimate.",
                    "details": {
                        "order_id": row["order_id"],
                        "product_id": row["product_id"],
                        "order_date": row["order_date"],
                    },
                }
            )

    inventory_settings = _inventory_settings(conn)
    inventory_valuation_enabled = bool(
        inventory_settings and inventory_settings["valuation_enabled"]
    )
    inventory_reviewed = bool(inventory_settings and inventory_settings["accountant_reviewed"])
    if inventory_valuation_enabled:
        if not inventory_reviewed:
            specs.append(
                {
                    "exception_type": "inventory_settings_unreviewed",
                    "severity": "blocking",
                    "target_type": "inventory_settings",
                    "target_id": "default",
                    "message": "Inventory valuation settings must be accountant-reviewed before official inventory output.",
                    "details": {"valuation_enabled": True},
                }
            )
        rows = conn.execute(
            """
            SELECT product_id, opening_balance_state
            FROM product_inventory_profiles
            WHERE inventory_mode = 'ledger_managed'
              AND opening_balance_state != 'reviewed'
            """
        ).fetchall()
        for row in rows:
            specs.append(
                {
                    "exception_type": "inventory_opening_balance_unreviewed",
                    "severity": "blocking",
                    "target_type": "product",
                    "target_id": row["product_id"],
                    "message": "Ledger-managed product opening balance is not reviewed.",
                    "details": {"opening_balance_state": row["opening_balance_state"]},
                }
            )
        rows = conn.execute(
            f"""
            SELECT o.id AS order_id, o.order_number, oi.product_id, oi.product_name
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN product_inventory_profiles pip
              ON pip.product_id = oi.product_id
             AND pip.inventory_mode = 'ledger_managed'
            WHERE {_period_order_clause()}
              AND NOT EXISTS (
                  SELECT 1
                  FROM inventory_movements im
                  WHERE im.order_id = oi.order_id
                    AND im.product_id = oi.product_id
                    AND im.order_item_key = oi.order_id || ':' || oi.product_id
                    AND im.movement_type = 'sale_issue'
              )
            """,
            (period_start, period_end),
        ).fetchall()
        for row in rows:
            specs.append(
                {
                    "exception_type": "inventory_sale_movement_missing",
                    "severity": "blocking",
                    "target_type": "order_item",
                    "target_id": f"{row['order_id']}:{row['product_id']}",
                    "message": f"Ledger-managed order item {row['product_name']} has no sale issue movement.",
                    "details": {"order_id": row["order_id"], "product_id": row["product_id"]},
                }
            )
        if inventory_reviewed:
            rows = conn.execute(
                f"""
                SELECT o.id AS order_id, o.order_number, oi.product_id, oi.product_name
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN product_inventory_profiles pip
                  ON pip.product_id = oi.product_id
                 AND pip.inventory_mode = 'ledger_managed'
                WHERE {_period_order_clause()}
                  AND NOT EXISTS (
                      SELECT 1
                      FROM cogs_ledger c
                      WHERE c.order_id = oi.order_id
                        AND c.product_id = oi.product_id
                        AND c.review_state != 'reversed'
                  )
                """,
                (period_start, period_end),
            ).fetchall()
            for row in rows:
                specs.append(
                    {
                        "exception_type": "inventory_cogs_missing",
                        "severity": "blocking",
                        "target_type": "order_item",
                        "target_id": f"{row['order_id']}:{row['product_id']}",
                        "message": f"Ledger-managed order item {row['product_name']} has no COGS ledger row.",
                        "details": {"order_id": row["order_id"], "product_id": row["product_id"]},
                    }
                )
        rows = conn.execute(
            f"""
            SELECT DISTINCT ie.*
            FROM inventory_exceptions ie
            WHERE ie.status = 'open'
              AND (
                EXISTS (
                    SELECT 1
                    FROM orders o
                    WHERE {_period_order_clause()}
                      AND (
                        (ie.target_type = 'order' AND ie.target_id = o.id)
                        OR (ie.source_type = 'order' AND ie.source_id = o.id)
                      )
                )
                OR EXISTS (
                    SELECT 1
                    FROM orders o
                    JOIN order_items oi ON oi.order_id = o.id
                    WHERE {_period_order_clause()}
                      AND ie.target_type = 'product'
                      AND ie.target_id = oi.product_id
                )
              )
            """,
            (period_start, period_end, period_start, period_end),
        ).fetchall()
        for row in rows:
            specs.append(
                {
                    "exception_type": f"inventory_{row['exception_type']}",
                    "severity": row["severity"],
                    "target_type": row["target_type"],
                    "target_id": row["target_id"],
                    "message": row["message"],
                    "details": {
                        "inventory_exception_id": row["id"],
                        "source_type": row["source_type"],
                        "source_id": row["source_id"],
                    },
                }
            )

    tolerance_cents = _tolerance_cents(conn)
    rows = conn.execute(
        f"""
        SELECT o.id, o.order_number, o.total_cents,
               COALESCE(SUM(oi.price_cents * oi.quantity), 0) + o.shipping_cents AS computed_total
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        WHERE {_period_order_clause()}
        GROUP BY o.id
        HAVING ABS(o.total_cents - computed_total) > ?
        """,
        (period_start, period_end, tolerance_cents),
    ).fetchall()
    for row in rows:
        specs.append(
            {
                "exception_type": "rounding_difference",
                "severity": "blocking",
                "target_type": "order",
                "target_id": row["id"],
                "message": f"Order {row['order_number'] or row['id']} total differs from line/shipping total beyond tolerance.",
                "details": {
                    "order_total_cents": row["total_cents"],
                    "computed_total_cents": row["computed_total"],
                    "tolerance_cents": tolerance_cents,
                },
            }
        )
    return specs


def _exception_key(spec: dict[str, object]) -> tuple[str, str, str]:
    return (
        str(spec["exception_type"]),
        str(spec.get("target_type") or ""),
        str(spec.get("target_id") or ""),
    )


def _upsert_exception(
    conn: sqlite3.Connection,
    *,
    period_id: str,
    spec: dict[str, object],
) -> None:
    raw_details = spec.get("details")
    details = dict(raw_details) if isinstance(raw_details, dict) else {}
    details["generated_by"] = _ENGINE_MARKER
    row = conn.execute(
        """
        SELECT * FROM finance_exceptions
        WHERE period_id = ?
          AND exception_type = ?
          AND COALESCE(target_type, '') = ?
          AND COALESCE(target_id, '') = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (period_id, *_exception_key(spec)),
    ).fetchone()
    if row is not None and row["status"] in {"resolved", "waived"}:
        return
    now = pricing.now_utc()
    if row is not None:
        conn.execute(
            """
            UPDATE finance_exceptions
            SET severity = ?, message = ?, details_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                spec["severity"],
                spec["message"],
                _json_dumps(details),
                now,
                row["id"],
            ),
        )
        return
    conn.execute(
        """
        INSERT INTO finance_exceptions (
            id, period_id, exception_type, severity, target_type, target_id,
            status, message, details_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            period_id,
            spec["exception_type"],
            spec["severity"],
            spec.get("target_type"),
            spec.get("target_id"),
            spec["message"],
            _json_dumps(details),
            now,
            now,
        ),
    )


def refresh_period_exceptions(conn: sqlite3.Connection, period_id: str) -> list[FinanceExceptionResponse]:
    """Recompute engine-managed exceptions for a period and return open rows."""
    period = _get_period_row(conn, period_id)
    desired_specs = _collect_exception_specs(conn, period)
    desired_keys = {_exception_key(spec) for spec in desired_specs}
    for spec in desired_specs:
        _upsert_exception(conn, period_id=period_id, spec=spec)

    for row in conn.execute(
        """
        SELECT * FROM finance_exceptions
        WHERE period_id = ? AND status = 'open'
        """,
        (period_id,),
    ).fetchall():
        details = _json_loads(row["details_json"], {})
        key = (row["exception_type"], row["target_type"] or "", row["target_id"] or "")
        if isinstance(details, dict) and details.get("generated_by") == _ENGINE_MARKER and key not in desired_keys:
            conn.execute(
                """
                UPDATE finance_exceptions
                SET status = 'resolved', resolved_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (pricing.now_utc(), pricing.now_utc(), row["id"]),
            )

    rows = conn.execute(
        """
        SELECT * FROM finance_exceptions
        WHERE period_id = ? AND status = 'open'
        ORDER BY severity, created_at
        """,
        (period_id,),
    ).fetchall()
    return [_exception_from_row(row) for row in rows]


def calculate_summary_totals(conn: sqlite3.Connection, period: sqlite3.Row) -> dict[str, object]:
    """Calculate pragmatic period summary totals from current operational tables."""
    period_start = period["period_start"]
    period_end = period["period_end"]
    params = (period_start, period_end)
    sales = conn.execute(
        f"""
        SELECT COALESCE(SUM(o.total_cents), 0) AS gross_sales_cents,
               COALESCE(SUM(o.shipping_cents), 0) AS shipping_charged_cents,
               COUNT(*) AS order_count
        FROM orders o
        WHERE {_period_order_clause()}
        """,
        params,
    ).fetchone()
    returns = conn.execute(
        f"""
        SELECT COALESCE(SUM(r.amount_cents), 0) AS refunded_cents,
               COUNT(*) AS refund_count
        FROM payment_refunds r
        JOIN orders o ON o.id = r.order_id
        WHERE {_period_order_clause()} AND r.status = 'succeeded'
        """,
        params,
    ).fetchone()
    payments = conn.execute(
        f"""
        SELECT COALESCE(SUM(p.amount_cents), 0) AS customer_payments_cents
        FROM payments p
        JOIN orders o ON o.id = p.order_id
        WHERE {_period_order_clause()}
        """,
        params,
    ).fetchone()
    stripe = conn.execute(
        """
        SELECT COALESCE(SUM(fee_amount_cents), 0) AS stripe_fees_cents,
               COALESCE(SUM(net_amount_cents), 0) AS net_provider_payouts_cents
        FROM stripe_balance_transactions
        WHERE COALESCE(substr(provider_created_at, 1, 10), substr(payout_effective_at, 1, 10), substr(imported_at, 1, 10))
              BETWEEN ? AND ?
          AND match_status != 'ignored'
        """,
        params,
    ).fetchone()
    cod = conn.execute(
        f"""
        SELECT COALESCE(SUM(o.total_cents), 0) AS cod_receivable_cents
        FROM orders o
        WHERE {_period_order_clause()}
          AND o.payment_method = 'cod'
          AND o.status = 'delivered'
          AND NOT EXISTS (SELECT 1 FROM cod_settlements c WHERE c.order_id = o.id)
        """,
        params,
    ).fetchone()
    expenses = conn.execute(
        """
        SELECT COALESCE(SUM(gross_amount_cents), 0) AS recorded_expenses_cents,
               COALESCE(SUM(CASE WHEN category_key IN ('materials', 'packaging')
                                 THEN gross_amount_cents ELSE 0 END), 0)
                   AS material_packaging_expenses_cents
        FROM expense_evidence
        WHERE purchase_date BETWEEN ? AND ?
        """,
        params,
    ).fetchone()
    product_cost = conn.execute(
        f"""
        SELECT COALESCE(SUM(oi.quantity * COALESCE((
            SELECT pc.estimated_unit_cost_cents
            FROM product_cost_versions pc
            WHERE pc.product_id = oi.product_id
              AND pc.effective_date <= substr(o.created_at, 1, 10)
              AND pc.review_status != 'archived'
            ORDER BY pc.effective_date DESC, pc.created_at DESC
            LIMIT 1
        ), 0)), 0) AS estimated_product_cost_cents
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE {_period_order_clause()}
        """,
        params,
    ).fetchone()
    open_count, blocking_count = _period_counts(conn, period["id"])
    gross_sales_cents = int(sales["gross_sales_cents"] or 0)
    refunded_cents = int(returns["refunded_cents"] or 0)
    estimated_product_cost_cents = int(product_cost["estimated_product_cost_cents"] or 0)
    net_sales_cents = gross_sales_cents - refunded_cents
    inventory_settings = _inventory_settings(conn)
    inventory_enabled = bool(inventory_settings and inventory_settings["valuation_enabled"])
    inventory_values = conn.execute(
        """
        SELECT item_type,
               COALESCE(SUM(CASE WHEN quantity >= 0 THEN total_value_cents ELSE -total_value_cents END), 0)
                   AS ending_value_cents
        FROM inventory_valuation_layers
        WHERE substr(valuation_date, 1, 10) <= ?
          AND review_state != 'reversed'
        GROUP BY item_type
        """,
        (period_end,),
    ).fetchall()
    inventory_value_by_type = {
        row["item_type"]: int(row["ending_value_cents"] or 0) for row in inventory_values
    }
    cogs = conn.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN review_state = 'reversed'
                                 THEN -total_cost_cents ELSE total_cost_cents END), 0)
                   AS cogs_cents
        FROM cogs_ledger
        WHERE substr(cogs_date, 1, 10) BETWEEN ? AND ?
        """,
        params,
    ).fetchone()
    writeoffs = conn.execute(
        """
        SELECT COALESCE(SUM(vl.total_value_cents), 0) AS writeoffs_cents
        FROM inventory_valuation_layers vl
        JOIN inventory_movements im ON im.id = vl.movement_id
        WHERE substr(vl.valuation_date, 1, 10) BETWEEN ? AND ?
          AND im.movement_type IN (
              'return_write_off', 'write_off', 'spoilage',
              'stock_count_correction', 'adjustment'
          )
        """,
        params,
    ).fetchone()
    inventory_exception_count = conn.execute(
        "SELECT COUNT(*) FROM inventory_exceptions WHERE status = 'open'"
    ).fetchone()[0]
    return {
        "currency": period["currency"],
        "gross_sales_cents": gross_sales_cents,
        "discounts_cents": 0,
        "returns_reversals_cents": refunded_cents,
        "net_sales_cents": net_sales_cents,
        "shipping_charged_cents": int(sales["shipping_charged_cents"] or 0),
        "vat_tax_cents": 0,
        "customer_payments_cents": int(payments["customer_payments_cents"] or 0),
        "stripe_fees_cents": int(stripe["stripe_fees_cents"] or 0),
        "courier_cod_fees_cents": 0,
        "net_provider_payouts_cents": int(stripe["net_provider_payouts_cents"] or 0),
        "cod_receivable_cents": int(cod["cod_receivable_cents"] or 0),
        "refunds_pending_cents": 0,
        "recorded_expenses_cents": int(expenses["recorded_expenses_cents"] or 0),
        "material_packaging_expenses_cents": int(
            expenses["material_packaging_expenses_cents"] or 0
        ),
        "estimated_product_cost_cents": estimated_product_cost_cents,
        "material_on_hand_value_cents": inventory_value_by_type.get("material", 0),
        "finished_goods_on_hand_value_cents": inventory_value_by_type.get("finished_good", 0),
        "inventory_cogs_cents": int(cogs["cogs_cents"] or 0),
        "inventory_writeoffs_cents": int(writeoffs["writeoffs_cents"] or 0),
        "inventory_exception_count": int(inventory_exception_count or 0),
        "inventory_valuation_enabled": inventory_enabled,
        "inventory_valuation_reviewed": bool(
            inventory_settings and inventory_settings["accountant_reviewed"]
        ),
        "estimated_gross_margin_cents": net_sales_cents - estimated_product_cost_cents,
        "review_required_item_count": open_count,
        "blocking_exception_count": blocking_count,
        "order_count": int(sales["order_count"] or 0),
        "refund_count": int(returns["refund_count"] or 0),
        "generated_at": pricing.now_utc(),
        "estimate_notice": "Product-cost and margin values are management estimates unless accountant-reviewed.",
    }


def create_period(
    body: FinancePeriodCreateRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinancePeriodResponse:
    """Create an open finance period and audit the action."""
    _validate_date_range(body.period_start, body.period_end)
    period_id = str(uuid.uuid4())
    now = pricing.now_utc()
    with get_db() as conn:
        overlap = conn.execute(
            """
            SELECT id FROM finance_periods
            WHERE currency = ?
              AND NOT (period_end < ? OR period_start > ?)
            LIMIT 1
            """,
            (body.currency, body.period_start, body.period_end),
        ).fetchone()
        if overlap is not None:
            raise FinancePeriodError(
                409,
                "FINANCE_PERIOD_OVERLAP",
                "A finance period already overlaps this date range and currency.",
                {"overlapping_period_id": overlap["id"]},
            )
        conn.execute(
            """
            INSERT INTO finance_periods (
                id, period_start, period_end, currency, status,
                created_by_admin_id, updated_by_admin_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?)
            """,
            (
                period_id,
                body.period_start,
                body.period_end,
                body.currency,
                actor_user_id,
                actor_user_id,
                now,
                now,
            ),
        )
        accounting_config_service.write_finance_audit_event(
            conn,
            action="finance_period.create",
            target_type="finance_period",
            target_id=period_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            after=body.model_dump(mode="json"),
        )
        row = _get_period_row(conn, period_id)
        return _period_from_row(conn, row)


def list_periods(status: str | None = None) -> FinancePeriodListResponse:
    """List finance periods, newest first."""
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM finance_periods WHERE status = ? ORDER BY period_start DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM finance_periods ORDER BY period_start DESC, created_at DESC"
            ).fetchall()
        return FinancePeriodListResponse(
            items=[_period_from_row(conn, row) for row in rows],
            total=len(rows),
        )


def get_period(period_id: str) -> FinancePeriodResponse:
    """Return one finance period."""
    with get_db() as conn:
        return _period_from_row(conn, _get_period_row(conn, period_id))


def start_review(
    period_id: str,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinancePeriodResponse:
    """Move an open/reopened period into review and compute exceptions."""
    with get_db() as conn:
        period = _get_period_row(conn, period_id)
        _ensure_transition(period, {"open", "reopened", "review"}, "start review for")
        before = dict(period)
        _assign_orders_to_period(conn, period)
        refresh_period_exceptions(conn, period_id)
        summary = calculate_summary_totals(conn, period)
        now = pricing.now_utc()
        conn.execute(
            """
            UPDATE finance_periods
            SET status = 'review', summary_totals_json = ?, updated_by_admin_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (_json_dumps(summary), actor_user_id, now, period_id),
        )
        row = _get_period_row(conn, period_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="finance_period.start_review",
            target_type="finance_period",
            target_id=period_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(row),
        )
        return _period_from_row(conn, row)


def close_period(
    period_id: str,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinancePeriodResponse:
    """Close a period if no blocking exceptions remain open."""
    with get_db() as conn:
        period = _get_period_row(conn, period_id)
        _ensure_transition(period, {"open", "review", "reopened"}, "close")
        before = dict(period)
        _assign_orders_to_period(conn, period)
        refresh_period_exceptions(conn, period_id)
        blocking = conn.execute(
            """
            SELECT * FROM finance_exceptions
            WHERE period_id = ? AND status = 'open' AND severity = 'blocking'
            ORDER BY created_at
            """,
            (period_id,),
        ).fetchall()
        if blocking:
            raise FinancePeriodError(
                409,
                "FINANCE_PERIOD_CLOSE_BLOCKED",
                "Cannot close finance period while blocking exceptions are open.",
                {"blocking_exceptions": [_exception_from_row(row).model_dump() for row in blocking]},
            )
        summary = calculate_summary_totals(conn, period)
        now = pricing.now_utc()
        conn.execute(
            """
            UPDATE finance_periods
            SET status = 'closed', summary_totals_json = ?, closed_by_admin_id = ?,
                closed_at = ?, updated_by_admin_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (_json_dumps(summary), actor_user_id, now, actor_user_id, now, period_id),
        )
        row = _get_period_row(conn, period_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="finance_period.close",
            target_type="finance_period",
            target_id=period_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(row),
        )
        return _period_from_row(conn, row)


def mark_exported(
    period_id: str,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinancePeriodResponse:
    """Move a closed period to exported after package generation."""
    with get_db() as conn:
        period = _get_period_row(conn, period_id)
        _ensure_transition(period, {"closed", "exported"}, "mark exported")
        before = dict(period)
        now = pricing.now_utc()
        conn.execute(
            """
            UPDATE finance_periods
            SET status = 'exported', updated_by_admin_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (actor_user_id, now, period_id),
        )
        row = _get_period_row(conn, period_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="finance_period.mark_exported",
            target_type="finance_period",
            target_id=period_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(row),
        )
        return _period_from_row(conn, row)


def accept_period(
    period_id: str,
    body: FinancePeriodActionRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinancePeriodResponse:
    """Mark an exported period accepted by the accountant."""
    with get_db() as conn:
        period = _get_period_row(conn, period_id)
        _ensure_transition(period, {"exported", "accepted"}, "accept")
        before = dict(period)
        now = pricing.now_utc()
        conn.execute(
            """
            UPDATE finance_periods
            SET status = 'accepted', accepted_at = COALESCE(accepted_at, ?),
                updated_by_admin_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, actor_user_id, now, period_id),
        )
        row = _get_period_row(conn, period_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="finance_period.accept",
            target_type="finance_period",
            target_id=period_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after={**dict(row), "acceptance_note": body.reason},
            reason=body.reason,
        )
        return _period_from_row(conn, row)


def reopen_period(
    period_id: str,
    body: FinancePeriodActionRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinancePeriodResponse:
    """Reopen a closed/exported/accepted period while preserving old exports."""
    if not body.reason:
        raise FinancePeriodError(422, "REOPEN_REASON_REQUIRED", "A reopen reason is required.")
    with get_db() as conn:
        period = _get_period_row(conn, period_id)
        _ensure_transition(period, {"closed", "exported", "accepted"}, "reopen")
        before = dict(period)
        export = conn.execute(
            """
            SELECT id FROM finance_export_packages
            WHERE period_id = ? AND current_final = 1
            ORDER BY version DESC LIMIT 1
            """,
            (period_id,),
        ).fetchone()
        now = pricing.now_utc()
        conn.execute(
            """
            UPDATE finance_periods
            SET status = 'reopened', reopened_from_export_id = ?, reopen_reason = ?,
                updated_by_admin_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (export["id"] if export else None, body.reason, actor_user_id, now, period_id),
        )
        row = _get_period_row(conn, period_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="finance_period.reopen",
            target_type="finance_period",
            target_id=period_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(row),
            reason=body.reason,
        )
        return _period_from_row(conn, row)


def list_exceptions(
    period_id: str,
    *,
    status: str | None = None,
    refresh: bool = True,
) -> FinanceExceptionListResponse:
    """List exceptions for a period."""
    with get_db() as conn:
        _get_period_row(conn, period_id)
        if refresh:
            refresh_period_exceptions(conn, period_id)
        if status:
            rows = conn.execute(
                """
                SELECT * FROM finance_exceptions
                WHERE period_id = ? AND status = ?
                ORDER BY severity, created_at
                """,
                (period_id, status),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM finance_exceptions
                WHERE period_id = ?
                ORDER BY status, severity, created_at
                """,
                (period_id,),
            ).fetchall()
        return FinanceExceptionListResponse(
            items=[_exception_from_row(row) for row in rows],
            total=len(rows),
        )


def resolve_exception(
    exception_id: str,
    body: FinanceExceptionActionRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinanceExceptionResponse:
    """Resolve an exception with an admin reason."""
    with get_db() as conn:
        row = _get_exception_row(conn, exception_id)
        before = dict(row)
        now = pricing.now_utc()
        conn.execute(
            """
            UPDATE finance_exceptions
            SET status = 'resolved', resolved_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, now, exception_id),
        )
        updated = _get_exception_row(conn, exception_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="finance_exception.resolve",
            target_type="finance_exception",
            target_id=exception_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(updated),
            reason=body.reason,
        )
        return _exception_from_row(updated)


def waive_exception(
    exception_id: str,
    body: FinanceExceptionActionRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinanceExceptionResponse:
    """Waive an exception with an admin reason."""
    with get_db() as conn:
        row = _get_exception_row(conn, exception_id)
        before = dict(row)
        now = pricing.now_utc()
        conn.execute(
            """
            UPDATE finance_exceptions
            SET status = 'waived', waived_by_admin_id = ?, waiver_reason = ?,
                waived_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (actor_user_id, body.reason, now, now, exception_id),
        )
        updated = _get_exception_row(conn, exception_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="finance_exception.waive",
            target_type="finance_exception",
            target_id=exception_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(updated),
            reason=body.reason,
        )
        return _exception_from_row(updated)
