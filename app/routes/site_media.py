"""Public and admin routes for reusable site media assets."""

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse

from app.dependencies.auth import require_admin
from app.models.site_media import (
    PublicSiteMediaResponse,
    SiteMediaAdminResponse,
    SiteMediaAssetAdmin,
)
from app.responses import error_response
from app.services import site_media_service
from app.services.image_service import (
    FileTooLargeError,
    ImageProcessingError,
    InvalidImageTypeError,
)

MAX_SITE_MEDIA_FILE_SIZE = 10 * 1024 * 1024

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get("", response_model=PublicSiteMediaResponse)
async def get_site_media() -> PublicSiteMediaResponse:
    """Return public effective URLs for managed reusable media slots."""
    return PublicSiteMediaResponse(**site_media_service.get_public_assets())


@admin_router.get("", response_model=SiteMediaAdminResponse)
async def admin_list_site_media() -> SiteMediaAdminResponse:
    """Return all reusable media slots for admin editing."""
    return SiteMediaAdminResponse(**site_media_service.list_admin_assets())


@admin_router.post("/assets/{key}/image", response_model=SiteMediaAssetAdmin)
async def admin_upload_site_media_image(
    key: str, file: UploadFile = File(...)
) -> SiteMediaAssetAdmin | JSONResponse:
    """Upload or replace one reusable UI media asset."""
    try:
        asset = site_media_service.set_asset_image(key, await _read_upload_with_limit(file))
    except site_media_service.SiteMediaNotFoundError:
        return _error(404, "site_media_not_found", "Site media asset not found")
    except FileTooLargeError:
        return _error(422, "file_too_large", "File size exceeds maximum of 10MB")
    except InvalidImageTypeError:
        return _error(422, "invalid_image_type", "Unsupported image format")
    except ImageProcessingError:
        return _error(422, "image_processing_failed", "Image could not be processed")
    return SiteMediaAssetAdmin(**asset)


@admin_router.delete("/assets/{key}/image", response_model=SiteMediaAssetAdmin)
async def admin_clear_site_media_image(key: str) -> SiteMediaAssetAdmin | JSONResponse:
    """Clear one reusable UI media asset and restore its default."""
    try:
        asset = site_media_service.clear_asset_image(key)
    except site_media_service.SiteMediaNotFoundError:
        return _error(404, "site_media_not_found", "Site media asset not found")
    return SiteMediaAssetAdmin(**asset)


async def _read_upload_with_limit(file: UploadFile) -> bytes:
    chunks = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > MAX_SITE_MEDIA_FILE_SIZE:
            raise FileTooLargeError("File size exceeds maximum of 10MB")
    return bytes(chunks)


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return error_response(status_code, code, message)
