"""Delivery data endpoints — courier offices, cities, and served places lookup.

Read-only endpoints backed by `delivery_service`. No auth required — office
data is public. See `courier-offices-data` spec for the endpoint contract.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.dependencies.session import require_session
from app.models.delivery import Courier, OfficeResponse, OfficeType
from app.models.shipping import (
    CalculateShippingRequest,
    CalculateShippingResponse,
    CityPlace,
)
from app.services import delivery_service, shipping_service

router = APIRouter()

Locale = Literal["en", "bg"]


@router.get(
    "/offices",
    response_model=list[OfficeResponse],
    summary="List courier offices",
    description="Get offices and lockers (автомати) for a courier, filtered by city. "
    "Case-insensitive city match against both Bulgarian and English names, so "
    "`city=Sofia` and `city=София` return the same results. Optionally filter by "
    "type: `office` (staffed) or `apt` (locker). Returns an empty array if the "
    "courier has no data loaded or no offices match.",
)
async def list_offices(
    courier: Courier = Query(..., description="Courier: 'speedy' or 'econt'"),
    city: str = Query(..., min_length=1, max_length=100, description="City name (BG or EN)"),
    type: OfficeType | None = Query(
        default=None,
        description="Filter by office type: 'office' (staffed) or 'apt' (locker)",
    ),
    locale: Locale = Query(default="bg", description="Content locale for name/city/hours"),
) -> list[OfficeResponse]:
    """List offices for a courier in a given city."""
    offices = delivery_service.get_offices(
        courier,
        city,
        office_type=type,
        locale=locale,
    )
    return [OfficeResponse(**o) for o in offices]


@router.get(
    "/cities",
    response_model=list[str],
    summary="List cities supported by courier",
    description="Get the distinct list of cities where the given courier has at "
    "least one office. Optionally filter by a case-insensitive prefix matched "
    "against both Bulgarian and English city names, so `q=So` and `q=Со` return "
    "the same cities. Returns an empty array if the courier has no data loaded "
    "or no cities match the prefix.",
)
async def list_cities(
    courier: Courier = Query(..., description="Courier: 'speedy' or 'econt'"),
    q: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Optional case-insensitive prefix filter (BG or EN)",
    ),
    locale: Locale = Query(default="bg", description="Content locale for returned city names"),
) -> list[str]:
    """List distinct cities served by a courier, optionally filtered by prefix."""
    return delivery_service.get_cities(courier, query=q, locale=locale)


@router.get(
    "/places",
    response_model=list[CityPlace],
    summary="List served places (with postcode) for a courier",
    description="Get specific served delivery places for a courier — each a "
    "name + region + postcode. Same-named towns (e.g. the three 'Садово') are "
    "distinct rows disambiguated by region and postcode, so the door-delivery "
    "picker can supply the postcode the pricing API needs. Optional prefix "
    "filter matches case-insensitively against both Bulgarian and English "
    "names. Couriers without a places source (Speedy) return an empty array.",
)
async def list_places(
    courier: Courier = Query(..., description="Courier: 'speedy' or 'econt'"),
    q: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Optional case-insensitive prefix filter (BG or EN)",
    ),
    locale: Locale = Query(default="bg", description="Content locale for returned names"),
) -> list[CityPlace]:
    """List served places for a courier, optionally filtered by prefix."""
    return [CityPlace(**p) for p in delivery_service.get_places(courier, query=q, locale=locale)]


@router.post(
    "/calculate",
    response_model=CalculateShippingResponse,
    summary="Calculate shipping cost",
    description="Return a shipping quote per requested courier for the current "
    "cart. Approximate mode (city only) is used for side-by-side comparison; "
    "exact mode (office_id/address, one courier) refines the price. Free shipping "
    "(items ≥ €50) short-circuits to 0¢. A courier being down yields a flat "
    "fallback quote rather than an error — the endpoint never fails.",
)
async def calculate_shipping(
    body: CalculateShippingRequest,
    session_id: Annotated[str, Depends(require_session)],
) -> CalculateShippingResponse:
    """Calculate shipping quotes for the caller's cart."""
    with get_db() as conn:
        weight_grams = shipping_service.cart_weight_grams(conn, session_id)

    quotes = await shipping_service.calculate_quotes(
        couriers=body.couriers,
        method=body.method,
        city=body.city,
        office_id=body.office_id,
        address=body.address,
        weight_grams=weight_grams,
        items_total_cents=body.items_total_cents,
    )
    return CalculateShippingResponse(quotes=quotes)
