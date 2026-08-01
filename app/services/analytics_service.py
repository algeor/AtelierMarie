"""First-party analytics validation, storage, and aggregate reporting."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import structlog

from app.config import get_settings
from app.database import get_db
from app.models.analytics import (
    AnalyticsEventRequest,
    AnalyticsEventType,
    AnalyticsFunnelStep,
    AnalyticsHealthResponse,
)

logger = structlog.get_logger(__name__)

FUNNEL_SEQUENCE: tuple[AnalyticsEventType, ...] = (
    AnalyticsEventType.PRODUCT_VIEW,
    AnalyticsEventType.LISTING_FILTER,
    AnalyticsEventType.ADD_TO_CART,
    AnalyticsEventType.CART_OPEN,
    AnalyticsEventType.CHECKOUT_START,
    AnalyticsEventType.DELIVERY_SELECTED,
    AnalyticsEventType.SHIPPING_QUOTE_SELECTED,
    AnalyticsEventType.ORDER_SUBMIT,
    AnalyticsEventType.PAYMENT_REDIRECT,
    AnalyticsEventType.PURCHASE_CONFIRMED,
)

PROPERTY_ALLOWLIST: dict[AnalyticsEventType, set[str]] = {
    AnalyticsEventType.PRODUCT_VIEW: {"product_id", "category", "currency", "value_cents"},
    AnalyticsEventType.LISTING_FILTER: {"filter_name", "filter_value", "category", "sort"},
    AnalyticsEventType.ADD_TO_CART: {"product_id", "quantity", "currency", "value_cents"},
    AnalyticsEventType.CART_OPEN: {"item_count", "currency", "value_cents"},
    AnalyticsEventType.CHECKOUT_START: {"item_count", "currency", "value_cents"},
    AnalyticsEventType.DELIVERY_SELECTED: {"delivery_method", "delivery_courier"},
    AnalyticsEventType.SHIPPING_QUOTE_SELECTED: {
        "delivery_method",
        "delivery_courier",
        "quote_cents",
        "currency",
    },
    AnalyticsEventType.ORDER_SUBMIT: {
        "payment_method",
        "delivery_method",
        "currency",
        "value_cents",
    },
    AnalyticsEventType.PAYMENT_REDIRECT: {
        "order_id",
        "payment_method",
        "payment_provider",
        "currency",
        "value_cents",
    },
    AnalyticsEventType.PURCHASE_CONFIRMED: {
        "order_id",
        "payment_method",
        "delivery_method",
        "delivery_courier",
        "currency",
        "value_cents",
    },
}

PII_KEY_FRAGMENTS = {
    "email",
    "phone",
    "name",
    "address",
    "street",
    "city",
    "note",
    "comment",
    "ip",
    "user_agent",
    "card",
    "iban",
}

STRING_VALUE_MAX_LENGTH = 160
MAX_PROPERTIES = 16
MAX_EVENT_BYTES = 8192


class AnalyticsValidationError(ValueError):
    """Raised when an analytics event violates the first-party contract."""


def _duckdb_connect(path: str):
    import duckdb

    return duckdb.connect(path)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _date_bounds(start_date: str | None, end_date: str | None) -> tuple[str, str]:
    end = datetime.now(UTC).date() if end_date is None else datetime.fromisoformat(end_date).date()
    start = (
        end - timedelta(days=30)
        if start_date is None
        else datetime.fromisoformat(start_date).date()
    )
    end_exclusive = end + timedelta(days=1)
    return start.isoformat(), end_exclusive.isoformat()


def record_consent(
    *,
    session_id: str,
    analytics: bool,
    consent_version: str,
    locale: str,
) -> None:
    """Persist the current server-side analytics consent for a session."""
    settings = get_settings()
    if consent_version != settings.analytics_consent_version:
        raise AnalyticsValidationError("analytics consent version is not current")
    normalized_locale = locale if locale in {"en", "bg"} else "en"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO analytics_consents (
                session_id, analytics, consent_version, locale, updated_at
            ) VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(session_id) DO UPDATE SET
                analytics = excluded.analytics,
                consent_version = excluded.consent_version,
                locale = excluded.locale,
                updated_at = datetime('now')
            """,
            (session_id, 1 if analytics else 0, consent_version, normalized_locale),
        )


def has_current_analytics_consent(session_id: str) -> bool:
    """Return True only when the server has current analytics consent."""
    settings = get_settings()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT analytics FROM analytics_consents
            WHERE session_id = ? AND consent_version = ?
            """,
            (session_id, settings.analytics_consent_version),
        ).fetchone()
    return bool(row and row["analytics"])


def _display_range(start_date: str | None, end_date: str | None) -> tuple[str, str]:
    start, end_exclusive = _date_bounds(start_date, end_date)
    end = (datetime.fromisoformat(end_exclusive).date() - timedelta(days=1)).isoformat()
    return start, end


def initialize_storage() -> None:
    """Initialize analytics JSONL/DuckDB storage when analytics is enabled."""
    settings = get_settings()
    Path(settings.analytics_data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.analytics_events_jsonl_path).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.analytics_duckdb_path).parent.mkdir(parents=True, exist_ok=True)

    with _duckdb_connect(settings.analytics_duckdb_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_events (
                event_id VARCHAR NOT NULL,
                session_id VARCHAR NOT NULL,
                user_id VARCHAR,
                event_type VARCHAR NOT NULL,
                occurred_at TIMESTAMP NOT NULL,
                received_at TIMESTAMP NOT NULL,
                locale VARCHAR NOT NULL,
                page_path VARCHAR,
                properties_json VARCHAR NOT NULL,
                product_id VARCHAR,
                order_id VARCHAR,
                value_cents BIGINT,
                currency VARCHAR,
                payment_method VARCHAR,
                delivery_method VARCHAR,
                delivery_courier VARCHAR,
                anonymized BOOLEAN NOT NULL DEFAULT false
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_event_id_session
            ON analytics_events(event_id, session_id)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_delivery_health (
                metric VARCHAR PRIMARY KEY,
                value BIGINT NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_state (
                key VARCHAR PRIMARY KEY,
                value VARCHAR NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        for metric in ("accepted", "rejected", "duplicate", "validation_failure"):
            conn.execute(
                """
                INSERT INTO analytics_delivery_health
                SELECT ?, 0, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM analytics_delivery_health WHERE metric = ?
                )
                """,
                (metric, _utc_now(), metric),
            )
    load_jsonl_to_duckdb()


def _set_state(key: str, value: str) -> None:
    settings = get_settings()
    with _duckdb_connect(settings.analytics_duckdb_path) as conn:
        conn.execute("DELETE FROM analytics_state WHERE key = ?", (key,))
        conn.execute("INSERT INTO analytics_state VALUES (?, ?, ?)", (key, value, _utc_now()))


def _increment_metric(metric: str, amount: int = 1) -> None:
    settings = get_settings()
    try:
        initialize_storage()
        with _duckdb_connect(settings.analytics_duckdb_path) as conn:
            conn.execute(
                """
                INSERT INTO analytics_delivery_health
                SELECT ?, 0, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM analytics_delivery_health WHERE metric = ?
                )
                """,
                (metric, _utc_now(), metric),
            )
            conn.execute(
                """
                UPDATE analytics_delivery_health
                SET value = value + ?, updated_at = ?
                WHERE metric = ?
                """,
                (amount, _utc_now(), metric),
            )
    except Exception:
        logger.exception("analytics_metric_update_failed", metric=metric)


def _validate_properties(event: AnalyticsEventRequest) -> dict[str, Any]:
    raw = event.properties or {}
    encoded_size = len(json.dumps(raw, ensure_ascii=False).encode("utf-8"))
    if encoded_size > MAX_EVENT_BYTES:
        raise AnalyticsValidationError("analytics properties exceed payload limit")
    if len(raw) > MAX_PROPERTIES:
        raise AnalyticsValidationError("analytics properties exceed key limit")

    allowed = PROPERTY_ALLOWLIST[event.event_type]
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        normalized_key = key.lower()
        if normalized_key not in allowed:
            raise AnalyticsValidationError(f"unknown analytics property: {key}")
        if any(fragment in normalized_key for fragment in PII_KEY_FRAGMENTS):
            raise AnalyticsValidationError(f"PII-like analytics property rejected: {key}")
        if isinstance(value, str):
            if len(value) > STRING_VALUE_MAX_LENGTH:
                raise AnalyticsValidationError(f"analytics property too long: {key}")
            if "@" in value or "\n" in value or "\r" in value:
                raise AnalyticsValidationError(f"PII-like analytics value rejected: {key}")
            cleaned[normalized_key] = value
        elif isinstance(value, bool):
            cleaned[normalized_key] = value
        elif isinstance(value, int | float):
            cleaned[normalized_key] = value
        elif value is None:
            cleaned[normalized_key] = None
        else:
            raise AnalyticsValidationError(f"unsupported analytics property value: {key}")
    return cleaned


def _normalized_event(
    event: AnalyticsEventRequest,
    *,
    session_id: str,
    user_id: str | None,
) -> dict[str, Any]:
    properties = _validate_properties(event)
    occurred_at = event.occurred_at.astimezone(UTC).replace(microsecond=0).isoformat()
    return {
        "event_id": event.event_id,
        "session_id": session_id,
        "user_id": user_id,
        "event_type": event.event_type.value,
        "occurred_at": occurred_at,
        "received_at": _utc_now(),
        "locale": event.locale,
        "page_path": event.page_path,
        "properties": properties,
        "product_id": properties.get("product_id"),
        "order_id": properties.get("order_id"),
        "value_cents": properties.get("value_cents"),
        "currency": properties.get("currency"),
        "payment_method": properties.get("payment_method"),
        "delivery_method": properties.get("delivery_method"),
        "delivery_courier": properties.get("delivery_courier"),
    }


def _event_exists(event_id: str, session_id: str) -> bool:
    settings = get_settings()
    initialize_storage()
    with _duckdb_connect(settings.analytics_duckdb_path) as conn:
        row = conn.execute(
            """
            SELECT 1 FROM analytics_events
            WHERE event_id = ? AND session_id = ?
            LIMIT 1
            """,
            (event_id, session_id),
        ).fetchone()
    return row is not None


def _append_jsonl(event: dict[str, Any]) -> None:
    settings = get_settings()
    path = Path(settings.analytics_events_jsonl_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _insert_duckdb(event: dict[str, Any]) -> None:
    settings = get_settings()
    anonymized = bool(event.get("anonymized", False))
    with _duckdb_connect(settings.analytics_duckdb_path) as conn:
        conn.execute(
            """
            INSERT INTO analytics_events
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM analytics_events WHERE event_id = ? AND session_id = ?
            )
            """,
            (
                event["event_id"],
                event["session_id"],
                event["user_id"],
                event["event_type"],
                event["occurred_at"],
                event["received_at"],
                event["locale"],
                event["page_path"],
                json.dumps(event["properties"], ensure_ascii=False, sort_keys=True),
                event["product_id"],
                event["order_id"],
                event["value_cents"],
                event["currency"],
                event["payment_method"],
                event["delivery_method"],
                event["delivery_courier"],
                anonymized,
                event["event_id"],
                event["session_id"],
            ),
        )
    _set_state("last_successful_flush_at", _utc_now())
    _set_state("duckdb_load_status", "ok")


def ingest_events(
    events: list[AnalyticsEventRequest],
    *,
    session_id: str | None,
    user_id: str | None = None,
    consent_verified: bool = False,
) -> dict[str, int | bool]:
    """Validate and persist a public analytics batch."""
    settings = get_settings()
    if not settings.analytics_enabled:
        return {"accepted": 0, "duplicates": 0, "disabled": True}
    if session_id is None:
        _increment_metric("rejected")
        _increment_metric("validation_failure")
        raise AnalyticsValidationError("session is required for analytics")
    if len(events) > settings.analytics_batch_size:
        _increment_metric("rejected")
        _increment_metric("validation_failure")
        raise AnalyticsValidationError("analytics batch exceeds configured limit")

    for event in events:
        _validate_properties(event)
    if not consent_verified:
        _increment_metric("rejected")
        return {"accepted": 0, "duplicates": 0, "disabled": True}

    accepted = 0
    duplicates = 0
    normalized: list[dict[str, Any]] = []
    seen_in_batch: set[str] = set()
    for event in events:
        if event.event_id in seen_in_batch or _event_exists(event.event_id, session_id):
            duplicates += 1
            continue
        seen_in_batch.add(event.event_id)
        normalized.append(_normalized_event(event, session_id=session_id, user_id=user_id))

    for normalized_event in normalized:
        _append_jsonl(normalized_event)
        _insert_duckdb(normalized_event)
        accepted += 1

    if accepted:
        _increment_metric("accepted", accepted)
    if duplicates:
        _increment_metric("duplicate", duplicates)
    return {"accepted": accepted, "duplicates": duplicates, "disabled": False}


def load_jsonl_to_duckdb() -> int:
    """Load missing JSONL events into DuckDB; JSONL remains source of truth."""
    settings = get_settings()
    path = Path(settings.analytics_events_jsonl_path)
    if not path.exists():
        _set_state("duckdb_load_status", "ok")
        return 0

    loaded = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                _insert_duckdb(json.loads(line))
                loaded += 1
            except Exception:
                _set_state("duckdb_load_status", "failed")
                logger.exception("analytics_jsonl_load_failed")
                raise
    _set_state("duckdb_load_status", "ok")
    return loaded


def rebuild_duckdb_from_jsonl() -> int:
    """Recreate DuckDB query tables from the durable JSONL log."""
    settings = get_settings()
    db_path = Path(settings.analytics_duckdb_path)
    if db_path.exists():
        db_path.unlink()
    initialize_storage()
    return load_jsonl_to_duckdb()


def record_purchase_confirmed(
    *,
    order_id: str,
    session_id: str,
    user_id: str | None,
    locale: str,
    total_cents: int,
    payment_method: str,
    delivery_method: str | None,
    delivery_courier: str | None,
    analytics_consent: bool,
) -> None:
    """Record backend-confirmed purchase without blocking checkout."""
    settings = get_settings()
    if not settings.analytics_enabled or not analytics_consent:
        return
    try:
        event = AnalyticsEventRequest(
            event_id=f"purchase-{order_id}",
            event_type=AnalyticsEventType.PURCHASE_CONFIRMED,
            occurred_at=datetime.now(UTC),
            locale=locale if locale in {"en", "bg"} else "en",
            page_path=None,
            properties={
                "order_id": order_id,
                "value_cents": total_cents,
                "currency": "BGN",
                "payment_method": payment_method,
                "delivery_method": delivery_method,
                "delivery_courier": delivery_courier,
            },
        )
        ingest_events([event], session_id=session_id, user_id=user_id, consent_verified=True)
    except Exception:
        logger.exception("analytics_purchase_confirmed_failed", order_id=order_id)


def _event_occurred_at(event: dict[str, Any]) -> datetime | None:
    value = event.get("occurred_at")
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def cleanup_expired_events(retention_days: int | None = None) -> int:
    """Delete analytics events older than the configured retention window."""
    settings = get_settings()
    if not settings.analytics_enabled:
        return 0
    days = retention_days if retention_days is not None else settings.analytics_retention_days
    cutoff = datetime.now(UTC) - timedelta(days=days)
    initialize_storage()

    path = Path(settings.analytics_events_jsonl_path)
    jsonl_removed = 0
    if path.exists():
        next_lines: list[str] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                event = json.loads(line)
                occurred_at = _event_occurred_at(event)
                if occurred_at is not None and occurred_at < cutoff:
                    jsonl_removed += 1
                    continue
                next_lines.append(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        if jsonl_removed:
            tmp_path = path.with_suffix(path.suffix + ".tmp")
            with tmp_path.open("w", encoding="utf-8") as handle:
                handle.writelines(next_lines)
                handle.flush()
                os.fsync(handle.fileno())
            tmp_path.replace(path)

    with _duckdb_connect(settings.analytics_duckdb_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM analytics_events WHERE occurred_at < ?",
            (cutoff.isoformat(),),
        ).fetchone()
        duckdb_removed = int(row[0] if row else 0)
        if duckdb_removed:
            conn.execute(
                "DELETE FROM analytics_events WHERE occurred_at < ?",
                (cutoff.isoformat(),),
            )

    removed = max(jsonl_removed, duckdb_removed)
    if removed:
        _set_state("last_retention_cleanup_at", _utc_now())
    return removed


def get_health() -> AnalyticsHealthResponse:
    settings = get_settings()
    try:
        initialize_storage()
        with _duckdb_connect(settings.analytics_duckdb_path) as conn:
            metrics = dict(
                conn.execute("SELECT metric, value FROM analytics_delivery_health").fetchall()
            )
            state = dict(conn.execute("SELECT key, value FROM analytics_state").fetchall())
        return AnalyticsHealthResponse(
            accepted=int(metrics.get("accepted", 0)),
            rejected=int(metrics.get("rejected", 0)),
            duplicate=int(metrics.get("duplicate", 0)),
            validation_failure=int(metrics.get("validation_failure", 0)),
            last_successful_flush_at=state.get("last_successful_flush_at"),
            duckdb_load_status=state.get("duckdb_load_status", "ok"),
            retention_days=settings.analytics_retention_days,
        )
    except Exception:
        logger.exception("analytics_health_query_failed")
        return AnalyticsHealthResponse(retention_days=settings.analytics_retention_days)


def get_funnel(
    start_date: str | None = None, end_date: str | None = None
) -> list[AnalyticsFunnelStep]:
    start, end_exclusive = _date_bounds(start_date, end_date)
    initialize_storage()
    with _duckdb_connect(get_settings().analytics_duckdb_path) as conn:
        rows = conn.execute(
            """
            SELECT event_type, COUNT(*) AS count
            FROM analytics_events
            WHERE occurred_at >= ? AND occurred_at < ? AND anonymized = false
            GROUP BY event_type
            """,
            (start, end_exclusive),
        ).fetchall()
    counts = {row[0]: int(row[1]) for row in rows}
    previous = 0
    steps: list[AnalyticsFunnelStep] = []
    for event_type in FUNNEL_SEQUENCE:
        count = counts.get(event_type.value, 0)
        conversion = 0.0 if previous == 0 else round((count / previous) * 100, 2)
        steps.append(
            AnalyticsFunnelStep(
                event_type=event_type,
                count=count,
                conversion_from_previous=conversion,
            )
        )
        previous = count
    return steps


def _sqlite_order_totals(start_date: str | None, end_date: str | None) -> dict[str, int]:
    start, end_exclusive = _date_bounds(start_date, end_date)
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS order_count, COALESCE(SUM(total_cents), 0) AS revenue_cents,
                   COALESCE(SUM(CASE WHEN analytics_consent = 1 THEN 1 ELSE 0 END), 0)
                   AS consented_order_count
            FROM orders
            WHERE created_at >= ? AND created_at < ? AND status != 'cancelled'
            """,
            (start, end_exclusive),
        ).fetchone()
    return {
        "order_count": int(row["order_count"] if row else 0),
        "revenue_cents": int(row["revenue_cents"] if row else 0),
        "consented_order_count": int(row["consented_order_count"] if row else 0),
    }


def get_summary(start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    start, end_exclusive = _date_bounds(start_date, end_date)
    display_start, display_end = _display_range(start_date, end_date)
    initialize_storage()
    with _duckdb_connect(get_settings().analytics_duckdb_path) as conn:
        event_row = conn.execute(
            """
            SELECT COUNT(*) AS events, COUNT(DISTINCT session_id) AS sessions
            FROM analytics_events
            WHERE occurred_at >= ? AND occurred_at < ? AND anonymized = false
            """,
            (start, end_exclusive),
        ).fetchone()
        purchase_row = conn.execute(
            """
            SELECT COUNT(*) AS purchases, COALESCE(SUM(value_cents), 0) AS revenue
            FROM analytics_events
            WHERE event_type = 'purchase_confirmed'
              AND occurred_at >= ? AND occurred_at < ? AND anonymized = false
            """,
            (start, end_exclusive),
        ).fetchone()

    order_totals = _sqlite_order_totals(start_date, end_date)
    accepted_events = int(event_row[0] or 0)
    consented_sessions = int(event_row[1] or 0)
    analytics_purchases = int(purchase_row[0] or 0)
    analytics_revenue = int(purchase_row[1] or 0)
    backend_orders = order_totals["order_count"]
    coverage = (
        0.0 if backend_orders == 0 else round((analytics_purchases / backend_orders) * 100, 2)
    )
    conversion = (
        0.0
        if consented_sessions == 0
        else round((analytics_purchases / consented_sessions) * 100, 2)
    )
    consented_delta = order_totals["consented_order_count"] - analytics_purchases
    return {
        "start_date": display_start,
        "end_date": display_end,
        "consented_sessions": consented_sessions,
        "accepted_events": accepted_events,
        "conversion_rate": conversion,
        "backend_order_count": backend_orders,
        "backend_revenue_cents": order_totals["revenue_cents"],
        "analytics_purchase_count": analytics_purchases,
        "analytics_purchase_revenue_cents": analytics_revenue,
        "coverage_percent": coverage,
        "consented_order_count": order_totals["consented_order_count"],
        "consented_order_delta": consented_delta,
        "delivery_warning": consented_delta > get_settings().analytics_delivery_tolerance,
        "health": get_health(),
    }


def get_product_metrics(
    start_date: str | None = None, end_date: str | None = None
) -> list[dict[str, Any]]:
    start, end_exclusive = _date_bounds(start_date, end_date)
    initialize_storage()
    with _duckdb_connect(get_settings().analytics_duckdb_path) as duck:
        behavior_rows = duck.execute(
            """
            SELECT product_id,
                   SUM(CASE WHEN event_type = 'product_view' THEN 1 ELSE 0 END) AS views,
                   SUM(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS add_to_cart
            FROM analytics_events
            WHERE product_id IS NOT NULL
              AND occurred_at >= ? AND occurred_at < ? AND anonymized = false
            GROUP BY product_id
            """,
            (start, end_exclusive),
        ).fetchall()
        purchase_order_rows = duck.execute(
            """
            SELECT DISTINCT order_id
            FROM analytics_events
            WHERE event_type = 'purchase_confirmed'
              AND order_id IS NOT NULL
              AND occurred_at >= ? AND occurred_at < ? AND anonymized = false
            """,
            (start, end_exclusive),
        ).fetchall()

    metrics: dict[str, dict[str, int]] = {}
    for product_id, views, add_to_cart in behavior_rows:
        metrics.setdefault(
            product_id,
            {"views": 0, "add_to_cart": 0, "purchases": 0, "revenue_cents": 0},
        )
        metrics[product_id]["views"] += int(views or 0)
        metrics[product_id]["add_to_cart"] += int(add_to_cart or 0)

    order_ids = [row[0] for row in purchase_order_rows]
    names: dict[str, str] = {}
    if order_ids:
        placeholders = ",".join("?" * len(order_ids))
        with get_db() as conn:
            purchase_rows = conn.execute(
                f"""
                SELECT oi.product_id,
                       COALESCE(NULLIF(p.name_en, ''), p.name_bg, oi.product_name, oi.product_id)
                       AS name,
                       SUM(oi.quantity) AS purchases,
                       SUM(oi.quantity * oi.price_cents) AS revenue_cents
                FROM order_items oi
                LEFT JOIN products p ON p.id = oi.product_id
                WHERE oi.order_id IN ({placeholders})
                GROUP BY oi.product_id, name
                """,
                order_ids,
            ).fetchall()
        for row in purchase_rows:
            product_id = row["product_id"]
            names[product_id] = row["name"]
            metrics.setdefault(
                product_id,
                {"views": 0, "add_to_cart": 0, "purchases": 0, "revenue_cents": 0},
            )
            metrics[product_id]["purchases"] += int(row["purchases"] or 0)
            metrics[product_id]["revenue_cents"] += int(row["revenue_cents"] or 0)

    if metrics:
        product_ids = list(metrics)
        placeholders = ",".join("?" * len(product_ids))
        with get_db() as conn:
            for row in conn.execute(
                f"""
                SELECT id, COALESCE(NULLIF(name_en, ''), name_bg, id) AS name
                FROM products WHERE id IN ({placeholders})
                """,
                product_ids,
            ).fetchall():
                names.setdefault(row["id"], row["name"])

    result: list[dict[str, Any]] = []
    for product_id, row_metrics in metrics.items():
        views_i = row_metrics["views"]
        purchases_i = row_metrics["purchases"]
        add_to_cart = row_metrics["add_to_cart"]
        revenue_cents = row_metrics["revenue_cents"]
        conversion_rate = 0.0 if views_i == 0 else round((purchases_i / views_i) * 100, 2)
        result.append(
            {
                "product_id": product_id,
                "product_name": names.get(product_id),
                "views": views_i,
                "add_to_cart": add_to_cart,
                "purchases": purchases_i,
                "revenue_cents": revenue_cents,
                "conversion_rate": conversion_rate,
            }
        )
    result.sort(key=lambda item: (-item["views"], -item["add_to_cart"], -item["purchases"]))
    return result


def get_checkout_metrics(
    start_date: str | None = None, end_date: str | None = None
) -> dict[str, Any]:
    start, end_exclusive = _date_bounds(start_date, end_date)
    initialize_storage()
    with _duckdb_connect(get_settings().analytics_duckdb_path) as conn:
        counts = dict(
            conn.execute(
                """
                SELECT event_type, COUNT(*)
                FROM analytics_events
                WHERE occurred_at >= ? AND occurred_at < ? AND anonymized = false
                GROUP BY event_type
                """,
                (start, end_exclusive),
            ).fetchall()
        )
        delivery_methods = dict(
            conn.execute(
                """
                SELECT delivery_method, COUNT(*)
                FROM analytics_events
                WHERE delivery_method IS NOT NULL AND occurred_at >= ? AND occurred_at < ?
                  AND anonymized = false
                GROUP BY delivery_method
                """,
                (start, end_exclusive),
            ).fetchall()
        )
        delivery_couriers = dict(
            conn.execute(
                """
                SELECT delivery_courier, COUNT(*)
                FROM analytics_events
                WHERE delivery_courier IS NOT NULL AND occurred_at >= ? AND occurred_at < ?
                  AND anonymized = false
                GROUP BY delivery_courier
                """,
                (start, end_exclusive),
            ).fetchall()
        )
        payment_methods = dict(
            conn.execute(
                """
                SELECT payment_method, COUNT(*)
                FROM analytics_events
                WHERE payment_method IS NOT NULL AND occurred_at >= ? AND occurred_at < ?
                  AND anonymized = false
                GROUP BY payment_method
                """,
                (start, end_exclusive),
            ).fetchall()
        )
    return {
        "checkout_starts": int(counts.get("checkout_start", 0)),
        "order_submits": int(counts.get("order_submit", 0)),
        "payment_redirects": int(counts.get("payment_redirect", 0)),
        "purchase_confirmed": int(counts.get("purchase_confirmed", 0)),
        "delivery_methods": {str(k): int(v) for k, v in delivery_methods.items()},
        "delivery_couriers": {str(k): int(v) for k, v in delivery_couriers.items()},
        "payment_methods": {str(k): int(v) for k, v in payment_methods.items()},
    }


def anonymize_subject(
    *,
    session_ids: list[str] | None = None,
    user_ids: list[str] | None = None,
    order_ids: list[str] | None = None,
) -> int:
    """Pseudonymize analytics rows linked to a GDPR erasure subject."""
    initialize_storage()
    conditions: list[str] = []
    params: list[Any] = []
    for field, values in (
        ("session_id", session_ids or []),
        ("user_id", user_ids or []),
        ("order_id", order_ids or []),
    ):
        if values:
            placeholders = ",".join("?" * len(values))
            conditions.append(f"{field} IN ({placeholders})")
            params.extend(values)
    if not conditions:
        return 0
    anon = f"erased-{uuid.uuid4()}"
    jsonl_count = _anonymize_jsonl_source(
        anon=anon,
        session_ids=set(session_ids or []),
        user_ids=set(user_ids or []),
        order_ids=set(order_ids or []),
    )
    with _duckdb_connect(get_settings().analytics_duckdb_path) as conn:
        conn.execute(
            f"""
            UPDATE analytics_events
            SET session_id = ?,
                user_id = NULL,
                order_id = NULL,
                properties_json = '{{}}',
                anonymized = true
            WHERE {" OR ".join(conditions)}
            """,
            [anon, *params],
        )
        row = conn.execute(
            "SELECT COUNT(*) FROM analytics_events WHERE session_id = ?", (anon,)
        ).fetchone()
    if jsonl_count:
        rebuild_duckdb_from_jsonl()
    return max(int(row[0] if row else 0), jsonl_count)


def _anonymize_jsonl_source(
    *,
    anon: str,
    session_ids: set[str],
    user_ids: set[str],
    order_ids: set[str],
) -> int:
    settings = get_settings()
    path = Path(settings.analytics_events_jsonl_path)
    if not path.exists():
        return 0
    count = 0
    next_lines: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            event = json.loads(line)
            linked = (
                event.get("session_id") in session_ids
                or event.get("user_id") in user_ids
                or event.get("order_id") in order_ids
                or event.get("properties", {}).get("order_id") in order_ids
            )
            if linked:
                event["session_id"] = anon
                event["user_id"] = None
                event["order_id"] = None
                event["properties"] = {}
                event["anonymized"] = True
                count += 1
            next_lines.append(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.writelines(next_lines)
        handle.flush()
        os.fsync(handle.fileno())
    tmp_path.replace(path)
    return count


def count_events_by_type(
    start_date: str | None = None, end_date: str | None = None
) -> dict[str, int]:
    """Testing/admin helper for count parity checks."""
    start, end_exclusive = _date_bounds(start_date, end_date)
    initialize_storage()
    with _duckdb_connect(get_settings().analytics_duckdb_path) as conn:
        return {
            row[0]: int(row[1])
            for row in conn.execute(
                """
                SELECT event_type, COUNT(*)
                FROM analytics_events
                WHERE occurred_at >= ? AND occurred_at < ?
                GROUP BY event_type
                """,
                (start, end_exclusive),
            ).fetchall()
        }


def mark_validation_failure() -> None:
    """Record a validation failure observed before service ingestion runs."""
    _increment_metric("rejected")
    _increment_metric("validation_failure")


def mark_rejected() -> None:
    """Record a rejected analytics event that was syntactically valid."""
    _increment_metric("rejected")
