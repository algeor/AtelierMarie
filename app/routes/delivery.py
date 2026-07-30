"""Delivery data endpoints — courier offices and cities lookup.

Read-only endpoints backed by `delivery_service`. No auth required — office
data is public. See `courier-offices-data` spec for the endpoint contract.
"""

from typing import Literal

from fastapi import APIRouter, Query

from app.models.delivery import Courier, DeliveryConfigResponse, OfficeResponse, OfficeType
from app.services import delivery_service, econt_settings_service

router = APIRouter()

Locale = Literal["en", "bg"]


@router.get(
    "/config",
    response_model=DeliveryConfigResponse,
    summary="Get public delivery configuration",
    description="Return checkout-safe delivery settings such as Econt Office Locator behavior.",
)
async def get_delivery_config() -> DeliveryConfigResponse:
    """Return public-safe delivery configuration for checkout."""
    return econt_settings_service.get_public_delivery_config()


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
