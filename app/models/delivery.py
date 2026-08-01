"""Delivery request models for structured shipping information.

Structured shipping payload on orders: method (office pickup vs to-door),
courier (Speedy/Econt), and either an office reference or a full address.

Design decisions:
- Nested optional `office`/`door` (not a discriminated union) — simpler OpenAPI.
- Phone is required for BOTH methods — Bulgarian couriers always call the
  recipient regardless of pickup style.
- `office_type` distinguishes staffed offices from automated lockers
  (автомати) so the UI can render locker-specific pickup instructions.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

DeliveryMethod = Literal["office", "door"]
Courier = Literal["speedy", "econt"]
OfficeType = Literal["office", "apt"]

# Phone: 8–15 chars, digits + optional leading '+'. Matches Speedy/Econt reqs
# for BG mobile/landline numbers and doesn't over-constrain international formats.
_PHONE_REGEX = r"^\+?\d{8,15}$"


def normalize_phone(value: str) -> str:
    """Strip whitespace/dashes/parens, then apply the phone regex."""
    normalized = "".join(ch for ch in value if ch.isdigit() or ch == "+")
    if not re.match(_PHONE_REGEX, normalized):
        raise ValueError("phone must be 8–15 digits with optional leading '+'")
    return normalized


def _validate_phone(value: str) -> str:
    """Normalize user-entered courier phone numbers before storing."""
    return normalize_phone(value)


class DeliveryOffice(BaseModel):
    """Office pickup destination — a Speedy/Econt staffed office or locker.

    `city` is the office's city — carried so the shipping calculator can quote
    an office pickup without a separate lookup (the courier calculate APIs are
    city-keyed). Sourced from the selected office record at checkout.
    """

    courier: Courier
    office_id: str = Field(..., min_length=1, max_length=64)
    office_code: str | None = Field(default=None, max_length=64)
    office_name: str = Field(..., min_length=1, max_length=255)
    office_type: OfficeType
    city: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=8, max_length=20)

    @field_validator("phone")
    @classmethod
    def _phone_format(cls, value: str) -> str:
        return _validate_phone(value)


class DeliveryDoor(BaseModel):
    """Door-to-door delivery — full address for the courier."""

    courier: Courier
    city: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=10)
    street: str = Field(..., min_length=1, max_length=200)
    building: str | None = Field(default=None, max_length=50)
    apartment: str | None = Field(default=None, max_length=50)
    phone: str = Field(..., min_length=8, max_length=20)

    @field_validator("phone")
    @classmethod
    def _phone_format(cls, value: str) -> str:
        return _validate_phone(value)


class OfficeResponse(BaseModel):
    """API-shape office record returned by `GET /v1/delivery/offices`.

    Distinct from `DeliveryOffice` (the checkout request payload). The
    fields here match the `courier-offices-data` spec exactly and mirror
    the on-disk unified schema, locale-resolved by `delivery_service`.
    """

    id: str
    code: str | None = None
    name: str
    type: OfficeType
    city: str
    address: str
    working_hours: str


class EcontCheckoutConfig(BaseModel):
    """Public-safe Econt checkout behavior flags."""

    office_locator_enabled: bool
    office_locator_url: str
    office_locator_origins: list[str]


class DeliveryConfigResponse(BaseModel):
    """Public delivery configuration consumed by checkout UI."""

    econt: EcontCheckoutConfig


class DeliveryInfo(BaseModel):
    """Top-level delivery selection: method + method-specific details."""

    method: DeliveryMethod
    office: DeliveryOffice | None = None
    door: DeliveryDoor | None = None

    @model_validator(mode="after")
    def _details_match_method(self) -> "DeliveryInfo":
        """The correct sub-object must be present, the other must not."""
        if self.method == "office":
            if self.office is None:
                raise ValueError("office details required when method is 'office'")
            if self.door is not None:
                raise ValueError("door details must be null when method is 'office'")
        elif self.method == "door":
            if self.door is None:
                raise ValueError("door details required when method is 'door'")
            if self.office is not None:
                raise ValueError("office details must be null when method is 'door'")
        return self


class DeliverySettingsUpdate(BaseModel):
    """Admin update for delivery-method availability switches."""

    speedy_office_enabled: bool = True
    speedy_door_enabled: bool = True
    econt_office_enabled: bool = True
    econt_door_enabled: bool = True
    cod_enabled: bool = True
    card_enabled: bool = True
    bank_transfer_enabled: bool = True


class DeliverySettingsResponse(DeliverySettingsUpdate):
    """Current delivery-method availability settings."""

    updated_at: str
