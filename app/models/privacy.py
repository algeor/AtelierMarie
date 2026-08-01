"""Privacy Policy request and response models."""

from pydantic import BaseModel, ConfigDict, Field

MAX_PRIVACY_LABEL_LENGTH = 300
MAX_PRIVACY_TEXT_LENGTH = 8_000
MAX_PRIVACY_PARAGRAPH_COUNT = 120


class PrivacySectionPublic(BaseModel):
    """Localized public Privacy Policy section."""

    id: str
    title: str
    nav: str
    body: list[str] = Field(default_factory=list)


class PrivacyPublicResponse(BaseModel):
    """Localized public Privacy Policy page payload."""

    meta_title: str
    meta_description: str
    eyebrow: str
    title: str
    subtitle: str
    last_updated: str
    controller_title: str
    sections: list[PrivacySectionPublic] = Field(default_factory=list)


class PrivacyPageAdmin(BaseModel):
    """Raw bilingual Privacy Policy page-level copy."""

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
    controller_title_en: str
    controller_title_bg: str | None = None
    created_at: str
    updated_at: str


class PrivacySectionAdmin(BaseModel):
    """Raw bilingual Privacy Policy section copy."""

    slug: str
    title_en: str
    title_bg: str | None = None
    nav_en: str
    nav_bg: str | None = None
    body_en: list[str] = Field(default_factory=list)
    body_bg: list[str] | None = None
    sort_order: int
    created_at: str
    updated_at: str


class PrivacyAdminResponse(BaseModel):
    """Admin Privacy Policy payload."""

    page: PrivacyPageAdmin
    sections: list[PrivacySectionAdmin] = Field(default_factory=list)


class PatchPrivacyPageRequest(BaseModel):
    """Patch editable Privacy Policy page-level text fields."""

    model_config = ConfigDict(extra="forbid")

    meta_title_en: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    meta_title_bg: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    meta_description_en: str | None = Field(default=None, max_length=MAX_PRIVACY_TEXT_LENGTH)
    meta_description_bg: str | None = Field(default=None, max_length=MAX_PRIVACY_TEXT_LENGTH)
    eyebrow_en: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    eyebrow_bg: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    title_en: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    subtitle_en: str | None = Field(default=None, max_length=MAX_PRIVACY_TEXT_LENGTH)
    subtitle_bg: str | None = Field(default=None, max_length=MAX_PRIVACY_TEXT_LENGTH)
    last_updated_en: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    last_updated_bg: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    controller_title_en: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    controller_title_bg: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)


class PatchPrivacySectionRequest(BaseModel):
    """Patch editable Privacy Policy section fields."""

    model_config = ConfigDict(extra="forbid")

    title_en: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    nav_en: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    nav_bg: str | None = Field(default=None, max_length=MAX_PRIVACY_LABEL_LENGTH)
    body_en: list[str] | None = Field(default=None, max_length=MAX_PRIVACY_PARAGRAPH_COUNT)
    body_bg: list[str] | None = Field(default=None, max_length=MAX_PRIVACY_PARAGRAPH_COUNT)
