"""Admin return/refund workflow API models."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ReturnReason = Literal[
    "not_picked_up",
    "refused_delivery",
    "customer_return",
    "wrong_address",
    "unreachable_customer",
    "damaged_by_courier",
    "lost_by_courier",
    "merchant_error",
    "other",
]
ReturnSource = Literal["admin", "speedy", "econt", "customer", "stripe", "system"]
ReturnStatus = Literal[
    "requested",
    "return_in_transit",
    "received",
    "inspected",
    "rejected",
    "closed",
]
RestockDecision = Literal["restock", "do_not_restock", "partial"]
CourierClaimStatus = Literal["none", "filed", "approved", "rejected", "paid"]
RefundStatus = Literal["pending", "succeeded", "failed", "cancelled"]


class ReturnCaseResponse(BaseModel):
    id: str
    order_id: str
    reason: ReturnReason
    source: ReturnSource
    status: ReturnStatus
    refund_amount_cents: int | None = None
    courier_return_fee_cents: int = 0
    courier_claim_id: str | None = None
    courier_claim_status: CourierClaimStatus = "none"
    courier_claim_amount_cents: int | None = None
    restock_decision: Literal["pending", "restock", "do_not_restock", "partial"] = "pending"
    returned_at: str | None = None
    received_at: str | None = None
    inspected_at: str | None = None
    closed_at: str | None = None
    notes: str | None = None
    created_by_admin_id: str | None = None
    updated_by_admin_id: str | None = None
    created_at: str
    updated_at: str


class ReturnEventResponse(BaseModel):
    id: str
    order_return_id: str | None = None
    order_id: str
    event_type: str
    source: ReturnSource
    payload_json: str | None = None
    admin_user_id: str | None = None
    admin_email: str | None = None
    created_at: str


class PaymentRefundResponse(BaseModel):
    id: str
    order_id: str
    payment_id: str | None = None
    provider: Literal["stripe", "manual", "bank_transfer", "cod_adjustment"]
    provider_refund_id: str | None = None
    amount_cents: int
    status: RefundStatus
    reason: str | None = None
    idempotency_key: str | None = None
    failure_reason: str | None = None
    created_by_admin_id: str | None = None
    created_at: str
    confirmed_at: str | None = None


class CodSettlementResponse(BaseModel):
    id: str
    order_id: str
    amount_cents: int
    settlement_date: str
    courier_reference: str | None = None
    notes: str | None = None
    mismatch_review: bool = False
    created_by_admin_id: str | None = None
    created_at: str
    updated_at: str


class RecordCodSettlementRequest(BaseModel):
    amount_cents: int = Field(..., ge=0)
    settlement_date: str = Field(..., min_length=1, max_length=32)
    courier_reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("settlement_date", "courier_reference", "notes", mode="before")
    @classmethod
    def _strip_cod_text(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class UpdateReturnAccountingRequest(BaseModel):
    courier_return_fee_cents: int | None = Field(default=None, ge=0)
    courier_claim_id: str | None = Field(default=None, max_length=120)
    courier_claim_status: CourierClaimStatus | None = None
    courier_claim_amount_cents: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("courier_claim_id", "notes", mode="before")
    @classmethod
    def _strip_accounting_text(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class CreateStripeRefundRequest(BaseModel):
    amount_cents: int | None = Field(default=None, ge=1)
    reason: str | None = Field(default=None, max_length=200)
    idempotency_key: str = Field(..., min_length=8, max_length=160)

    @field_validator("reason", "idempotency_key", mode="before")
    @classmethod
    def _strip_refund_text(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class CreateReturnCaseRequest(BaseModel):
    reason: ReturnReason
    source: ReturnSource = "admin"
    status: Literal["requested", "return_in_transit"] = "requested"
    notes: str | None = Field(default=None, max_length=2000)
    refund_amount_cents: int | None = Field(default=None, ge=0)
    courier_return_fee_cents: int = Field(default=0, ge=0)
    courier_claim_id: str | None = Field(default=None, max_length=120)
    courier_claim_status: CourierClaimStatus = "none"
    courier_claim_amount_cents: int | None = Field(default=None, ge=0)

    @field_validator("notes", "courier_claim_id", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class InspectReturnCaseRequest(BaseModel):
    restock_decision: RestockDecision
    restock_quantities: dict[str, int] | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("restock_quantities")
    @classmethod
    def _validate_quantities(cls, value: dict[str, int] | None) -> dict[str, int] | None:
        if value is None:
            return value
        for quantity in value.values():
            if quantity < 1:
                msg = "restock quantities must be positive"
                raise ValueError(msg)
        return value

    @field_validator("notes", mode="before")
    @classmethod
    def _strip_notes(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None
