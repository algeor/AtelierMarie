"""Taxonomy request and response models (dynamic-categories).

Product types, categories/tiers, and labels are managed taxonomy terms. Slugs
are immutable server-derived keys; names are display data. Public responses
carry a locale-resolved `name`; admin responses carry both language fields plus
management metadata.
"""

from pydantic import BaseModel, Field


class TaxonomyTerm(BaseModel):
    """Public taxonomy term — locale-resolved name for storefront rendering."""

    slug: str
    name: str
    sort_order: int


class TaxonomyResponse(BaseModel):
    """Public taxonomy payload for building storefront filter menus."""

    product_types: list[TaxonomyTerm] = Field(default_factory=list)
    categories: list[TaxonomyTerm] = Field(default_factory=list)
    labels: list[TaxonomyTerm] = Field(default_factory=list)


class AdminTaxonomyTerm(BaseModel):
    """Admin taxonomy term — both languages, active state, in-use count."""

    slug: str
    name_en: str
    name_bg: str | None = None
    sort_order: int
    is_active: bool
    product_count: int
    created_at: str
    updated_at: str


class CreateTaxonomyTermRequest(BaseModel):
    """Create a taxonomy term. The slug is derived server-side from `name_en`.

    A `slug` sent by the client is ignored (extra fields are dropped) so slugs
    stay immutable and server-controlled.
    """

    name_en: str = Field(..., min_length=1, max_length=100)
    name_bg: str | None = Field(default=None, max_length=100)
    sort_order: int = Field(default=0, ge=0, le=10_000)


class UpdateTaxonomyTermRequest(BaseModel):
    """Update a taxonomy term. All fields optional; the slug is immutable.

    Use model_dump(exclude_unset=True) so omitted fields are left unchanged.
    """

    name_en: str | None = Field(default=None, min_length=1, max_length=100)
    name_bg: str | None = Field(default=None, max_length=100)
    sort_order: int | None = Field(default=None, ge=0, le=10_000)
    is_active: bool | None = None
