"""Return case service for admin-controlled returns and restocking."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from app.services.order_service import (
    _insert_inventory_exception,
    _is_ledger_managed_mode,
    _order_item_key,
    _product_inventory_mode,
    _record_finished_good_movement,
)

_DT_FMT = "%Y-%m-%d %H:%M:%S"

ReturnReason = Literal[
    "not_picked_up",
    "refused_delivery",
    "customer_return",
    "wrong_address",
    "unreachable_customer",
    "damaged_by_courier",
    "lost_by_courier",
    "merchant_error",
    "other",
]
ReturnSource = Literal["admin", "speedy", "econt", "customer", "stripe", "system"]
ReturnStatus = Literal[
    "requested",
    "return_in_transit",
    "received",
    "inspected",
    "rejected",
    "closed",
]
RestockDecision = Literal["pending", "restock", "do_not_restock", "partial"]

VALID_RETURN_REASONS: frozenset[str] = frozenset(ReturnReason.__args__)  # type: ignore[attr-defined]
VALID_RETURN_SOURCES: frozenset[str] = frozenset(ReturnSource.__args__)  # type: ignore[attr-defined]
VALID_RETURN_STATUSES: frozenset[str] = frozenset(ReturnStatus.__args__)  # type: ignore[attr-defined]
VALID_RESTOCK_DECISIONS: frozenset[str] = frozenset(RestockDecision.__args__)  # type: ignore[attr-defined]

RETURN_TRANSITIONS: dict[str, set[str]] = {
    "requested": {"return_in_transit", "received", "rejected", "closed"},
    "return_in_transit": {"received", "rejected"},
    "received": {"inspected", "rejected"},
    "inspected": {"closed"},
    "rejected": {"closed"},
    "closed": set(),
}


class ReturnServiceError(Exception):
    """Base class for return workflow errors."""


class ReturnCaseNotFoundError(ReturnServiceError):
    def __init__(self, return_id: str) -> None:
        self.return_id = return_id
        super().__init__(f"Return case not found: {return_id}")


class InvalidReturnValueError(ReturnServiceError):
    def __init__(self, field: str, value: str) -> None:
        self.field = field
        self.value = value
        super().__init__(f"Invalid {field}: {value}")


class InvalidReturnTransitionError(ReturnServiceError):
    def __init__(self, return_id: str, current_status: str, requested_status: str) -> None:
        self.return_id = return_id
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__(
            f"Invalid return transition from '{current_status}' to '{requested_status}'"
        )


class InvalidRestockQuantityError(ReturnServiceError):
    def __init__(self, product_id: str, quantity: int, max_quantity: int) -> None:
        self.product_id = product_id
        self.quantity = quantity
        self.max_quantity = max_quantity
        super().__init__(
            f"Invalid restock quantity for {product_id}: {quantity} exceeds {max_quantity}"
        )


def _now() -> str:
    return datetime.now(UTC).strftime(_DT_FMT)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _validate_choice(field: str, value: str, valid: frozenset[str]) -> None:
    if value not in valid:
        raise InvalidReturnValueError(field, value)


def _append_return_event(
    conn: sqlite3.Connection,
    *,
    order_return_id: str | None,
    order_id: str,
    event_type: str,
    source: str,
    payload: dict[str, Any],
    admin_id: str | None,
    admin_email: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO order_return_events (
            id, order_return_id, order_id, event_type, source, payload_json,
            admin_user_id, admin_email
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            order_return_id,
            order_id,
            event_type,
            source,
            json.dumps(payload, separators=(",", ":")),
            admin_id,
            admin_email,
        ),
    )


def _get_return_case(conn: sqlite3.Connection, return_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM order_returns WHERE id = ?", (return_id,)).fetchone()
    if row is None:
        raise ReturnCaseNotFoundError(return_id)
    return row


def get_return_case(conn: sqlite3.Connection, return_id: str) -> dict[str, Any]:
    """Return a return case row as a plain dict."""
    return _row_to_dict(_get_return_case(conn, return_id))


def list_return_cases_for_order(conn: sqlite3.Connection, order_id: str) -> list[dict[str, Any]]:
    """List return cases for admin order detail payloads."""
    rows = conn.execute(
        "SELECT * FROM order_returns WHERE order_id = ? ORDER BY created_at ASC, id ASC",
        (order_id,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_return_events_for_order(conn: sqlite3.Connection, order_id: str) -> list[dict[str, Any]]:
    """List return audit events for admin order detail payloads."""
    rows = conn.execute(
        """
        SELECT * FROM order_return_events
        WHERE order_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (order_id,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_refunds_for_order(conn: sqlite3.Connection, order_id: str) -> list[dict[str, Any]]:
    """List refund records for admin order detail payloads."""
    rows = conn.execute(
        """
        SELECT * FROM payment_refunds
        WHERE order_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (order_id,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_cod_settlement_for_order(conn: sqlite3.Connection, order_id: str) -> dict[str, Any] | None:
    """Return a COD settlement row for admin order detail payloads."""
    row = conn.execute("SELECT * FROM cod_settlements WHERE order_id = ?", (order_id,)).fetchone()
    return _row_to_dict(row) if row is not None else None


def cod_settlement_required_for_order(conn: sqlite3.Connection, order_id: str) -> bool:
    """Return True when a delivered COD order has no explicit settlement record."""
    row = conn.execute(
        "SELECT status, payment_method FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if row is None:
        raise InvalidReturnValueError("order_id", order_id)
    if row["payment_method"] != "cod" or row["status"] != "delivered":
        return False
    settlement = conn.execute(
        "SELECT 1 FROM cod_settlements WHERE order_id = ?",
        (order_id,),
    ).fetchone()
    return settlement is None


def record_cod_settlement(
    conn: sqlite3.Connection,
    *,
    order_id: str,
    amount_cents: int,
    settlement_date: str,
    courier_reference: str | None = None,
    notes: str | None = None,
    admin_id: str | None = None,
) -> dict[str, Any]:
    """Record or replace explicit COD settlement details for a delivered COD order."""
    if amount_cents < 0:
        raise InvalidReturnValueError("amount_cents", str(amount_cents))
    if not settlement_date:
        raise InvalidReturnValueError("settlement_date", settlement_date)
    order = conn.execute(
        "SELECT id, status, payment_method, total_cents FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if order is None:
        raise InvalidReturnValueError("order_id", order_id)
    if order["payment_method"] != "cod":
        raise InvalidReturnValueError("payment_method", order["payment_method"])
    if order["status"] != "delivered":
        raise InvalidReturnValueError("status", order["status"])

    mismatch_review = 1 if int(amount_cents) != int(order["total_cents"]) else 0
    settlement_id = str(uuid.uuid4())
    now = _now()
    conn.execute(
        """
        INSERT INTO cod_settlements (
            id, order_id, amount_cents, settlement_date, courier_reference, notes,
            mismatch_review, created_by_admin_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(order_id) DO UPDATE SET
            amount_cents = excluded.amount_cents,
            settlement_date = excluded.settlement_date,
            courier_reference = excluded.courier_reference,
            notes = excluded.notes,
            mismatch_review = excluded.mismatch_review,
            created_by_admin_id = excluded.created_by_admin_id,
            updated_at = excluded.updated_at
        """,
        (
            settlement_id,
            order_id,
            amount_cents,
            settlement_date,
            courier_reference,
            notes,
            mismatch_review,
            admin_id,
            now,
            now,
        ),
    )
    row = conn.execute("SELECT * FROM cod_settlements WHERE order_id = ?", (order_id,)).fetchone()
    return _row_to_dict(row)


def update_return_accounting(
    conn: sqlite3.Connection,
    return_id: str,
    *,
    courier_return_fee_cents: int | None = None,
    courier_claim_id: str | None = None,
    courier_claim_status: str | None = None,
    courier_claim_amount_cents: int | None = None,
    notes: str | None = None,
    admin_id: str | None = None,
    admin_email: str | None = None,
) -> dict[str, Any]:
    """Record courier fee and manual claim details without calling courier APIs."""
    row = _get_return_case(conn, return_id)
    assignments = ["updated_by_admin_id = ?"]
    params: list[Any] = [admin_id]
    payload: dict[str, Any] = {}

    if courier_return_fee_cents is not None:
        if courier_return_fee_cents < 0:
            raise InvalidReturnValueError("courier_return_fee_cents", str(courier_return_fee_cents))
        assignments.append("courier_return_fee_cents = ?")
        params.append(courier_return_fee_cents)
        payload["courier_return_fee_cents"] = courier_return_fee_cents
    if courier_claim_id is not None:
        assignments.append("courier_claim_id = ?")
        params.append(courier_claim_id)
        payload["courier_claim_id"] = courier_claim_id
    if courier_claim_status is not None:
        _validate_choice(
            "courier_claim_status",
            courier_claim_status,
            frozenset({"none", "filed", "approved", "rejected", "paid"}),
        )
        assignments.append("courier_claim_status = ?")
        params.append(courier_claim_status)
        payload["courier_claim_status"] = courier_claim_status
    if courier_claim_amount_cents is not None:
        if courier_claim_amount_cents < 0:
            raise InvalidReturnValueError("courier_claim_amount_cents", str(courier_claim_amount_cents))
        assignments.append("courier_claim_amount_cents = ?")
        params.append(courier_claim_amount_cents)
        payload["courier_claim_amount_cents"] = courier_claim_amount_cents
    if notes is not None:
        assignments.append("notes = ?")
        params.append(notes)
        payload["notes"] = notes

    if not payload:
        raise InvalidReturnValueError("accounting_update", "empty")

    params.append(return_id)
    conn.execute(
        f"UPDATE order_returns SET {', '.join(assignments)} WHERE id = ?",  # noqa: S608
        params,
    )
    _append_return_event(
        conn,
        order_return_id=return_id,
        order_id=row["order_id"],
        event_type="return_accounting_updated",
        source="admin",
        payload=payload,
        admin_id=admin_id,
        admin_email=admin_email,
    )
    return get_return_case(conn, return_id)


def create_return_case(
    conn: sqlite3.Connection,
    *,
    order_id: str,
    reason: str,
    source: str = "admin",
    status: str = "requested",
    notes: str | None = None,
    refund_amount_cents: int | None = None,
    courier_return_fee_cents: int = 0,
    courier_claim_id: str | None = None,
    courier_claim_status: str = "none",
    courier_claim_amount_cents: int | None = None,
    admin_id: str | None = None,
    admin_email: str | None = None,
) -> dict[str, Any]:
    """Create a return case and its audit event on the same DB connection."""
    _validate_choice("reason", reason, VALID_RETURN_REASONS)
    _validate_choice("source", source, VALID_RETURN_SOURCES)
    _validate_choice("status", status, VALID_RETURN_STATUSES)
    _validate_choice(
        "courier_claim_status",
        courier_claim_status,
        frozenset({"none", "filed", "approved", "rejected", "paid"}),
    )
    if refund_amount_cents is not None and refund_amount_cents < 0:
        raise InvalidReturnValueError("refund_amount_cents", str(refund_amount_cents))
    if courier_return_fee_cents < 0:
        raise InvalidReturnValueError("courier_return_fee_cents", str(courier_return_fee_cents))
    if courier_claim_amount_cents is not None and courier_claim_amount_cents < 0:
        raise InvalidReturnValueError("courier_claim_amount_cents", str(courier_claim_amount_cents))

    order = conn.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        raise InvalidReturnValueError("order_id", order_id)

    return_id = str(uuid.uuid4())
    now = _now()
    returned_at = now if status == "return_in_transit" else None
    conn.execute(
        """
        INSERT INTO order_returns (
            id, order_id, reason, source, status, refund_amount_cents,
            courier_return_fee_cents, courier_claim_id, courier_claim_status,
            courier_claim_amount_cents, restock_decision, returned_at, notes,
            created_by_admin_id, updated_by_admin_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (
            return_id,
            order_id,
            reason,
            source,
            status,
            refund_amount_cents,
            courier_return_fee_cents,
            courier_claim_id,
            courier_claim_status,
            courier_claim_amount_cents,
            returned_at,
            notes,
            admin_id,
            admin_id,
        ),
    )
    _append_return_event(
        conn,
        order_return_id=return_id,
        order_id=order_id,
        event_type="return_created",
        source=source,
        payload={"reason": reason, "status": status, "notes": notes},
        admin_id=admin_id,
        admin_email=admin_email,
    )
    return get_return_case(conn, return_id)


def _transition_return_case(
    conn: sqlite3.Connection,
    *,
    return_id: str,
    new_status: str,
    event_type: str,
    timestamp_column: str | None,
    payload: dict[str, Any],
    admin_id: str | None,
    admin_email: str | None,
) -> dict[str, Any]:
    _validate_choice("status", new_status, VALID_RETURN_STATUSES)
    row = _get_return_case(conn, return_id)
    current_status = row["status"]
    if new_status not in RETURN_TRANSITIONS.get(current_status, set()):
        raise InvalidReturnTransitionError(return_id, current_status, new_status)

    assignments = ["status = ?", "updated_by_admin_id = ?"]
    params: list[Any] = [new_status, admin_id]
    if timestamp_column:
        assignments.append(f"{timestamp_column} = COALESCE({timestamp_column}, ?)")
        params.append(_now())
    params.append(return_id)
    conn.execute(
        f"UPDATE order_returns SET {', '.join(assignments)} WHERE id = ?",  # noqa: S608
        params,
    )
    _append_return_event(
        conn,
        order_return_id=return_id,
        order_id=row["order_id"],
        event_type=event_type,
        source="admin",
        payload={"old_status": current_status, "new_status": new_status, **payload},
        admin_id=admin_id,
        admin_email=admin_email,
    )
    return get_return_case(conn, return_id)


def receive_return_case(
    conn: sqlite3.Connection,
    return_id: str,
    *,
    admin_id: str | None = None,
    admin_email: str | None = None,
) -> dict[str, Any]:
    """Mark a return received. Stock stays unchanged until inspection."""
    return _transition_return_case(
        conn,
        return_id=return_id,
        new_status="received",
        event_type="return_received",
        timestamp_column="received_at",
        payload={},
        admin_id=admin_id,
        admin_email=admin_email,
    )


def _ordered_quantities(conn: sqlite3.Connection, order_id: str) -> dict[str, int]:
    rows = conn.execute(
        "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    return {row["product_id"]: row["quantity"] for row in rows}


def _restock_quantities_for_decision(
    ordered: dict[str, int],
    decision: str,
    restock_quantities: dict[str, int] | None,
) -> dict[str, int]:
    _validate_choice("restock_decision", decision, VALID_RESTOCK_DECISIONS)
    if decision == "pending":
        raise InvalidReturnValueError("restock_decision", decision)
    if decision == "do_not_restock":
        return {}
    if decision == "restock":
        return dict(ordered)
    if not restock_quantities:
        raise InvalidReturnValueError("restock_quantities", "required_for_partial")

    normalized: dict[str, int] = {}
    for product_id, quantity in restock_quantities.items():
        max_quantity = ordered.get(product_id, 0)
        if quantity < 1 or quantity > max_quantity:
            raise InvalidRestockQuantityError(product_id, quantity, max_quantity)
        normalized[product_id] = quantity
    return normalized


def inspect_return_case(
    conn: sqlite3.Connection,
    return_id: str,
    *,
    restock_decision: str,
    restock_quantities: dict[str, int] | None = None,
    notes: str | None = None,
    admin_id: str | None = None,
    admin_email: str | None = None,
) -> dict[str, Any]:
    """Inspect a received return and apply explicit restock adjustments."""
    row = _get_return_case(conn, return_id)
    if row["status"] != "received":
        raise InvalidReturnTransitionError(return_id, row["status"], "inspected")

    ordered = _ordered_quantities(conn, row["order_id"])
    quantities = _restock_quantities_for_decision(ordered, restock_decision, restock_quantities)
    non_restock_quantities = {
        product_id: ordered_quantity - quantities.get(product_id, 0)
        for product_id, ordered_quantity in ordered.items()
        if ordered_quantity - quantities.get(product_id, 0) > 0
    }
    now = _now()
    reason = "return_restock" if restock_decision == "restock" else "return_partial_restock"
    for product_id, quantity in quantities.items():
        if _is_ledger_managed_mode(_product_inventory_mode(conn, product_id)):
            _record_finished_good_movement(
                conn,
                product_id=product_id,
                movement_type="return_restock",
                quantity_delta=quantity,
                source_type="order_return",
                source_id=return_id,
                order_id=row["order_id"],
                order_item_key=_order_item_key(row["order_id"], product_id),
                actor_user_id=admin_id,
                actor_email=admin_email,
                reason=reason,
                notes=notes,
                review_state="reviewed",
                occurred_at=now,
                metadata={"restock_decision": restock_decision},
            )
        else:
            cursor = conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (quantity, product_id),
            )
            if cursor.rowcount == 0:
                raise InvalidReturnValueError("product_id", product_id)
            conn.execute(
                """
                INSERT INTO inventory_adjustments (
                    id, order_id, order_return_id, product_id, quantity, reason,
                    source, notes, created_by_admin_id
                ) VALUES (?, ?, ?, ?, ?, ?, 'admin', ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    row["order_id"],
                    return_id,
                    product_id,
                    quantity,
                    reason,
                    notes,
                    admin_id,
                ),
            )

    for product_id, quantity in non_restock_quantities.items():
        if not _is_ledger_managed_mode(_product_inventory_mode(conn, product_id)):
            continue
        key = _order_item_key(row["order_id"], product_id)
        received_movement_id = _record_finished_good_movement(
            conn,
            product_id=product_id,
            movement_type="return_restock",
            quantity_delta=quantity,
            source_type="order_return",
            source_id=return_id,
            order_id=row["order_id"],
            order_item_key=key,
            actor_user_id=admin_id,
            actor_email=admin_email,
            reason="return_received_for_write_off",
            notes=notes,
            review_state="unreviewed",
            occurred_at=now,
            metadata={"restock_decision": restock_decision, "write_off_pending": True},
        )
        _record_finished_good_movement(
            conn,
            product_id=product_id,
            movement_type="return_write_off",
            quantity_delta=-quantity,
            source_type="order_return",
            source_id=return_id,
            order_id=row["order_id"],
            order_item_key=key,
            actor_user_id=admin_id,
            actor_email=admin_email,
            reason="return_not_restocked",
            notes=notes,
            reversal_of_movement_id=received_movement_id,
            review_state="unreviewed",
            occurred_at=now,
            metadata={"restock_decision": restock_decision},
        )
        _insert_inventory_exception(
            conn,
            exception_type="returned_item_write_off_review",
            message="Returned ledger-managed item was not restocked and needs write-off review.",
            target_type="product",
            target_id=product_id,
            source_type="order_return",
            source_id=return_id,
        )

    conn.execute(
        """
        UPDATE order_returns
        SET status = 'inspected', restock_decision = ?, inspected_at = COALESCE(inspected_at, ?),
            notes = COALESCE(?, notes), updated_by_admin_id = ?
        WHERE id = ?
        """,
        (restock_decision, now, notes, admin_id, return_id),
    )
    _append_return_event(
        conn,
        order_return_id=return_id,
        order_id=row["order_id"],
        event_type="return_inspected",
        source="admin",
        payload={
            "old_status": row["status"],
            "new_status": "inspected",
            "restock_decision": restock_decision,
            "restock_quantities": quantities,
            "notes": notes,
        },
        admin_id=admin_id,
        admin_email=admin_email,
    )
    return get_return_case(conn, return_id)


def close_return_case(
    conn: sqlite3.Connection,
    return_id: str,
    *,
    admin_id: str | None = None,
    admin_email: str | None = None,
) -> dict[str, Any]:
    """Close an inspected or rejected return case."""
    return _transition_return_case(
        conn,
        return_id=return_id,
        new_status="closed",
        event_type="return_closed",
        timestamp_column="closed_at",
        payload={},
        admin_id=admin_id,
        admin_email=admin_email,
    )
