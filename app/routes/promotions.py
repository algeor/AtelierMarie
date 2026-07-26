"""Promotion campaign + managed banner routes.

- `admin_router` (admin-only): campaign CRUD/apply/remove and banner settings,
  mounted at `/v1/admin/promotions`.
- `public_router` (public): active banner read, mounted at `/v1/promotions`.

The bulk product discount endpoint lives with the other product admin routes in
`app/routes/admin.py` (`PATCH /v1/admin/products/bulk-discount`).
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.dependencies.auth import require_admin
from app.models.promotions import (
    BannerAdminResponse,
    BannerUpdateRequest,
    BulkDiscountResponse,
    CampaignCreateRequest,
    CampaignListResponse,
    CampaignResponse,
    CampaignUpdateRequest,
    PublicBannerResponse,
)
from app.services import banner_service, promotion_service
from app.services.product_service import BulkTargetLimitError, DiscountValidationError

admin_router = APIRouter(dependencies=[Depends(require_admin)])
public_router = APIRouter()


def _campaign_not_found() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "NOT_FOUND", "message": "Campaign not found"}},
    )


# --- Admin campaigns -------------------------------------------------------


@admin_router.post(
    "/campaigns",
    response_model=CampaignResponse,
    status_code=201,
    summary="Create promotion campaign",
    description="Create a campaign management record. No product is changed until Apply.",
)
async def admin_create_campaign(body: CampaignCreateRequest) -> CampaignResponse:
    """Create a draft campaign."""
    campaign = promotion_service.create_campaign(body.model_dump(exclude_unset=False))
    return CampaignResponse(**campaign)


@admin_router.get(
    "/campaigns",
    response_model=CampaignListResponse,
    summary="List promotion campaigns",
)
async def admin_list_campaigns() -> CampaignListResponse:
    """List all campaigns, newest first."""
    campaigns, total = promotion_service.list_campaigns()
    return CampaignListResponse(items=[CampaignResponse(**c) for c in campaigns], total=total)


@admin_router.get(
    "/campaigns/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get promotion campaign",
    responses={404: {"description": "Campaign not found"}},
)
async def admin_get_campaign(campaign_id: str) -> CampaignResponse | JSONResponse:
    """Get one campaign by ID."""
    try:
        campaign = promotion_service.get_campaign(campaign_id)
    except promotion_service.CampaignNotFoundError:
        return _campaign_not_found()
    return CampaignResponse(**campaign)


@admin_router.patch(
    "/campaigns/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update promotion campaign",
    responses={
        404: {"description": "Campaign not found"},
        422: {"description": "Validation error"},
    },
)
async def admin_update_campaign(
    campaign_id: str, body: CampaignUpdateRequest
) -> CampaignResponse | JSONResponse:
    """Partially update a campaign."""
    try:
        campaign = promotion_service.update_campaign(
            campaign_id, body.model_dump(exclude_unset=True)
        )
    except promotion_service.CampaignNotFoundError:
        return _campaign_not_found()
    except DiscountValidationError as e:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": str(e)}},
        )
    return CampaignResponse(**campaign)


@admin_router.delete(
    "/campaigns/{campaign_id}",
    status_code=204,
    response_class=Response,
    summary="Delete promotion campaign",
    responses={404: {"description": "Campaign not found"}},
)
async def admin_delete_campaign(campaign_id: str) -> Response:
    """Delete a campaign record (applied product discounts are left untouched)."""
    try:
        promotion_service.delete_campaign(campaign_id)
    except promotion_service.CampaignNotFoundError:
        return _campaign_not_found()
    return Response(status_code=204)


@admin_router.post(
    "/campaigns/{campaign_id}/apply",
    response_model=BulkDiscountResponse,
    summary="Apply campaign discount to target products",
    responses={
        404: {"description": "Campaign not found"},
        422: {"description": "Target set exceeds the 500-product cap"},
    },
)
async def admin_apply_campaign(campaign_id: str) -> BulkDiscountResponse | JSONResponse:
    """Apply a campaign's discount to its resolved target products."""
    try:
        result = promotion_service.apply_campaign(campaign_id)
    except promotion_service.CampaignNotFoundError:
        return _campaign_not_found()
    except BulkTargetLimitError as e:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "BULK_TARGET_LIMIT_EXCEEDED", "message": str(e)}},
        )
    return BulkDiscountResponse(**result)


@admin_router.post(
    "/campaigns/{campaign_id}/remove",
    response_model=BulkDiscountResponse,
    summary="Remove campaign discount from applied products",
    responses={404: {"description": "Campaign not found"}},
)
async def admin_remove_campaign(campaign_id: str) -> BulkDiscountResponse | JSONResponse:
    """Conservatively clear a campaign's discount from its applied products."""
    try:
        result = promotion_service.remove_campaign(campaign_id)
    except promotion_service.CampaignNotFoundError:
        return _campaign_not_found()
    return BulkDiscountResponse(**result)


# --- Admin banner ----------------------------------------------------------


@admin_router.get(
    "/banner",
    response_model=BannerAdminResponse,
    summary="Get managed banner settings (admin)",
)
async def admin_get_banner() -> BannerAdminResponse:
    """Return the full managed banner settings for editing."""
    return BannerAdminResponse(**banner_service.get_banner_admin())


@admin_router.put(
    "/banner",
    response_model=BannerAdminResponse,
    summary="Update managed banner settings (admin)",
    responses={422: {"description": "Validation error"}},
)
async def admin_update_banner(body: BannerUpdateRequest) -> BannerAdminResponse:
    """Update the managed banner. Changing visible content bumps the version."""
    return BannerAdminResponse(**banner_service.update_banner(body.model_dump()))


# --- Public banner ---------------------------------------------------------


@public_router.get(
    "/banner",
    response_model=PublicBannerResponse,
    summary="Get the active site banner",
    description="Returns the currently visible banner for the locale, or null.",
)
async def get_public_banner(
    locale: str = Query(default="en", pattern="^(en|bg)$"),
) -> PublicBannerResponse:
    """Return the active localized banner, or null when none is visible."""
    banner = banner_service.get_public_banner(locale)
    return PublicBannerResponse(banner=banner)
