"""Terms & Conditions request and response models."""

from pydantic import BaseModel, ConfigDict, Field

MAX_TERMS_LABEL_LENGTH = 300
MAX_TERMS_TEXT_LENGTH = 8_000
MAX_TERMS_PARAGRAPH_COUNT = 120


class TermsSectionPublic(BaseModel):
    """Localized public Terms section."""

    id: str
    title: str
    nav: str
    body: list[str] = Field(default_factory=list)
    model_form_title: str | None = None
    model_form_intro: str | None = None
    model_form_lines: list[str] | None = None


class TermsPublicResponse(BaseModel):
    """Localized public Terms page payload."""

    meta_title: str
    meta_description: str
    eyebrow: str
    title: str
    subtitle: str
    last_updated: str
    identity_intro: str
    policy_links_title: str
    privacy_link: str
    cookies_link: str
    nav_label: str
    back_to_top: str
    sections: list[TermsSectionPublic] = Field(default_factory=list)


class TermsPageAdmin(BaseModel):
    """Raw bilingual Terms page-level copy."""

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
    identity_intro_en: str
    identity_intro_bg: str | None = None
    policy_links_title_en: str
    policy_links_title_bg: str | None = None
    privacy_link_en: str
    privacy_link_bg: str | None = None
    cookies_link_en: str
    cookies_link_bg: str | None = None
    nav_label_en: str
    nav_label_bg: str | None = None
    back_to_top_en: str
    back_to_top_bg: str | None = None
    created_at: str
    updated_at: str


class TermsSectionAdmin(BaseModel):
    """Raw bilingual Terms section copy."""

    slug: str
    title_en: str
    title_bg: str | None = None
    nav_en: str
    nav_bg: str | None = None
    body_en: list[str] = Field(default_factory=list)
    body_bg: list[str] | None = None
    model_form_title_en: str | None = None
    model_form_title_bg: str | None = None
    model_form_intro_en: str | None = None
    model_form_intro_bg: str | None = None
    model_form_lines_en: list[str] | None = None
    model_form_lines_bg: list[str] | None = None
    sort_order: int
    created_at: str
    updated_at: str


class TermsAdminResponse(BaseModel):
    """Admin Terms payload."""

    page: TermsPageAdmin
    sections: list[TermsSectionAdmin] = Field(default_factory=list)


class PatchTermsPageRequest(BaseModel):
    """Patch editable Terms page-level text fields."""

    model_config = ConfigDict(extra="forbid")

    meta_title_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    meta_title_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    meta_description_en: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    meta_description_bg: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    eyebrow_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    eyebrow_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    title_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    subtitle_en: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    subtitle_bg: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    last_updated_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    last_updated_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    identity_intro_en: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    identity_intro_bg: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    policy_links_title_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    policy_links_title_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    privacy_link_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    privacy_link_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    cookies_link_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    cookies_link_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    nav_label_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    nav_label_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    back_to_top_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    back_to_top_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)


class PatchTermsSectionRequest(BaseModel):
    """Patch editable Terms section fields."""

    model_config = ConfigDict(extra="forbid")

    title_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    nav_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    nav_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    body_en: list[str] | None = Field(default=None, max_length=MAX_TERMS_PARAGRAPH_COUNT)
    body_bg: list[str] | None = Field(default=None, max_length=MAX_TERMS_PARAGRAPH_COUNT)
    model_form_title_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    model_form_title_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    model_form_intro_en: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    model_form_intro_bg: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    model_form_lines_en: list[str] | None = Field(
        default=None, max_length=MAX_TERMS_PARAGRAPH_COUNT
    )
    model_form_lines_bg: list[str] | None = Field(
        default=None, max_length=MAX_TERMS_PARAGRAPH_COUNT
    )
