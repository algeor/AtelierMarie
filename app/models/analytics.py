"""First-party analytics request and response models."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class AnalyticsEventType(StrEnum):
    """Initial storefront funnel event taxonomy."""

    PRODUCT_IMPRESSION = "product_impression"
    PRODUCT_CLICK = "product_click"
    PRODUCT_VIEW = "product_view"
    LISTING_FILTER = "listing_filter"
    ADD_TO_CART = "add_to_cart"
    CART_OPEN = "cart_open"
    CHECKOUT_START = "checkout_start"
    DELIVERY_SELECTED = "delivery_selected"
    SHIPPING_QUOTE_SELECTED = "shipping_quote_selected"
    ORDER_SUBMIT = "order_submit"
    PAYMENT_REDIRECT = "payment_redirect"
    PURCHASE_CONFIRMED = "purchase_confirmed"


class AnalyticsEventRequest(BaseModel):
    """Client-submitted analytics event.

    The backend derives session/user identity. Clients must not send session IDs.
    """

    event_id: str = Field(..., min_length=8, max_length=80)
    event_type: AnalyticsEventType
    occurred_at: datetime
    locale: Literal["en", "bg"] = "en"
    page_path: str | None = Field(default=None, max_length=300)
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_id")
    @classmethod
    def _validate_event_id(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if any(char not in allowed for char in value):
            msg = "event_id may contain only letters, numbers, '-' and '_'"
            raise ValueError(msg)
        return value

    @field_validator("page_path")
    @classmethod
    def _validate_page_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("/"):
            msg = "page_path must be a local path"
            raise ValueError(msg)
        if "@" in value or "?" in value:
            msg = "page_path must not include query strings or personal data"
            raise ValueError(msg)
        return value


class AnalyticsIngestionRequest(BaseModel):
    """Wrapper that accepts either one event or a bounded batch."""

    event: AnalyticsEventRequest | None = None
    events: list[AnalyticsEventRequest] | None = None

    @model_validator(mode="after")
    def _require_event_or_events(self) -> "AnalyticsIngestionRequest":
        if self.event is None and self.events is None:
            msg = "event or events is required"
            raise ValueError(msg)
        if self.event is not None and self.events is not None:
            msg = "send either event or events, not both"
            raise ValueError(msg)
        return self

    def event_list(self) -> list[AnalyticsEventRequest]:
        """Return the normalized event list."""
        if self.event is not None:
            return [self.event]
        return self.events or []


class AnalyticsIngestionResponse(BaseModel):
    """Public analytics ingestion response."""

    accepted: int
    duplicates: int = 0
    disabled: bool = False


class AnalyticsConsentRequest(BaseModel):
    """Session-scoped analytics consent preference."""

    analytics: bool
    consent_version: str = Field(..., min_length=1, max_length=40)
    locale: Literal["en", "bg"] = "en"


class AnalyticsConsentResponse(BaseModel):
    """Persisted analytics consent preference."""

    analytics: bool
    consent_version: str


class AnalyticsHealthResponse(BaseModel):
    """Admin event delivery health metrics."""

    accepted: int = 0
    rejected: int = 0
    duplicate: int = 0
    validation_failure: int = 0
    last_successful_flush_at: str | None = None
    duckdb_load_status: str = "not_initialized"
    retention_days: int


class AnalyticsSummaryResponse(BaseModel):
    """Admin analytics summary metrics for a selected range."""

    start_date: str
    end_date: str
    consented_sessions: int
    accepted_events: int
    conversion_rate: float
    backend_order_count: int
    backend_revenue_cents: int
    analytics_purchase_count: int
    analytics_purchase_revenue_cents: int
    coverage_percent: float
    consented_order_count: int
    consented_order_delta: int
    delivery_warning: bool
    health: AnalyticsHealthResponse


class AnalyticsFunnelStep(BaseModel):
    """One funnel step aggregate."""

    event_type: AnalyticsEventType
    count: int
    conversion_from_previous: float


class AnalyticsFunnelResponse(BaseModel):
    """Admin funnel metrics response."""

    steps: list[AnalyticsFunnelStep]


class ProductAnalyticsRow(BaseModel):
    """Product-level analytics aggregate."""

    product_id: str
    product_name: str | None = None
    impressions: int = 0
    clicks: int = 0
    views: int = 0
    add_to_cart: int = 0
    purchases: int = 0
    revenue_cents: int = 0
    click_through_rate: float = 0.0
    conversion_rate: float = 0.0


class ProductAnalyticsResponse(BaseModel):
    """Admin product analytics response."""

    products: list[ProductAnalyticsRow]


class CheckoutAnalyticsResponse(BaseModel):
    """Admin checkout, delivery, and payment metrics."""

    checkout_starts: int = 0
    order_submits: int = 0
    payment_redirects: int = 0
    purchase_confirmed: int = 0
    delivery_methods: dict[str, int] = Field(default_factory=dict)
    delivery_couriers: dict[str, int] = Field(default_factory=dict)
    payment_methods: dict[str, int] = Field(default_factory=dict)
