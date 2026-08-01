"""Terms & Conditions endpoints: public content and admin editing."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.dependencies.auth import require_admin
from app.models.products import Locale
from app.models.terms import (
    PatchTermsPageRequest,
    PatchTermsSectionRequest,
    TermsAdminResponse,
    TermsPageAdmin,
    TermsPublicResponse,
    TermsSectionAdmin,
)
from app.responses import error_response
from app.services import terms_service
from app.services.terms_service import TermsNotFoundError, TermsValidationError

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get("", response_model=TermsPublicResponse, summary="Get public Terms")
async def get_terms(
    locale: Locale | str = Query(default="en", description="Content locale (en or bg)"),
) -> TermsPublicResponse:
    """Return localized Terms & Conditions content."""
    return TermsPublicResponse(**terms_service.get_public_terms(locale))


@admin_router.get("", response_model=TermsAdminResponse, summary="Get admin Terms")
async def admin_list_terms() -> TermsAdminResponse | JSONResponse:
    """Return raw bilingual Terms content for admin editing."""
    try:
        return TermsAdminResponse(**terms_service.list_admin_terms())
    except TermsNotFoundError:
        return _error(404, "terms_not_found", "Terms content not found")


@admin_router.patch("/page", response_model=TermsPageAdmin)
async def admin_update_terms_page(
    body: PatchTermsPageRequest,
) -> TermsPageAdmin | JSONResponse:
    try:
        page = terms_service.update_page(body.model_dump(exclude_unset=True))
    except TermsNotFoundError:
        return _error(404, "terms_not_found", "Terms content not found")
    except TermsValidationError as e:
        return _error(422, "invalid_terms", str(e))
    return TermsPageAdmin(**page)


@admin_router.patch("/sections/{slug}", response_model=TermsSectionAdmin)
async def admin_update_terms_section(
    slug: str, body: PatchTermsSectionRequest
) -> TermsSectionAdmin | JSONResponse:
    try:
        section = terms_service.update_section(slug, body.model_dump(exclude_unset=True))
    except TermsNotFoundError:
        return _error(404, "terms_section_not_found", "Terms section not found")
    except TermsValidationError as e:
        return _error(422, "invalid_terms", str(e))
    return TermsSectionAdmin(**section)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return error_response(status_code, code, message)
