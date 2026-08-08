"""Public and admin routes for editable homepage content."""

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from app.dependencies.auth import require_admin
from app.models.home import (
    CreateHomeItemRequest,
    HomeAdminResponse,
    HomeItemAdmin,
    HomePublicResponse,
    HomePublishToggleRequest,
    HomeSectionAdmin,
    PatchHomeItemRequest,
    PatchHomeSectionRequest,
    ReorderHomeItemsRequest,
    ReorderHomeSectionsRequest,
)
from app.models.products import Locale
from app.responses import error_response
from app.services import home_service
from app.services.home_service import (
    HomeItemNotFoundError,
    HomeReorderError,
    HomeSectionNotFoundError,
    HomeValidationError,
)
from app.services.image_service import (
    MAX_FILE_SIZE,
    FileTooLargeError,
    ImageProcessingError,
    InvalidImageTypeError,
)

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get("", response_model=HomePublicResponse)
async def get_home(
    locale: Locale = Query(default="en", description="Content locale (en or bg)"),
) -> HomePublicResponse:
    """Return published homepage content localized for the storefront."""
    return HomePublicResponse(**home_service.get_public_home(locale))


@admin_router.get("", response_model=HomeAdminResponse)
async def admin_list_home() -> HomeAdminResponse:
    """Return all raw bilingual homepage content for admin editing."""
    return HomeAdminResponse(**home_service.list_admin_home())


@admin_router.post("/sections/reorder", response_model=list[HomeSectionAdmin])
async def admin_reorder_sections(
    body: ReorderHomeSectionsRequest,
) -> list[HomeSectionAdmin] | JSONResponse:
    try:
        return [HomeSectionAdmin(**s) for s in home_service.reorder_sections(body.slugs)]
    except HomeReorderError as e:
        return _error(409, "invalid_home_order", str(e))


@admin_router.patch("/sections/{slug}", response_model=HomeSectionAdmin)
async def admin_update_section(
    slug: str, body: PatchHomeSectionRequest
) -> HomeSectionAdmin | JSONResponse:
    try:
        section = home_service.update_section_text(slug, body.model_dump(exclude_unset=True))
    except HomeSectionNotFoundError:
        return _error(404, "home_section_not_found", "Homepage section not found")
    except HomeValidationError as e:
        return _error(422, "invalid_home_section", str(e))
    return HomeSectionAdmin(**section)


@admin_router.patch("/sections/{slug}/publish", response_model=HomeSectionAdmin)
async def admin_publish_section(
    slug: str, body: HomePublishToggleRequest
) -> HomeSectionAdmin | JSONResponse:
    try:
        section = home_service.set_section_published(slug, body.is_published)
    except HomeSectionNotFoundError:
        return _error(404, "home_section_not_found", "Homepage section not found")
    return HomeSectionAdmin(**section)


@admin_router.post("/sections/{slug}/items", response_model=HomeItemAdmin, status_code=201)
async def admin_create_item(slug: str, body: CreateHomeItemRequest) -> HomeItemAdmin | JSONResponse:
    try:
        item = home_service.create_item(slug, body.model_dump())
    except HomeSectionNotFoundError:
        return _error(404, "home_section_not_found", "Homepage section not found")
    except HomeValidationError as e:
        return _error(422, "invalid_home_item", str(e))
    return HomeItemAdmin(**item)


@admin_router.post("/sections/{slug}/items/reorder", response_model=list[HomeItemAdmin])
async def admin_reorder_items(
    slug: str, body: ReorderHomeItemsRequest
) -> list[HomeItemAdmin] | JSONResponse:
    try:
        return [HomeItemAdmin(**i) for i in home_service.reorder_items(slug, body.ids)]
    except HomeSectionNotFoundError:
        return _error(404, "home_section_not_found", "Homepage section not found")
    except HomeReorderError as e:
        return _error(409, "invalid_home_item_order", str(e))


@admin_router.patch("/sections/{slug}/items/{item_id}", response_model=HomeItemAdmin)
async def admin_update_item(
    slug: str, item_id: int, body: PatchHomeItemRequest
) -> HomeItemAdmin | JSONResponse:
    try:
        item = home_service.update_item(slug, item_id, body.model_dump(exclude_unset=True))
    except HomeItemNotFoundError:
        return _error(404, "home_item_not_found", "Homepage item not found")
    except HomeValidationError as e:
        return _error(422, "invalid_home_item", str(e))
    return HomeItemAdmin(**item)


@admin_router.delete("/sections/{slug}/items/{item_id}", status_code=204, response_class=Response)
async def admin_delete_item(slug: str, item_id: int) -> Response:
    try:
        home_service.delete_item(slug, item_id)
    except HomeItemNotFoundError:
        return _error(404, "home_item_not_found", "Homepage item not found")
    return Response(status_code=204)


@admin_router.patch("/sections/{slug}/items/{item_id}/publish", response_model=HomeItemAdmin)
async def admin_publish_item(
    slug: str, item_id: int, body: HomePublishToggleRequest
) -> HomeItemAdmin | JSONResponse:
    try:
        item = home_service.set_item_published(slug, item_id, body.is_published)
    except HomeItemNotFoundError:
        return _error(404, "home_item_not_found", "Homepage item not found")
    return HomeItemAdmin(**item)


@admin_router.post("/sections/{slug}/image", response_model=HomeSectionAdmin)
async def admin_upload_section_image(
    slug: str, file: UploadFile = File(...)
) -> HomeSectionAdmin | JSONResponse:
    try:
        section = home_service.set_section_image(slug, await _read_upload_with_limit(file))
    except HomeSectionNotFoundError:
        return _error(404, "home_section_not_found", "Homepage section not found")
    except FileTooLargeError:
        return _error(422, "file_too_large", "File size exceeds maximum of 5MB")
    except InvalidImageTypeError:
        return _error(422, "invalid_image_type", "Unsupported image format")
    except ImageProcessingError:
        return _error(422, "image_processing_failed", "Image could not be processed")
    return HomeSectionAdmin(**section)


@admin_router.delete("/sections/{slug}/image", response_model=HomeSectionAdmin)
async def admin_clear_section_image(slug: str) -> HomeSectionAdmin | JSONResponse:
    try:
        section = home_service.clear_section_image(slug)
    except HomeSectionNotFoundError:
        return _error(404, "home_section_not_found", "Homepage section not found")
    return HomeSectionAdmin(**section)


@admin_router.post("/sections/{slug}/items/{item_id}/image", response_model=HomeItemAdmin)
async def admin_upload_item_image(
    slug: str, item_id: int, file: UploadFile = File(...)
) -> HomeItemAdmin | JSONResponse:
    try:
        item = home_service.set_item_image(slug, item_id, await _read_upload_with_limit(file))
    except HomeItemNotFoundError:
        return _error(404, "home_item_not_found", "Homepage item not found")
    except FileTooLargeError:
        return _error(422, "file_too_large", "File size exceeds maximum of 5MB")
    except InvalidImageTypeError:
        return _error(422, "invalid_image_type", "Unsupported image format")
    except ImageProcessingError:
        return _error(422, "image_processing_failed", "Image could not be processed")
    return HomeItemAdmin(**item)


@admin_router.delete("/sections/{slug}/items/{item_id}/image", response_model=HomeItemAdmin)
async def admin_clear_item_image(slug: str, item_id: int) -> HomeItemAdmin | JSONResponse:
    try:
        item = home_service.clear_item_image(slug, item_id)
    except HomeItemNotFoundError:
        return _error(404, "home_item_not_found", "Homepage item not found")
    return HomeItemAdmin(**item)


async def _read_upload_with_limit(file: UploadFile) -> bytes:
    data = await file.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        raise FileTooLargeError("File size exceeds maximum")
    return data


def _error(status: int, code: str, message: str) -> JSONResponse:
    return error_response(status, code, message)
