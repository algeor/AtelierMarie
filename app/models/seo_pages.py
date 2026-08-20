"""SEO landing page request and response models."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.terms import MAX_TERMS_LABEL_LENGTH, MAX_TERMS_PARAGRAPH_COUNT, MAX_TERMS_TEXT_LENGTH


class SeoLandingFaqPublic(BaseModel):
    """Localized FAQ row for a landing page."""

    id: int
    question: str
    answer: str


class SeoLandingPagePublic(BaseModel):
    """Localized public SEO landing page payload."""

    slug: str
    product_type: str
    path: str
    meta_title: str
    meta_description: str
    eyebrow: str
    title: str
    intro: str
    note: str
    shop_all_label: str
    section_title: str
    empty_text: str
    benefits_title: str
    benefits: list[str] = Field(default_factory=list)
    faq_title: str
    faq: list[SeoLandingFaqPublic] = Field(default_factory=list)


class SeoLandingFaqAdmin(BaseModel):
    """Raw bilingual FAQ row for admin editing."""

    id: int
    page_slug: str
    question_en: str
    question_bg: str | None = None
    answer_en: str
    answer_bg: str | None = None
    sort_order: int
    is_published: bool
    created_at: str
    updated_at: str


class SeoLandingPageAdmin(BaseModel):
    """Raw bilingual SEO landing page copy."""

    slug: str
    product_type: str
    path_en: str
    path_bg: str
    meta_title_en: str
    meta_title_bg: str | None = None
    meta_description_en: str
    meta_description_bg: str | None = None
    eyebrow_en: str
    eyebrow_bg: str | None = None
    title_en: str
    title_bg: str | None = None
    intro_en: str
    intro_bg: str | None = None
    note_en: str
    note_bg: str | None = None
    shop_all_label_en: str
    shop_all_label_bg: str | None = None
    section_title_en: str
    section_title_bg: str | None = None
    empty_text_en: str
    empty_text_bg: str | None = None
    benefits_title_en: str
    benefits_title_bg: str | None = None
    faq_title_en: str
    faq_title_bg: str | None = None
    benefits_en: list[str] = Field(default_factory=list)
    benefits_bg: list[str] | None = None
    is_published: bool
    created_at: str
    updated_at: str
    faq: list[SeoLandingFaqAdmin] = Field(default_factory=list)


class SeoLandingAdminResponse(BaseModel):
    """Admin response for all SEO landing pages."""

    pages: list[SeoLandingPageAdmin] = Field(default_factory=list)


class PatchSeoLandingPageRequest(BaseModel):
    """Patch editable SEO landing page fields."""

    model_config = ConfigDict(extra="forbid")

    meta_title_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    meta_title_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    meta_description_en: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    meta_description_bg: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    eyebrow_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    eyebrow_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    title_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    intro_en: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    intro_bg: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    note_en: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    note_bg: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    shop_all_label_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    shop_all_label_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    section_title_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    section_title_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    empty_text_en: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    empty_text_bg: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    benefits_title_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    benefits_title_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    faq_title_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    faq_title_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    benefits_en: list[str] | None = Field(default=None, max_length=MAX_TERMS_PARAGRAPH_COUNT)
    benefits_bg: list[str] | None = Field(default=None, max_length=MAX_TERMS_PARAGRAPH_COUNT)
    is_published: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_required_nulls(cls, data: dict) -> dict:
        required = {
            "meta_title_en",
            "meta_description_en",
            "eyebrow_en",
            "title_en",
            "intro_en",
            "note_en",
            "shop_all_label_en",
            "section_title_en",
            "empty_text_en",
            "benefits_title_en",
            "faq_title_en",
            "benefits_en",
        }
        if isinstance(data, dict):
            for field in required:
                if field in data and data[field] is None:
                    raise ValueError(f"{field} cannot be null")
        return data


class PatchSeoLandingFaqRequest(BaseModel):
    """Patch editable FAQ fields for a SEO landing page."""

    model_config = ConfigDict(extra="forbid")

    question_en: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    question_bg: str | None = Field(default=None, max_length=MAX_TERMS_LABEL_LENGTH)
    answer_en: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    answer_bg: str | None = Field(default=None, max_length=MAX_TERMS_TEXT_LENGTH)
    is_published: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_required_nulls(cls, data: dict) -> dict:
        if isinstance(data, dict):
            for field in {"question_en", "answer_en"}:
                if field in data and data[field] is None:
                    raise ValueError(f"{field} cannot be null")
        return data
