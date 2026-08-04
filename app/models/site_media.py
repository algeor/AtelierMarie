"""Pydantic models for admin-managed reusable site media."""

from typing import Literal

from pydantic import BaseModel

SiteMediaKey = Literal[
    "home_hero",
    "home_hero_fallback",
    "atelier_hero_fallback",
    "atelier_story_fallback",
    "atelier_atelier_fallback",
    "atelier_collections_fallback",
    "atelier_process_fallback",
    "error_page_image",
    "page_background",
]


class SiteMediaAssetAdmin(BaseModel):
    """One reusable UI media slot as shown in admin."""

    key: SiteMediaKey
    label: str
    description: str
    default_url: str | None = None
    image_id: str | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None
    zoom_url: str | None = None
    effective_url: str | None = None
    updated_at: str


class SiteMediaAdminResponse(BaseModel):
    """All managed media slots for admin editing."""

    assets: list[SiteMediaAssetAdmin]


class PublicSiteMediaResponse(BaseModel):
    """Public effective URLs for reusable UI media slots."""

    assets: dict[SiteMediaKey, str | None]
