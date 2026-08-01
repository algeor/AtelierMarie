"""Shipping-pricing orchestrator (shipping-pricing — Phase A).

Coordinates the two courier clients. Responsibilities:

1. Free-shipping short-circuit FIRST — items ≥ €50 returns 0¢ live quotes
   before any courier call (design Decision 4), so an outage never charges a
   fallback price on a qualifying order.
2. Cart weight from the DB — sums each line's `products.weight_grams × quantity`
   plus `PACKAGING_WEIGHT_GRAMS`.
3. Fan-out — calls both couriers in parallel (approximate) or one (exact); each
   quote carries independent provenance.

Never raises for a courier being down — the clients degrade to a flat fallback.
"""

import asyncio
import sqlite3
from datetime import UTC, datetime

import structlog

from app.config import get_settings
from app.constants import (
    FREE_SHIPPING_THRESHOLD_CENTS,
    PACKAGING_WEIGHT_GRAMS,
    SQLITE_DATETIME_FORMAT,
)
from app.models.delivery import Courier
from app.models.shipping import ShippingAddress, ShippingQuote
from app.services import delivery_service, econt_client, speedy_client

logger = structlog.get_logger(__name__)


def cart_weight_grams(conn: sqlite3.Connection, session_id: str) -> int:
    """Sum each cart line's product weight × quantity, plus the packaging buffer.

    Reads `products.weight_grams` (default 300g) server-side — the client never
    supplies weights. An empty cart still yields the packaging buffer; callers
    that need to reject empty carts do so before pricing.
    """
    row = conn.execute(
        """
        SELECT COALESCE(SUM(p.weight_grams * ci.quantity), 0) AS total
        FROM cart_items ci
        JOIN products p ON p.id = ci.product_id
        WHERE ci.session_id = ?
        """,
        (session_id,),
    ).fetchone()
    summed = int(row["total"]) if row and row["total"] is not None else 0
    return summed + PACKAGING_WEIGHT_GRAMS


def _free_shipping_quotes(couriers: list[Courier], quoted_at: str) -> list[ShippingQuote]:
    """0¢ live quotes for a qualifying order — one per requested courier."""
    return [
        ShippingQuote(
            courier=c,
            cents=0,
            estimated_delivery_days=None,
            is_fallback=False,
            price_source="live",
            quoted_at=quoted_at,
        )
        for c in couriers
    ]


def _courier_door_address(
    courier: Courier, address: ShippingAddress | None
) -> ShippingAddress | None:
    """Copy `address` with its city translated to Bulgarian for courier APIs.

    Returns a new model rather than mutating the caller's — the same
    `door_address` instance may be shared across courier calls. `None` (office
    mode) passes through untouched.
    """
    if address is None:
        return None
    return address.model_copy(
        update={"city": delivery_service.resolve_city_bg(courier, address.city)}
    )


def _courier_office_id(courier: Courier, office_id: str | None) -> str | None:
    """Return the courier-native office identifier for price APIs."""
    if not office_id:
        return None
    if courier != "econt":
        return office_id
    office = delivery_service.get_office("econt", office_id, locale="bg")
    if office is None:
        return office_id
    return office["code"] or office_id


async def calculate_quotes(
    *,
    couriers: list[Courier],
    method: str,
    city: str,
    office_id: str | None,
    address: ShippingAddress | None,
    weight_grams: int,
    items_total_cents: int,
) -> list[ShippingQuote]:
    """Return one `ShippingQuote` per requested courier.

    Evaluates the free-shipping short-circuit before any courier call. Otherwise
    fans out to the requested couriers concurrently; each quote independently
    reflects whether that courier answered live or degraded to the flat fallback.

    In door mode (`method == "door"`) `address` carries the full street/postal
    destination and is forwarded to the clients so the quote is address-exact
    rather than city-approximate. In office mode `office_id` is forwarded and
    `address` is ignored.
    """
    quoted_at = datetime.now(UTC).strftime(SQLITE_DATETIME_FORMAT)

    if items_total_cents >= FREE_SHIPPING_THRESHOLD_CENTS:
        return _free_shipping_quotes(couriers, quoted_at)

    settings = get_settings()
    # Door mode forwards the exact address; office mode forwards the office id.
    door_address = address if method == "door" else None
    office = office_id if method == "office" else None

    async def _quote_for(courier: Courier) -> ShippingQuote:
        if courier == "speedy":
            return await speedy_client.calculate(
                client_id=settings.speedy_client_id,
                recipient_city=delivery_service.resolve_city_bg("speedy", city),
                recipient_office_id=_courier_office_id("speedy", office),
                weight_grams=weight_grams,
                username=settings.speedy_api_username,
                password=settings.speedy_api_password.get_secret_value(),
                address=_courier_door_address("speedy", door_address),
                quoted_at=quoted_at,
            )
        return await econt_client.calculate(
            recipient_city=delivery_service.resolve_city_bg("econt", city),
            recipient_office_id=_courier_office_id("econt", office),
            weight_grams=weight_grams,
            username=settings.econt_api_username,
            password=settings.econt_api_password.get_secret_value(),
            sender_name=settings.econt_sender_name,
            sender_phone=settings.econt_sender_phone,
            sender_address=settings.econt_sender_address,
            sender_city=settings.econt_sender_city,
            address=_courier_door_address("econt", door_address),
            quoted_at=quoted_at,
        )

    return list(await asyncio.gather(*(_quote_for(c) for c in couriers)))
