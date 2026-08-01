"""Pydantic models for Speedy admin operations."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SpeedyHealthStatus = Literal["healthy", "blocked", "warning", "unavailable"]
SpeedyActionStatus = Literal["created", "existing", "success", "cancelled", "skipped"]


class SpeedyCircuitState(BaseModel):
    name: str
    state: str
    failure_count: int
    failure_threshold: int
    recovery_remaining_seconds: float | None = None


class SpeedyHealthResponse(BaseModel):
    status: SpeedyHealthStatus
    ok: bool
    message: str
    username_configured: bool
    password_configured: bool
    client_id_configured: bool
    client_id_numeric: bool
    configured_client_id: str | None = None
    verified_client_id: str | None = None
    client_id_matches: bool | None = None
    blockers: list[str] = Field(default_factory=list)
    circuit: SpeedyCircuitState
    last_failure_category: str | None = None
    last_successful_check_at: str | None = None
    checked_at: str


class SpeedyOrderSummary(BaseModel):
    order_id: str
    order_number: str | None = None
    status: str
    customer_email: str
    customer_name: str | None = None
    delivery_method: str | None = None
    delivery_label: str | None = None
    total_cents: int
    tracking_number: str | None = None
    tracking_url: str | None = None
    courier_status: str | None = None
    courier_sync_status: str | None = None
    courier_last_error: str | None = None
    courier_last_synced_at: str | None = None
    created_at: str
    updated_at: str


class SpeedyQueuesResponse(BaseModel):
    ready_to_ship: list[SpeedyOrderSummary]
    shipped: list[SpeedyOrderSummary]


class SpeedyEventResponse(BaseModel):
    id: int
    order_id: str
    action: str
    status: str
    request: dict[str, Any] | None = None
    response: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    actor_user_id: str | None = None
    created_at: str


class SpeedyMetricsResponse(BaseModel):
    recent_successes: int
    recent_failures: int
    failures_by_category: dict[str, int]
    cancellation_count: int
    pickup_request_count: int
    last_successful_health_check_at: str | None = None


class SpeedyOfficeRefreshStatusResponse(BaseModel):
    status: str | None = None
    refreshed_at: str | None = None
    records: int | None = None
    error: str | None = None


class SpeedyAdminOverviewResponse(BaseModel):
    health: SpeedyHealthResponse
    queues: SpeedyQueuesResponse
    events: list[SpeedyEventResponse]
    metrics: SpeedyMetricsResponse
    office_refresh: SpeedyOfficeRefreshStatusResponse


class SpeedyActionResponse(BaseModel):
    order_id: str
    action: str
    status: SpeedyActionStatus | str
    shipment_number: str | None = None
    tracking_url: str | None = None
    courier_status: str | None = None
    status_updated_to: str | None = None
    details: dict[str, Any] | None = None


class SpeedyShipmentSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: str = Field(..., min_length=1, max_length=128)
    include_returns: bool = False
    shipments_only: bool = True

    @field_validator("reference", mode="before")
    @classmethod
    def _strip_reference(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class SpeedyShipmentSearchResponse(BaseModel):
    reference: str
    barcodes: list[str]


class SpeedyShipmentInfoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_ids: list[str] = Field(..., min_length=1, max_length=20)

    @field_validator("shipment_ids", mode="after")
    @classmethod
    def _clean_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("at least one shipment id is required")
        return cleaned


class SpeedyShipmentInfoResponse(BaseModel):
    shipments: list[dict[str, Any]]


class SpeedyCancelShipmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment: str | None = Field(default=None, max_length=255)


class SpeedyPickupTermsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_ids: list[str] = Field(default_factory=list, max_length=50)
    starting_date_utc_ms: int | None = Field(default=None, ge=0)

    @field_validator("shipment_ids", mode="after")
    @classmethod
    def _clean_optional_shipment_ids(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class SpeedyPickupTermsResponse(BaseModel):
    cutoffs: list[str]


class SpeedyPickupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_ids: list[str] = Field(..., min_length=1, max_length=50)
    pickup_datetime: str = Field(..., min_length=1, max_length=64)
    visit_end_time: str = Field(..., min_length=1, max_length=16)
    contact_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=6, max_length=30)

    @field_validator("shipment_ids", mode="after")
    @classmethod
    def _clean_shipment_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("at least one shipment id is required")
        return cleaned

    @field_validator("pickup_datetime", "visit_end_time", "contact_name", "phone", mode="before")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class SpeedyPickupResponse(BaseModel):
    orders: list[dict[str, Any]]
