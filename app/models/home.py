"""Homepage content request and response models."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.constants import HomeSectionType
from app.models.about import MAX_ABOUT_TEXT_LENGTH, MAX_ABOUT_TITLE_LENGTH, MAX_ABOUT_URL_LENGTH


class HomeCtaPublic(BaseModel):
    """Localized CTA returned by the public homepage API."""

    label: str
    href: str


class HomeItemPublic(BaseModel):
    """Localized child item for editable homepage sections."""

    id: int
    title: str
    text: str | None = None
    image: str | None = None
    link: str | None = None


class HomeSectionPublic(BaseModel):
    """Localized public homepage section."""

    slug: str
    type: HomeSectionType
    heading: str
    subheading: str | None = None
    body: str | None = None
    cta: HomeCtaPublic | None = None
    image: str | None = None
    items: list[HomeItemPublic] = Field(default_factory=list)


class HomePublicResponse(BaseModel):
    """Public homepage API response."""

    sections: list[HomeSectionPublic]


class HomeItemAdmin(BaseModel):
    """Raw bilingual child item for admin editing."""

    id: int
    section: str
    title_en: str
    title_bg: str | None = None
    text_en: str | None = None
    text_bg: str | None = None
    image_id: str | None = None
    image: str | None = None
    link_href: str | None = None
    sort_order: int
    is_published: bool
    created_at: str
    updated_at: str


class HomeSectionAdmin(BaseModel):
    """Raw bilingual homepage section for admin editing."""

    slug: str
    type: HomeSectionType
    heading_en: str
    heading_bg: str | None = None
    subheading_en: str | None = None
    subheading_bg: str | None = None
    body_en: str | None = None
    body_bg: str | None = None
    cta_label_en: str | None = None
    cta_label_bg: str | None = None
    cta_href: str | None = None
    image_id: str | None = None
    image: str | None = None
    sort_order: int
    is_published: bool
    created_at: str
    updated_at: str
    items: list[HomeItemAdmin] = Field(default_factory=list)


class HomeAdminResponse(BaseModel):
    """Admin homepage content response."""

    sections: list[HomeSectionAdmin]


class PatchHomeSectionRequest(BaseModel):
    """Patch editable bilingual section text and CTA fields only."""

    model_config = ConfigDict(extra="forbid")

    heading_en: str | None = Field(default=None, min_length=1, max_length=MAX_ABOUT_TITLE_LENGTH)
    heading_bg: str | None = Field(default=None, max_length=MAX_ABOUT_TITLE_LENGTH)
    subheading_en: str | None = Field(default=None, max_length=MAX_ABOUT_TITLE_LENGTH)
    subheading_bg: str | None = Field(default=None, max_length=MAX_ABOUT_TITLE_LENGTH)
    body_en: str | None = Field(default=None, max_length=MAX_ABOUT_TEXT_LENGTH)
    body_bg: str | None = Field(default=None, max_length=MAX_ABOUT_TEXT_LENGTH)
    cta_label_en: str | None = Field(default=None, max_length=MAX_ABOUT_TITLE_LENGTH)
    cta_label_bg: str | None = Field(default=None, max_length=MAX_ABOUT_TITLE_LENGTH)
    cta_href: str | None = Field(default=None, max_length=MAX_ABOUT_URL_LENGTH)

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null_heading_en(cls, data: dict) -> dict:
        if isinstance(data, dict) and "heading_en" in data and data["heading_en"] is None:
            msg = "heading_en cannot be null"
            raise ValueError(msg)
        return data


class CreateHomeItemRequest(BaseModel):
    """Create an item under an existing homepage section."""

    model_config = ConfigDict(extra="forbid")

    title_en: str = Field(..., min_length=1, max_length=MAX_ABOUT_TITLE_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_ABOUT_TITLE_LENGTH)
    text_en: str | None = Field(default=None, max_length=MAX_ABOUT_TEXT_LENGTH)
    text_bg: str | None = Field(default=None, max_length=MAX_ABOUT_TEXT_LENGTH)
    link_href: str | None = Field(default=None, max_length=MAX_ABOUT_URL_LENGTH)
    is_published: bool = True


class PatchHomeItemRequest(BaseModel):
    """Patch editable homepage item fields."""

    model_config = ConfigDict(extra="forbid")

    title_en: str | None = Field(default=None, min_length=1, max_length=MAX_ABOUT_TITLE_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_ABOUT_TITLE_LENGTH)
    text_en: str | None = Field(default=None, max_length=MAX_ABOUT_TEXT_LENGTH)
    text_bg: str | None = Field(default=None, max_length=MAX_ABOUT_TEXT_LENGTH)
    link_href: str | None = Field(default=None, max_length=MAX_ABOUT_URL_LENGTH)
    is_published: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null_title_en(cls, data: dict) -> dict:
        if isinstance(data, dict) and "title_en" in data and data["title_en"] is None:
            msg = "title_en cannot be null"
            raise ValueError(msg)
        return data


class ReorderHomeSectionsRequest(BaseModel):
    """Replace homepage section display order by slug."""

    slugs: list[str] = Field(..., min_length=1, max_length=50)


class ReorderHomeItemsRequest(BaseModel):
    """Replace homepage item display order by id."""

    ids: list[int] = Field(..., min_length=0, max_length=100)


class HomePublishToggleRequest(BaseModel):
    """Set homepage section or item publish state."""

    is_published: bool
