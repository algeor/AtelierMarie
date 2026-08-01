"""Accounting document registry service."""

from __future__ import annotations

import json
import sqlite3
import uuid

from app.database import get_db
from app.models.accounting import (
    AccountingDocumentListResponse,
    AccountingDocumentRequest,
    AccountingDocumentResponse,
)
from app.services import accounting_config_service, pricing
from app.services.finance_period_service import FinancePeriodError


def _json_dumps(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _json_loads(value: str | None) -> dict[str, object] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _document_from_row(row: sqlite3.Row) -> AccountingDocumentResponse:
    return AccountingDocumentResponse(
        id=row["id"],
        document_type=row["document_type"],
        source_system=row["source_system"],
        document_number=row["document_number"],
        issue_date=row["issue_date"],
        order_id=row["order_id"],
        refund_id=row["refund_id"],
        period_id=row["period_id"],
        currency=row["currency"],
        net_amount_cents=row["net_amount_cents"],
        tax_amount_cents=row["tax_amount_cents"],
        gross_amount_cents=row["gross_amount_cents"],
        vat_summary=_json_loads(row["vat_summary_json"]),
        original_document_id=row["original_document_id"],
        file_reference=row["file_reference"],
        status=row["status"],
        notes=row["notes"],
        created_by_admin_id=row["created_by_admin_id"],
        updated_by_admin_id=row["updated_by_admin_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_document_row(conn: sqlite3.Connection, document_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM accounting_documents WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        raise FinancePeriodError(
            404, "ACCOUNTING_DOCUMENT_NOT_FOUND", "Accounting document not found."
        )
    return row


def _validate_document(conn: sqlite3.Connection, body: AccountingDocumentRequest) -> None:
    if body.document_type == "credit_note" and not body.original_document_id:
        raise FinancePeriodError(
            422,
            "CREDIT_NOTE_ORIGINAL_REQUIRED",
            "Credit notes require original_document_id.",
        )
    if body.original_document_id:
        _get_document_row(conn, body.original_document_id)
    if (
        body.order_id
        and conn.execute("SELECT 1 FROM orders WHERE id = ?", (body.order_id,)).fetchone() is None
    ):
        raise FinancePeriodError(404, "ORDER_NOT_FOUND", "Linked order not found.")
    if (
        body.refund_id
        and conn.execute("SELECT 1 FROM payment_refunds WHERE id = ?", (body.refund_id,)).fetchone()
        is None
    ):
        raise FinancePeriodError(404, "REFUND_NOT_FOUND", "Linked refund not found.")
    if (
        body.period_id
        and conn.execute("SELECT 1 FROM finance_periods WHERE id = ?", (body.period_id,)).fetchone()
        is None
    ):
        raise FinancePeriodError(
            404, "FINANCE_PERIOD_NOT_FOUND", "Linked finance period not found."
        )


def list_documents(
    *,
    order_id: str | None = None,
    refund_id: str | None = None,
    period_id: str | None = None,
) -> AccountingDocumentListResponse:
    """List accounting document references."""
    clauses: list[str] = []
    params: list[str] = []
    if order_id:
        clauses.append("order_id = ?")
        params.append(order_id)
    if refund_id:
        clauses.append("refund_id = ?")
        params.append(refund_id)
    if period_id:
        clauses.append("period_id = ?")
        params.append(period_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM accounting_documents {where} ORDER BY issue_date DESC, created_at DESC",  # noqa: S608
            params,
        ).fetchall()
    return AccountingDocumentListResponse(
        items=[_document_from_row(row) for row in rows],
        total=len(rows),
    )


def create_document(
    body: AccountingDocumentRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
    reason: str | None = None,
) -> AccountingDocumentResponse:
    """Create an accounting document reference and audit it."""
    document_id = str(uuid.uuid4())
    now = pricing.now_utc()
    with get_db() as conn:
        _validate_document(conn, body)
        conn.execute(
            """
            INSERT INTO accounting_documents (
                id, document_type, source_system, document_number, issue_date,
                order_id, refund_id, period_id, currency, net_amount_cents,
                tax_amount_cents, gross_amount_cents, vat_summary_json,
                original_document_id, file_reference, status, notes,
                created_by_admin_id, updated_by_admin_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                body.document_type,
                body.source_system,
                body.document_number,
                body.issue_date,
                body.order_id,
                body.refund_id,
                body.period_id,
                body.currency,
                body.net_amount_cents,
                body.tax_amount_cents,
                body.gross_amount_cents,
                _json_dumps(body.vat_summary),
                body.original_document_id,
                body.file_reference,
                body.status,
                body.notes,
                actor_user_id,
                actor_user_id,
                now,
                now,
            ),
        )
        row = _get_document_row(conn, document_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="accounting_document.create",
            target_type="accounting_document",
            target_id=document_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            after=_document_from_row(row).model_dump(mode="json"),
            reason=reason,
        )
    return _document_from_row(row)


def update_document(
    document_id: str,
    body: AccountingDocumentRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
    reason: str | None = None,
) -> AccountingDocumentResponse:
    """Replace an accounting document reference and audit old/new values."""
    now = pricing.now_utc()
    with get_db() as conn:
        before = _get_document_row(conn, document_id)
        _validate_document(conn, body)
        conn.execute(
            """
            UPDATE accounting_documents
            SET document_type = ?, source_system = ?, document_number = ?, issue_date = ?,
                order_id = ?, refund_id = ?, period_id = ?, currency = ?,
                net_amount_cents = ?, tax_amount_cents = ?, gross_amount_cents = ?,
                vat_summary_json = ?, original_document_id = ?, file_reference = ?,
                status = ?, notes = ?, updated_by_admin_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                body.document_type,
                body.source_system,
                body.document_number,
                body.issue_date,
                body.order_id,
                body.refund_id,
                body.period_id,
                body.currency,
                body.net_amount_cents,
                body.tax_amount_cents,
                body.gross_amount_cents,
                _json_dumps(body.vat_summary),
                body.original_document_id,
                body.file_reference,
                body.status,
                body.notes,
                actor_user_id,
                now,
                document_id,
            ),
        )
        after = _get_document_row(conn, document_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="accounting_document.update",
            target_type="accounting_document",
            target_id=document_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=_document_from_row(before).model_dump(mode="json"),
            after=_document_from_row(after).model_dump(mode="json"),
            reason=reason,
        )
    return _document_from_row(after)
