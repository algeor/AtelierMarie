"""Speedy courier price calculation client (shipping-pricing — Phase A).

Thin, isolated module exposing a single `calculate(...)` coroutine returning a
normalized `ShippingQuote`. On any failure (timeout, 5xx, auth failure, bad
shape) it does NOT raise — it returns a flat fallback quote tagged
`price_source="flat", is_fallback=True` so the orchestrator/endpoint never fails
because a courier is down (design Decision 3).
"""

import httpx
import structlog

from app.config import get_settings
from app.constants import COURIER_TIMEOUT_SECONDS, FALLBACK_SHIPPING_CENTS
from app.models.shipping import ShippingAddress, ShippingQuote, parse_price_cents

logger = structlog.get_logger(__name__)

# Speedy's standard "24h to address/office" service. An empty `serviceIds` list
# is rejected with a 400 (verified live, task 0) — a concrete service must be
# named, so calculate always filters to this one.
_DEFAULT_SERVICE_ID = 505

# Timeout for shipment/track/print — these are real operations (not the
# best-effort pricing path), so they get a longer budget than a price quote.
_OPERATION_TIMEOUT_SECONDS = 15


# ---------------------------------------------------------------------------
# Typed exceptions (design Decision 6 — shipment/track/print never silently
# degrade; a documented Speedy error maps to a typed exception surfaced to admin)
# ---------------------------------------------------------------------------


class SpeedyError(Exception):
    """Base for Speedy operation failures (shipment/track/print).

    Carries the Speedy error `context`/`message` (when present) so the admin
    sees WHY Speedy rejected the operation, not just that it failed.
    """

    def __init__(self, message: str, *, context: str | None = None) -> None:
        self.context = context
        super().__init__(message)


class ShipmentCreationError(SpeedyError):
    """Waybill creation via POST /shipment failed."""


class TrackingError(SpeedyError):
    """Tracking via POST /track failed."""


class LabelPrintError(SpeedyError):
    """Label printing via POST /print failed."""


def _speedy_error_fields(data: object) -> tuple[str | None, str | None]:
    """Pull (context, message) from a Speedy `error` object, if present.

    Speedy returns errors as `{"error": {"context": ..., "message": ...}}`
    (verified live — the sender-probe script reads exactly these keys). Returns
    (None, None) when the body carries no error object.
    """
    if not isinstance(data, dict):
        return None, None
    err = data.get("error")
    if not isinstance(err, dict):
        return None, None
    context = err.get("context")
    message = err.get("message")
    return (
        context if isinstance(context, str) else None,
        message if isinstance(message, str) else None,
    )


def _sender_client_id(client_id: str) -> int | None:
    """Return the numeric sender clientId, or None (with a distinct warning).

    Speedy's `sender.clientId` is a numeric registered-client id. An empty or
    non-numeric value is a misconfiguration, NOT a Speedy outage — it gets its
    own `speedy_sender_client_id_invalid` warning so the two are distinguishable
    in logs (design Decision 1 / spec: diagnosable sender).
    """
    if client_id and client_id.isdigit():
        return int(client_id)
    logger.warning("speedy_sender_client_id_invalid", client_id_present=bool(client_id))
    return None


def _fallback_quote(quoted_at: str | None = None) -> ShippingQuote:
    """Flat last-resort quote when live pricing is unavailable."""
    return ShippingQuote(
        courier="speedy",
        cents=FALLBACK_SHIPPING_CENTS,
        estimated_delivery_days=None,
        is_fallback=True,
        price_source="flat",
        quoted_at=quoted_at,
    )


def build_calculate_payload(
    *,
    client_id: str,
    recipient_city: str,
    recipient_office_id: str | None,
    weight_grams: int,
    username: str,
    password: str,
    address: ShippingAddress | None = None,
) -> dict:
    """Assemble the Speedy `/calculate` request body.

    Split out from `calculate` so a unit test can assert the payload shape
    (numeric `sender.clientId`, numeric `pickupOfficeId` in office mode)
    independent of any mocked HTTP response — a canned price must not be able
    to hide a payload Speedy would reject (spec: payload contract).
    """
    if address is not None:
        # postal_code/street/building are optional on a preview address; only
        # send the keys that carry a value so Speedy doesn't see JSON nulls.
        address_location: dict = {"siteName": address.city}
        if address.postal_code:
            address_location["postCode"] = address.postal_code
        if address.street:
            address_location["streetName"] = address.street
        if address.building:
            address_location["streetNo"] = address.building
        recipient: dict = {
            "privatePerson": True,
            "addressLocation": address_location,
        }
    else:
        # Office mode: send ONLY `pickupOfficeId`, never alongside an
        # `addressLocation`. Speedy rejects a recipient carrying both with
        # `calculation.recipient.address.forbidden` ("населено място не се
        # изисква ако е подаден офис до поискване" — verified live 2026-07-31),
        # which silently degraded every office quote to the flat fallback.
        # `pickupOfficeId` must be a numeric int (the Phase A 400 root cause);
        # a non-numeric office ref is dropped and we fall back to a city address
        # so Speedy still gets a resolvable recipient.
        if recipient_office_id is not None and str(recipient_office_id).isdigit():
            recipient = {
                "privatePerson": True,
                "pickupOfficeId": int(recipient_office_id),
            }
        else:
            recipient = {
                "privatePerson": True,
                "addressLocation": {"siteName": recipient_city},
            }

    return {
        "userName": username,
        "password": password,
        "service": {"serviceIds": [_DEFAULT_SERVICE_ID]},
        "sender": {"clientId": _sender_client_id(client_id)},
        "recipient": recipient,
        "content": {"parcelsCount": 1, "totalWeight": weight_grams / 1000.0},
        "payment": {"courierServicePayer": "RECIPIENT"},
    }


async def calculate(
    *,
    client_id: str,
    recipient_city: str,
    recipient_office_id: str | None,
    weight_grams: int,
    username: str,
    password: str,
    address: ShippingAddress | None = None,
    quoted_at: str | None = None,
) -> ShippingQuote:
    """Return a live Speedy shipping quote, or a flat fallback on any failure.

    Speedy's calculate API takes credentials in the JSON body (not headers).
    Weight is sent in kilograms. In door mode (`address` set) the full street
    address is sent so the quote reflects the real destination; otherwise the
    numeric `pickupOfficeId` is used. The per-request timeout is
    COURIER_TIMEOUT_SECONDS; anything slower degrades to the flat fallback.
    """
    payload = build_calculate_payload(
        client_id=client_id,
        recipient_city=recipient_city,
        recipient_office_id=recipient_office_id,
        weight_grams=weight_grams,
        username=username,
        password=password,
        address=address,
    )
    calculate_url = f"{get_settings().speedy_base_url}/calculate"

    try:
        async with httpx.AsyncClient(timeout=COURIER_TIMEOUT_SECONDS) as client:
            response = await client.post(calculate_url, json=payload)
        if response.status_code >= 400:
            # Log Speedy's error body (truncated) so a 400 is diagnosable — the
            # status alone doesn't say WHY it was rejected (bad creds, payload
            # shape, etc.). The response body is Speedy's, not our request, so it
            # carries no credentials.
            logger.warning(
                "speedy_calculate_http_error",
                status=response.status_code,
                body=response.text[:500],
            )
            return _fallback_quote(quoted_at)
        data = response.json()
        # Speedy returns a `calculations` array; take the first service's price.
        calculations = data.get("calculations") or []
        if not calculations:
            logger.warning("speedy_calculate_empty_result")
            return _fallback_quote(quoted_at)
        price = calculations[0].get("price", {})
        total = price.get("total")
        if total is None:
            logger.warning("speedy_calculate_missing_price")
            return _fallback_quote(quoted_at)
        cents = parse_price_cents(total)
        if cents is None:
            logger.warning("speedy_calculate_bad_price", total=repr(total))
            return _fallback_quote(quoted_at)
        days = calculations[0].get("deliveryDeadline")
        return ShippingQuote(
            courier="speedy",
            cents=cents,
            estimated_delivery_days=days if isinstance(days, int) else None,
            is_fallback=False,
            price_source="live",
            quoted_at=quoted_at,
        )
    except Exception as exc:  # noqa: BLE001 - any failure degrades to fallback.
        # Log the exception type, not just str(exc): several httpx transport
        # errors (ConnectError/ConnectTimeout) stringify to "", which made this
        # fallback undiagnosable (review W4). In local dev with no route to
        # api.speedy.bg this fires every call — expected, not a code bug.
        logger.warning(
            "speedy_calculate_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return _fallback_quote(quoted_at)


# ---------------------------------------------------------------------------
# Shipment creation (design Decision 3)
# ---------------------------------------------------------------------------


def build_shipment_payload(
    *,
    client_id: str,
    recipient_name: str,
    recipient_phone: str,
    weight_grams: int,
    username: str,
    password: str,
    order_ref: str,
    recipient_office_id: str | None = None,
    recipient_city: str | None = None,
    recipient_postcode: str | None = None,
    recipient_street: str | None = None,
    recipient_building: str | None = None,
    cod_amount_cents: int | None = None,
) -> dict:
    """Assemble the Speedy `/shipment` (create waybill) request body.

    Unlike `calculate` (which sends a placeholder recipient), this carries the
    REAL recipient from the order's delivery snapshot: name, phone, and either
    a numeric `pickupOfficeId` (office mode) or a full address (door mode).

    Split out so a unit test can assert the payload shape (real recipient,
    numeric client id, office-vs-door recipient) independent of any mocked HTTP
    response (spec: payload contract, extended to shipment).
    """
    if recipient_office_id is not None and str(recipient_office_id).isdigit():
        recipient: dict = {
            "privatePerson": True,
            "clientName": recipient_name,
            "phone1": {"number": recipient_phone},
            "pickupOfficeId": int(recipient_office_id),
        }
    else:
        address: dict = {"siteName": recipient_city or ""}
        if recipient_postcode:
            address["postCode"] = recipient_postcode
        if recipient_street:
            address["streetName"] = recipient_street
        if recipient_building:
            address["streetNo"] = recipient_building
        recipient = {
            "privatePerson": True,
            "clientName": recipient_name,
            "phone1": {"number": recipient_phone},
            "address": address,
        }

    # COD: the recipient pays cash on delivery; otherwise the sender pays the
    # courier service. `cashOnDeliveryAmount` is in the shipment currency (BGN).
    if cod_amount_cents is not None and cod_amount_cents > 0:
        payment = {
            "courierServicePayer": "RECIPIENT",
            "declaredValuePayer": "RECIPIENT",
        }
        cod_block: dict | None = {
            "amount": round(cod_amount_cents / 100.0, 2),
            "processingType": "CASH",
        }
    else:
        payment = {"courierServicePayer": "SENDER"}
        cod_block = None

    payload: dict = {
        "userName": username,
        "password": password,
        "service": {"serviceId": _DEFAULT_SERVICE_ID, "additionalServices": {}},
        "sender": {"clientId": _sender_client_id(client_id)},
        "recipient": recipient,
        "content": {
            "parcelsCount": 1,
            "totalWeight": weight_grams / 1000.0,
            "contents": "Candles",
            "package": "BOX",
        },
        "payment": payment,
        "ref1": order_ref,
    }
    if cod_block is not None:
        payload["service"]["additionalServices"]["cod"] = cod_block
    return payload


async def create_shipment(
    *,
    client_id: str,
    recipient_name: str,
    recipient_phone: str,
    weight_grams: int,
    username: str,
    password: str,
    order_ref: str,
    recipient_office_id: str | None = None,
    recipient_city: str | None = None,
    recipient_postcode: str | None = None,
    recipient_street: str | None = None,
    recipient_building: str | None = None,
    cod_amount_cents: int | None = None,
) -> str:
    """Create a Speedy waybill and return its tracking (shipment) number.

    Raises `ShipmentCreationError` on any failure — unlike pricing, shipment
    creation does NOT silently degrade (design Decision 6). The returned `id`
    is Speedy's shipment number, persisted as the order's `tracking_number`.
    """
    payload = build_shipment_payload(
        client_id=client_id,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        weight_grams=weight_grams,
        username=username,
        password=password,
        order_ref=order_ref,
        recipient_office_id=recipient_office_id,
        recipient_city=recipient_city,
        recipient_postcode=recipient_postcode,
        recipient_street=recipient_street,
        recipient_building=recipient_building,
        cod_amount_cents=cod_amount_cents,
    )
    url = f"{get_settings().speedy_base_url}/shipment"

    try:
        async with httpx.AsyncClient(timeout=_OPERATION_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
    except Exception as exc:  # noqa: BLE001 - transport failure → typed error.
        logger.warning(
            "speedy_shipment_transport_error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise ShipmentCreationError(f"Speedy shipment request failed: {exc}") from exc

    if response.status_code >= 400:
        context, message = _speedy_error_fields(_safe_json(response))
        logger.warning(
            "speedy_shipment_http_error",
            status=response.status_code,
            context=context,
            body=response.text[:500],
        )
        raise ShipmentCreationError(
            message or f"Speedy shipment failed (HTTP {response.status_code})",
            context=context,
        )

    data = _safe_json(response)
    context, message = _speedy_error_fields(data)
    if context or message:
        logger.warning("speedy_shipment_error_body", context=context)
        raise ShipmentCreationError(message or "Speedy shipment rejected", context=context)

    shipment_id = data.get("id") if isinstance(data, dict) else None
    if shipment_id is None:
        logger.warning("speedy_shipment_missing_id", body=response.text[:500])
        raise ShipmentCreationError("Speedy shipment response missing id")
    return str(shipment_id)


def _parse_shipment_response(response: httpx.Response) -> str:
    """Validate a /shipment response and return the shipment id, or raise.

    Shared by the async and sync create paths so error mapping stays identical.
    """
    if response.status_code >= 400:
        context, message = _speedy_error_fields(_safe_json(response))
        logger.warning(
            "speedy_shipment_http_error",
            status=response.status_code,
            context=context,
            body=response.text[:500],
        )
        raise ShipmentCreationError(
            message or f"Speedy shipment failed (HTTP {response.status_code})",
            context=context,
        )
    data = _safe_json(response)
    context, message = _speedy_error_fields(data)
    if context or message:
        logger.warning("speedy_shipment_error_body", context=context)
        raise ShipmentCreationError(message or "Speedy shipment rejected", context=context)
    shipment_id = data.get("id") if isinstance(data, dict) else None
    if shipment_id is None:
        logger.warning("speedy_shipment_missing_id", body=response.text[:500])
        raise ShipmentCreationError("Speedy shipment response missing id")
    return str(shipment_id)


def create_shipment_sync(
    *,
    client_id: str,
    recipient_name: str,
    recipient_phone: str,
    weight_grams: int,
    username: str,
    password: str,
    order_ref: str,
    recipient_office_id: str | None = None,
    recipient_city: str | None = None,
    recipient_postcode: str | None = None,
    recipient_street: str | None = None,
    recipient_building: str | None = None,
    cod_amount_cents: int | None = None,
) -> str:
    """Synchronous waybill creation, for the sync order-service ship path.

    `order_service.update_status` runs inside a sync sqlite3 transaction; calling
    this before the `UPDATE orders` means a `ShipmentCreationError` aborts the
    transaction and the order never lands in `shipped` without a waybill
    (design Decision 3). Shares payload assembly and error mapping with the async
    `create_shipment`.
    """
    payload = build_shipment_payload(
        client_id=client_id,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        weight_grams=weight_grams,
        username=username,
        password=password,
        order_ref=order_ref,
        recipient_office_id=recipient_office_id,
        recipient_city=recipient_city,
        recipient_postcode=recipient_postcode,
        recipient_street=recipient_street,
        recipient_building=recipient_building,
        cod_amount_cents=cod_amount_cents,
    )
    url = f"{get_settings().speedy_base_url}/shipment"
    try:
        with httpx.Client(timeout=_OPERATION_TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload)
    except Exception as exc:  # noqa: BLE001 - transport failure → typed error.
        logger.warning(
            "speedy_shipment_transport_error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise ShipmentCreationError(f"Speedy shipment request failed: {exc}") from exc
    return _parse_shipment_response(response)


# ---------------------------------------------------------------------------
# Tracking (design Decision 4 — read-only; normalized display enum)
# ---------------------------------------------------------------------------

# Our small display vocabulary — describes physical transit, NOT order state.
CourierStatus = str  # one of the values below

# Speedy publishes numeric track-and-trace operation codes (Appendix 1). The
# exact enum is not in the public web-api excerpt, so we normalize by matching
# the operation's textual description against known keywords, with a safe
# `in_transit` default for any recognized-but-unmapped movement. This keeps the
# mapping honest (Decision 4): courier-only states like "returned"/"failed" get
# their own label rather than being coerced into an order status.
_STATUS_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("delivered", "доставена", "доставен", "получена"), "delivered"),
    (("out for delivery", "разнос", "за доставка"), "out_for_delivery"),
    (("returned", "върната", "връщане", "return to sender"), "returned"),
    (("failed", "unsuccessful", "неуспешна", "отказана", "refused"), "failed"),
)


def normalize_track_status(description: str | None) -> CourierStatus:
    """Map a Speedy operation description to our display enum.

    Narrow and one-directional (Speedy code → `courier_status`). Unknown or
    generic movement normalizes to `in_transit` — never coerced into an order
    state. See design Decision 4.
    """
    if not description:
        return "in_transit"
    text = description.lower()
    for keywords, status in _STATUS_KEYWORDS:
        if any(kw in text for kw in keywords):
            return status
    return "in_transit"


async def track_shipment(
    *,
    tracking_number: str,
    username: str,
    password: str,
) -> CourierStatus:
    """Return the normalized `courier_status` for a Speedy shipment.

    Read-only (design Decision 4): callers MUST NOT feed the result into
    `order_service.update_status` — the order state machine stays admin-driven.
    Raises `TrackingError` on failure.
    """
    payload = {
        "userName": username,
        "password": password,
        "parcels": [{"id": tracking_number}],
        "lastOperationOnly": True,
    }
    url = f"{get_settings().speedy_base_url}/track"

    try:
        async with httpx.AsyncClient(timeout=_OPERATION_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
    except Exception as exc:  # noqa: BLE001 - transport failure → typed error.
        logger.warning(
            "speedy_track_transport_error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise TrackingError(f"Speedy track request failed: {exc}") from exc

    if response.status_code >= 400:
        context, message = _speedy_error_fields(_safe_json(response))
        logger.warning(
            "speedy_track_http_error",
            status=response.status_code,
            context=context,
            body=response.text[:500],
        )
        raise TrackingError(
            message or f"Speedy track failed (HTTP {response.status_code})",
            context=context,
        )

    data = _safe_json(response)
    context, message = _speedy_error_fields(data)
    if context or message:
        raise TrackingError(message or "Speedy track rejected", context=context)

    parcels = data.get("parcels") if isinstance(data, dict) else None
    if not parcels:
        raise TrackingError("Speedy track response had no parcels")
    operations = parcels[0].get("operations") or []
    if not operations:
        # No scan yet — the waybill exists but hasn't moved.
        return "in_transit"
    last = operations[-1]
    description = last.get("description") if isinstance(last, dict) else None
    return normalize_track_status(description)


# ---------------------------------------------------------------------------
# Label printing (design Decision 5)
# ---------------------------------------------------------------------------


async def print_label(
    *,
    tracking_number: str,
    username: str,
    password: str,
    paper_size: str = "A6",
) -> bytes:
    """Return the PDF label bytes for a Speedy shipment.

    Raises `LabelPrintError` on failure. A6 is the default thermal-label size.
    """
    payload = {
        "userName": username,
        "password": password,
        "paperSize": paper_size,
        "parcels": [{"parcel": {"id": tracking_number}}],
    }
    url = f"{get_settings().speedy_base_url}/print"

    try:
        async with httpx.AsyncClient(timeout=_OPERATION_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
    except Exception as exc:  # noqa: BLE001 - transport failure → typed error.
        logger.warning(
            "speedy_print_transport_error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise LabelPrintError(f"Speedy print request failed: {exc}") from exc

    if response.status_code >= 400:
        context, message = _speedy_error_fields(_safe_json(response))
        logger.warning(
            "speedy_print_http_error",
            status=response.status_code,
            context=context,
            body=response.text[:500],
        )
        raise LabelPrintError(
            message or f"Speedy print failed (HTTP {response.status_code})",
            context=context,
        )

    # A successful print returns raw PDF bytes; an error returns JSON. Guard by
    # content-type so a JSON error body isn't handed back as a "PDF".
    content_type = response.headers.get("content-type", "")
    if "application/pdf" not in content_type.lower():
        context, message = _speedy_error_fields(_safe_json(response))
        logger.warning("speedy_print_not_pdf", content_type=content_type, context=context)
        raise LabelPrintError(
            message or f"Speedy print returned non-PDF ({content_type})",
            context=context,
        )
    return response.content


def _safe_json(response: httpx.Response) -> object:
    """Parse a response body as JSON, returning None if it isn't JSON."""
    try:
        return response.json()
    except Exception:  # noqa: BLE001 - a non-JSON body just yields None.
        return None
