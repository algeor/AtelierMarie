"""Econt integration settings service.

Reads/writes the singleton non-secret settings row and merges it with env-backed
secret/config state. Raw private keys are never returned.
"""

import sqlite3
from typing import Any

import structlog

from app.config import Settings, get_settings
from app.database import get_db
from app.models.delivery import DeliveryConfigResponse, EcontCheckoutConfig
from app.models.econt import (
    EcontConnectionTestResponse,
    EcontReadiness,
    EcontSecretState,
    EcontSettingsResponse,
    EcontSettingsUpdate,
)
from app.services import pricing
from app.services.econt_delivery_client import EcontDeliveryClient, EcontDeliveryError

logger = structlog.get_logger(__name__)

_SETTINGS_ID = "default"
_DEMO_BASE_URL = "https://delivery-demo.econt.com/services/"
_PRODUCTION_BASE_URL = "https://delivery.econt.com/services/"
_DEMO_LOCATOR_URL = "https://delivery-demo.econt.com/customer_info.php"
_PRODUCTION_LOCATOR_URL = "https://delivery.econt.com/customer_info.php"
_DEMO_LOCATOR_ORIGIN = "https://delivery-demo.econt.com"
_PRODUCTION_LOCATOR_ORIGIN = "https://delivery.econt.com"

_UPDATE_FIELDS = {
    "enabled",
    "environment",
    "shop_id",
    "credential_source",
    "sender_delivery_mode",
    "sender_office_code",
    "sender_city",
    "sender_post_code",
    "sender_address",
    "sender_quarter",
    "sender_street",
    "sender_num",
    "sender_other",
    "default_pack_count",
    "shipment_description",
    "declared_value_enabled",
    "default_payment_side",
    "return_parcel_destination",
    "days_until_return",
    "return_parcel_payment_side",
    "reject_action",
    "reject_payment_side",
    "reject_return_payment_side",
    "courier_currency",
    "currency_conversion_rate",
    "office_locator_enabled",
}

_BOOL_FIELDS = {
    "enabled",
    "declared_value_enabled",
    "office_locator_enabled",
}


def _get_row(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM econt_settings WHERE id = ?", (_SETTINGS_ID,)).fetchone()
    if row is None:
        conn.execute("INSERT OR IGNORE INTO econt_settings (id) VALUES (?)", (_SETTINGS_ID,))
        row = conn.execute("SELECT * FROM econt_settings WHERE id = ?", (_SETTINGS_ID,)).fetchone()
    return row


def _configured_secret(settings: Settings, row: sqlite3.Row) -> bool:
    if row["credential_source"] == "env":
        return bool(settings.econt_delivery_private_key.get_secret_value())
    # Stored encrypted secrets are intentionally not implemented before an app
    # encryption key and secret storage service exist.
    return False


def _effective_shop_id(settings: Settings, row: sqlite3.Row) -> str | None:
    return row["shop_id"] or settings.econt_delivery_shop_id or None


def _effective_base_url(settings: Settings, environment: str) -> str:
    if settings.econt_delivery_base_url:
        return settings.econt_delivery_base_url.rstrip("/") + "/"
    if environment == "production":
        return _PRODUCTION_BASE_URL
    return _DEMO_BASE_URL


def _effective_locator_url(settings: Settings, environment: str) -> str:
    if settings.econt_office_locator_url:
        return settings.econt_office_locator_url.strip()
    if environment == "production":
        return _PRODUCTION_LOCATOR_URL
    return _DEMO_LOCATOR_URL


def _effective_locator_origins(settings: Settings, environment: str) -> list[str]:
    if settings.econt_office_locator_origins:
        return settings.econt_office_locator_origins
    if environment == "production":
        return [_PRODUCTION_LOCATOR_ORIGIN]
    return [_DEMO_LOCATOR_ORIGIN]


def _secret_state(settings: Settings, row: sqlite3.Row) -> EcontSecretState:
    return EcontSecretState(
        credential_source=row["credential_source"],
        private_key_configured=_configured_secret(settings, row),
        shop_id_configured=bool(_effective_shop_id(settings, row)),
        encryption_key_configured=bool(settings.econt_secret_encryption_key.get_secret_value()),
    )


def _readiness(settings: Settings, row: sqlite3.Row) -> EcontReadiness:
    blockers: list[str] = []

    if not row["enabled"]:
        blockers.append("integration_disabled")
    if not _effective_shop_id(settings, row):
        blockers.append("shop_id_missing")
    if not _configured_secret(settings, row):
        blockers.append("private_key_missing")

    if row["sender_delivery_mode"] == "office" and not row["sender_office_code"]:
        blockers.append("sender_office_code_missing")
    if row["sender_delivery_mode"] == "door" and not (row["sender_city"] and row["sender_address"]):
        blockers.append("sender_address_missing")
    if row["courier_currency"] == "BGN" and not row["currency_conversion_rate"]:
        blockers.append("currency_conversion_rate_missing")

    return EcontReadiness(ready=not blockers, blockers=blockers)


def _row_to_response(row: sqlite3.Row, settings: Settings) -> EcontSettingsResponse:
    return EcontSettingsResponse(
        enabled=bool(row["enabled"]),
        environment=row["environment"],
        shop_id=row["shop_id"],
        credential_source=row["credential_source"],
        sender_delivery_mode=row["sender_delivery_mode"],
        sender_office_code=row["sender_office_code"],
        sender_city=row["sender_city"],
        sender_post_code=row["sender_post_code"],
        sender_address=row["sender_address"],
        sender_quarter=row["sender_quarter"],
        sender_street=row["sender_street"],
        sender_num=row["sender_num"],
        sender_other=row["sender_other"],
        default_pack_count=row["default_pack_count"],
        shipment_description=row["shipment_description"],
        declared_value_enabled=bool(row["declared_value_enabled"]),
        default_payment_side=row["default_payment_side"],
        return_parcel_destination=row["return_parcel_destination"],
        days_until_return=row["days_until_return"],
        return_parcel_payment_side=row["return_parcel_payment_side"],
        reject_action=row["reject_action"],
        reject_payment_side=row["reject_payment_side"],
        reject_return_payment_side=row["reject_return_payment_side"],
        courier_currency=row["courier_currency"],
        currency_conversion_rate=row["currency_conversion_rate"],
        office_locator_enabled=bool(row["office_locator_enabled"]),
        auto_confirm_on_label=False,
        auto_delivered_on_trace=False,
        base_url=_effective_base_url(settings, row["environment"]),
        office_locator_url=_effective_locator_url(settings, row["environment"]),
        office_locator_origins=_effective_locator_origins(settings, row["environment"]),
        secret_state=_secret_state(settings, row),
        last_health_status=row["last_health_status"],
        last_health_checked_at=row["last_health_checked_at"],
        last_health_error=row["last_health_error"],
        updated_at=row["updated_at"],
    )


def get_econt_settings() -> EcontSettingsResponse:
    """Read admin-safe Econt settings merged with env-backed secret state."""
    settings = get_settings()
    with get_db() as conn:
        row = _get_row(conn)
    return _row_to_response(row, settings)


def get_public_delivery_config() -> DeliveryConfigResponse:
    """Return public-safe delivery config for checkout."""
    settings = get_settings()
    with get_db() as conn:
        row = _get_row(conn)
    return DeliveryConfigResponse(
        econt=EcontCheckoutConfig(
            office_locator_enabled=bool(row["office_locator_enabled"]),
            office_locator_url=_effective_locator_url(settings, row["environment"]),
            office_locator_origins=_effective_locator_origins(settings, row["environment"]),
        )
    )


def update_econt_settings(body: EcontSettingsUpdate) -> EcontSettingsResponse:
    """Patch non-secret Econt settings."""
    data = body.model_dump(exclude_unset=True)
    updates: dict[str, Any] = {k: v for k, v in data.items() if k in _UPDATE_FIELDS}
    if not updates:
        return get_econt_settings()

    for field in _BOOL_FIELDS:
        if field in updates:
            updates[field] = 1 if updates[field] else 0

    settings = get_settings()
    with get_db() as conn:
        _get_row(conn)
        assignments = ", ".join(f"{field} = ?" for field in updates)
        params = [*updates.values(), pricing.now_utc(), _SETTINGS_ID]
        conn.execute(
            f"UPDATE econt_settings SET {assignments}, updated_at = ? WHERE id = ?",  # noqa: S608
            params,
        )
        row = _get_row(conn)

    logger.info("econt_settings_updated", fields=sorted(updates))
    return _row_to_response(row, settings)


async def test_econt_configuration() -> EcontConnectionTestResponse:
    """Validate current Econt configuration without creating a shipment."""
    settings = get_settings()
    checked_at = pricing.now_utc()

    with get_db() as conn:
        row = _get_row(conn)
        readiness = _readiness(settings, row)
        if not readiness.ready:
            status = "missing_configuration"
            message = "Econt configuration is incomplete."
            details: dict[str, Any] = {"blockers": readiness.blockers}
            _record_health(conn, status, checked_at, ",".join(readiness.blockers))
            return EcontConnectionTestResponse(
                status=status,
                ok=False,
                message=message,
                checked_at=checked_at,
                details=details,
            )

        base_url = _effective_base_url(settings, row["environment"])
        private_key = settings.econt_delivery_private_key.get_secret_value()
        shop_id = _effective_shop_id(settings, row) or ""

    try:
        await EcontDeliveryClient(
            base_url=base_url,
            private_key=private_key,
            shop_id=shop_id,
        ).test_connection()
    except EcontDeliveryError as exc:
        status = _connection_status_from_error(exc)
        message = _connection_message(status)
        safe_error = exc.to_safe_dict()
        details = {"blockers": [], "error": safe_error}
        with get_db() as conn:
            _record_health(conn, status, checked_at, str(exc))
        return EcontConnectionTestResponse(
            status=status,
            ok=False,
            message=message,
            checked_at=checked_at,
            details=details,
        )

    status = "success"
    message = "Econt configuration reached the safe API validation path."
    details = {"blockers": []}
    with get_db() as conn:
        _record_health(conn, status, checked_at, None)
    return EcontConnectionTestResponse(
        status=status,
        ok=True,
        message=message,
        checked_at=checked_at,
        details=details,
    )


def _record_health(
    conn: sqlite3.Connection,
    status: str,
    checked_at: str,
    error: str | None,
) -> None:
    conn.execute(
        """
        UPDATE econt_settings
        SET last_health_status = ?, last_health_checked_at = ?, last_health_error = ?
        WHERE id = ?
        """,
        (status, checked_at, error, _SETTINGS_ID),
    )


def _connection_status_from_error(exc: EcontDeliveryError) -> str:
    if exc.category == "auth":
        return "authentication_failed"
    if exc.category == "validation":
        return "validation_failed"
    if exc.category == "config":
        return "missing_configuration"
    if exc.category == "transient" and "timed out" in str(exc).casefold():
        return "timeout"
    return "service_outage"


def _connection_message(status: str) -> str:
    messages = {
        "authentication_failed": "Econt authentication failed.",
        "validation_failed": "Econt rejected the connection test request.",
        "missing_configuration": "Econt configuration is incomplete.",
        "timeout": "Econt connection test timed out.",
        "service_outage": "Econt service is unavailable or returned an unexpected response.",
    }
    return messages.get(status, "Econt connection test failed.")
