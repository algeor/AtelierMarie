"""Pydantic models for admin inventory, materials, and stock movements."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MaterialUom = Literal["g", "kg", "ml", "l", "piece", "pcs", "unit", "m", "cm"]
MaterialMovementType = Literal["adjustment", "spoilage", "write_off", "stock_count_correction"]
MaterialReviewState = Literal["draft", "needs_review", "reviewed", "rejected"]
InventoryReviewState = Literal["unreviewed", "reviewed", "estimate", "official", "reversed"]
RecipeStatus = Literal["draft", "active", "archived"]
RecipeReviewState = Literal["estimate", "reviewed", "accountant_reviewed", "invalid"]
QuantityBasis = Literal["per_unit", "per_batch"]
ProductionBatchStatus = Literal["draft", "produced", "cancelled"]
ValuationMethod = Literal["weighted_average", "fifo"]
COGSDateBasis = Literal["order_date", "payment_date", "shipment_date", "delivery_date", "period_close"]


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


class RecipeComponentRequest(BaseModel):
    """One material component line in a recipe/BOM."""

    model_config = ConfigDict(extra="forbid")

    material_id: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    uom: MaterialUom
    quantity_basis: QuantityBasis = "per_batch"
    wastage_percent: float = Field(default=0, ge=0, le=1000)
    required: bool = True
    substitute_group: str | None = Field(default=None, max_length=100)
    sort_order: int = Field(default=0, ge=0)

    @field_validator("substitute_group", mode="before")
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class RecipeVersionCreateRequest(BaseModel):
    """Admin request to create a draft recipe/BOM version."""

    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(..., min_length=1, max_length=100)
    version_label: str = Field(..., min_length=1, max_length=100)
    effective_date: str = Field(..., min_length=10, max_length=32)
    output_quantity: float = Field(..., gt=0)
    output_uom: str = Field(default="unit", min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=1000)
    components: list[RecipeComponentRequest] = Field(default_factory=list)

    @field_validator("version_label", "output_uom", "notes", mode="before")
    @classmethod
    def _strings(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class RecipeVersionUpdateRequest(BaseModel):
    """Admin request to update a draft recipe/BOM version."""

    model_config = ConfigDict(extra="forbid")

    version_label: str | None = Field(default=None, min_length=1, max_length=100)
    effective_date: str | None = Field(default=None, min_length=10, max_length=32)
    output_quantity: float | None = Field(default=None, gt=0)
    output_uom: str | None = Field(default=None, min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=1000)
    components: list[RecipeComponentRequest] | None = None

    @field_validator("version_label", "output_uom", "notes", mode="before")
    @classmethod
    def _strings(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class RecipeReviewRequest(BaseModel):
    """Admin request to set recipe review state."""

    model_config = ConfigDict(extra="forbid")

    review_state: RecipeReviewState = "reviewed"
    review_note: str | None = Field(default=None, max_length=1000)

    @field_validator("review_note", mode="before")
    @classmethod
    def _note(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class RecipeCostSnapshotRequest(BaseModel):
    """Optional management estimates included in a recipe cost snapshot."""

    model_config = ConfigDict(extra="forbid")

    labor_cost_cents: int = Field(default=0, ge=0)
    overhead_cost_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)

    @field_validator("currency", mode="before")
    @classmethod
    def _currency_upper(cls, value: str) -> str:
        return value.strip().upper()


class RecipeDiagnosticResponse(BaseModel):
    code: str
    severity: Literal["blocking", "warning"] = "warning"
    message: str
    target_type: str | None = None
    target_id: str | None = None


class RecipeComponentResponse(BaseModel):
    id: str
    recipe_version_id: str
    material_id: str
    material_name: str | None = None
    material_active: bool | None = None
    material_category: str | None = None
    quantity: float
    uom: str
    quantity_basis: QuantityBasis
    wastage_percent: float
    required: bool
    substitute_group: str | None = None
    sort_order: int
    review_state: Literal["valid", "warning", "invalid"]
    created_at: str
    updated_at: str


class RecipeCostSnapshotResponse(BaseModel):
    id: str
    recipe_version_id: str
    currency: str
    material_cost_cents: int
    packaging_cost_cents: int
    labor_cost_cents: int
    overhead_cost_cents: int
    batch_cost_cents: int
    expected_unit_cost_cents: int
    source_cost_references_json: str | None = None
    missing_cost_count: int
    estimate_label: str
    review_state: Literal["estimate", "incomplete", "reviewed", "accountant_reviewed"]
    calculated_at: str
    created_by_admin_id: str | None = None
    created_at: str


class RecipeVersionResponse(BaseModel):
    id: str
    product_id: str
    version_label: str
    status: RecipeStatus
    effective_date: str
    output_quantity: float
    output_uom: str
    review_state: RecipeReviewState
    accountant_reviewed: bool
    reviewed_by_admin_id: str | None = None
    reviewed_at: str | None = None
    notes: str | None = None
    created_by_admin_id: str | None = None
    updated_by_admin_id: str | None = None
    components: list[RecipeComponentResponse] = Field(default_factory=list)
    latest_cost_snapshot: RecipeCostSnapshotResponse | None = None
    diagnostics: list[RecipeDiagnosticResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str


class RecipeVersionListResponse(BaseModel):
    recipes: list[RecipeVersionResponse]
    total: int


class RecipeDiagnosticsListResponse(BaseModel):
    diagnostics: list[RecipeDiagnosticResponse]


class ProductionBatchCreateRequest(BaseModel):
    """Admin request to create a draft one-step production batch."""

    model_config = ConfigDict(extra="forbid")

    batch_number: str = Field(..., min_length=1, max_length=100)
    product_id: str = Field(..., min_length=1, max_length=100)
    recipe_version_id: str | None = Field(default=None, max_length=100)
    planned_output_quantity: float = Field(..., gt=0)
    output_uom: str = Field(default="unit", min_length=1, max_length=40)
    production_date: str = Field(..., min_length=10, max_length=32)
    ready_date: str | None = Field(default=None, min_length=10, max_length=32)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("batch_number", "output_uom", "notes", mode="before")
    @classmethod
    def _strings(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class ProductionBatchUpdateRequest(BaseModel):
    """Admin request to edit a draft production batch."""

    model_config = ConfigDict(extra="forbid")

    planned_output_quantity: float | None = Field(default=None, gt=0)
    production_date: str | None = Field(default=None, min_length=10, max_length=32)
    ready_date: str | None = Field(default=None, min_length=10, max_length=32)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes", mode="before")
    @classmethod
    def _notes(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class ProductionBatchActualConsumptionRequest(BaseModel):
    """Actual material usage for a batch posting."""

    model_config = ConfigDict(extra="forbid")

    batch_consumption_id: str | None = Field(default=None, max_length=100)
    material_id: str = Field(..., min_length=1, max_length=100)
    material_lot_id: str | None = Field(default=None, max_length=100)
    actual_quantity: float = Field(..., ge=0)
    waste_quantity: float = Field(default=0, ge=0)
    uom: MaterialUom | None = None


class ProductionBatchPostRequest(BaseModel):
    """Admin request to post a draft batch as produced."""

    model_config = ConfigDict(extra="forbid")

    actual_output_quantity: float = Field(..., gt=0)
    actual_consumption: list[ProductionBatchActualConsumptionRequest] = Field(default_factory=list)
    variance_tolerance_percent: float = Field(default=10, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes", mode="before")
    @classmethod
    def _notes(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class ProductionBatchCorrectionRequest(BaseModel):
    """Admin request to correct a produced batch through a new movement."""

    model_config = ConfigDict(extra="forbid")

    item_type: Literal["material", "finished_good"]
    item_id: str = Field(..., min_length=1, max_length=100)
    quantity_delta: float
    uom: str = Field(..., min_length=1, max_length=40)
    reason: str = Field(..., min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _quantity_nonzero(self) -> ProductionBatchCorrectionRequest:
        if self.quantity_delta == 0:
            raise ValueError("quantity_delta must not be zero")
        return self

    @field_validator("reason", "notes", mode="before")
    @classmethod
    def _strings(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class ProductionBatchConsumptionResponse(BaseModel):
    id: str
    production_batch_id: str
    recipe_component_id: str | None = None
    material_id: str
    material_name: str | None = None
    material_lot_id: str | None = None
    expected_quantity: float | None = None
    actual_quantity: float | None = None
    waste_quantity: float
    uom: str
    unit_cost_amount: str | None = None
    currency: str
    movement_id: str | None = None
    review_state: MaterialReviewState
    created_at: str
    updated_at: str


class ProductionBatchOutputResponse(BaseModel):
    id: str
    production_batch_id: str
    product_id: str
    batch_number: str
    quantity: float
    uom: str
    unit_cost_amount: str | None = None
    currency: str
    movement_id: str | None = None
    remaining_quantity_snapshot: float | None = None
    valuation_review_state: Literal["estimate", "reviewed", "official"]
    created_at: str


class ProductionBatchResponse(BaseModel):
    id: str
    batch_number: str
    product_id: str
    recipe_version_id: str | None = None
    planned_output_quantity: float
    actual_output_quantity: float | None = None
    output_uom: str
    status: ProductionBatchStatus
    production_date: str
    ready_date: str | None = None
    cost_snapshot_id: str | None = None
    variance_review_state: Literal["not_reviewed", "warning", "reviewed"]
    actor_user_id: str | None = None
    notes: str | None = None
    consumption: list[ProductionBatchConsumptionResponse] = Field(default_factory=list)
    outputs: list[ProductionBatchOutputResponse] = Field(default_factory=list)
    exceptions: list[InventoryExceptionResponse] = Field(default_factory=list)
    created_by_admin_id: str | None = None
    updated_by_admin_id: str | None = None
    created_at: str
    updated_at: str


class ProductionBatchListResponse(BaseModel):
    batches: list[ProductionBatchResponse]
    total: int


class ProductionTraceabilityResponse(ProductionBatchResponse):
    source_movements: list[InventoryMovementResponse] = Field(default_factory=list)
    finished_movements: list[InventoryMovementResponse] = Field(default_factory=list)
    linked_order_lines: list[dict[str, object]] = Field(default_factory=list)


class InventoryValuationSettingsRequest(BaseModel):
    """Admin request to update inventory valuation policy."""

    model_config = ConfigDict(extra="forbid")

    ledger_mode: Literal["legacy", "setup", "ledger_managed"] = "setup"
    valuation_enabled: bool = False
    valuation_method: ValuationMethod = "weighted_average"
    effective_date: str = Field(..., min_length=10, max_length=32)
    cogs_date_basis: COGSDateBasis = "order_date"
    rounding_policy: Literal["half_up_2dp", "half_up_4dp"] = "half_up_2dp"
    missing_cost_behavior: Literal["allow_estimate", "warn", "block_official"] = "block_official"
    included_cost_components: dict[str, object] | None = None
    write_off_mapping: dict[str, object] | None = None
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    accountant_reviewed: bool = False
    reviewed_by_name: str | None = Field(default=None, max_length=200)
    review_notes: str | None = Field(default=None, max_length=1000)

    @field_validator("currency", mode="before")
    @classmethod
    def _currency_upper(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("reviewed_by_name", "review_notes", mode="before")
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class InventoryValuationSettingsResponse(BaseModel):
    id: str = "default"
    ledger_mode: Literal["legacy", "setup", "ledger_managed"]
    valuation_enabled: bool
    valuation_method: ValuationMethod
    effective_date: str
    cogs_date_basis: COGSDateBasis
    rounding_policy: str
    missing_cost_behavior: str
    included_cost_components: dict[str, object] | None = None
    write_off_mapping: dict[str, object] | None = None
    currency: str
    settings_version: int
    accountant_reviewed: bool
    reviewed_by_admin_id: str | None = None
    reviewed_by_name: str | None = None
    reviewed_at: str | None = None
    review_notes: str | None = None
    created_at: str
    updated_at: str


class OpeningBalanceRequest(BaseModel):
    """Reviewed opening balance for a material or finished good."""

    model_config = ConfigDict(extra="forbid")

    item_type: Literal["material", "finished_good"]
    item_id: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., ge=0)
    uom: str = Field(..., min_length=1, max_length=40)
    unit_value_amount: str | None = Field(default=None, max_length=40)
    total_value_cents: int | None = Field(default=None, ge=0)
    reviewed: bool = False
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("unit_value_amount", "notes", mode="before")
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class ValuationLayerResponse(BaseModel):
    id: str
    movement_id: str | None = None
    item_type: Literal["material", "finished_good"]
    item_id: str
    quantity: float
    unit_value_amount: str | None = None
    total_value_cents: int | None = None
    currency: str
    valuation_method: Literal["weighted_average", "fifo", "revaluation"]
    source_type: str | None = None
    source_id: str | None = None
    valuation_date: str
    review_state: Literal["estimate", "reviewed", "official", "reversed"]
    method_metadata_json: str | None = None
    reversal_layer_id: str | None = None
    created_at: str


class ValuationLayerListResponse(BaseModel):
    layers: list[ValuationLayerResponse]
    total: int


class COGSLedgerResponse(BaseModel):
    id: str
    order_id: str | None = None
    order_number: str | None = None
    order_item_key: str | None = None
    product_id: str | None = None
    quantity_sold: float
    cogs_date: str
    unit_cost_amount: str | None = None
    total_cost_cents: int
    currency: str
    valuation_method: ValuationMethod
    source_movement_id: str | None = None
    source_valuation_layer_id: str | None = None
    source_finished_batch_id: str | None = None
    review_state: Literal["estimate", "reviewed", "official", "reversed"]
    reversal_cogs_id: str | None = None
    created_at: str


class COGSLedgerListResponse(BaseModel):
    rows: list[COGSLedgerResponse]
    total: int


class InventoryClosePreviewResponse(BaseModel):
    period_start: str
    period_end: str
    currency: str
    valuation_method: ValuationMethod
    official: bool
    opening_value_cents: int
    receipts_value_cents: int
    production_consumption_value_cents: int
    finished_output_value_cents: int
    sales_cogs_value_cents: int
    returns_value_cents: int
    adjustments_value_cents: int
    ending_value_cents: int
    exception_count: int
    policy_snapshot: dict[str, object]
