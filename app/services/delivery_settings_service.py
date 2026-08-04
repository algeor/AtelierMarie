"""Admin-managed availability switches for courier delivery methods."""

from datetime import datetime

import psycopg
import structlog

from app.database import get_db
from app.models.delivery import Courier, DeliveryMethod
from app.services import pricing

logger = structlog.get_logger(__name__)

# Mirror of ``order_service._fmt_ts``/``_DT_FMT`` to avoid a circular import
# (order_service imports this module at its top level, Decision 15).
_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _fmt_ts(value: object) -> str | None:
    """Render a TIMESTAMPTZ column read as the canonical ``_DT_FMT`` string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime(_DT_FMT)
    return str(value)


_SETTINGS_ID = "default"


def _row_to_settings(row: dict) -> dict:
    return {
        "speedy_office_enabled": bool(row["speedy_office_enabled"]),
        "speedy_door_enabled": bool(row["speedy_door_enabled"]),
        "econt_office_enabled": bool(row["econt_office_enabled"]),
        "econt_door_enabled": bool(row["econt_door_enabled"]),
        "cod_enabled": bool(row["cod_enabled"]),
        "card_enabled": bool(row["card_enabled"]),
        "bank_transfer_enabled": bool(row["bank_transfer_enabled"]),
        "updated_at": _fmt_ts(row["updated_at"]),
    }


def _get_row(conn: psycopg.Connection) -> dict:
    row = conn.execute(
        "SELECT * FROM delivery_settings WHERE id = %s",
        (_SETTINGS_ID,),
    ).fetchone()
    if row is None:
        conn.execute(
            """
            INSERT INTO delivery_settings (
                id, speedy_office_enabled, speedy_door_enabled,
                econt_office_enabled, econt_door_enabled,
                cod_enabled, card_enabled, bank_transfer_enabled, updated_at
            ) VALUES (%s, 1, 1, 1, 1, 1, 1, 1, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (_SETTINGS_ID, pricing.now_utc()),
        )
        row = conn.execute(
            "SELECT * FROM delivery_settings WHERE id = %s",
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
            SET speedy_office_enabled = %s, speedy_door_enabled = %s,
                econt_office_enabled = %s, econt_door_enabled = %s,
                cod_enabled = %s, card_enabled = %s, bank_transfer_enabled = %s,
                updated_at = %s
            WHERE id = %s
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


def disabled_requested_methods(couriers: list[Courier], method: DeliveryMethod) -> list[dict]:
    """Return disabled courier/method pairs from a public quote request."""
    settings = get_delivery_settings()
    return [
        {"courier": courier, "method": method}
        for courier in couriers
        if not settings[f"{courier}_{method}_enabled"]
    ]
