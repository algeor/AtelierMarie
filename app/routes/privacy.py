"""Privacy Policy endpoints: public content and admin editing."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.dependencies.auth import require_admin
from app.models.privacy import (
    PatchPrivacyPageRequest,
    PatchPrivacySectionRequest,
    PrivacyAdminResponse,
    PrivacyPageAdmin,
    PrivacyPublicResponse,
    PrivacySectionAdmin,
)
from app.models.products import Locale
from app.responses import error_response
from app.services import privacy_service
from app.services.privacy_service import PrivacyNotFoundError, PrivacyValidationError

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get("", response_model=PrivacyPublicResponse, summary="Get public Privacy Policy")
async def get_privacy(
    locale: Locale | str = Query(default="en", description="Content locale (en or bg)"),
) -> PrivacyPublicResponse:
    """Return localized Privacy Policy content."""
    return PrivacyPublicResponse(**privacy_service.get_public_privacy(locale))


@admin_router.get("", response_model=PrivacyAdminResponse, summary="Get admin Privacy Policy")
async def admin_list_privacy() -> PrivacyAdminResponse | JSONResponse:
    """Return raw bilingual Privacy Policy content for admin editing."""
    try:
        return PrivacyAdminResponse(**privacy_service.list_admin_privacy())
    except PrivacyNotFoundError:
        return _error(404, "privacy_not_found", "Privacy Policy content not found")


@admin_router.patch("/page", response_model=PrivacyPageAdmin)
async def admin_update_privacy_page(
    body: PatchPrivacyPageRequest,
) -> PrivacyPageAdmin | JSONResponse:
    try:
        page = privacy_service.update_page(body.model_dump(exclude_unset=True))
    except PrivacyNotFoundError:
        return _error(404, "privacy_not_found", "Privacy Policy content not found")
    except PrivacyValidationError as e:
        return _error(422, "invalid_privacy", str(e))
    return PrivacyPageAdmin(**page)


@admin_router.patch("/sections/{slug}", response_model=PrivacySectionAdmin)
async def admin_update_privacy_section(
    slug: str, body: PatchPrivacySectionRequest
) -> PrivacySectionAdmin | JSONResponse:
    try:
        section = privacy_service.update_section(slug, body.model_dump(exclude_unset=True))
    except PrivacyNotFoundError:
        return _error(404, "privacy_section_not_found", "Privacy Policy section not found")
    except PrivacyValidationError as e:
        return _error(422, "invalid_privacy", str(e))
    return PrivacySectionAdmin(**section)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return error_response(status_code, code, message)
