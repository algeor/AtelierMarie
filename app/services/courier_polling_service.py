"""Async courier status polling with database-backed leases."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import get_settings
from app.database import get_db
from app.services import econt_fulfillment_service, speedy_admin_service
from app.services.econt_delivery_client import EcontDeliveryError
from app.services.econt_fulfillment_service import EcontFulfillmentError
from app.services.econt_redaction import redact_mapping
from app.services.pricing import CANONICAL_DT_FMT, now_utc
from app.services.speedy_admin_service import SpeedyAdminError
from app.services.speedy_client import SpeedyError


class CourierPollingError(Exception):
    """Base class for courier polling errors."""


class CourierPollingValidationError(CourierPollingError):
    """Raised when an order cannot be refreshed through courier polling."""

    def __init__(self, message: str, *, blockers: list[str] | None = None) -> None:
        self.blockers = blockers or []
        super().__init__(message)


def _after(seconds: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=seconds)).strftime(CANONICAL_DT_FMT)


def _provider_for(row: sqlite3.Row) -> str | None:
    provider = row["courier_provider"] or row["tracking_carrier"] or row["delivery_courier"]
    return provider if provider in {"speedy", "econt"} else None


def _safe_error(exc: Exception) -> dict[str, Any]:
    if hasattr(exc, "to_safe_dict"):
        return redact_mapping(exc.to_safe_dict())  # type: ignore[no-any-return, attr-defined]
    validation_error = isinstance(
        exc,
        (CourierPollingValidationError, EcontFulfillmentError, SpeedyAdminError),
    )
    payload: dict[str, Any] = {
        "category": "validation" if validation_error else "unexpected",
        "message": str(exc),
    }
    blockers = getattr(exc, "blockers", None)
    if blockers:
        payload["blockers"] = list(blockers)
    return redact_mapping(payload)


def _enabled_providers() -> set[str]:
    settings = get_settings()
    providers: set[str] = set()
    if settings.courier_polling_speedy_enabled:
        providers.add("speedy")
    if settings.courier_polling_econt_enabled:
        providers.add("econt")
    return providers


def _identifier(row: sqlite3.Row) -> str | None:
    return row["courier_shipment_number"] or row["tracking_number"]


def _select_due_candidates(
    conn: sqlite3.Connection,
    *,
    providers: set[str],
    batch_size: int,
    now: str,
) -> list[sqlite3.Row]:
    if not providers or batch_size < 1:
        return []
    placeholders = ",".join("?" for _ in providers)
    params: list[Any] = [*sorted(providers), now, now, batch_size]
    return conn.execute(
        f"""
        SELECT id, status, delivery_courier, tracking_carrier, tracking_number,
               tracking_url, courier_provider, courier_shipment_number,
               courier_poll_attempts
        FROM orders
        WHERE COALESCE(courier_provider, tracking_carrier, delivery_courier) IN ({placeholders})
          AND status IN ('shipped', 'return_in_transit')
          AND COALESCE(courier_shipment_number, tracking_number) IS NOT NULL
          AND (courier_next_poll_at IS NULL OR courier_next_poll_at <= ?)
          AND (courier_poll_lease_expires_at IS NULL OR courier_poll_lease_expires_at <= ?)
        ORDER BY COALESCE(courier_next_poll_at, created_at), created_at, id
        LIMIT ?
        """,  # noqa: S608 - placeholders are generated from trusted provider count.
        params,
    ).fetchall()


def acquire_due_orders(
    conn: sqlite3.Connection,
    *,
    batch_size: int | None = None,
    lease_seconds: int | None = None,
    providers: set[str] | None = None,
) -> list[sqlite3.Row]:
    """Acquire durable polling leases for due active courier shipments."""
    settings = get_settings()
    if not settings.courier_polling_enabled:
        return []
    now = now_utc()
    lease_until = _after(lease_seconds or settings.courier_polling_lease_seconds)
    acquired: list[sqlite3.Row] = []
    for row in _select_due_candidates(
        conn,
        providers=providers or _enabled_providers(),
        batch_size=batch_size or settings.courier_polling_batch_size,
        now=now,
    ):
        token = uuid.uuid4().hex
        cursor = conn.execute(
            """
            UPDATE orders
            SET courier_poll_lease_token = ?, courier_poll_lease_expires_at = ?
            WHERE id = ?
              AND (courier_poll_lease_expires_at IS NULL OR courier_poll_lease_expires_at <= ?)
            """,
            (token, lease_until, row["id"], now),
        )
        if cursor.rowcount:
            conn.commit()
            acquired.append(row)
    return acquired


async def _refresh_provider(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    *,
    actor_user_id: str | None,
    speedy_track_func: Any | None = None,
    econt_client: Any | None = None,
) -> dict[str, Any]:
    provider = _provider_for(row)
    if provider == "speedy":
        return await speedy_admin_service.refresh_tracking(
            conn,
            row["id"],
            actor_user_id=actor_user_id,
            track_shipment_func=speedy_track_func,
        )
    if provider == "econt":
        return await econt_fulfillment_service.refresh_trace(
            conn,
            row["id"],
            actor_user_id=actor_user_id,
            client=econt_client,
        )
    raise CourierPollingValidationError(
        "Order has no supported courier provider",
        blockers=["courier_provider_missing"],
    )


def _mark_success(conn: sqlite3.Connection, order_id: str, *, interval_seconds: int) -> None:
    now = now_utc()
    conn.execute(
        """
        UPDATE orders
        SET courier_last_polled_at = ?, courier_next_poll_at = ?, courier_poll_attempts = 0,
            courier_poll_lease_token = NULL, courier_poll_lease_expires_at = NULL
        WHERE id = ?
        """,
        (now, _after(interval_seconds), order_id),
    )


def _mark_failure(
    conn: sqlite3.Connection,
    order_id: str,
    exc: Exception,
    *,
    interval_seconds: int,
    max_backoff_seconds: int,
) -> None:
    row = conn.execute(
        "SELECT courier_poll_attempts FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    attempts = int(row["courier_poll_attempts"] or 0) + 1 if row else 1
    backoff = min(interval_seconds * (2 ** min(attempts - 1, 6)), max_backoff_seconds)
    now = now_utc()
    conn.execute(
        """
        UPDATE orders
        SET courier_sync_status = 'poll_failed', courier_last_error = ?,
            courier_last_polled_at = ?, courier_next_poll_at = ?,
            courier_poll_attempts = ?, courier_poll_lease_token = NULL,
            courier_poll_lease_expires_at = NULL
        WHERE id = ?
        """,
        (
            json.dumps(_safe_error(exc), ensure_ascii=False, sort_keys=True),
            now,
            _after(backoff),
            attempts,
            order_id,
        ),
    )


async def poll_due_shipments(
    conn: sqlite3.Connection,
    *,
    batch_size: int | None = None,
    providers: set[str] | None = None,
    actor_user_id: str | None = None,
    speedy_track_func: Any | None = None,
    econt_client: Any | None = None,
) -> dict[str, int]:
    """Poll due active Speedy/Econt shipments and store evidence only."""
    settings = get_settings()
    rows = acquire_due_orders(
        conn,
        batch_size=batch_size or settings.courier_polling_batch_size,
        lease_seconds=settings.courier_polling_lease_seconds,
        providers=providers,
    )
    result = {"acquired": len(rows), "succeeded": 0, "failed": 0, "skipped": 0}
    for row in rows:
        if not _identifier(row):
            result["skipped"] += 1
            continue
        try:
            await _refresh_provider(
                conn,
                row,
                actor_user_id=actor_user_id,
                speedy_track_func=speedy_track_func,
                econt_client=econt_client,
            )
        except (
            CourierPollingValidationError,
            EcontDeliveryError,
            EcontFulfillmentError,
            SpeedyError,
            SpeedyAdminError,
        ) as exc:
            _mark_failure(
                conn,
                row["id"],
                exc,
                interval_seconds=settings.courier_polling_interval_seconds,
                max_backoff_seconds=settings.courier_polling_max_backoff_seconds,
            )
            conn.commit()
            result["failed"] += 1
            continue
        _mark_success(conn, row["id"], interval_seconds=settings.courier_polling_interval_seconds)
        conn.commit()
        result["succeeded"] += 1
    return result


async def poll_due_shipments_from_settings() -> dict[str, int]:
    """Open a DB connection and poll due shipments for the background loop."""
    with get_db() as conn:
        return await poll_due_shipments(conn)


async def refresh_order_now(
    conn: sqlite3.Connection,
    order_id: str,
    *,
    provider: str | None = None,
    actor_user_id: str | None = None,
    speedy_track_func: Any | None = None,
    econt_client: Any | None = None,
) -> dict[str, Any]:
    """Manually refresh one order through the same async provider path."""
    row = conn.execute(
        """
        SELECT id, status, delivery_courier, tracking_carrier, tracking_number,
               tracking_url, courier_provider, courier_shipment_number,
               courier_poll_attempts
        FROM orders
        WHERE id = ?
        """,
        (order_id,),
    ).fetchone()
    if row is None:
        raise CourierPollingValidationError("Order not found", blockers=["order_not_found"])
    detected_provider = _provider_for(row)
    if provider and detected_provider and provider != detected_provider:
        raise CourierPollingValidationError(
            "Order courier provider does not match manual refresh provider",
            blockers=["courier_provider_mismatch"],
        )
    if provider and not detected_provider:
        conn.execute("UPDATE orders SET courier_provider = ? WHERE id = ?", (provider, order_id))
        row = conn.execute(
            """
            SELECT id, status, delivery_courier, tracking_carrier, tracking_number,
                   tracking_url, courier_provider, courier_shipment_number,
                   courier_poll_attempts
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
    try:
        payload = await _refresh_provider(
            conn,
            row,
            actor_user_id=actor_user_id,
            speedy_track_func=speedy_track_func,
            econt_client=econt_client,
        )
    except (
        CourierPollingValidationError,
        EcontDeliveryError,
        EcontFulfillmentError,
        SpeedyError,
        SpeedyAdminError,
    ) as exc:
        settings = get_settings()
        _mark_failure(
            conn,
            order_id,
            exc,
            interval_seconds=settings.courier_polling_interval_seconds,
            max_backoff_seconds=settings.courier_polling_max_backoff_seconds,
        )
        raise
    _mark_success(
        conn,
        order_id,
        interval_seconds=get_settings().courier_polling_interval_seconds,
    )
    return payload
