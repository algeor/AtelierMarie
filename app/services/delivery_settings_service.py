"""Admin-managed availability switches for courier delivery methods."""

import sqlite3

import structlog

from app.database import get_db
from app.models.delivery import Courier, DeliveryMethod
from app.models.orders import PaymentMethod
from app.services import pricing

logger = structlog.get_logger(__name__)

_SETTINGS_ID = "default"


def _row_to_settings(row: sqlite3.Row) -> dict:
    return {
        "speedy_office_enabled": bool(row["speedy_office_enabled"]),
        "speedy_door_enabled": bool(row["speedy_door_enabled"]),
        "econt_office_enabled": bool(row["econt_office_enabled"]),
        "econt_door_enabled": bool(row["econt_door_enabled"]),
        "cod_enabled": bool(row["cod_enabled"]),
        "card_enabled": bool(row["card_enabled"]),
        "bank_transfer_enabled": bool(row["bank_transfer_enabled"]),
        "updated_at": row["updated_at"],
    }


def _get_row(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM delivery_settings WHERE id = ?",
        (_SETTINGS_ID,),
    ).fetchone()
    if row is None:
        conn.execute(
            """
            INSERT OR IGNORE INTO delivery_settings (
                id, speedy_office_enabled, speedy_door_enabled,
                econt_office_enabled, econt_door_enabled,
                cod_enabled, card_enabled, bank_transfer_enabled, updated_at
            ) VALUES (?, 1, 1, 1, 1, 1, 1, 1, ?)
            """,
            (_SETTINGS_ID, pricing.now_utc()),
        )
        row = conn.execute(
            "SELECT * FROM delivery_settings WHERE id = ?",
            (_SETTINGS_ID,),
        ).fetchone()
    return row


def get_delivery_settings() -> dict:
    """Return current delivery-method availability settings."""
    with get_db() as conn:
        row = _get_row(conn)
    return _row_to_settings(row)


def update_delivery_settings(data: dict) -> dict:
    """Persist all delivery-method availability switches."""
    now = pricing.now_utc()
    with get_db() as conn:
        _get_row(conn)
        conn.execute(
            """
            UPDATE delivery_settings
            SET speedy_office_enabled = ?, speedy_door_enabled = ?,
                econt_office_enabled = ?, econt_door_enabled = ?,
                cod_enabled = ?, card_enabled = ?, bank_transfer_enabled = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                1 if data.get("speedy_office_enabled") else 0,
                1 if data.get("speedy_door_enabled") else 0,
                1 if data.get("econt_office_enabled") else 0,
                1 if data.get("econt_door_enabled") else 0,
                1 if data.get("cod_enabled") else 0,
                1 if data.get("card_enabled") else 0,
                1 if data.get("bank_transfer_enabled") else 0,
                now,
                _SETTINGS_ID,
            ),
        )
        row = _get_row(conn)

    settings = _row_to_settings(row)
    logger.info(
        "delivery_settings_updated",
        speedy_office_enabled=settings["speedy_office_enabled"],
        speedy_door_enabled=settings["speedy_door_enabled"],
        econt_office_enabled=settings["econt_office_enabled"],
        econt_door_enabled=settings["econt_door_enabled"],
        cod_enabled=settings["cod_enabled"],
        card_enabled=settings["card_enabled"],
        bank_transfer_enabled=settings["bank_transfer_enabled"],
    )
    return settings


def is_delivery_method_enabled(courier: Courier, method: DeliveryMethod) -> bool:
    """True when the given courier/method pair is currently available."""
    settings = get_delivery_settings()
    return bool(settings[f"{courier}_{method}_enabled"])


def is_payment_method_enabled(payment_method: PaymentMethod) -> bool:
    """True when the given payment method is currently available."""
    settings = get_delivery_settings()
    return bool(settings[f"{payment_method}_enabled"])


def disabled_requested_methods(couriers: list[Courier], method: DeliveryMethod) -> list[dict]:
    """Return disabled courier/method pairs from a public quote request."""
    settings = get_delivery_settings()
    return [
        {"courier": courier, "method": method}
        for courier in couriers
        if not settings[f"{courier}_{method}_enabled"]
    ]
