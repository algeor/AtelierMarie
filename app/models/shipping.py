"""Shipping-pricing request/response models (shipping-pricing — Phase A).

`ShippingQuote` is the normalized shape returned by both courier clients and
the `/v1/delivery/calculate` endpoint. `CalculateShippingRequest` is the
single-endpoint payload for both approximate (city-only) and exact
(office_id / address) modes — see design Decision 2.
"""

import math

from pydantic import BaseModel, Field, model_validator

from app.constants import ShippingPriceSource
from app.models.delivery import Courier, CourierDeliveryMethod


def parse_price_cents(total: object) -> int | None:
    """Convert an untrusted courier price to non-negative integer cents.

    Returns None (caller degrades to fallback) for anything that isn't a clean,
    non-negative, finite number: European comma-decimals (`"5,00"`), NaN/inf,
    negatives, or non-numeric shapes. Kept here so both courier clients share
    one guard — see review W4 (silent-fallback was undiagnosable).
    """
    if isinstance(total, bool):  # bool is an int subclass — reject explicitly.
        return None
    if not isinstance(total, int | float | str):
        return None
    try:
        value = float(total)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return round(value * 100)


class ShippingQuote(BaseModel):
    """Normalized shipping price for one courier, with provenance.

    `is_fallback` is true whenever `price_source != "live"`. `quoted_at` is a
    Canonical UTC timestamp stamped by the orchestrator when the quote is
    produced — echoed back at checkout and persisted for later reconciliation.
    """

    courier: Courier
    cents: int = Field(..., ge=0)
    estimated_delivery_days: int | None = None
    is_fallback: bool = False
    price_source: ShippingPriceSource = "live"
    quoted_at: str | None = None


class ShippingAddress(BaseModel):
    """Door address for a PRICE PREVIEW — deliberately looser than checkout.

    The checkout `DeliveryDoor` requires phone/postal_code/street for the real
    waybill. Pricing needs none of that: the couriers send a placeholder
    receiver and only read city (+ postcode to disambiguate same-named towns).
    So only `city` is required here; the rest refine the quote when present.
    `phone` is intentionally absent — a preview must not force the shopper to
    enter one before seeing a price.
    """

    courier: Courier
    city: str = Field(..., min_length=1, max_length=100)
    postal_code: str | None = Field(default=None, min_length=1, max_length=10)
    street: str | None = Field(default=None, min_length=1, max_length=200)
    building: str | None = Field(default=None, max_length=50)


class CalculateShippingRequest(BaseModel):
    """Input for `POST /v1/delivery/calculate`.

    Approximate mode: `office_id` and `address` both null → city-level estimate.
    Exact mode: exactly one courier plus an `office_id` (office) or `address`
    (door). `couriers` names which couriers to quote (1 for exact, up to 2 for
    approximate comparison).
    """

    method: CourierDeliveryMethod
    city: str = Field(..., min_length=1, max_length=100)
    office_id: str | None = Field(default=None, min_length=1, max_length=64)
    address: ShippingAddress | None = None
    items_total_cents: int = Field(..., ge=0)
    couriers: list[Courier] = Field(..., min_length=1, max_length=2)

    @model_validator(mode="after")
    def _validate_mode(self) -> "CalculateShippingRequest":
        """Enforce coherent method/destination and dedupe couriers."""
        if len(set(self.couriers)) != len(self.couriers):
            raise ValueError("couriers must be distinct")
        if self.method == "office" and self.address is not None:
            raise ValueError("address must be null when method is 'office'")
        if self.method == "door" and self.office_id is not None:
            raise ValueError("office_id must be null when method is 'door'")
        # Exact mode (a specific destination) implies a single courier.
        is_exact = self.office_id is not None or self.address is not None
        if is_exact and len(self.couriers) != 1:
            raise ValueError("exact-mode calculation requires exactly one courier")
        return self


class CalculateShippingResponse(BaseModel):
    """Response for `POST /v1/delivery/calculate` — one quote per requested courier."""

    quotes: list[ShippingQuote]


class CityPlace(BaseModel):
    """A served delivery place — name + region + postcode.

    Region distinguishes same-named towns (e.g. the three "Садово"); the
    postcode is the disambiguator the pricing API needs so an ambiguous town
    prices live instead of degrading to the flat fallback. Returned by
    `GET /v1/delivery/places` and used by the door-delivery place picker.
    """

    name: str
    region: str | None = None
    postal_code: str | None = None
