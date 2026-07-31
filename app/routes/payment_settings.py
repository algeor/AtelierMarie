"""Payment settings endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.database import get_db
from app.dependencies.auth import require_admin
from app.middleware.request_id import request_id_var
from app.models.payments import (
    PaymentSettingsResponse,
    PaymentSettingsUpdate,
    PublicPaymentSettingsResponse,
)
from app.models.users import UserResponse
from app.responses import error_response
from app.services.payment_settings_service import (
    PaymentSettingsValidationError,
    get_payment_settings,
    public_payment_settings,
    stripe_config_health,
    update_payment_settings,
)

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get(
    "/payments",
    response_model=PublicPaymentSettingsResponse,
    summary="Get safe public payment settings",
)
def get_public_payment_settings() -> PublicPaymentSettingsResponse:
    """Return checkout-safe payment method availability without secrets."""
    settings = get_settings()
    with get_db() as conn:
        data = public_payment_settings(conn, settings)
    return PublicPaymentSettingsResponse(**data)


@admin_router.get(
    "/payments",
    response_model=PaymentSettingsResponse,
    summary="Get admin payment settings",
)
def admin_get_payment_settings() -> PaymentSettingsResponse:
    """Return admin-editable payment settings plus Stripe config health."""
    settings = get_settings()
    with get_db() as conn:
        data = get_payment_settings(conn)
    return PaymentSettingsResponse(**data, stripe=stripe_config_health(settings))


@admin_router.put(
    "/payments",
    response_model=PaymentSettingsResponse,
    summary="Update admin payment settings",
)
def admin_update_payment_settings(
    body: PaymentSettingsUpdate,
    request: Request,
    admin_user: Annotated[UserResponse | None, Depends(require_admin)],
) -> PaymentSettingsResponse:
    """Persist admin payment settings and write audit events."""
    settings = get_settings()
    admin_id = admin_user.id if admin_user else None
    admin_email = admin_user.email if admin_user else None
    request_id = request_id_var.get() or request.headers.get("x-request-id")

    with get_db() as conn:
        try:
            data = update_payment_settings(
                conn,
                body.model_dump(),
                settings,
                admin_id=admin_id,
                admin_email=admin_email,
                request_id=request_id,
            )
        except PaymentSettingsValidationError as exc:
            return error_response(422, "PAYMENT_SETTINGS_INVALID", str(exc))

    return PaymentSettingsResponse(**data, stripe=stripe_config_health(settings))
