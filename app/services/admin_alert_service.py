"""Admin alert service — durable in-app operational alerts."""

import json
import sqlite3
import uuid


def create_admin_alert(
    conn: sqlite3.Connection,
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
    conn: sqlite3.Connection,
    *,
    limit: int = 20,
    unread_only: bool = False,
) -> tuple[list[dict], int]:
    """List recent admin alerts for the in-app alert surface."""
    limit = min(max(limit, 1), 100)
    where_clause = "WHERE is_read = 0" if unread_only else ""
    total = conn.execute(f"SELECT COUNT(*) FROM admin_alerts {where_clause}").fetchone()[0]
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
        alerts.append(alert)
    return alerts, total
