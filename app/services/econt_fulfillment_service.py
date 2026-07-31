"""Econt fulfillment service.

Maps local orders to Econt payloads, validates label readiness, calls the thin
client, persists shipment metadata, and records redacted audit events.
"""

import json
import sqlite3
from typing import Any

from app.config import Settings, get_settings
from app.constants import tracking_url_for
from app.models.econt import (
    EcontCustomerInfo,
    EcontOrderItem,
    EcontOrderPayload,
    EcontSenderInfo,
)
from app.services import delivery_service, pricing
from app.services.econt_delivery_client import EcontDeliveryClient, EcontDeliveryError
from app.services.econt_redaction import redact_mapping
from app.services.order_service import OrderNotFoundError, get_order_admin, update_status

_SETTINGS_ID = "default"
_DEMO_BASE_URL = "https://delivery-demo.econt.com/services/"
_PRODUCTION_BASE_URL = "https://delivery.econt.com/services/"
_DEFAULT_WEIGHT_GRAMS = 300
_LABEL_STATUSES = {"confirmed"}
_DELIVERED_STATUS_HINTS = {"delivered", "доставена", "доставено", "получена", "получено"}


class EcontFulfillmentError(Exception):
    """Base class for Econt fulfillment errors."""

    def __init__(self, message: str, *, blockers: list[str] | None = None) -> None:
        self.blockers = blockers or []
        super().__init__(message)


class EcontFulfillmentValidationError(EcontFulfillmentError):
    """Raised when local settings/order data cannot produce a safe Econt call."""


def _settings_row(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM econt_settings WHERE id = ?", (_SETTINGS_ID,)).fetchone()
    if row is None:
        conn.execute("INSERT OR IGNORE INTO econt_settings (id) VALUES (?)", (_SETTINGS_ID,))
        row = conn.execute("SELECT * FROM econt_settings WHERE id = ?", (_SETTINGS_ID,)).fetchone()
    return row


def _base_url(settings: Settings, row: sqlite3.Row) -> str:
    if settings.econt_delivery_base_url:
        return settings.econt_delivery_base_url.rstrip("/") + "/"
    return _PRODUCTION_BASE_URL if row["environment"] == "production" else _DEMO_BASE_URL


def _private_key(settings: Settings, row: sqlite3.Row) -> str:
    if row["credential_source"] == "env":
        return settings.econt_delivery_private_key.get_secret_value()
    return ""


def _shop_id(settings: Settings, row: sqlite3.Row) -> str:
    return row["shop_id"] or settings.econt_delivery_shop_id or ""


def make_client(conn: sqlite3.Connection) -> EcontDeliveryClient:
    """Build an Econt client from current DB settings + env secrets."""
    settings = get_settings()
    row = _settings_row(conn)
    return EcontDeliveryClient(
        base_url=_base_url(settings, row),
        private_key=_private_key(settings, row),
        shop_id=_shop_id(settings, row),
    )


def validate_label_readiness(conn: sqlite3.Connection, order_id: str) -> dict[str, Any]:
    """Return readiness blockers for creating an Econt label."""
    blockers = _readiness_blockers(conn, order_id)
    return {"ready": not blockers, "blockers": blockers}


def get_fulfillment_state(conn: sqlite3.Connection, order_id: str) -> dict[str, Any]:
    """Return admin-safe Econt fulfillment state for an order."""
    order = get_order_admin(conn, order_id)
    readiness = validate_label_readiness(conn, order_id)
    return {
        "order_id": order_id,
        "ready": readiness["ready"],
        "blockers": readiness["blockers"],
        "courier_provider": order["courier_provider"],
        "courier_order_id": order["courier_order_id"],
        "courier_shipment_number": order["courier_shipment_number"],
        "courier_label_url": order["courier_label_url"],
        "courier_sync_status": order["courier_sync_status"],
        "courier_last_error": order["courier_last_error"],
        "courier_last_synced_at": order["courier_last_synced_at"],
        "tracking_number": order["tracking_number"],
        "tracking_url": order["tracking_url"],
    }


def repair_order_fields(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    office_code: str | None = None,
    recipient_phone: str | None = None,
    pack_count: int | None = None,
    shipment_description: str | None = None,
    payment_side: str | None = None,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    """Persist admin Econt repair fields on the local order before label creation."""
    order = get_order_admin(conn, order_id)
    blockers: list[str] = []
    if order["delivery_courier"] != "econt":
        blockers.append("order_not_econt")
    if order["courier_shipment_number"]:
        blockers.append("label_already_created")
    if office_code and order["delivery_method"] != "office":
        blockers.append("office_code_not_applicable")
    if blockers:
        raise EcontFulfillmentValidationError("Econt repair is not allowed", blockers=blockers)

    details = dict(order["delivery_details"] or {})
    if office_code is not None:
        details["office_code"] = office_code
    if recipient_phone is not None:
        details["phone"] = recipient_phone

    overrides = dict(details.get("econt_overrides") or {})
    if pack_count is not None:
        overrides["pack_count"] = pack_count
    if shipment_description is not None:
        overrides["shipment_description"] = shipment_description
    if payment_side is not None:
        overrides["payment_side"] = payment_side
    if overrides:
        details["econt_overrides"] = overrides

    request_payload = {
        "office_code": office_code,
        "recipient_phone": recipient_phone,
        "pack_count": pack_count,
        "shipment_description": shipment_description,
        "payment_side": payment_side,
    }

    conn.execute(
        """
        UPDATE orders
        SET delivery_details = ?, courier_sync_status = ?, courier_last_error = NULL,
            courier_last_synced_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (json.dumps(details, ensure_ascii=False), "repaired", order_id),
    )
    _record_event(
        conn,
        order_id,
        "repair_order",
        "success",
        request_payload,
        {"courier_sync_status": "repaired"},
        None,
        actor_user_id,
    )
    conn.commit()
    return get_fulfillment_state(conn, order_id)


def build_order_payload(conn: sqlite3.Connection, order_id: str) -> EcontOrderPayload:
    """Build an Econt Order payload from local order data and settings."""
    blockers = _readiness_blockers(conn, order_id, require_status=False, require_enabled=False)
    local_blockers = [b for b in blockers if not b.startswith("settings_")]
    if local_blockers:
        raise EcontFulfillmentValidationError(
            "Order is not mappable to Econt",
            blockers=local_blockers,
        )

    order = get_order_admin(conn, order_id)
    row = _settings_row(conn)
    delivery_details = order["delivery_details"] or {}
    overrides = delivery_details.get("econt_overrides") or {}
    payment_method = order["payment_method"]
    cod = payment_method == "cod"
    total = _amount_for_currency(order["total_cents"], row)

    return EcontOrderPayload(
        order_number=order["id"],
        order_time=order["created_at"],
        order_sum=total,
        declared_value=total if row["declared_value_enabled"] else None,
        cod=cod,
        currency=row["courier_currency"],
        shipment_description=overrides.get("shipment_description") or row["shipment_description"],
        sender_info=_sender_info(row),
        customer_info=_customer_info(order, delivery_details),
        items=_order_items(conn, order_id),
        pack_count=overrides.get("pack_count") or row["default_pack_count"],
        payment_side=overrides.get("payment_side") or row["default_payment_side"],
    )


def sync_order(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    client: EcontDeliveryClient | None = None,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    """Call Econt updateOrder and persist sync metadata/event."""
    _raise_if_not_ready(conn, order_id, require_status=False)
    payload = build_order_payload(conn, order_id)
    client = client or make_client(conn)
    try:
        response = client.update_order(payload)
    except EcontDeliveryError as exc:
        _persist_failure(conn, order_id, "sync_order", payload, exc, actor_user_id)
        raise

    now = pricing.now_utc()
    courier_order_id = response.get("orderID") or response.get("orderId") or response.get("id")
    conn.execute(
        """
        UPDATE orders
        SET courier_provider = 'econt', courier_order_id = ?, courier_sync_status = 'synced',
            courier_last_error = NULL, courier_last_synced_at = ?
        WHERE id = ?
        """,
        (courier_order_id, now, order_id),
    )
    _record_event(conn, order_id, "sync_order", "success", payload, response, None, actor_user_id)
    return {"status": "synced", "courier_order_id": courier_order_id}


def create_label(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    client: EcontDeliveryClient | None = None,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    """Create an Econt AWB label unless one already exists."""
    existing = conn.execute(
        "SELECT courier_shipment_number, courier_label_url FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if existing is None:
        raise OrderNotFoundError(order_id)
    if existing["courier_shipment_number"]:
        _record_event(
            conn,
            order_id,
            "create_label",
            "skipped",
            None,
            {
                "reason": "shipment_already_exists",
                "shipmentNumber": existing["courier_shipment_number"],
            },
            None,
            actor_user_id,
        )
        return {
            "status": "existing",
            "shipment_number": existing["courier_shipment_number"],
            "label_url": existing["courier_label_url"],
        }

    _raise_if_not_ready(conn, order_id, require_status=True)
    order_before_label = get_order_admin(conn, order_id)
    payload = build_order_payload(conn, order_id)
    client = client or make_client(conn)
    try:
        shipment = client.create_awb(payload)
    except EcontDeliveryError as exc:
        _persist_failure(conn, order_id, "create_label", payload, exc, actor_user_id)
        raise

    if not shipment.shipment_number:
        raise EcontFulfillmentValidationError("Econt did not return a shipment number")

    now = pricing.now_utc()
    tracking_url = shipment.tracking_url or tracking_url_for("econt", shipment.shipment_number)
    conn.execute(
        """
        UPDATE orders
        SET courier_provider = 'econt', courier_shipment_number = ?, courier_label_url = ?,
            courier_label_created_at = ?, courier_sync_status = 'label_created',
            courier_last_error = NULL, courier_last_synced_at = ?, tracking_number = ?,
            tracking_carrier = 'econt', tracking_url = ?
        WHERE id = ?
        """,
        (
            shipment.shipment_number,
            shipment.pdf_url,
            now,
            now,
            shipment.shipment_number,
            tracking_url,
            order_id,
        ),
    )
    _record_event(conn, order_id, "create_label", "success", payload, shipment, None, actor_user_id)
    status_updated_to = None
    if _settings_row(conn)["auto_confirm_on_label"] and order_before_label["status"] == "pending":
        update_status(conn, order_id, "confirmed")
        status_updated_to = "confirmed"
        _record_event(
            conn,
            order_id,
            "auto_confirm_on_label",
            "success",
            None,
            {"status": "confirmed"},
            None,
            actor_user_id,
        )
    return {
        "status": "created",
        "shipment_number": shipment.shipment_number,
        "label_url": shipment.pdf_url,
        "tracking_url": tracking_url,
        "status_updated_to": status_updated_to,
    }


def delete_label(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    client: EcontDeliveryClient | None = None,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    order = get_order_admin(conn, order_id)
    if order["status"] in {"shipped", "delivered"}:
        raise EcontFulfillmentValidationError("Cannot delete label for shipped/delivered order")
    shipment_number = order["courier_shipment_number"]
    if not shipment_number:
        raise EcontFulfillmentValidationError("Order has no Econt shipment number")
    client = client or make_client(conn)
    try:
        response = client.delete_label(shipment_number)
    except EcontDeliveryError as exc:
        _persist_failure(
            conn,
            order_id,
            "delete_label",
            {"shipmentNumber": shipment_number},
            exc,
            actor_user_id,
        )
        raise

    now = pricing.now_utc()
    conn.execute(
        """
        UPDATE orders
        SET courier_shipment_number = NULL, courier_label_url = NULL,
            courier_label_created_at = NULL, courier_sync_status = 'label_deleted',
            courier_last_error = NULL, courier_last_synced_at = ?, tracking_number = NULL,
            tracking_carrier = NULL, tracking_url = NULL
        WHERE id = ?
        """,
        (now, order_id),
    )
    _record_event(
        conn,
        order_id,
        "delete_label",
        "success",
        {"shipmentNumber": shipment_number},
        response,
        None,
        actor_user_id,
    )
    return {"status": "deleted"}


def refresh_trace(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    client: EcontDeliveryClient | None = None,
    actor_user_id: str | None = None,
) -> dict[str, Any]:
    order = get_order_admin(conn, order_id)
    shipment_number = order["courier_shipment_number"] or order["tracking_number"]
    if not shipment_number:
        raise EcontFulfillmentValidationError("Order has no Econt shipment number")
    client = client or make_client(conn)
    try:
        shipment = client.get_trace(shipment_number)
    except EcontDeliveryError as exc:
        _persist_failure(
            conn,
            order_id,
            "refresh_trace",
            {"shipmentNumber": shipment_number},
            exc,
            actor_user_id,
        )
        raise

    now = pricing.now_utc()
    conn.execute(
        """
        UPDATE orders
        SET courier_provider = 'econt', courier_sync_status = 'trace_synced',
            courier_last_error = NULL, courier_last_synced_at = ?
        WHERE id = ?
        """,
        (now, order_id),
    )
    _record_event(
        conn,
        order_id,
        "refresh_trace",
        "success",
        {"shipmentNumber": shipment_number},
        shipment,
        None,
        actor_user_id,
    )
    status_updated_to = None
    if _settings_row(conn)["auto_delivered_on_trace"] and order["status"] == "shipped":
        if _shipment_indicates_delivered(shipment):
            update_status(conn, order_id, "delivered")
            status_updated_to = "delivered"
            _record_event(
                conn,
                order_id,
                "auto_delivered_on_trace",
                "success",
                {"shipmentNumber": shipment_number},
                {"status": "delivered"},
                None,
                actor_user_id,
            )
    return {
        "status": "trace_synced",
        "shipment": shipment.model_dump(by_alias=True),
        "status_updated_to": status_updated_to,
    }


def _readiness_blockers(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    require_status: bool = True,
    require_enabled: bool = True,
) -> list[str]:
    settings = get_settings()
    row = _settings_row(conn)
    try:
        order = get_order_admin(conn, order_id)
    except OrderNotFoundError:
        raise

    blockers: list[str] = []
    if require_enabled and not row["enabled"]:
        blockers.append("settings_disabled")
    if not _shop_id(settings, row):
        blockers.append("settings_shop_id_missing")
    if not _private_key(settings, row):
        blockers.append("settings_private_key_missing")
    if row["sender_delivery_mode"] == "office" and not row["sender_office_code"]:
        blockers.append("settings_sender_office_code_missing")
    if row["sender_delivery_mode"] == "door" and not (row["sender_city"] and row["sender_address"]):
        blockers.append("settings_sender_address_missing")
    if row["courier_currency"] == "BGN" and not row["currency_conversion_rate"]:
        blockers.append("settings_currency_conversion_rate_missing")
    if order["delivery_courier"] != "econt":
        blockers.append("order_not_econt")
    if require_status and not _label_status_supported(order["status"], row):
        blockers.append("order_status_not_supported")

    details = order["delivery_details"] or {}
    if order["delivery_method"] == "office" and not details.get("office_code"):
        blockers.append("order_office_code_missing")
    if not details.get("phone"):
        blockers.append("order_recipient_phone_missing")
    if order["delivery_method"] == "door" and not (details.get("city") and details.get("street")):
        blockers.append("order_door_address_missing")
    return blockers


def _label_status_supported(status: str, row: sqlite3.Row) -> bool:
    if status in _LABEL_STATUSES:
        return True
    return bool(row["auto_confirm_on_label"] and status == "pending")


def _shipment_indicates_delivered(shipment: Any) -> bool:
    values: list[str] = []
    if getattr(shipment, "status", None):
        values.append(str(shipment.status))
    for event in getattr(shipment, "events", []) or []:
        if getattr(event, "status", None):
            values.append(str(event.status))
        if getattr(event, "details", None):
            values.append(str(event.details))
    return any(
        any(hint in value.casefold() for hint in _DELIVERED_STATUS_HINTS) for value in values
    )


def _raise_if_not_ready(conn: sqlite3.Connection, order_id: str, *, require_status: bool) -> None:
    blockers = _readiness_blockers(conn, order_id, require_status=require_status)
    if blockers:
        raise EcontFulfillmentValidationError("Econt order is not ready", blockers=blockers)


def _customer_info(order: dict[str, Any], details: dict[str, Any]) -> EcontCustomerInfo:
    name = order.get("customer_name") or order.get("customer_email") or "Atelier Marie customer"
    if order["delivery_method"] == "office":
        office = delivery_service.get_office("econt", details["office_id"], locale="bg")
        return EcontCustomerInfo(
            name=name,
            phone=details.get("phone"),
            email=order.get("customer_email"),
            city_name=office["city"] if office else None,
            office_code=details.get("office_code"),
        )
    return EcontCustomerInfo(
        name=name,
        phone=details.get("phone"),
        email=order.get("customer_email"),
        city_name=details.get("city"),
        post_code=details.get("postal_code"),
        address=_door_address(details),
        street=details.get("street"),
        other=_door_other(details),
    )


def _sender_info(row: sqlite3.Row) -> EcontSenderInfo:
    if row["sender_delivery_mode"] == "office":
        return EcontSenderInfo(office_code=row["sender_office_code"])
    return EcontSenderInfo(
        city_name=row["sender_city"],
        post_code=row["sender_post_code"],
        address=row["sender_address"],
        quarter=row["sender_quarter"],
        street=row["sender_street"],
        num=row["sender_num"],
        other=row["sender_other"],
    )


def _order_items(conn: sqlite3.Connection, order_id: str) -> list[EcontOrderItem]:
    rows = conn.execute(
        """
        SELECT oi.product_id, oi.product_name, oi.price_cents, oi.quantity,
               COALESCE(p.weight_grams, ?) AS weight_grams
        FROM order_items oi
        LEFT JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = ?
        ORDER BY oi.product_id
        """,
        (_DEFAULT_WEIGHT_GRAMS, order_id),
    ).fetchall()
    return [
        EcontOrderItem(
            name=row["product_name"],
            sku=row["product_id"],
            quantity=row["quantity"],
            price=round(row["price_cents"] / 100, 2),
            total_weight=round((row["weight_grams"] * row["quantity"]) / 1000, 3),
        )
        for row in rows
    ]


def _amount_for_currency(total_cents: int, row: sqlite3.Row) -> float:
    amount = total_cents / 100
    if row["courier_currency"] == "BGN":
        return round(amount * float(row["currency_conversion_rate"]), 2)
    return round(amount, 2)


def _door_address(details: dict[str, Any]) -> str | None:
    pieces = [details.get("street"), details.get("building"), details.get("apartment")]
    text = ", ".join(str(piece) for piece in pieces if piece)
    return text or None


def _door_other(details: dict[str, Any]) -> str | None:
    pieces = []
    if details.get("building"):
        pieces.append(f"building {details['building']}")
    if details.get("apartment"):
        pieces.append(f"apartment {details['apartment']}")
    return ", ".join(pieces) or None


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
        ) VALUES (?, 'econt', ?, ?, ?, ?, ?, ?)
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
    exc: EcontDeliveryError,
    actor_user_id: str | None,
) -> None:
    safe_error = exc.to_safe_dict()
    conn.execute(
        """
        UPDATE orders
        SET courier_provider = 'econt', courier_sync_status = 'failed', courier_last_error = ?,
            courier_last_synced_at = ?
        WHERE id = ?
        """,
        (_json_or_none(safe_error), pricing.now_utc(), order_id),
    )
    _record_event(
        conn,
        order_id,
        action,
        "failed",
        request_payload,
        None,
        safe_error,
        actor_user_id,
    )


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        value = value.model_dump(by_alias=True, exclude_none=True)
    return json.dumps(redact_mapping(value), ensure_ascii=False, sort_keys=True)
