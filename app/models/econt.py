"""Pydantic models for Econt integration settings and health state."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.delivery import normalize_phone

EcontEnvironment = Literal["demo", "production"]
EcontCredentialSource = Literal["env", "stored"]
EcontDeliveryMode = Literal["office", "door"]
EcontPaymentSide = Literal["sender", "receiver"]
EcontCurrency = Literal["EUR", "BGN"]
EcontConnectionStatus = Literal[
    "success",
    "missing_configuration",
    "authentication_failed",
    "validation_failed",
    "timeout",
    "service_outage",
]


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class EcontSecretState(BaseModel):
    """Public-safe state of Econt credentials."""

    credential_source: EcontCredentialSource
    private_key_configured: bool
    shop_id_configured: bool
    encryption_key_configured: bool


class EcontSettingsResponse(BaseModel):
    """Admin-safe Econt settings response. Never includes raw secrets."""

    enabled: bool
    environment: EcontEnvironment
    shop_id: str | None = None
    credential_source: EcontCredentialSource
    sender_delivery_mode: EcontDeliveryMode
    sender_office_code: str | None = None
    sender_city: str | None = None
    sender_post_code: str | None = None
    sender_address: str | None = None
    sender_quarter: str | None = None
    sender_street: str | None = None
    sender_num: str | None = None
    sender_other: str | None = None
    default_pack_count: int
    shipment_description: str
    declared_value_enabled: bool
    default_payment_side: EcontPaymentSide
    courier_currency: EcontCurrency
    currency_conversion_rate: float | None = None
    office_locator_enabled: bool
    auto_confirm_on_label: bool
    auto_delivered_on_trace: bool
    base_url: str
    office_locator_url: str
    office_locator_origins: list[str]
    secret_state: EcontSecretState
    last_health_status: str | None = None
    last_health_checked_at: str | None = None
    last_health_error: str | None = None
    updated_at: str


class EcontSettingsUpdate(BaseModel):
    """Admin update payload for non-secret Econt settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    environment: EcontEnvironment | None = None
    shop_id: str | None = Field(default=None, max_length=100)
    credential_source: EcontCredentialSource | None = None
    sender_delivery_mode: EcontDeliveryMode | None = None
    sender_office_code: str | None = Field(default=None, max_length=64)
    sender_city: str | None = Field(default=None, max_length=100)
    sender_post_code: str | None = Field(default=None, max_length=20)
    sender_address: str | None = Field(default=None, max_length=255)
    sender_quarter: str | None = Field(default=None, max_length=100)
    sender_street: str | None = Field(default=None, max_length=100)
    sender_num: str | None = Field(default=None, max_length=20)
    sender_other: str | None = Field(default=None, max_length=255)
    default_pack_count: int | None = Field(default=None, ge=1, le=99)
    shipment_description: str | None = Field(default=None, min_length=1, max_length=255)
    declared_value_enabled: bool | None = None
    default_payment_side: EcontPaymentSide | None = None
    courier_currency: EcontCurrency | None = None
    currency_conversion_rate: float | None = Field(default=None, gt=0)
    office_locator_enabled: bool | None = None
    auto_confirm_on_label: bool | None = None
    auto_delivered_on_trace: bool | None = None

    @field_validator("credential_source")
    @classmethod
    def _env_backed_credentials_only(
        cls, value: EcontCredentialSource | None
    ) -> EcontCredentialSource | None:
        if value == "stored":
            raise ValueError("stored Econt secrets are not supported yet")
        return value

    @field_validator(
        "shop_id",
        "sender_office_code",
        "sender_city",
        "sender_post_code",
        "sender_address",
        "sender_quarter",
        "sender_street",
        "sender_num",
        "sender_other",
        mode="before",
    )
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("shipment_description", mode="before")
    @classmethod
    def _strip_required_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("shipment_description must not be blank")
        return stripped


class EcontConnectionTestResponse(BaseModel):
    """Result of an admin Econt configuration/test-connection action."""

    status: EcontConnectionStatus
    ok: bool
    message: str
    checked_at: str
    details: dict[str, object] | None = None


class EcontOrderFulfillmentResponse(BaseModel):
    """Admin Econt fulfillment state for one local order."""

    order_id: str
    ready: bool
    blockers: list[str]
    courier_provider: str | None = None
    courier_order_id: str | None = None
    courier_shipment_number: str | None = None
    courier_label_url: str | None = None
    courier_sync_status: str | None = None
    courier_last_error: str | None = None
    courier_last_synced_at: str | None = None
    tracking_number: str | None = None
    tracking_url: str | None = None


class EcontFulfillmentActionResponse(BaseModel):
    """Admin response for an Econt fulfillment action."""

    order_id: str
    action: str
    status: str
    courier_order_id: str | None = None
    shipment_number: str | None = None
    label_url: str | None = None
    tracking_url: str | None = None
    status_updated_to: str | None = None
    ready: bool | None = None
    blockers: list[str] | None = None


class EcontOrderRepairRequest(BaseModel):
    """Admin repair fields used before Econt label creation."""

    model_config = ConfigDict(extra="forbid")

    office_code: str | None = Field(default=None, max_length=64)
    recipient_phone: str | None = Field(default=None, min_length=8, max_length=20)
    pack_count: int | None = Field(default=None, ge=1, le=99)
    shipment_description: str | None = Field(default=None, min_length=1, max_length=255)
    payment_side: EcontPaymentSide | None = None

    @field_validator("office_code", mode="before")
    @classmethod
    def _optional_code(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("recipient_phone", mode="before")
    @classmethod
    def _optional_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_phone(value)

    @field_validator("shipment_description", mode="before")
    @classmethod
    def _optional_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("shipment_description must not be blank")
        return stripped


class EcontReadiness(BaseModel):
    """Computed readiness state used by settings and later fulfillment actions."""

    ready: bool
    blockers: list[str]

    @model_validator(mode="after")
    def _ready_matches_blockers(self) -> "EcontReadiness":
        if self.ready and self.blockers:
            raise ValueError("ready cannot be true when blockers are present")
        return self


class _EcontApiModel(BaseModel):
    """Base for flexible Econt API payload/response models."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class EcontCustomerInfo(_EcontApiModel):
    name: str | None = None
    face: str | None = None
    phone: str | None = None
    email: str | None = None
    country_code: str | None = Field(default="BGR", alias="countryCode")
    city_name: str | None = Field(default=None, alias="cityName")
    post_code: str | None = Field(default=None, alias="postCode")
    office_code: str | None = Field(default=None, alias="officeCode")
    zip_code: str | None = Field(default=None, alias="zipCode")
    address: str | None = None
    quarter: str | None = None
    street: str | None = None
    num: str | None = None
    other: str | None = None


class EcontSenderInfo(EcontCustomerInfo):
    pass


class EcontOrderItem(_EcontApiModel):
    name: str
    sku: str | None = None
    quantity: int = Field(default=1, ge=1)
    price: float | None = None
    total_weight: float | None = Field(default=None, gt=0, alias="totalWeight")


class EcontOrderPayload(_EcontApiModel):
    order_number: str = Field(alias="orderNumber")
    order_time: str | None = Field(default=None, alias="orderTime")
    order_sum: float | None = Field(default=None, ge=0, alias="orderSum")
    declared_value: float | None = Field(default=None, ge=0, alias="declaredValue")
    cod: bool = False
    currency: str = "EUR"
    shipment_description: str | None = Field(default=None, alias="shipmentDescription")
    shipment_number: str | None = Field(default=None, alias="shipmentNumber")
    sender_info: EcontSenderInfo | None = Field(default=None, alias="senderInfo")
    customer_info: EcontCustomerInfo = Field(alias="customerInfo")
    items: list[EcontOrderItem] = Field(default_factory=list)
    pack_count: int = Field(default=1, ge=1, alias="packCount")
    payment_side: EcontPaymentSide | None = Field(default=None, alias="paymentSide")


class EcontTraceEvent(_EcontApiModel):
    time: str | None = None
    status: str | None = None
    location: str | None = None
    details: str | None = None


class EcontShipmentStatus(_EcontApiModel):
    shipment_number: str | None = Field(default=None, alias="shipmentNumber")
    pdf_url: str | None = Field(default=None, alias="pdfURL")
    tracking_url: str | None = Field(default=None, alias="trackingURL")
    status: str | None = None
    price: float | None = None
    events: list[EcontTraceEvent] = Field(default_factory=list)
