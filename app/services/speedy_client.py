"""Speedy courier price calculation client (shipping-pricing — Phase A).

Thin, isolated module exposing a single `calculate(...)` coroutine returning a
normalized `ShippingQuote`. On any failure (timeout, 5xx, auth failure, bad
shape) it does NOT raise — it returns a flat fallback quote tagged
`price_source="flat", is_fallback=True` so the orchestrator/endpoint never fails
because a courier is down (design Decision 3).
"""

import httpx
import structlog

from app.constants import COURIER_TIMEOUT_SECONDS, FALLBACK_SHIPPING_CENTS
from app.models.shipping import ShippingAddress, ShippingQuote, parse_price_cents

logger = structlog.get_logger(__name__)

_CALCULATE_URL = "https://api.speedy.bg/v1/calculate"


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


async def calculate(
    *,
    sender_office_id: str,
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
    city-level `addressLocation` is used. The per-request timeout is
    COURIER_TIMEOUT_SECONDS; anything slower degrades to the flat fallback.
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
        recipient = {
            "privatePerson": True,
            "addressLocation": {"siteName": recipient_city},
            "pickupOfficeId": recipient_office_id,
        }

    payload = {
        "userName": username,
        "password": password,
        "service": {"serviceIds": []},
        "sender": {"clientId": sender_office_id},
        "recipient": recipient,
        "content": {"parcelsCount": 1, "totalWeight": weight_grams / 1000.0},
        "payment": {"courierServicePayer": "RECIPIENT"},
    }

    try:
        async with httpx.AsyncClient(timeout=COURIER_TIMEOUT_SECONDS) as client:
            response = await client.post(_CALCULATE_URL, json=payload)
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
