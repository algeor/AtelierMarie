"""Payment settings and payment-related API models."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.orders import PaymentMethod, PaymentStatus

PaymentProvider = Literal["stripe", "card", "cod", "bank_transfer", "pay_on_delivery"]
PaymentEventSource = Literal["stripe", "admin", "system", "customer"]


class StripeConfigHealth(BaseModel):
    """Safe Stripe configuration projection for admins."""

    mode: Literal["not_configured", "test", "live", "unknown"]
    secret_key_configured: bool
    webhook_secret_configured: bool
    publishable_key_configured: bool
    ready_for_card_payments: bool
    problems: list[str] = Field(default_factory=list)


class PaymentSettingsUpdate(BaseModel):
    """Admin-editable payment settings."""

    card_payments_enabled: bool
    pay_on_delivery_enabled: bool
    pay_on_delivery_max_cents: int = Field(default=5000, ge=0, le=5000)


class PaymentSettingsResponse(PaymentSettingsUpdate):
    """Admin payment settings response."""

    stripe: StripeConfigHealth


class PublicPaymentSettingsResponse(BaseModel):
    """Safe checkout-facing payment settings."""

    card_payments_enabled: bool
    pay_on_delivery_enabled: bool
    pay_on_delivery_max_cents: int
    bank_transfer_enabled: bool
    available_payment_methods: list[Literal["card", "cod", "bank_transfer"]]


class PaymentEventResponse(BaseModel):
    """Safe payment event projection for admin timelines."""

    id: str
    order_id: str | None = None
    payment_id: str | None = None
    event_type: str
    source: PaymentEventSource
    stripe_event_id: str | None = None
    stripe_event_type: str | None = None
    provider: PaymentProvider | None = None
    provider_status: str | None = None
    processing_status: str
    admin_email: str | None = None
    admin_note: str | None = None
    request_id: str | None = None
    created_at: str


class CheckoutPaymentResponse(BaseModel):
    """Payment-specific checkout result fields."""

    order_id: str
    order_number: str | None = None
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    reserved_until: str | None = None
    stripe_checkout_url: str | None = None
