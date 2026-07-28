"""Atelier story page request and response models."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.constants import AboutSectionType

MAX_ABOUT_TEXT_LENGTH = 8_000
MAX_ABOUT_TITLE_LENGTH = 300
MAX_ABOUT_URL_LENGTH = 500


class AboutCtaPublic(BaseModel):
    """Localized CTA returned by the public about API."""

    label: str
    href: str


class AboutItemPublic(BaseModel):
    """Localized child item for cards, timeline, and collections sections."""

    id: int
    title: str
    text: str | None = None
    image: str | None = None
    link: str | None = None


class AboutSectionPublic(BaseModel):
    """Localized public atelier story section."""

    slug: str
    type: AboutSectionType
    heading: str
    subheading: str | None = None
    body: str | None = None
    cta: AboutCtaPublic | None = None
    image: str | None = None
    items: list[AboutItemPublic] = Field(default_factory=list)


class AboutPublicResponse(BaseModel):
    """Public about API response."""

    sections: list[AboutSectionPublic]


class AboutItemAdmin(BaseModel):
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


class AboutSectionAdmin(BaseModel):
    """Raw bilingual section for admin editing."""

    slug: str
    type: AboutSectionType
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
    items: list[AboutItemAdmin] = Field(default_factory=list)


class AboutAdminResponse(BaseModel):
    """Admin about API response."""

    sections: list[AboutSectionAdmin]


class PatchAboutSectionRequest(BaseModel):
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


class CreateAboutItemRequest(BaseModel):
    """Create an item under an existing atelier section."""

    model_config = ConfigDict(extra="forbid")

    title_en: str = Field(..., min_length=1, max_length=MAX_ABOUT_TITLE_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_ABOUT_TITLE_LENGTH)
    text_en: str | None = Field(default=None, max_length=MAX_ABOUT_TEXT_LENGTH)
    text_bg: str | None = Field(default=None, max_length=MAX_ABOUT_TEXT_LENGTH)
    link_href: str | None = Field(default=None, max_length=MAX_ABOUT_URL_LENGTH)
    is_published: bool = True


class PatchAboutItemRequest(BaseModel):
    """Patch editable item fields."""

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


class ReorderAboutSectionsRequest(BaseModel):
    """Replace section display order by slug."""

    slugs: list[str] = Field(..., min_length=1, max_length=50)


class ReorderAboutItemsRequest(BaseModel):
    """Replace item display order by id."""

    ids: list[int] = Field(..., min_length=0, max_length=100)


class PublishToggleRequest(BaseModel):
    """Set section or item publish state."""

    is_published: bool
