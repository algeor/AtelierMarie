"""Cookie Policy endpoints: public content and admin editing."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.dependencies.auth import require_admin
from app.models.cookies import (
    CookieInventoryAdmin,
    CookieSectionAdmin,
    CookiesAdminResponse,
    CookiesPageAdmin,
    CookiesPublicResponse,
    PatchCookieInventoryRequest,
    PatchCookieSectionRequest,
    PatchCookiesPageRequest,
)
from app.models.products import Locale
from app.responses import error_response
from app.services import cookies_service
from app.services.cookies_service import CookiesNotFoundError, CookiesValidationError

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get("", response_model=CookiesPublicResponse, summary="Get public Cookie Policy")
async def get_cookies(
    locale: Locale | str = Query(default="en", description="Content locale (en or bg)"),
) -> CookiesPublicResponse:
    """Return localized Cookie Policy content."""
    return CookiesPublicResponse(**cookies_service.get_public_cookies(locale))


@admin_router.get("", response_model=CookiesAdminResponse, summary="Get admin Cookie Policy")
async def admin_list_cookies() -> CookiesAdminResponse | JSONResponse:
    """Return raw bilingual Cookie Policy content for admin editing."""
    try:
        return CookiesAdminResponse(**cookies_service.list_admin_cookies())
    except CookiesNotFoundError:
        return _error(404, "cookies_not_found", "Cookie Policy content not found")


@admin_router.patch("/page", response_model=CookiesPageAdmin)
async def admin_update_cookies_page(
    body: PatchCookiesPageRequest,
) -> CookiesPageAdmin | JSONResponse:
    try:
        page = cookies_service.update_page(body.model_dump(exclude_unset=True))
    except CookiesNotFoundError:
        return _error(404, "cookies_not_found", "Cookie Policy content not found")
    except CookiesValidationError as e:
        return _error(422, "invalid_cookies", str(e))
    return CookiesPageAdmin(**page)


@admin_router.patch("/inventory/{name}", response_model=CookieInventoryAdmin)
async def admin_update_cookie_inventory(
    name: str, body: PatchCookieInventoryRequest
) -> CookieInventoryAdmin | JSONResponse:
    try:
        item = cookies_service.update_inventory_item(name, body.model_dump(exclude_unset=True))
    except CookiesNotFoundError:
        return _error(404, "cookie_inventory_not_found", "Cookie inventory row not found")
    except CookiesValidationError as e:
        return _error(422, "invalid_cookies", str(e))
    return CookieInventoryAdmin(**item)


@admin_router.patch("/sections/{slug}", response_model=CookieSectionAdmin)
async def admin_update_cookie_section(
    slug: str, body: PatchCookieSectionRequest
) -> CookieSectionAdmin | JSONResponse:
    try:
        section = cookies_service.update_section(slug, body.model_dump(exclude_unset=True))
    except CookiesNotFoundError:
        return _error(404, "cookie_section_not_found", "Cookie Policy section not found")
    except CookiesValidationError as e:
        return _error(422, "invalid_cookies", str(e))
    return CookieSectionAdmin(**section)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return error_response(status_code, code, message)
