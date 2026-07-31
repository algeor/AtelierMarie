"""Payment settings stored in DB; Stripe secrets stay in environment."""

import json
import sqlite3
from typing import Any

from app.config import Settings

DEFAULT_PAY_ON_DELIVERY_MAX_CENTS = 5000

_DEFAULT_SETTINGS: dict[str, Any] = {
    "card_payments_enabled": False,
    "pay_on_delivery_enabled": True,
    "pay_on_delivery_max_cents": DEFAULT_PAY_ON_DELIVERY_MAX_CENTS,
}


class PaymentSettingsError(Exception):
    """Base payment settings exception."""


class PaymentSettingsValidationError(PaymentSettingsError):
    """Raised when an admin settings update is invalid."""


def stripe_mode(secret_key: str) -> str:
    """Return a safe Stripe mode label from the secret key prefix."""
    if not secret_key:
        return "not_configured"
    if secret_key.startswith("sk_test_"):
        return "test"
    if secret_key.startswith("sk_live_"):
        return "live"
    return "unknown"


def stripe_config_health(settings: Settings) -> dict[str, Any]:
    """Return non-secret Stripe configuration health for admins/settings gates."""
    mode = stripe_mode(settings.stripe_secret_key)
    problems: list[str] = []

    if not settings.stripe_secret_key:
        problems.append("STRIPE_SECRET_KEY is missing")
    elif mode == "unknown":
        problems.append("STRIPE_SECRET_KEY has an unrecognized prefix")

    if not settings.stripe_webhook_secret:
        problems.append("STRIPE_WEBHOOK_SECRET is missing")

    if not settings.stripe_success_url:
        problems.append("STRIPE_SUCCESS_URL is missing")

    if not settings.stripe_cancel_url:
        problems.append("STRIPE_CANCEL_URL is missing")

    if settings.environment == "production" and mode != "live":
        problems.append("Production card payments require a live Stripe secret key")

    ready = not problems
    return {
        "mode": mode,
        "secret_key_configured": bool(settings.stripe_secret_key),
        "webhook_secret_configured": bool(settings.stripe_webhook_secret),
        "publishable_key_configured": bool(settings.stripe_publishable_key),
        "ready_for_card_payments": ready,
        "problems": problems,
    }


def _encode(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _decode(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def ensure_payment_settings(conn: sqlite3.Connection) -> None:
    """Insert default payment settings if missing."""
    for key, value in _DEFAULT_SETTINGS.items():
        conn.execute(
            """
            INSERT OR IGNORE INTO site_settings (key, value, value_type, is_public)
            VALUES (?, ?, 'json', 1)
            """,
            (key, _encode(value)),
        )


def get_payment_settings(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return payment settings, applying DB defaults lazily."""
    ensure_payment_settings(conn)
    rows = conn.execute(
        "SELECT key, value FROM site_settings WHERE key IN (?, ?, ?)",
        tuple(_DEFAULT_SETTINGS.keys()),
    ).fetchall()
    values = dict(_DEFAULT_SETTINGS)
    for row in rows:
        values[row["key"]] = _decode(row["value"], _DEFAULT_SETTINGS[row["key"]])
    return values


def validate_payment_settings_update(data: dict[str, Any], settings: Settings) -> None:
    """Validate admin-editable payment settings."""
    if not data["card_payments_enabled"] and not data["pay_on_delivery_enabled"]:
        raise PaymentSettingsValidationError("At least one payment method must be enabled")

    if data["pay_on_delivery_max_cents"] > DEFAULT_PAY_ON_DELIVERY_MAX_CENTS:
        raise PaymentSettingsValidationError("Pay-on-delivery max amount cannot exceed EUR 50")

    if data["card_payments_enabled"]:
        health = stripe_config_health(settings)
        if not health["ready_for_card_payments"]:
            problems = "; ".join(health["problems"])
            raise PaymentSettingsValidationError(f"Card payments cannot be enabled: {problems}")


def update_payment_settings(
    conn: sqlite3.Connection,
    data: dict[str, Any],
    settings: Settings,
    *,
    admin_id: str | None,
    admin_email: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    """Persist payment settings and append one audit event per changed key."""
    validate_payment_settings_update(data, settings)
    current = get_payment_settings(conn)

    for key in _DEFAULT_SETTINGS:
        old_value = current[key]
        new_value = data[key]
        if old_value == new_value:
            continue
        conn.execute(
            """
            UPDATE site_settings
            SET value = ?, value_type = 'json', is_public = 1
            WHERE key = ?
            """,
            (_encode(new_value), key),
        )
        conn.execute(
            """
            INSERT INTO site_setting_events (
                setting_key, old_value, new_value, admin_id, admin_email, request_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (key, _encode(old_value), _encode(new_value), admin_id, admin_email, request_id),
        )

    return get_payment_settings(conn)


def public_payment_settings(
    conn: sqlite3.Connection,
    settings: Settings,
) -> dict[str, Any]:
    """Return safe checkout-facing payment method availability."""
    values = get_payment_settings(conn)
    card_enabled = bool(values["card_payments_enabled"]) and bool(
        stripe_config_health(settings)["ready_for_card_payments"]
    )
    cod_enabled = bool(values["pay_on_delivery_enabled"])
    bank_enabled = bool(settings.bank_iban)
    methods: list[str] = []
    if card_enabled:
        methods.append("card")
    if cod_enabled:
        methods.append("cod")
    if bank_enabled:
        methods.append("bank_transfer")
    return {
        "card_payments_enabled": card_enabled,
        "pay_on_delivery_enabled": cod_enabled,
        "pay_on_delivery_max_cents": int(values["pay_on_delivery_max_cents"]),
        "bank_transfer_enabled": bank_enabled,
        "available_payment_methods": methods,
    }


def payment_method_available(
    conn: sqlite3.Connection,
    settings: Settings,
    payment_method: str,
) -> bool:
    """Return whether a submitted payment method is currently checkout-available."""
    values = get_payment_settings(conn)
    if payment_method == "card":
        return bool(values["card_payments_enabled"]) and bool(
            stripe_config_health(settings)["ready_for_card_payments"]
        )
    if payment_method == "cod":
        return bool(values["pay_on_delivery_enabled"])
    if payment_method == "bank_transfer":
        return bool(settings.bank_iban)
    return False
