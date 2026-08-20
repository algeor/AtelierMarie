"""SEO landing page endpoints: public content and admin editing."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.dependencies.auth import require_admin
from app.models.products import Locale
from app.models.seo_pages import (
    PatchSeoLandingFaqRequest,
    PatchSeoLandingPageRequest,
    SeoLandingAdminResponse,
    SeoLandingFaqAdmin,
    SeoLandingPageAdmin,
    SeoLandingPagePublic,
)
from app.responses import error_response
from app.services import seo_pages_service
from app.services.seo_pages_service import (
    SeoLandingPageNotFoundError,
    SeoLandingPageValidationError,
)

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get("/{slug}", response_model=SeoLandingPagePublic)
async def get_seo_landing_page(
    slug: str,
    locale: Locale | str = Query(default="en", description="Content locale (en or bg)"),
) -> SeoLandingPagePublic | JSONResponse:
    try:
        return SeoLandingPagePublic(**seo_pages_service.get_public_page(slug, locale))
    except SeoLandingPageNotFoundError:
        return _error(404, "seo_landing_page_not_found", "SEO landing page not found")


@admin_router.get("", response_model=SeoLandingAdminResponse)
async def admin_list_seo_landing_pages() -> SeoLandingAdminResponse:
    return SeoLandingAdminResponse(**seo_pages_service.list_admin_pages())


@admin_router.patch("/{slug}", response_model=SeoLandingPageAdmin)
async def admin_update_seo_landing_page(
    slug: str,
    body: PatchSeoLandingPageRequest,
) -> SeoLandingPageAdmin | JSONResponse:
    try:
        page = seo_pages_service.update_page(slug, body.model_dump(exclude_unset=True))
    except SeoLandingPageNotFoundError:
        return _error(404, "seo_landing_page_not_found", "SEO landing page not found")
    except SeoLandingPageValidationError as e:
        return _error(422, "invalid_seo_landing_page", str(e))
    return SeoLandingPageAdmin(**page)


@admin_router.patch("/{slug}/faq/{item_id}", response_model=SeoLandingFaqAdmin)
async def admin_update_seo_landing_faq_item(
    slug: str,
    item_id: int,
    body: PatchSeoLandingFaqRequest,
) -> SeoLandingFaqAdmin | JSONResponse:
    try:
        item = seo_pages_service.update_faq_item(
            slug,
            item_id,
            body.model_dump(exclude_unset=True),
        )
    except SeoLandingPageNotFoundError:
        return _error(404, "seo_landing_faq_not_found", "SEO landing FAQ item not found")
    except SeoLandingPageValidationError as e:
        return _error(422, "invalid_seo_landing_faq", str(e))
    return SeoLandingFaqAdmin(**item)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return error_response(status_code, code, message)
