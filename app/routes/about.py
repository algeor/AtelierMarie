"""Public and admin routes for the atelier story page."""

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from app.dependencies.auth import require_admin
from app.models.about import (
    AboutAdminResponse,
    AboutItemAdmin,
    AboutPublicResponse,
    AboutSectionAdmin,
    CreateAboutItemRequest,
    PatchAboutItemRequest,
    PatchAboutSectionRequest,
    PublishToggleRequest,
    ReorderAboutItemsRequest,
    ReorderAboutSectionsRequest,
)
from app.models.products import Locale
from app.services import about_service
from app.services.about_service import (
    AboutItemNotFoundError,
    AboutReorderError,
    AboutSectionNotFoundError,
    AboutValidationError,
)
from app.services.image_service import (
    MAX_FILE_SIZE,
    FileTooLargeError,
    ImageProcessingError,
    InvalidImageTypeError,
)

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get("", response_model=AboutPublicResponse)
async def get_about(
    locale: Locale = Query(default="en", description="Content locale (en or bg)"),
) -> AboutPublicResponse:
    """Return published atelier story content localized for the storefront."""
    return AboutPublicResponse(**about_service.get_public_about(locale))


@admin_router.get("", response_model=AboutAdminResponse)
async def admin_list_about() -> AboutAdminResponse:
    """Return all raw bilingual atelier story content for admin editing."""
    return AboutAdminResponse(**about_service.list_admin_about())


@admin_router.post("/sections/reorder", response_model=list[AboutSectionAdmin])
async def admin_reorder_sections(
    body: ReorderAboutSectionsRequest,
) -> list[AboutSectionAdmin] | JSONResponse:
    try:
        return [AboutSectionAdmin(**s) for s in about_service.reorder_sections(body.slugs)]
    except AboutReorderError as e:
        return _error(409, "invalid_about_order", str(e))


@admin_router.patch("/sections/{slug}", response_model=AboutSectionAdmin)
async def admin_update_section(
    slug: str, body: PatchAboutSectionRequest
) -> AboutSectionAdmin | JSONResponse:
    try:
        section = about_service.update_section_text(slug, body.model_dump(exclude_unset=True))
    except AboutSectionNotFoundError:
        return _error(404, "about_section_not_found", "About section not found")
    except AboutValidationError as e:
        return _error(422, "invalid_about_section", str(e))
    return AboutSectionAdmin(**section)


@admin_router.patch("/sections/{slug}/publish", response_model=AboutSectionAdmin)
async def admin_publish_section(
    slug: str, body: PublishToggleRequest
) -> AboutSectionAdmin | JSONResponse:
    try:
        section = about_service.set_section_published(slug, body.is_published)
    except AboutSectionNotFoundError:
        return _error(404, "about_section_not_found", "About section not found")
    return AboutSectionAdmin(**section)


@admin_router.post("/sections/{slug}/items", response_model=AboutItemAdmin, status_code=201)
async def admin_create_item(
    slug: str, body: CreateAboutItemRequest
) -> AboutItemAdmin | JSONResponse:
    try:
        item = about_service.create_item(slug, body.model_dump())
    except AboutSectionNotFoundError:
        return _error(404, "about_section_not_found", "About section not found")
    except AboutValidationError as e:
        return _error(422, "invalid_about_item", str(e))
    return AboutItemAdmin(**item)


@admin_router.post("/sections/{slug}/items/reorder", response_model=list[AboutItemAdmin])
async def admin_reorder_items(
    slug: str, body: ReorderAboutItemsRequest
) -> list[AboutItemAdmin] | JSONResponse:
    try:
        return [AboutItemAdmin(**i) for i in about_service.reorder_items(slug, body.ids)]
    except AboutSectionNotFoundError:
        return _error(404, "about_section_not_found", "About section not found")
    except AboutReorderError as e:
        return _error(409, "invalid_about_item_order", str(e))


@admin_router.patch("/sections/{slug}/items/{item_id}", response_model=AboutItemAdmin)
async def admin_update_item(
    slug: str, item_id: int, body: PatchAboutItemRequest
) -> AboutItemAdmin | JSONResponse:
    try:
        item = about_service.update_item(slug, item_id, body.model_dump(exclude_unset=True))
    except AboutItemNotFoundError:
        return _error(404, "about_item_not_found", "About item not found")
    except AboutValidationError as e:
        return _error(422, "invalid_about_item", str(e))
    return AboutItemAdmin(**item)


@admin_router.delete("/sections/{slug}/items/{item_id}", status_code=204, response_class=Response)
async def admin_delete_item(slug: str, item_id: int) -> Response:
    try:
        about_service.delete_item(slug, item_id)
    except AboutItemNotFoundError:
        return _error(404, "about_item_not_found", "About item not found")
    return Response(status_code=204)


@admin_router.patch("/sections/{slug}/items/{item_id}/publish", response_model=AboutItemAdmin)
async def admin_publish_item(
    slug: str, item_id: int, body: PublishToggleRequest
) -> AboutItemAdmin | JSONResponse:
    try:
        item = about_service.set_item_published(slug, item_id, body.is_published)
    except AboutItemNotFoundError:
        return _error(404, "about_item_not_found", "About item not found")
    return AboutItemAdmin(**item)


@admin_router.post("/sections/{slug}/image", response_model=AboutSectionAdmin)
async def admin_upload_section_image(
    slug: str, file: UploadFile = File(...)
) -> AboutSectionAdmin | JSONResponse:
    try:
        section = about_service.set_section_image(slug, await _read_upload_with_limit(file))
    except AboutSectionNotFoundError:
        return _error(404, "about_section_not_found", "About section not found")
    except FileTooLargeError:
        return _error(422, "file_too_large", "File size exceeds maximum of 5MB")
    except InvalidImageTypeError:
        return _error(422, "invalid_image_type", "Unsupported image format")
    except ImageProcessingError:
        return _error(422, "image_processing_failed", "Image could not be processed")
    return AboutSectionAdmin(**section)


@admin_router.delete("/sections/{slug}/image", response_model=AboutSectionAdmin)
async def admin_clear_section_image(slug: str) -> AboutSectionAdmin | JSONResponse:
    try:
        section = about_service.clear_section_image(slug)
    except AboutSectionNotFoundError:
        return _error(404, "about_section_not_found", "About section not found")
    return AboutSectionAdmin(**section)


@admin_router.post("/sections/{slug}/items/{item_id}/image", response_model=AboutItemAdmin)
async def admin_upload_item_image(
    slug: str, item_id: int, file: UploadFile = File(...)
) -> AboutItemAdmin | JSONResponse:
    try:
        item = about_service.set_item_image(slug, item_id, await _read_upload_with_limit(file))
    except AboutItemNotFoundError:
        return _error(404, "about_item_not_found", "About item not found")
    except FileTooLargeError:
        return _error(422, "file_too_large", "File size exceeds maximum of 5MB")
    except InvalidImageTypeError:
        return _error(422, "invalid_image_type", "Unsupported image format")
    except ImageProcessingError:
        return _error(422, "image_processing_failed", "Image could not be processed")
    return AboutItemAdmin(**item)


@admin_router.delete("/sections/{slug}/items/{item_id}/image", response_model=AboutItemAdmin)
async def admin_clear_item_image(slug: str, item_id: int) -> AboutItemAdmin | JSONResponse:
    try:
        item = about_service.clear_item_image(slug, item_id)
    except AboutItemNotFoundError:
        return _error(404, "about_item_not_found", "About item not found")
    return AboutItemAdmin(**item)


async def _read_upload_with_limit(file: UploadFile) -> bytes:
    chunks = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > MAX_FILE_SIZE:
            raise FileTooLargeError("File size exceeds maximum of 5MB")
    return bytes(chunks)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )
