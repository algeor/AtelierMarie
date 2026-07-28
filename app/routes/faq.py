"""FAQ endpoints — public listing and admin FAQ management."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.dependencies.auth import require_admin
from app.models.faq import (
    CreateFaqItemRequest,
    FaqAdminResponse,
    FaqItemAdminResponse,
    FaqResponse,
    FaqSectionAdminResponse,
    ReorderFaqItemsRequest,
    UpdateFaqItemRequest,
    UpdateFaqSectionRequest,
)
from app.models.products import Locale
from app.services import faq_service
from app.services.faq_service import (
    FaqItemNotFoundError,
    FaqSectionNotFoundError,
    FaqValidationError,
)

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get("", response_model=FaqResponse, summary="List public FAQ")
async def get_faq(
    locale: Locale | str = Query(default="en", description="Content locale (en or bg)"),
) -> FaqResponse:
    """Return published, localized FAQ content grouped by section."""
    return FaqResponse(**faq_service.get_public_faq(locale))


@admin_router.get("", response_model=FaqAdminResponse, summary="List admin FAQ")
async def admin_list_faq() -> FaqAdminResponse:
    """Return all FAQ sections and items, including hidden items."""
    return FaqAdminResponse(**faq_service.list_faq_admin())


@admin_router.post("", response_model=FaqItemAdminResponse, status_code=201)
async def admin_create_faq_item(
    body: CreateFaqItemRequest,
) -> FaqItemAdminResponse | JSONResponse:
    try:
        item = faq_service.create_item(body.model_dump(exclude_unset=True))
    except FaqSectionNotFoundError as e:
        return _validation(str(e))
    return FaqItemAdminResponse(**item)


@admin_router.patch("/items/{item_id}", response_model=FaqItemAdminResponse)
async def admin_update_faq_item(
    item_id: int, body: UpdateFaqItemRequest
) -> FaqItemAdminResponse | JSONResponse:
    try:
        item = faq_service.update_item(item_id, body.model_dump(exclude_unset=True))
    except FaqItemNotFoundError:
        return _not_found("FAQ item not found")
    except FaqSectionNotFoundError as e:
        return _validation(str(e))
    return FaqItemAdminResponse(**item)


@admin_router.delete("/items/{item_id}", status_code=204, response_class=Response)
async def admin_delete_faq_item(item_id: int) -> Response:
    try:
        faq_service.delete_item(item_id)
    except FaqItemNotFoundError:
        return _not_found("FAQ item not found")
    return Response(status_code=204)


@admin_router.patch("/reorder", response_model=FaqAdminResponse)
async def admin_reorder_faq_items(
    body: ReorderFaqItemsRequest,
) -> FaqAdminResponse | JSONResponse:
    try:
        faq = faq_service.reorder_items(body.section, body.ordered_ids)
    except FaqSectionNotFoundError as e:
        return _validation(str(e))
    except FaqItemNotFoundError:
        return _not_found("FAQ item not found")
    except FaqValidationError as e:
        return _validation(str(e))
    return FaqAdminResponse(**faq)


@admin_router.patch("/sections/{slug}", response_model=FaqSectionAdminResponse)
async def admin_update_faq_section(
    slug: str, body: UpdateFaqSectionRequest
) -> FaqSectionAdminResponse | JSONResponse:
    try:
        section = faq_service.update_section(slug, body.model_dump(exclude_unset=True))
    except FaqSectionNotFoundError:
        return _not_found("FAQ section not found")
    return FaqSectionAdminResponse(**section)


def _not_found(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "NOT_FOUND", "message": message}},
    )


def _validation(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "INVALID_FAQ", "message": message}},
    )
