"""Pydantic models for admin inventory, materials, and stock movements."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MaterialUom = Literal["g", "kg", "ml", "l", "piece", "pcs", "unit", "m", "cm"]
MaterialMovementType = Literal["adjustment", "spoilage", "write_off", "stock_count_correction"]
MaterialReviewState = Literal["draft", "needs_review", "reviewed", "rejected"]
InventoryReviewState = Literal["unreviewed", "reviewed", "estimate", "official", "reversed"]


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class MaterialCreateRequest(BaseModel):
    """Admin request to create a raw material or packaging item."""

    model_config = ConfigDict(extra="forbid")

    sku: str | None = Field(default=None, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(default="material", min_length=1, max_length=100)
    stock_uom: MaterialUom
    purchase_uom: MaterialUom | None = None
    purchase_to_stock_factor: float | None = Field(default=None, gt=0)
    preferred_supplier_name: str | None = Field(default=None, max_length=200)
    preferred_supplier_sku: str | None = Field(default=None, max_length=100)
    reorder_threshold: float | None = Field(default=None, ge=0)
    active: bool = True
    lot_tracked: bool = False
    expiry_tracked: bool = False
    evidence_required: bool = False
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator(
        "sku",
        "preferred_supplier_name",
        "preferred_supplier_sku",
        "notes",
        mode="before",
    )
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("name", "category", mode="before")
    @classmethod
    def _required_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be blank")
        return stripped


class MaterialUpdateRequest(BaseModel):
    """Admin request to update editable material fields."""

    model_config = ConfigDict(extra="forbid")

    sku: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    stock_uom: MaterialUom | None = None
    purchase_uom: MaterialUom | None = None
    purchase_to_stock_factor: float | None = Field(default=None, gt=0)
    preferred_supplier_name: str | None = Field(default=None, max_length=200)
    preferred_supplier_sku: str | None = Field(default=None, max_length=100)
    reorder_threshold: float | None = Field(default=None, ge=0)
    active: bool | None = None
    lot_tracked: bool | None = None
    expiry_tracked: bool | None = None
    evidence_required: bool | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator(
        "sku",
        "name",
        "category",
        "preferred_supplier_name",
        "preferred_supplier_sku",
        "notes",
        mode="before",
    )
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class MaterialReceiptRequest(BaseModel):
    """Admin request to record a purchased material receipt."""

    model_config = ConfigDict(extra="forbid")

    receipt_date: str | None = Field(default=None, min_length=10, max_length=32)
    quantity: float = Field(..., gt=0)
    uom: MaterialUom
    unit_cost_amount: str | None = Field(default=None, max_length=40)
    total_cost_cents: int | None = Field(default=None, ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    supplier_name: str | None = Field(default=None, max_length=200)
    supplier_lot: str | None = Field(default=None, max_length=100)
    expiry_date: str | None = Field(default=None, min_length=10, max_length=32)
    use_by_date: str | None = Field(default=None, min_length=10, max_length=32)
    expense_evidence_id: str | None = Field(default=None, max_length=100)
    document_reference: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator(
        "unit_cost_amount",
        "supplier_name",
        "supplier_lot",
        "expense_evidence_id",
        "document_reference",
        "notes",
        mode="before",
    )
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("currency", mode="before")
    @classmethod
    def _currency_upper(cls, value: str) -> str:
        return value.strip().upper()


class MaterialAdjustmentRequest(BaseModel):
    """Admin request to create a manual material movement."""

    model_config = ConfigDict(extra="forbid")

    movement_type: MaterialMovementType
    quantity_delta: float = Field(...)
    uom: MaterialUom | None = None
    reason: str = Field(..., min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    occurred_at: str | None = Field(default=None, min_length=10, max_length=32)

    @model_validator(mode="after")
    def _validate_delta(self) -> MaterialAdjustmentRequest:
        if self.quantity_delta == 0:
            raise ValueError("quantity_delta must not be zero")
        if self.movement_type in {"spoilage", "write_off"} and self.quantity_delta > 0:
            raise ValueError("spoilage and write_off movements must decrease stock")
        return self

    @field_validator("reason", mode="before")
    @classmethod
    def _reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be blank")
        return stripped

    @field_validator("notes", mode="before")
    @classmethod
    def _notes(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class InventoryExceptionResponse(BaseModel):
    id: str
    exception_type: str
    severity: Literal["blocking", "warning"]
    target_type: str | None = None
    target_id: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    status: Literal["open", "resolved", "waived"]
    message: str
    created_at: str


class InventoryMovementResponse(BaseModel):
    id: str
    item_type: Literal["material", "finished_good"]
    item_id: str
    movement_type: str
    quantity_delta: float
    uom: str
    source_type: str | None = None
    source_id: str | None = None
    material_lot_id: str | None = None
    actor_user_id: str | None = None
    actor_email: str | None = None
    reason: str | None = None
    notes: str | None = None
    review_state: InventoryReviewState
    occurred_at: str
    created_at: str


class MaterialLotResponse(BaseModel):
    id: str
    material_id: str
    receipt_id: str | None = None
    supplier_lot: str | None = None
    expiry_date: str | None = None
    use_by_date: str | None = None
    received_quantity: float
    stock_uom: str
    remaining_quantity_snapshot: float | None = None
    unit_cost_amount: str | None = None
    currency: str
    supplier_name: str | None = None
    review_state: MaterialReviewState
    lot_status: Literal["ok", "near_expiry", "expired", "unknown"] = "unknown"
    created_at: str
    updated_at: str


class MaterialReceiptResponse(BaseModel):
    id: str
    material_id: str
    receipt_date: str
    quantity: float
    uom: str
    stock_quantity: float
    stock_uom: str
    unit_cost_amount: str | None = None
    total_cost_cents: int | None = None
    currency: str
    supplier_name: str | None = None
    supplier_lot: str | None = None
    expiry_date: str | None = None
    use_by_date: str | None = None
    expense_evidence_id: str | None = None
    document_reference: str | None = None
    review_state: MaterialReviewState
    movement_id: str | None = None
    lot_id: str | None = None
    exceptions: list[InventoryExceptionResponse] = Field(default_factory=list)
    notes: str | None = None
    created_at: str
    updated_at: str


class MaterialResponse(BaseModel):
    id: str
    sku: str | None = None
    name: str
    category: str
    stock_uom: str
    purchase_uom: str | None = None
    purchase_to_stock_factor: float | None = None
    preferred_supplier_name: str | None = None
    preferred_supplier_sku: str | None = None
    reorder_threshold: float | None = None
    active: bool
    lot_tracked: bool
    expiry_tracked: bool
    evidence_required: bool
    on_hand_quantity: float = 0
    reorder_status: Literal["ok", "below_threshold", "not_configured", "inactive"]
    open_exception_count: int = 0
    latest_movement_at: str | None = None
    notes: str | None = None
    created_at: str
    updated_at: str


class MaterialDetailResponse(MaterialResponse):
    lots: list[MaterialLotResponse] = Field(default_factory=list)
    recent_movements: list[InventoryMovementResponse] = Field(default_factory=list)
    exceptions: list[InventoryExceptionResponse] = Field(default_factory=list)


class MaterialListResponse(BaseModel):
    materials: list[MaterialResponse]
    total: int


class MaterialLotListResponse(BaseModel):
    lots: list[MaterialLotResponse]
    total: int


class InventoryMovementListResponse(BaseModel):
    movements: list[InventoryMovementResponse]
    total: int
