"""Cookie Policy request and response models."""

from pydantic import BaseModel, ConfigDict, Field

MAX_COOKIE_LABEL_LENGTH = 300
MAX_COOKIE_TEXT_LENGTH = 8_000
MAX_COOKIE_PARAGRAPH_COUNT = 80


class CookieHeadersPublic(BaseModel):
    """Localized cookie inventory table headers."""

    name: str
    purpose: str
    type: str
    duration: str


class CookieInventoryPublic(BaseModel):
    """Localized public cookie inventory row."""

    name: str
    purpose: str
    type: str
    duration: str


class CookieSectionPublic(BaseModel):
    """Localized public Cookie Policy section."""

    id: str
    title: str
    body: list[str] = Field(default_factory=list)


class CookiesPublicResponse(BaseModel):
    """Localized public Cookie Policy payload."""

    meta_title: str
    meta_description: str
    eyebrow: str
    title: str
    subtitle: str
    last_updated: str
    inventory_title: str
    headers: CookieHeadersPublic
    cookies: list[CookieInventoryPublic] = Field(default_factory=list)
    sections: list[CookieSectionPublic] = Field(default_factory=list)


class CookiesPageAdmin(BaseModel):
    """Raw bilingual Cookie Policy page-level copy."""

    id: str
    meta_title_en: str
    meta_title_bg: str | None = None
    meta_description_en: str
    meta_description_bg: str | None = None
    eyebrow_en: str
    eyebrow_bg: str | None = None
    title_en: str
    title_bg: str | None = None
    subtitle_en: str
    subtitle_bg: str | None = None
    last_updated_en: str
    last_updated_bg: str | None = None
    inventory_title_en: str
    inventory_title_bg: str | None = None
    header_name_en: str
    header_name_bg: str | None = None
    header_purpose_en: str
    header_purpose_bg: str | None = None
    header_type_en: str
    header_type_bg: str | None = None
    header_duration_en: str
    header_duration_bg: str | None = None
    created_at: str
    updated_at: str


class CookieInventoryAdmin(BaseModel):
    """Raw bilingual cookie inventory row."""

    name: str
    purpose_en: str
    purpose_bg: str | None = None
    type_en: str
    type_bg: str | None = None
    duration_en: str
    duration_bg: str | None = None
    sort_order: int
    created_at: str
    updated_at: str


class CookieSectionAdmin(BaseModel):
    """Raw bilingual Cookie Policy section."""

    slug: str
    title_en: str
    title_bg: str | None = None
    body_en: list[str] = Field(default_factory=list)
    body_bg: list[str] | None = None
    sort_order: int
    created_at: str
    updated_at: str


class CookiesAdminResponse(BaseModel):
    """Admin Cookie Policy payload."""

    page: CookiesPageAdmin
    cookies: list[CookieInventoryAdmin] = Field(default_factory=list)
    sections: list[CookieSectionAdmin] = Field(default_factory=list)


class PatchCookiesPageRequest(BaseModel):
    """Patch editable Cookie Policy page-level text fields."""

    model_config = ConfigDict(extra="forbid")

    meta_title_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    meta_title_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    meta_description_en: str | None = Field(default=None, max_length=MAX_COOKIE_TEXT_LENGTH)
    meta_description_bg: str | None = Field(default=None, max_length=MAX_COOKIE_TEXT_LENGTH)
    eyebrow_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    eyebrow_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    title_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    subtitle_en: str | None = Field(default=None, max_length=MAX_COOKIE_TEXT_LENGTH)
    subtitle_bg: str | None = Field(default=None, max_length=MAX_COOKIE_TEXT_LENGTH)
    last_updated_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    last_updated_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    inventory_title_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    inventory_title_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    header_name_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    header_name_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    header_purpose_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    header_purpose_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    header_type_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    header_type_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    header_duration_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    header_duration_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)


class PatchCookieInventoryRequest(BaseModel):
    """Patch editable cookie inventory row fields."""

    model_config = ConfigDict(extra="forbid")

    purpose_en: str | None = Field(default=None, max_length=MAX_COOKIE_TEXT_LENGTH)
    purpose_bg: str | None = Field(default=None, max_length=MAX_COOKIE_TEXT_LENGTH)
    type_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    type_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    duration_en: str | None = Field(default=None, max_length=MAX_COOKIE_TEXT_LENGTH)
    duration_bg: str | None = Field(default=None, max_length=MAX_COOKIE_TEXT_LENGTH)


class PatchCookieSectionRequest(BaseModel):
    """Patch editable Cookie Policy section fields."""

    model_config = ConfigDict(extra="forbid")

    title_en: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_COOKIE_LABEL_LENGTH)
    body_en: list[str] | None = Field(default=None, max_length=MAX_COOKIE_PARAGRAPH_COUNT)
    body_bg: list[str] | None = Field(default=None, max_length=MAX_COOKIE_PARAGRAPH_COUNT)
