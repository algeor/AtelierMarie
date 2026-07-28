"""FAQ request and response models."""

from pydantic import BaseModel, Field

MAX_FAQ_QUESTION_LENGTH = 500
MAX_FAQ_ANSWER_LENGTH = 5000
MAX_FAQ_TITLE_LENGTH = 120
MAX_FAQ_ICON_LENGTH = 20


class FaqItemResponse(BaseModel):
    """Public FAQ item with locale-resolved text."""

    id: int
    question: str
    answer: str


class FaqSectionResponse(BaseModel):
    """Public FAQ section with locale-resolved title and ordered items."""

    slug: str
    title: str
    icon: str | None = None
    items: list[FaqItemResponse] = Field(default_factory=list)


class FaqResponse(BaseModel):
    """Public FAQ payload grouped by section."""

    sections: list[FaqSectionResponse] = Field(default_factory=list)


class FaqItemAdminResponse(BaseModel):
    """Admin FAQ item with both languages and management metadata."""

    id: int
    section: str
    question_en: str
    question_bg: str | None = None
    answer_en: str
    answer_bg: str | None = None
    sort_order: int
    is_published: bool
    created_at: str
    updated_at: str


class FaqSectionAdminResponse(BaseModel):
    """Admin FAQ section with both languages and all items."""

    slug: str
    title_en: str
    title_bg: str | None = None
    icon: str | None = None
    sort_order: int
    created_at: str
    updated_at: str
    items: list[FaqItemAdminResponse] = Field(default_factory=list)


class FaqAdminResponse(BaseModel):
    """Admin FAQ payload grouped by section."""

    sections: list[FaqSectionAdminResponse] = Field(default_factory=list)


class CreateFaqItemRequest(BaseModel):
    """Create an FAQ item. Text is trusted admin-authored plain text."""

    section: str = Field(..., min_length=1, max_length=100)
    question_en: str = Field(..., min_length=1, max_length=MAX_FAQ_QUESTION_LENGTH)
    answer_en: str = Field(..., min_length=1, max_length=MAX_FAQ_ANSWER_LENGTH)
    question_bg: str | None = Field(default=None, max_length=MAX_FAQ_QUESTION_LENGTH)
    answer_bg: str | None = Field(default=None, max_length=MAX_FAQ_ANSWER_LENGTH)
    sort_order: int | None = Field(default=None, ge=0, le=10_000)


class UpdateFaqItemRequest(BaseModel):
    """Partially update an FAQ item. Omitted fields are left unchanged."""

    section: str | None = Field(default=None, min_length=1, max_length=100)
    question_en: str | None = Field(default=None, min_length=1, max_length=MAX_FAQ_QUESTION_LENGTH)
    question_bg: str | None = Field(default=None, max_length=MAX_FAQ_QUESTION_LENGTH)
    answer_en: str | None = Field(default=None, min_length=1, max_length=MAX_FAQ_ANSWER_LENGTH)
    answer_bg: str | None = Field(default=None, max_length=MAX_FAQ_ANSWER_LENGTH)
    sort_order: int | None = Field(default=None, ge=0, le=10_000)
    is_published: bool | None = None


class ReorderFaqItemsRequest(BaseModel):
    """Replace item order within one FAQ section."""

    section: str = Field(..., min_length=1, max_length=100)
    ordered_ids: list[int] = Field(..., min_length=0, max_length=200)


class UpdateFaqSectionRequest(BaseModel):
    """Update editable section fields. Slugs are immutable and excluded."""

    title_en: str | None = Field(default=None, min_length=1, max_length=MAX_FAQ_TITLE_LENGTH)
    title_bg: str | None = Field(default=None, max_length=MAX_FAQ_TITLE_LENGTH)
    icon: str | None = Field(default=None, max_length=MAX_FAQ_ICON_LENGTH)
    sort_order: int | None = Field(default=None, ge=0, le=10_000)
