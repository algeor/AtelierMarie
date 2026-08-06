"""Admin alert service — durable in-app operational alerts."""

import json
import uuid
from datetime import datetime

from app.database import DbConnection, require_row

# Mirrors app.services.order_service._DT_FMT — kept local to avoid importing the
# heavy order_service module into this low-level alert helper.
_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _fmt_ts(value: object) -> str | None:
    """Normalise a TIMESTAMPTZ column (psycopg datetime) to the canonical string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime(_DT_FMT)
    return str(value)


def create_admin_alert(
    conn: DbConnection,
    *,
    alert_type: str,
    title: str,
    message: str,
    order_id: str | None = None,
    source: str = "system",
    severity: str = "warning",
    details: dict | None = None,
) -> str:
    """Create a durable admin alert and return its id."""
    alert_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO admin_alerts (
            id, alert_type, order_id, source, severity, title, message, details
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            alert_id,
            alert_type,
            order_id,
            source,
            severity,
            title,
            message,
            json.dumps(details or {}, separators=(",", ":")),
        ),
    )
    return alert_id


def list_admin_alerts(
    conn: DbConnection,
    *,
    limit: int = 20,
    unread_only: bool = False,
) -> tuple[list[dict], int]:
    """List recent admin alerts for the in-app alert surface."""
    limit = min(max(limit, 1), 100)
    where_clause = "WHERE is_read = 0" if unread_only else ""
    total = require_row(
        conn.execute(f"SELECT COUNT(*) AS n FROM admin_alerts {where_clause}").fetchone()
    )["n"]
    rows = conn.execute(
        f"""
        SELECT id, alert_type, order_id, source, severity, title, message,
               details, is_read, created_at
        FROM admin_alerts
        {where_clause}
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()

    alerts: list[dict] = []
    for row in rows:
        alert = dict(row)
        try:
            alert["details"] = json.loads(alert["details"] or "{}")
        except json.JSONDecodeError:
            alert["details"] = {}
        alert["is_read"] = bool(alert["is_read"])
        alert["created_at"] = _fmt_ts(alert.get("created_at"))
        alerts.append(alert)
    return alerts, total
