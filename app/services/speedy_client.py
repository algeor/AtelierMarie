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
