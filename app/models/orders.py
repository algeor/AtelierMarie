"""Order request and response models."""

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator, model_validator

from app.models.delivery import DeliveryInfo

OrderStatus = Literal[
    "pending",
    "confirmed",
    "shipped",
    "delivered",
    "return_in_transit",
    "returned",
    "cancelled",
]
PaymentMethod = Literal["cod", "card", "bank_transfer"]
PaymentStatus = Literal[
    "pending",
    "paid",
    "cod_pending",
    "failed",
    "review_required",
    "refund_pending",
    "partially_refunded",
    "refunded",
    "dispute_open",
    "dispute_won",
    "dispute_lost",
]

PAYMENT_METHOD_LABELS: dict[str, str] = {
    "cod": "Pay on delivery",
    "card": "Card payment",
    "bank_transfer": "Bank transfer",
}

PAYMENT_STATUS_LABELS: dict[str, str] = {
    "pending": "Payment pending",
    "paid": "Paid",
    "cod_pending": "Pay on delivery",
    "failed": "Payment failed",
    "review_required": "Review required",
    "refund_pending": "Refund pending",
    "partially_refunded": "Partially refunded",
    "refunded": "Refunded",
    "dispute_open": "Dispute open",
    "dispute_won": "Dispute won",
    "dispute_lost": "Dispute lost",
}


class OrderItemResponse(BaseModel):
    """Single item in an order — snapshot at purchase time."""

    product_id: str
    product_name: str
    price_cents: int
    quantity: int


class AdminOrderItemResponse(OrderItemResponse):
    """Admin item snapshot with inventory and valuation review context."""

    inventory_mode: Literal["legacy", "fallback", "ledger_managed"] = "legacy"
    ledger_managed: bool = False
    stock_issue_status: Literal["legacy", "issued", "missing", "reversed"] = "legacy"
    inventory_movement_ids: list[str] = Field(default_factory=list)
    source_movement_id: str | None = None
    finished_batch_id: str | None = None
    finished_batch_number: str | None = None
    cogs_row_id: str | None = None
    cogs_readiness: str = "not_required"
    valuation_method: str | None = None
    source_valuation_layer_id: str | None = None
    inventory_exception_ids: list[str] = Field(default_factory=list)
    inventory_exception_count: int = 0


class InvoiceProfile(BaseModel):
    """Optional checkout invoice/business document profile."""

    customer_type: Literal["individual", "business"] = "individual"
    legal_name: str = Field(..., min_length=1, max_length=200)
    vat_identification_number: str | None = Field(default=None, max_length=64)
    business_registration_number: str | None = Field(default=None, max_length=64)
    billing_address: str = Field(..., min_length=1, max_length=500)
    billing_country: str = Field(default="BG", min_length=2, max_length=2)
    invoice_email: EmailStr
    purchase_reference_note: str | None = Field(default=None, max_length=500)

    @field_validator(
        "legal_name",
        "vat_identification_number",
        "business_registration_number",
        "billing_address",
        "purchase_reference_note",
        mode="before",
    )
    @classmethod
    def _strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("billing_country", mode="before")
    @classmethod
    def _normalize_country(cls, value: str) -> str:
        return value.strip().upper()


class OrderResponse(BaseModel):
    """Public order representation.

    `items_total_cents` and `shipping_cents` sum to `total_cents`. Provenance
    (`shipping_price_source`, `shipping_is_fallback`) records how the shipping
    price was derived (shipping-pricing — Phase A).
    """

    id: str
    internal_sequence: int | None = None
    order_number: str | None = None
    status: OrderStatus
    items_total_cents: int
    shipping_cents: int = 0
    shipping_price_source: Literal["live", "table", "flat"] = "live"
    shipping_is_fallback: bool = False
    total_cents: int
    customer_email: str
    customer_name: str | None = None
    # Structured delivery fields.
    delivery_method: Literal["office", "door"] | None = None
    delivery_courier: Literal["speedy", "econt"] | None = None
    delivery_details: dict | None = None
    tracking_number: str | None = None
    tracking_carrier: str | None = None
    tracking_url: str | None = None
    courier_status: str | None = None
    label_url: str | None = None
    courier_provider: str | None = None
    courier_order_id: str | None = None
    courier_shipment_number: str | None = None
    courier_label_url: str | None = None
    courier_label_created_at: str | None = None
    courier_sync_status: str | None = None
    courier_last_error: str | None = None
    courier_last_synced_at: str | None = None
    notes: str | None = None
    # Payment fields (payment-integration).
    payment_method: PaymentMethod = "cod"
    payment_status: PaymentStatus = "cod_pending"
    reserved_until: str | None = None
    paid_at: str | None = None
    collected_at: str | None = None
    payment_return_token: str | None = None
    stripe_checkout_session_id: str | None = None
    stripe_checkout_url: str | None = None
    invoice_profile: InvoiceProfile | None = None
    accounting_currency: str = "EUR"
    seller_legal_profile_version_id: int | None = None
    vat_fiscal_settings_version_id: int | None = None
    accounting_classification_state: Literal[
        "unreviewed",
        "domestic_default",
        "business_vat_id_provided",
        "cross_border_candidate",
        "manual_review_required",
    ] = "unreviewed"
    accounting_snapshot: dict | None = None
    accounting_readiness_status: Literal["unreviewed", "ready", "review_required", "blocked"] = (
        "unreviewed"
    )
    finance_period_id: str | None = None
    document_reference_status: Literal["not_required", "missing", "recorded", "review_required"] = (
        "not_required"
    )
    payment_reconciliation_status: Literal[
        "not_applicable", "pending", "matched", "mismatch", "unmatched", "review_required"
    ] = "not_applicable"
    payout_reconciliation_status: Literal[
        "not_applicable", "pending", "matched", "mismatch", "unmatched", "review_required"
    ] = "not_applicable"
    cod_settlement_status: Literal["not_applicable", "pending", "settled", "mismatch"] = (
        "not_applicable"
    )
    blocking_exception_count: int = 0
    finance_hub_links: dict[str, str | None] | None = None
    analytics_consent: bool = False
    items: Sequence[OrderItemResponse]
    created_at: str
    updated_at: str

    @computed_field
    def payment_method_label(self) -> str:
        return PAYMENT_METHOD_LABELS.get(self.payment_method, self.payment_method)

    @computed_field
    def payment_status_label(self) -> str:
        return PAYMENT_STATUS_LABELS.get(self.payment_status, self.payment_status)


class OrderListResponse(BaseModel):
    """Paginated list of orders."""

    items: list[OrderResponse]
    total: int
    page: int
    limit: int


class AdminOrderDetailResponse(OrderResponse):
    """Admin order detail with payment timeline."""

    items: list[AdminOrderItemResponse]
    payment_events: list[dict] = Field(default_factory=list)
    return_cases: list[dict] = Field(default_factory=list)
    return_events: list[dict] = Field(default_factory=list)
    refund_records: list[dict] = Field(default_factory=list)
    cod_settlement: dict | None = None
    cod_settlement_required: bool = False
    econt_cod_evidence: dict | None = None
    inventory_context: dict | None = None


class CreateOrderRequest(BaseModel):
    """Input for placing a new order.

    Delivery is a structured object (method + courier + sub-object). See
    openspec change `shipping-courier-integration` Decision 1.

    `customer_email` is optional: when omitted by a logged-in user, the route
    falls back to the account email. Anonymous checkout must still supply it
    (the route returns EMAIL_REQUIRED otherwise). The order snapshots whichever
    value is resolved — it is a fact of the order, not a live user lookup.
    """

    customer_email: EmailStr | None = Field(default=None, max_length=320)
    customer_name: str = Field(..., min_length=1, max_length=200)
    delivery: DeliveryInfo
    notes: str | None = Field(default=None, max_length=2000)
    payment_method: PaymentMethod = "cod"
    analytics_consent: bool = False
    # Shipping price + provenance echoed from the selected quote (shipping-pricing).
    # Server re-enforces free shipping and range-validates shipping_cents — the
    # client value is advisory, not trusted (parent Decision 16).
    shipping_cents: int = Field(default=0, ge=0)
    shipping_price_source: Literal["live", "table", "flat"] = "live"
    shipping_is_fallback: bool = False
    shipping_quoted_at: str | None = Field(default=None, max_length=32)
    invoice_profile: InvoiceProfile | None = None

    @field_validator("customer_name", mode="before")
    @classmethod
    def _strip_customer_name(cls, v: str | None) -> str | None:
        """Strip whitespace; reject strings that become empty after trimming."""
        if v is None:
            return None
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped:
            msg = "customer_name must not be blank (whitespace-only)"
            raise ValueError(msg)
        return stripped


class MarkPaymentPaidRequest(BaseModel):
    """Input for admin marking a bank_transfer order as paid."""

    payment_status: Literal["paid"]


ManualPaymentAction = Literal[
    "mark_paid",
    "mark_collected",
    "mark_refunded",
    "mark_failed",
    "mark_review",
    "record_callback",
    "convert_to_cod",
    "cancel",
]
CallbackOutcome = Literal["confirmed", "declined", "unreachable", "needs_follow_up"]


class ManualPaymentActionRequest(BaseModel):
    """Input for note-required manual admin payment actions."""

    action: ManualPaymentAction
    note: str = Field(..., min_length=1, max_length=2000)
    callback_outcome: CallbackOutcome | None = None

    @field_validator("note", mode="before")
    @classmethod
    def _strip_note(cls, v: str | None) -> str | None:
        if v is None or not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped:
            msg = "note must not be blank"
            raise ValueError(msg)
        return stripped

    @model_validator(mode="after")
    def _validate_callback_fields(self) -> "ManualPaymentActionRequest":
        if self.action == "record_callback" and self.callback_outcome is None:
            msg = "callback_outcome is required for record_callback"
            raise ValueError(msg)
        if self.action == "convert_to_cod" and self.callback_outcome not in (None, "confirmed"):
            msg = "convert_to_cod requires callback_outcome to be confirmed"
            raise ValueError(msg)
        return self


class UpdateOrderStatusRequest(BaseModel):
    """Input for changing order status.

    Tracking fields are optional at the schema level and required only when
    `status == "shipped"` — that conditional check lives in the service layer
    (see order_service.TrackingRequiredError) so it can use the standard error
    envelope, not Pydantic's RequestValidationError shape.
    """

    status: OrderStatus = Field(..., description="New order status")
    tracking_number: str | None = Field(default=None, max_length=100)
    tracking_carrier: str | None = Field(default=None, max_length=50)
    tracking_url: str | None = Field(default=None, max_length=500)


class OrderEmailAudit(BaseModel):
    """One row of the order_emails send-attempt audit trail."""

    event: str
    recipient: str
    status: str
    reason: str | None = None
    attempts: int
    sent_at: str


class OrderEmailAuditResponse(BaseModel):
    """Audit trail for an order's email send attempts (admin-only)."""

    order_id: str
    emails: list[OrderEmailAudit]
