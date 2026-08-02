"""Speedy admin service.

Thin Speedy HTTP details live in `speedy_client`. This module owns local admin
behavior: health aggregation, eligible queues, guarded actions, audit events,
metadata policy, pickup validation, and metrics.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.constants import tracking_url_for
from app.services import pricing, speedy_client
from app.services.econt_redaction import redact_mapping
from app.services.order_service import OrderNotFoundError, get_order_admin, update_status_async

_SITE_HEALTH_KEY = "speedy_admin_health"
_SITE_REFRESH_KEY = "speedy_office_refresh_status"
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class SpeedyAdminError(Exception):
    """Base class for Speedy admin service errors."""

    def __init__(self, message: str, *, blockers: list[str] | None = None) -> None:
        self.blockers = blockers or []
        super().__init__(message)


class SpeedyAdminValidationError(SpeedyAdminError):
    """Raised when local state does not permit a Speedy admin action."""


def _settings_credentials() -> tuple[str, str, str]:
    settings = get_settings()
    return (
        settings.speedy_api_username,
        settings.speedy_api_password.get_secret_value(),
        settings.speedy_client_id,
    )


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(redact_mapping(value), ensure_ascii=False, sort_keys=True)


def _loads_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _set_site_json(conn: sqlite3.Connection, key: str, value: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO site_settings (key, value, value_type, is_public, updated_at)
        VALUES (%s, %s, 'json', 0, %s)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            value_type = excluded.value_type,
            is_public = excluded.is_public,
            updated_at = excluded.updated_at
        """,
        (
            key,
            json.dumps(redact_mapping(value), ensure_ascii=False, sort_keys=True),
            pricing.now_utc(),
        ),
    )


def _get_site_json(conn: sqlite3.Connection, key: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT value FROM site_settings WHERE key = %s", (key,)).fetchone()
    value = _loads_json(row["value"] if row else None)
    return value if isinstance(value, dict) else None


def _record_event(
    conn: sqlite3.Connection,
    order_id: str,
    action: str,
    status: str,
    request_payload: Any,
    response_payload: Any,
    error_payload: Any,
    actor_user_id: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO order_courier_events (
            order_id, courier, action, status, request_json, response_json,
            error_json, actor_user_id
        ) VALUES (%s, 'speedy', %s, %s, %s, %s, %s, %s)
        """,
        (
            order_id,
            action,
            status,
            _json_or_none(request_payload),
            _json_or_none(response_payload),
            _json_or_none(error_payload),
            actor_user_id,
        ),
    )


def _persist_failure(
    conn: sqlite3.Connection,
    order_id: str,
    action: str,
    request_payload: Any,
    exc: speedy_client.SpeedyError,
    actor_user_id: str | None,
) -> None:
    safe_error = exc.to_safe_dict()
    conn.execute(
        """
        UPDATE orders
        SET courier_provider = 'speedy', courier_sync_status = 'failed', courier_last_error = %s,
            courier_last_synced_at = %s
        WHERE id = %s
        """,
        (_json_or_none(safe_error), pricing.now_utc(), order_id),
    )
    _record_event(
        conn, order_id, action, "failed", request_payload, None, safe_error, actor_user_id
    )


def _record_failure_event(
    conn: sqlite3.Connection,
    order_id: str,
    action: str,
    request_payload: Any,
    exc: speedy_client.SpeedyError,
    actor_user_id: str | None,
) -> None:
    _record_event(
        conn,
        order_id,
        action,
        "failed",
        request_payload,
        None,
        exc.to_safe_dict(),
        actor_user_id,
    )


def _safe_order(conn: sqlite3.Connection, order_id: str) -> dict[str, Any]:
    try:
        return dict(get_order_admin(conn, order_id))
    except OrderNotFoundError:
        raise


def _speedy_tracking(order: dict[str, Any]) -> str | None:
    if order.get("tracking_carrier") == "speedy" and order.get("tracking_number"):
        return str(order["tracking_number"])
    if order.get("courier_provider") == "speedy" and order.get("courier_shipment_number"):
        return str(order["courier_shipment_number"])
    return None


def _tracking_result_status_and_payload(result: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(result, dict):
        courier_status = result.get("courier_status") or result.get("status")
        if not isinstance(courier_status, str) or not courier_status:
            raise SpeedyAdminValidationError(
                "Speedy tracking result is missing courier status",
                blockers=["tracking_status_missing"],
            )
        return courier_status, dict(result)
    return str(result), {"courier_status": str(result)}


def _delivery_label(details: Any) -> str | None:
    if not isinstance(details, dict):
        return None
    if details.get("office_name"):
        return str(details["office_name"])
    pieces = [details.get("street"), details.get("building"), details.get("city")]
    return ", ".join(str(piece) for piece in pieces if piece) or None


def _row_to_summary(row: sqlite3.Row) -> dict[str, Any]:
    details = _loads_json(row["delivery_details"] if "delivery_details" in row.keys() else None)
    return {
        "order_id": row["id"],
        "order_number": row["order_number"],
        "status": row["status"],
        "customer_email": row["customer_email"],
        "customer_name": row["customer_name"],
        "delivery_method": row["delivery_method"],
        "delivery_label": _delivery_label(details),
        "total_cents": row["total_cents"],
        "tracking_number": row["tracking_number"],
        "tracking_url": row["tracking_url"],
        "courier_status": row["courier_status"],
        "courier_sync_status": row["courier_sync_status"],
        "courier_last_error": row["courier_last_error"],
        "courier_last_synced_at": row["courier_last_synced_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


async def get_health(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return safe Speedy health state without creating shipments."""
    username, password, configured_client_id = _settings_credentials()
    checked_at = pricing.now_utc()
    blockers: list[str] = []
    if not username:
        blockers.append("username_missing")
    if not password:
        blockers.append("password_missing")
    if not configured_client_id:
        blockers.append("client_id_missing")
    elif not configured_client_id.isdigit():
        blockers.append("client_id_not_numeric")

    circuit = speedy_client.get_speedy_circuit_breaker().get_health()
    previous = _get_site_json(conn, _SITE_HEALTH_KEY) or {}
    base = {
        "username_configured": bool(username),
        "password_configured": bool(password),
        "client_id_configured": bool(configured_client_id),
        "client_id_numeric": bool(configured_client_id and configured_client_id.isdigit()),
        "configured_client_id": configured_client_id or None,
        "verified_client_id": None,
        "client_id_matches": None,
        "blockers": blockers,
        "circuit": circuit,
        "last_failure_category": previous.get("last_failure_category"),
        "last_successful_check_at": previous.get("last_successful_check_at"),
        "checked_at": checked_at,
    }

    if blockers:
        return {
            **base,
            "status": "blocked",
            "ok": False,
            "message": "Speedy configuration is incomplete.",
        }

    try:
        verified_client_id = await speedy_client.get_own_client_id(
            username=username, password=password
        )
    except speedy_client.SpeedyError as exc:
        status = "unavailable" if exc.category in {"transient", "circuit_open"} else "blocked"
        health = {
            **base,
            "status": status,
            "ok": False,
            "message": str(exc),
            "last_failure_category": exc.category,
        }
        _set_site_json(
            conn,
            _SITE_HEALTH_KEY,
            {
                "last_failure_category": exc.category,
                "last_failure_at": checked_at,
                "last_successful_check_at": previous.get("last_successful_check_at"),
            },
        )
        return health

    matches = verified_client_id == configured_client_id
    health = {
        **base,
        "verified_client_id": verified_client_id,
        "client_id_matches": matches,
        "status": "healthy" if matches else "warning",
        "ok": matches,
        "message": "Speedy configuration is healthy." if matches else "Speedy client id mismatch.",
        "last_failure_category": None,
        "last_successful_check_at": checked_at,
    }
    _set_site_json(
        conn,
        _SITE_HEALTH_KEY,
        {"last_successful_check_at": checked_at, "last_failure_category": None},
    )
    return health


def get_queues(conn: sqlite3.Connection, *, order_id: str | None = None) -> dict[str, Any]:
    params: list[Any] = []
    focus_sql = ""
    if order_id:
        focus_sql = " AND id = %s"
        params.append(order_id)

    ready_rows = conn.execute(
        f"""
        SELECT * FROM orders
        WHERE delivery_courier = 'speedy' AND status = 'confirmed'
          AND (tracking_number IS NULL OR TRIM(tracking_number) = '')
          AND (courier_shipment_number IS NULL OR TRIM(courier_shipment_number) = '')
          {focus_sql}
        ORDER BY created_at DESC
        LIMIT 50
        """,  # noqa: S608 - focus_sql is controlled static SQL.
        params,
    ).fetchall()

    shipped_rows = conn.execute(
        f"""
        SELECT * FROM orders
        WHERE status = 'shipped'
          AND (tracking_carrier = 'speedy' OR courier_provider = 'speedy')
          AND COALESCE(NULLIF(tracking_number, ''), NULLIF(courier_shipment_number, '')) IS NOT NULL
          {focus_sql}
        ORDER BY updated_at DESC
        LIMIT 50
        """,  # noqa: S608 - focus_sql is controlled static SQL.
        params,
    ).fetchall()
    return {
        "ready_to_ship": [_row_to_summary(row) for row in ready_rows],
        "shipped": [_row_to_summary(row) for row in shipped_rows],
    }


async def create_or_reuse_waybill(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    order = _safe_order(conn, order_id)
    if order["delivery_courier"] != "speedy":
        raise SpeedyAdminValidationError(
            "Order is not assigned to Speedy", blockers=["order_not_speedy"]
        )
    existing = _speedy_tracking(order)
    if existing:
        _record_event(
            conn,
            order_id,
            "create_waybill",
            "skipped",
            {"order_id": order_id},
            {"reason": "shipment_already_exists", "shipmentNumber": existing},
            None,
            actor_user_id,
        )
        return {
            "order_id": order_id,
            "action": "create_waybill",
            "status": "existing",
            "shipment_number": existing,
            "tracking_url": order.get("tracking_url") or tracking_url_for("speedy", existing),
            "status_updated_to": order["status"],
        }
    if order["status"] != "confirmed":
        raise SpeedyAdminValidationError(
            "Speedy waybill can only be created for confirmed orders",
            blockers=["order_status_not_supported"],
        )

    try:
        shipped = await update_status_async(conn, order_id, "shipped")
    except speedy_client.SpeedyError as exc:
        _persist_failure(
            conn, order_id, "create_waybill", {"order_id": order_id}, exc, actor_user_id
        )
        raise

    shipment_number = shipped["tracking_number"]
    response = {
        "status": "created",
        "shipment_number": shipment_number,
        "tracking_url": shipped["tracking_url"],
        "status_updated_to": shipped["status"],
    }
    _record_event(
        conn,
        order_id,
        "create_waybill",
        "success",
        {"order_id": order_id},
        response,
        None,
        actor_user_id,
    )
    return {"order_id": order_id, "action": "create_waybill", **response}


async def print_order_label(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    actor_user_id: str | None = None,
    print_label_func: Any | None = None,
) -> tuple[str, bytes]:
    order = _safe_order(conn, order_id)
    shipment_number = _speedy_tracking(order)
    if not shipment_number:
        raise SpeedyAdminValidationError(
            "Order has no Speedy waybill", blockers=["no_speedy_waybill"]
        )
    username, password, _client_id = _settings_credentials()
    request_payload = {"shipmentNumber": shipment_number, "paperSize": "A6"}
    try:
        label_client = print_label_func or speedy_client.print_label
        pdf = await label_client(
            tracking_number=shipment_number,
            username=username,
            password=password,
        )
    except speedy_client.SpeedyError as exc:
        _persist_failure(conn, order_id, "print_label", request_payload, exc, actor_user_id)
        raise
    _record_event(
        conn,
        order_id,
        "print_label",
        "success",
        request_payload,
        {"bytes": len(pdf), "content_type": "application/pdf"},
        None,
        actor_user_id,
    )
    return shipment_number, pdf


async def refresh_tracking(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    actor_user_id: str | None = None,
    track_shipment_func: Any | None = None,
) -> dict[str, Any]:
    order = _safe_order(conn, order_id)
    shipment_number = _speedy_tracking(order)
    if not shipment_number:
        raise SpeedyAdminValidationError(
            "Order has no Speedy waybill", blockers=["no_speedy_waybill"]
        )
    username, password, _client_id = _settings_credentials()
    request_payload = {"shipmentNumber": shipment_number}
    try:
        tracking_client = track_shipment_func or speedy_client.track_shipment_with_details
        tracking_result = await tracking_client(
            tracking_number=shipment_number,
            username=username,
            password=password,
        )
    except speedy_client.SpeedyError as exc:
        _persist_failure(conn, order_id, "refresh_tracking", request_payload, exc, actor_user_id)
        raise

    courier_status, response_payload = _tracking_result_status_and_payload(tracking_result)
    now = pricing.now_utc()
    conn.execute(
        """
        UPDATE orders
        SET courier_provider = 'speedy', courier_status = %s, courier_sync_status = 'track_synced',
            courier_last_error = NULL, courier_last_synced_at = %s
        WHERE id = %s
        """,
        (courier_status, now, order_id),
    )
    _record_event(
        conn,
        order_id,
        "refresh_tracking",
        "success",
        request_payload,
        response_payload,
        None,
        actor_user_id,
    )
    if courier_status in {"returned", "failed"}:
        _record_return_review_signal(conn, order_id, courier_status)
    return {
        "order_id": order_id,
        "action": "refresh_tracking",
        "status": "success",
        "shipment_number": shipment_number,
        "courier_status": courier_status,
    }


async def search_shipments(
    conn: sqlite3.Connection,
    reference: str,
    *,
    include_returns: bool = False,
    shipments_only: bool = True,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    username, password, _client_id = _settings_credentials()
    request_payload = {
        "reference": reference,
        "include_returns": include_returns,
        "shipments_only": shipments_only,
    }
    try:
        barcodes = await speedy_client.find_parcels_by_reference(
            reference,
            username=username,
            password=password,
            include_returns=include_returns,
            shipments_only=shipments_only,
        )
    except speedy_client.SpeedyError as exc:
        _record_search_failure_if_local(conn, reference, request_payload, exc, actor_user_id)
        raise
    _record_search_success_if_local(
        conn, reference, request_payload, {"barcodes": barcodes}, actor_user_id
    )
    return {"reference": reference, "barcodes": barcodes}


async def shipment_info(
    conn: sqlite3.Connection,
    shipment_ids: list[str],
    *,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    username, password, _client_id = _settings_credentials()
    request_payload = {"shipment_ids": shipment_ids}
    try:
        shipments = await speedy_client.get_shipment_info(
            shipment_ids,
            username=username,
            password=password,
        )
    except speedy_client.SpeedyError as exc:
        order_id = _order_id_for_shipment(conn, shipment_ids[0] if shipment_ids else "")
        if order_id:
            _persist_failure(conn, order_id, "shipment_info", request_payload, exc, actor_user_id)
        raise
    order_id = _order_id_for_shipment(conn, shipment_ids[0] if shipment_ids else "")
    if order_id:
        _record_event(
            conn,
            order_id,
            "shipment_info",
            "success",
            request_payload,
            {"shipments": shipments},
            None,
            actor_user_id,
        )
    return {"shipments": shipments}


async def cancel_order_shipment(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    comment: str | None = None,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    order = _safe_order(conn, order_id)
    shipment_number = _speedy_tracking(order)
    blockers: list[str] = []
    if order["delivery_courier"] != "speedy" and order.get("tracking_carrier") != "speedy":
        blockers.append("order_not_speedy")
    if not shipment_number:
        blockers.append("no_speedy_waybill")
    if order["status"] in {"delivered", "returned", "cancelled"}:
        blockers.append("order_status_not_cancellable")
    if order.get("courier_sync_status") == "shipment_cancelled":
        blockers.append("shipment_already_cancelled")
    if blockers:
        raise SpeedyAdminValidationError("Speedy shipment cannot be cancelled", blockers=blockers)
    if shipment_number is None:
        raise SpeedyAdminValidationError(
            "Speedy shipment cannot be cancelled",
            blockers=["no_speedy_waybill"],
        )

    username, password, _client_id = _settings_credentials()
    request_payload = {"shipmentId": shipment_number, "comment": comment}
    try:
        response = await speedy_client.cancel_shipment(
            shipment_number,
            username=username,
            password=password,
            comment=comment,
        )
    except speedy_client.SpeedyError as exc:
        _record_failure_event(
            conn, order_id, "cancel_shipment", request_payload, exc, actor_user_id
        )
        raise

    now = pricing.now_utc()
    conn.execute(
        """
        UPDATE orders
        SET courier_provider = 'speedy', courier_sync_status = 'shipment_cancelled',
            courier_status = 'cancelled', courier_last_error = NULL, courier_last_synced_at = %s
        WHERE id = %s
        """,
        (now, order_id),
    )
    _record_event(
        conn,
        order_id,
        "cancel_shipment",
        "success",
        request_payload,
        response,
        None,
        actor_user_id,
    )
    return {
        "order_id": order_id,
        "action": "cancel_shipment",
        "status": "cancelled",
        "shipment_number": shipment_number,
        "details": response,
    }


async def pickup_terms_for_shipments(
    conn: sqlite3.Connection,
    shipment_ids: list[str],
    *,
    starting_date_utc_ms: int | None = None,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    order_ids = _eligible_pickup_order_ids(conn, shipment_ids)
    username, password, client_id = _settings_credentials()
    request_payload = {"shipment_ids": shipment_ids, "starting_date_utc_ms": starting_date_utc_ms}
    try:
        cutoffs = await speedy_client.pickup_terms(
            client_id=client_id,
            username=username,
            password=password,
            starting_date_utc_ms=starting_date_utc_ms,
        )
    except speedy_client.SpeedyError as exc:
        for order_id in order_ids:
            _persist_failure(conn, order_id, "pickup_terms", request_payload, exc, actor_user_id)
        raise
    for order_id in order_ids:
        _record_event(
            conn,
            order_id,
            "pickup_terms",
            "success",
            request_payload,
            {"cutoffs": cutoffs},
            None,
            actor_user_id,
        )
    return {"cutoffs": cutoffs}


async def request_pickup(
    conn: sqlite3.Connection,
    *,
    shipment_ids: list[str],
    pickup_datetime: str,
    visit_end_time: str,
    contact_name: str,
    phone: str,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    order_ids = _eligible_pickup_order_ids(conn, shipment_ids)
    username, password, _client_id = _settings_credentials()
    request_payload = {
        "shipment_ids": shipment_ids,
        "pickup_datetime": pickup_datetime,
        "visit_end_time": visit_end_time,
        "contact_name": contact_name,
        "phone": phone,
    }
    try:
        orders = await speedy_client.request_pickup(
            shipment_ids=shipment_ids,
            pickup_datetime=pickup_datetime,
            visit_end_time=visit_end_time,
            contact_name=contact_name,
            phone=phone,
            username=username,
            password=password,
        )
    except speedy_client.SpeedyError as exc:
        for order_id in order_ids:
            _persist_failure(conn, order_id, "request_pickup", request_payload, exc, actor_user_id)
        raise
    for order_id in order_ids:
        _record_event(
            conn,
            order_id,
            "request_pickup",
            "success",
            request_payload,
            {"orders": orders},
            None,
            actor_user_id,
        )
    return {"orders": orders}


def list_events(conn: sqlite3.Connection, *, limit: int = 25) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, order_id, action, status, request_json, response_json, error_json,
               actor_user_id, created_at
        FROM order_courier_events
        WHERE courier = 'speedy'
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "order_id": row["order_id"],
            "action": row["action"],
            "status": row["status"],
            "request": _loads_json(row["request_json"]),
            "response": _loads_json(row["response_json"]),
            "error": _loads_json(row["error_json"]),
            "actor_user_id": row["actor_user_id"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_metrics(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT action, status, error_json
        FROM order_courier_events
        WHERE courier = 'speedy' AND created_at >= datetime('now', '-30 days')
        """
    ).fetchall()
    failures_by_category: Counter[str] = Counter()
    successes = 0
    failures = 0
    cancellation_count = 0
    pickup_request_count = 0
    for row in rows:
        if row["status"] in {"success", "skipped"}:
            successes += 1
        if row["status"] == "failed":
            failures += 1
            error = _loads_json(row["error_json"])
            category = error.get("category") if isinstance(error, dict) else None
            failures_by_category[str(category or "unknown")] += 1
        if row["action"] == "cancel_shipment" and row["status"] == "success":
            cancellation_count += 1
        if row["action"] == "request_pickup" and row["status"] == "success":
            pickup_request_count += 1
    health = _get_site_json(conn, _SITE_HEALTH_KEY) or {}
    return {
        "recent_successes": successes,
        "recent_failures": failures,
        "failures_by_category": dict(failures_by_category),
        "cancellation_count": cancellation_count,
        "pickup_request_count": pickup_request_count,
        "last_successful_health_check_at": health.get("last_successful_check_at"),
    }


def get_office_refresh_status(conn: sqlite3.Connection) -> dict[str, Any]:
    stored = _get_site_json(conn, _SITE_REFRESH_KEY)
    if stored is not None:
        return stored
    status_path = _DATA_DIR / "courier_refresh_status.json"
    try:
        refresh_status = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        refresh_status = None
    if isinstance(refresh_status, dict) and isinstance(refresh_status.get("speedy"), dict):
        return refresh_status["speedy"]
    path = _DATA_DIR / "speedy_offices.json"
    if not path.exists():
        return {"status": None, "refreshed_at": None, "records": None, "error": None}
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "unknown", "refreshed_at": None, "records": None, "error": "unreadable"}
    return {
        "status": "unknown",
        "refreshed_at": None,
        "records": len(records) if isinstance(records, list) else None,
        "error": None,
    }


def record_office_refresh_status(
    conn: sqlite3.Connection,
    *,
    status: str,
    records: int | None = None,
    error: str | None = None,
) -> None:
    _set_site_json(
        conn,
        _SITE_REFRESH_KEY,
        {"status": status, "refreshed_at": pricing.now_utc(), "records": records, "error": error},
    )


async def get_overview(conn: sqlite3.Connection, *, order_id: str | None = None) -> dict[str, Any]:
    return {
        "health": await get_health(conn),
        "queues": get_queues(conn, order_id=order_id),
        "events": list_events(conn),
        "metrics": get_metrics(conn),
        "office_refresh": get_office_refresh_status(conn),
    }


def _order_id_for_shipment(conn: sqlite3.Connection, shipment_id: str) -> str | None:
    if not shipment_id:
        return None
    row = conn.execute(
        """
        SELECT id FROM orders
        WHERE (tracking_carrier = 'speedy' AND tracking_number = %s)
           OR (courier_provider = 'speedy' AND courier_shipment_number = %s)
        LIMIT 1
        """,
        (shipment_id, shipment_id),
    ).fetchone()
    return row["id"] if row else None


def _record_search_success_if_local(
    conn: sqlite3.Connection,
    reference: str,
    request_payload: Any,
    response_payload: Any,
    actor_user_id: str | None,
) -> None:
    row = conn.execute(
        "SELECT id FROM orders WHERE id = %s OR order_number = %s", (reference, reference)
    ).fetchone()
    if row:
        _record_event(
            conn,
            row["id"],
            "shipment_search",
            "success",
            request_payload,
            response_payload,
            None,
            actor_user_id,
        )


def _record_search_failure_if_local(
    conn: sqlite3.Connection,
    reference: str,
    request_payload: Any,
    exc: speedy_client.SpeedyError,
    actor_user_id: str | None,
) -> None:
    row = conn.execute(
        "SELECT id FROM orders WHERE id = %s OR order_number = %s", (reference, reference)
    ).fetchone()
    if row:
        _persist_failure(conn, row["id"], "shipment_search", request_payload, exc, actor_user_id)


def _eligible_pickup_order_ids(conn: sqlite3.Connection, shipment_ids: list[str]) -> list[str]:
    normalized_ids = [str(item).strip() for item in shipment_ids if str(item).strip()]
    if not normalized_ids:
        raise SpeedyAdminValidationError(
            "At least one shipment is required", blockers=["shipment_ids_missing"]
        )
    order_ids: list[str] = []
    blockers: list[str] = []
    for shipment_id in normalized_ids:
        row = conn.execute(
            """
            SELECT id, status, courier_sync_status FROM orders
            WHERE (tracking_carrier = 'speedy' AND tracking_number = %s)
               OR (courier_provider = 'speedy' AND courier_shipment_number = %s)
            LIMIT 1
            """,
            (shipment_id, shipment_id),
        ).fetchone()
        if row is None:
            blockers.append(f"shipment_not_local:{shipment_id}")
            continue
        if row["status"] not in {"shipped", "confirmed"}:
            blockers.append(f"shipment_status_not_eligible:{shipment_id}")
        if row["courier_sync_status"] == "shipment_cancelled":
            blockers.append(f"shipment_cancelled:{shipment_id}")
        order_ids.append(row["id"])
    if blockers:
        raise SpeedyAdminValidationError("Shipment is not eligible for pickup", blockers=blockers)
    return order_ids


def _record_return_review_signal(
    conn: sqlite3.Connection, order_id: str, courier_status: str
) -> None:
    """Hook Speedy return/failed tracking into the active returns workflow.

    The parallel returns/refunds change owns the actual return workflow. This
    hook records a lightweight Speedy-sourced return case only if no return case
    exists yet, leaving all refund/restock decisions to admins.
    """
    try:
        from app.services import return_service
    except ImportError:
        return
    existing = conn.execute(
        "SELECT id FROM order_returns WHERE order_id = %s LIMIT 1", (order_id,)
    ).fetchone()
    if existing is not None:
        return
    reason = "not_picked_up" if courier_status == "returned" else "other"
    return_service.create_return_case(
        conn,
        order_id=order_id,
        reason=reason,
        source="speedy",
        status="requested",
        notes=f"Speedy tracking reported {courier_status}.",
    )
