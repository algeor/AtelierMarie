"""Econt courier price calculation client (shipping-pricing — Phase A).

Mirrors `speedy_client`: a single `calculate(...)` coroutine returning a
normalized `ShippingQuote`, degrading to a flat fallback on any failure
(timeout, 5xx, auth failure, bad shape) rather than raising. Econt's Shipments
service uses HTTP Basic auth (design task 1.4).
"""

import httpx
import structlog

from app.config import get_settings
from app.constants import COURIER_TIMEOUT_SECONDS, FALLBACK_SHIPPING_CENTS
from app.models.shipping import ShippingAddress, ShippingQuote, parse_price_cents

logger = structlog.get_logger(__name__)

# Econt has no dedicated price-only endpoint; createLabel with `mode=calculate`
# is the documented way to price a shipment WITHOUT registering a real waybill.
# The mode flag is load-bearing: if it were ever dropped, every /calculate would
# create a billable label. `_ECONT_CALCULATE_MODE` is asserted in the payload
# and covered by a regression test (test_courier_clients).
# TODO(before-production): verify mode=calculate against the Econt sandbox — the
# billing downside if this flag is wrong is high (review W1).
_ECONT_CALCULATE_MODE = "calculate"

# label.shipmentType — confirmed valid tokens against the live API are `pack`
# (parcel), `document`/`documents`, `post_pack`. Candles are a parcel → `pack`.
# NOTE: the `shipmentTypes` array in the offices nomenclature (cargo/courier/
# pallet/post) is a DIFFERENT vocabulary (office capabilities); it does not
# apply to this field.
_SHIPMENT_TYPE = "pack"

# Econt's calculate mode still validates a full label (sender + receiver name
# and phone), even though it registers no waybill and creates no billable
# shipment. The real receiver is only known at order creation (a later phase),
# so at price-preview time we send a benign placeholder — safe because
# mode=calculate never creates a real shipment.
_PLACEHOLDER_RECEIVER_NAME = "Получател"
_PLACEHOLDER_RECEIVER_PHONE = "0000000000"


def _fallback_quote(quoted_at: str | None = None) -> ShippingQuote:
    """Flat last-resort quote when live pricing is unavailable."""
    return ShippingQuote(
        courier="econt",
        cents=FALLBACK_SHIPPING_CENTS,
        estimated_delivery_days=None,
        is_fallback=True,
        price_source="flat",
        quoted_at=quoted_at,
    )


async def calculate(
    *,
    recipient_city: str,
    recipient_office_id: str | None,
    weight_grams: int,
    username: str,
    password: str,
    sender_name: str,
    sender_phone: str,
    sender_address: str,
    sender_city: str,
    address: ShippingAddress | None = None,
    quoted_at: str | None = None,
) -> ShippingQuote:
    """Return a live Econt shipping quote, or a flat fallback on any failure.

    Uses Econt's `LabelService.createLabel` with `mode=calculate` (price-only,
    no real label). Econt validates a full label even in calculate mode, so the
    payload carries sender name/phone/address (the shop's fixed origin) and a
    placeholder receiver name/phone (the real recipient is only known at order
    creation, a later phase). In door mode (`address` set) the full street
    address is sent; otherwise an office pickup is priced via
    `receiverOfficeCode`. Weight is sent in kilograms. Auth is HTTP Basic. The
    per-request timeout is COURIER_TIMEOUT_SECONDS; anything slower degrades to
    the flat fallback.
    """
    sender_client = {"name": sender_name, "phones": [sender_phone]}
    sender_address_obj = {"city": {"name": sender_city}, "street": sender_address}
    receiver_client = {
        "name": _PLACEHOLDER_RECEIVER_NAME,
        "phones": [_PLACEHOLDER_RECEIVER_PHONE],
    }

    if address is not None:
        # postCode MUST sit inside the `city` object — Econt uses it to
        # disambiguate settlements that share a name (ExMultipleCity otherwise).
        # An address-level `postCode` is ignored for this and the call 517s
        # (confirmed live 2026-07-29 against several villages named "Садово").
        # street/postCode/num are optional on a preview address, so only
        # include the keys that carry a value.
        city_obj: dict = {"name": address.city}
        if address.postal_code:
            city_obj["postCode"] = address.postal_code
        receiver_address: dict = {"city": city_obj}
        if address.street:
            receiver_address["street"] = address.street
        if address.building:
            receiver_address["num"] = address.building
        label = {
            "senderClient": sender_client,
            "senderAddress": sender_address_obj,
            "receiverClient": receiver_client,
            "receiverAddress": receiver_address,
            "shipmentType": _SHIPMENT_TYPE,
            "packCount": 1,
            "weight": weight_grams / 1000.0,
        }
    else:
        # Office mode carries no postcode, and our office ids are synthetic
        # slugs (not real Econt office codes), so an ambiguous city name
        # (several settlements share it) will 517 with ExMultipleCity and
        # degrade to the flat fallback. Unambiguous cities price fine. A real
        # postcode/office-code source would remove this limitation.
        label = {
            "senderClient": sender_client,
            "senderAddress": sender_address_obj,
            "receiverClient": receiver_client,
            "receiverOfficeCode": recipient_office_id,
            "receiverAddress": {"city": {"name": recipient_city}},
            "shipmentType": _SHIPMENT_TYPE,
            "packCount": 1,
            "weight": weight_grams / 1000.0,
        }

    payload = {"mode": _ECONT_CALCULATE_MODE, "label": label}

    try:
        async with httpx.AsyncClient(
            timeout=COURIER_TIMEOUT_SECONDS, auth=(username, password)
        ) as client:
            response = await client.post(get_settings().econt_calculate_url, json=payload)
        if response.status_code >= 400:
            # Log Econt's error body (truncated) so a 4xx/5xx is diagnosable —
            # the status alone doesn't say WHY (bad sender id, office code shape,
            # auth). Mirrors speedy_client. The body is Econt's response, not our
            # request, so it carries no credentials.
            logger.warning(
                "econt_calculate_http_error",
                status=response.status_code,
                body=response.text[:500],
            )
            return _fallback_quote(quoted_at)
        data = response.json()
        # Econt returns a `label` object carrying the calculated total price.
        label_resp = data.get("label") or {}
        total = label_resp.get("totalPrice")
        if total is None:
            logger.warning("econt_calculate_missing_price")
            return _fallback_quote(quoted_at)
        cents = parse_price_cents(total)
        if cents is None:
            logger.warning("econt_calculate_bad_price", total=repr(total))
            return _fallback_quote(quoted_at)
        days = label_resp.get("deliveryDays")
        return ShippingQuote(
            courier="econt",
            cents=cents,
            estimated_delivery_days=days if isinstance(days, int) else None,
            is_fallback=False,
            price_source="live",
            quoted_at=quoted_at,
        )
    except Exception as exc:  # noqa: BLE001 - any failure degrades to fallback.
        # Log the exception type, not just str(exc): several httpx transport
        # errors stringify to "" (review W4). In local dev with no route to the
        # Econt API this fires every call — expected, not a code bug.
        logger.warning(
            "econt_calculate_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return _fallback_quote(quoted_at)
