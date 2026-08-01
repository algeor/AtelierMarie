"""Expense evidence and product-cost estimate services."""

from __future__ import annotations

import json
import sqlite3
import uuid

from app.database import get_db
from app.models.accounting import (
    ExpenseEvidenceListResponse,
    ExpenseEvidenceRequest,
    ExpenseEvidenceResponse,
    ExpensePaymentStatusRequest,
    MissingProductCostDiagnostic,
    MissingProductCostDiagnosticsResponse,
    ProductCostComponentResponse,
    ProductCostVersionListResponse,
    ProductCostVersionRequest,
    ProductCostVersionResponse,
)
from app.services import accounting_config_service, pricing
from app.services.finance_period_service import FinancePeriodError


def _json_dumps(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _json_loads(value: str | None, default: object | None = None) -> object | None:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _expense_from_row(row: sqlite3.Row) -> ExpenseEvidenceResponse:
    return ExpenseEvidenceResponse(
        id=row["id"],
        supplier_name=row["supplier_name"],
        supplier_identifier=row["supplier_identifier"],
        document_number=row["document_number"],
        document_date=row["document_date"],
        purchase_date=row["purchase_date"],
        payment_date=row["payment_date"],
        payment_status=row["payment_status"],
        category_key=row["category_key"],
        net_amount_cents=row["net_amount_cents"],
        tax_amount_cents=row["tax_amount_cents"],
        gross_amount_cents=row["gross_amount_cents"],
        currency=row["currency"],
        attachment_reference=row["attachment_reference"],
        linked_product_id=row["linked_product_id"],
        linked_material_name=row["linked_material_name"],
        linked_courier=row["linked_courier"],
        linked_order_id=row["linked_order_id"],
        review_status=row["review_status"],
        notes=row["notes"],
        created_by_admin_id=row["created_by_admin_id"],
        updated_by_admin_id=row["updated_by_admin_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_expense_row(conn: sqlite3.Connection, expense_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM expense_evidence WHERE id = ?", (expense_id,)).fetchone()
    if row is None:
        raise FinancePeriodError(404, "EXPENSE_EVIDENCE_NOT_FOUND", "Expense evidence not found.")
    return row


def _validate_expense_links(conn: sqlite3.Connection, body: ExpenseEvidenceRequest) -> None:
    if body.linked_product_id and conn.execute("SELECT 1 FROM products WHERE id = ?", (body.linked_product_id,)).fetchone() is None:
        raise FinancePeriodError(404, "PRODUCT_NOT_FOUND", "Linked product not found.")
    if body.linked_order_id and conn.execute("SELECT 1 FROM orders WHERE id = ?", (body.linked_order_id,)).fetchone() is None:
        raise FinancePeriodError(404, "ORDER_NOT_FOUND", "Linked order not found.")


def list_expenses(category_key: str | None = None, review_status: str | None = None) -> ExpenseEvidenceListResponse:
    clauses: list[str] = []
    params: list[str] = []
    if category_key:
        clauses.append("category_key = ?")
        params.append(category_key)
    if review_status:
        clauses.append("review_status = ?")
        params.append(review_status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM expense_evidence {where} ORDER BY purchase_date DESC, created_at DESC",  # noqa: S608
            params,
        ).fetchall()
    return ExpenseEvidenceListResponse(items=[_expense_from_row(row) for row in rows], total=len(rows))


def create_expense(
    body: ExpenseEvidenceRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> ExpenseEvidenceResponse:
    expense_id = str(uuid.uuid4())
    now = pricing.now_utc()
    with get_db() as conn:
        _validate_expense_links(conn, body)
        conn.execute(
            """
            INSERT INTO expense_evidence (
                id, supplier_name, supplier_identifier, document_number, document_date,
                purchase_date, payment_date, payment_status, category_key,
                net_amount_cents, tax_amount_cents, gross_amount_cents, currency,
                attachment_reference, linked_product_id, linked_material_name,
                linked_courier, linked_order_id, review_status, notes,
                created_by_admin_id, updated_by_admin_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                expense_id,
                body.supplier_name,
                body.supplier_identifier,
                body.document_number,
                body.document_date,
                body.purchase_date,
                body.payment_date,
                body.payment_status,
                body.category_key,
                body.net_amount_cents,
                body.tax_amount_cents,
                body.gross_amount_cents,
                body.currency,
                body.attachment_reference,
                body.linked_product_id,
                body.linked_material_name,
                body.linked_courier,
                body.linked_order_id,
                body.review_status,
                body.notes,
                actor_user_id,
                actor_user_id,
                now,
                now,
            ),
        )
        row = _get_expense_row(conn, expense_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="expense_evidence.create",
            target_type="expense_evidence",
            target_id=expense_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            after=_expense_from_row(row).model_dump(mode="json"),
        )
    return _expense_from_row(row)


def update_expense(
    expense_id: str,
    body: ExpenseEvidenceRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> ExpenseEvidenceResponse:
    now = pricing.now_utc()
    with get_db() as conn:
        before = _get_expense_row(conn, expense_id)
        _validate_expense_links(conn, body)
        conn.execute(
            """
            UPDATE expense_evidence
            SET supplier_name = ?, supplier_identifier = ?, document_number = ?,
                document_date = ?, purchase_date = ?, payment_date = ?, payment_status = ?,
                category_key = ?, net_amount_cents = ?, tax_amount_cents = ?,
                gross_amount_cents = ?, currency = ?, attachment_reference = ?,
                linked_product_id = ?, linked_material_name = ?, linked_courier = ?,
                linked_order_id = ?, review_status = ?, notes = ?, updated_by_admin_id = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                body.supplier_name,
                body.supplier_identifier,
                body.document_number,
                body.document_date,
                body.purchase_date,
                body.payment_date,
                body.payment_status,
                body.category_key,
                body.net_amount_cents,
                body.tax_amount_cents,
                body.gross_amount_cents,
                body.currency,
                body.attachment_reference,
                body.linked_product_id,
                body.linked_material_name,
                body.linked_courier,
                body.linked_order_id,
                body.review_status,
                body.notes,
                actor_user_id,
                now,
                expense_id,
            ),
        )
        after = _get_expense_row(conn, expense_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="expense_evidence.update",
            target_type="expense_evidence",
            target_id=expense_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=_expense_from_row(before).model_dump(mode="json"),
            after=_expense_from_row(after).model_dump(mode="json"),
        )
    return _expense_from_row(after)


def update_expense_payment_status(
    expense_id: str,
    body: ExpensePaymentStatusRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> ExpenseEvidenceResponse:
    now = pricing.now_utc()
    with get_db() as conn:
        before = _get_expense_row(conn, expense_id)
        conn.execute(
            """
            UPDATE expense_evidence
            SET payment_status = ?, payment_date = ?, updated_by_admin_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (body.payment_status, body.payment_date, actor_user_id, now, expense_id),
        )
        after = _get_expense_row(conn, expense_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="expense_evidence.update_payment_status",
            target_type="expense_evidence",
            target_id=expense_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=_expense_from_row(before).model_dump(mode="json"),
            after=_expense_from_row(after).model_dump(mode="json"),
            reason=body.reason,
        )
    return _expense_from_row(after)


def _component_from_row(row: sqlite3.Row) -> ProductCostComponentResponse:
    return ProductCostComponentResponse(
        id=row["id"],
        cost_version_id=row["cost_version_id"],
        component_type=row["component_type"],
        description=row["description"],
        quantity=row["quantity"],
        unit=row["unit"],
        unit_cost_cents=row["unit_cost_cents"],
        total_cost_cents=row["total_cost_cents"],
        source_expense_id=row["source_expense_id"],
        created_at=row["created_at"],
    )


def _cost_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> ProductCostVersionResponse:
    components = conn.execute(
        "SELECT * FROM product_cost_components WHERE cost_version_id = ? ORDER BY created_at, id",
        (row["id"],),
    ).fetchall()
    source_ids = _json_loads(row["source_expense_ids_json"], [])
    if not isinstance(source_ids, list):
        source_ids = []
    return ProductCostVersionResponse(
        id=row["id"],
        product_id=row["product_id"],
        sku=row["sku"],
        product_name=row["product_name"],
        effective_date=row["effective_date"],
        costing_basis=row["costing_basis"],
        material_cost_cents=row["material_cost_cents"],
        packaging_cost_cents=row["packaging_cost_cents"],
        labor_cost_cents=row["labor_cost_cents"],
        overhead_cost_cents=row["overhead_cost_cents"],
        estimated_unit_cost_cents=row["estimated_unit_cost_cents"],
        currency=row["currency"],
        reviewed=bool(row["reviewed"]),
        accountant_reviewed=bool(row["accountant_reviewed"]),
        review_status=row["review_status"],
        source_expense_ids=[str(value) for value in source_ids],
        notes=row["notes"],
        components=[_component_from_row(component) for component in components],
        created_by_admin_id=row["created_by_admin_id"],
        updated_by_admin_id=row["updated_by_admin_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_cost_row(conn: sqlite3.Connection, cost_version_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM product_cost_versions WHERE id = ?", (cost_version_id,)).fetchone()
    if row is None:
        raise FinancePeriodError(404, "PRODUCT_COST_VERSION_NOT_FOUND", "Product-cost version not found.")
    return row


def _estimated_unit_cost(body: ProductCostVersionRequest) -> int:
    if body.estimated_unit_cost_cents is not None:
        return body.estimated_unit_cost_cents
    component_total = sum(component.total_cost_cents for component in body.components)
    direct_total = (
        body.material_cost_cents
        + body.packaging_cost_cents
        + body.labor_cost_cents
        + body.overhead_cost_cents
    )
    return component_total or direct_total


def _insert_components(
    conn: sqlite3.Connection,
    cost_version_id: str,
    body: ProductCostVersionRequest,
) -> None:
    for component in body.components:
        conn.execute(
            """
            INSERT INTO product_cost_components (
                id, cost_version_id, component_type, description, quantity, unit,
                unit_cost_cents, total_cost_cents, source_expense_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                cost_version_id,
                component.component_type,
                component.description,
                component.quantity,
                component.unit,
                component.unit_cost_cents,
                component.total_cost_cents,
                component.source_expense_id,
                pricing.now_utc(),
            ),
        )


def list_product_costs(product_id: str | None = None) -> ProductCostVersionListResponse:
    with get_db() as conn:
        if product_id:
            rows = conn.execute(
                "SELECT * FROM product_cost_versions WHERE product_id = ? ORDER BY effective_date DESC",
                (product_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM product_cost_versions ORDER BY effective_date DESC, created_at DESC"
            ).fetchall()
        return ProductCostVersionListResponse(
            items=[_cost_from_row(conn, row) for row in rows],
            total=len(rows),
        )


def create_product_cost(
    body: ProductCostVersionRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> ProductCostVersionResponse:
    cost_id = str(uuid.uuid4())
    now = pricing.now_utc()
    estimated = _estimated_unit_cost(body)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO product_cost_versions (
                id, product_id, sku, product_name, effective_date, costing_basis,
                material_cost_cents, packaging_cost_cents, labor_cost_cents,
                overhead_cost_cents, estimated_unit_cost_cents, currency, reviewed,
                accountant_reviewed, review_status, source_expense_ids_json, notes,
                created_by_admin_id, updated_by_admin_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cost_id,
                body.product_id,
                body.sku,
                body.product_name,
                body.effective_date,
                body.costing_basis,
                body.material_cost_cents,
                body.packaging_cost_cents,
                body.labor_cost_cents,
                body.overhead_cost_cents,
                estimated,
                body.currency,
                1 if body.reviewed else 0,
                1 if body.accountant_reviewed else 0,
                body.review_status,
                _json_dumps(body.source_expense_ids),
                body.notes,
                actor_user_id,
                actor_user_id,
                now,
                now,
            ),
        )
        _insert_components(conn, cost_id, body)
        row = _get_cost_row(conn, cost_id)
        response = _cost_from_row(conn, row)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="product_cost_version.create",
            target_type="product_cost_version",
            target_id=cost_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            after=response.model_dump(mode="json"),
        )
        return response


def update_product_cost(
    cost_version_id: str,
    body: ProductCostVersionRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> ProductCostVersionResponse:
    now = pricing.now_utc()
    estimated = _estimated_unit_cost(body)
    with get_db() as conn:
        before = _cost_from_row(conn, _get_cost_row(conn, cost_version_id))
        conn.execute(
            """
            UPDATE product_cost_versions
            SET product_id = ?, sku = ?, product_name = ?, effective_date = ?,
                costing_basis = ?, material_cost_cents = ?, packaging_cost_cents = ?,
                labor_cost_cents = ?, overhead_cost_cents = ?, estimated_unit_cost_cents = ?,
                currency = ?, reviewed = ?, accountant_reviewed = ?, review_status = ?,
                source_expense_ids_json = ?, notes = ?, updated_by_admin_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                body.product_id,
                body.sku,
                body.product_name,
                body.effective_date,
                body.costing_basis,
                body.material_cost_cents,
                body.packaging_cost_cents,
                body.labor_cost_cents,
                body.overhead_cost_cents,
                estimated,
                body.currency,
                1 if body.reviewed else 0,
                1 if body.accountant_reviewed else 0,
                body.review_status,
                _json_dumps(body.source_expense_ids),
                body.notes,
                actor_user_id,
                now,
                cost_version_id,
            ),
        )
        conn.execute("DELETE FROM product_cost_components WHERE cost_version_id = ?", (cost_version_id,))
        _insert_components(conn, cost_version_id, body)
        after = _cost_from_row(conn, _get_cost_row(conn, cost_version_id))
        accounting_config_service.write_finance_audit_event(
            conn,
            action="product_cost_version.update",
            target_type="product_cost_version",
            target_id=cost_version_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before.model_dump(mode="json"),
            after=after.model_dump(mode="json"),
        )
        return after


def effective_product_cost(product_id: str, effective_date: str) -> ProductCostVersionResponse | None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM product_cost_versions
            WHERE product_id = ? AND effective_date <= ? AND review_status != 'archived'
            ORDER BY effective_date DESC, created_at DESC
            LIMIT 1
            """,
            (product_id, effective_date),
        ).fetchone()
        return _cost_from_row(conn, row) if row else None


def missing_product_costs(period_id: str) -> MissingProductCostDiagnosticsResponse:
    with get_db() as conn:
        period = conn.execute("SELECT * FROM finance_periods WHERE id = ?", (period_id,)).fetchone()
        if period is None:
            raise FinancePeriodError(404, "FINANCE_PERIOD_NOT_FOUND", "Finance period not found.")
        rows = conn.execute(
            """
            SELECT DISTINCT o.id AS order_id, o.order_number, substr(o.created_at, 1, 10) AS order_date,
                   oi.product_id, oi.product_name
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE substr(o.created_at, 1, 10) BETWEEN ? AND ?
              AND NOT EXISTS (
                  SELECT 1 FROM product_cost_versions pc
                  WHERE pc.product_id = oi.product_id
                    AND pc.effective_date <= substr(o.created_at, 1, 10)
                    AND pc.review_status != 'archived'
              )
            ORDER BY o.created_at, o.id, oi.product_id
            """,
            (period["period_start"], period["period_end"]),
        ).fetchall()
    items = [
        MissingProductCostDiagnostic(
            order_id=row["order_id"],
            order_number=row["order_number"],
            order_date=row["order_date"],
            product_id=row["product_id"],
            product_name=row["product_name"],
        )
        for row in rows
    ]
    return MissingProductCostDiagnosticsResponse(items=items, total=len(items))
