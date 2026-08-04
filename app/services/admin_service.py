"""Admin service — dashboard statistics and administrative queries."""

from app.database import get_db


def get_dashboard_stats() -> dict:
    """Fetch basic dashboard statistics from SQLite.

    Returns counts and revenue figures from the orders and products tables.
    All monetary values are in cents.
    """
    with get_db() as conn:
        # Product counts
        product_row = conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active "
            "FROM products"
        ).fetchone()

        # Order counts and paid revenue
        order_row = conn.execute(
            """
            SELECT COUNT(*) as total,
                   COALESCE(SUM(CASE WHEN payment_status = 'paid' THEN total_cents ELSE 0 END), 0)
                   as revenue_cents
            FROM orders
            """
        ).fetchone()

        # Orders by status
        status_rows = conn.execute(
            "SELECT status, COUNT(*) as count FROM orders GROUP BY status"
        ).fetchall()

        payment_status_rows = conn.execute(
            "SELECT payment_status, COUNT(*) as count FROM orders GROUP BY payment_status"
        ).fetchall()

        today_row = conn.execute(
            "SELECT COUNT(*) as count FROM orders WHERE date(created_at) = CURRENT_DATE"
        ).fetchone()

        week_revenue_row = conn.execute(
            """
            SELECT COALESCE(SUM(total_cents), 0) as revenue_cents
            FROM orders
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days' AND payment_status = 'paid'
            """
        ).fetchone()

        # Low-stock products (active products with stock <= 5)
        low_stock_row = conn.execute(
            "SELECT COUNT(*) as count FROM products WHERE is_active = 1 AND stock <= 5"
        ).fetchone()

    orders_by_status = {row["status"]: row["count"] for row in status_rows}
    orders_by_payment_status = {row["payment_status"]: row["count"] for row in payment_status_rows}

    return {
        "products": {
            "total": product_row["total"],
            "active": product_row["active"] or 0,
        },
        "orders": {
            "total": order_row["total"],
            "revenue_cents": order_row["revenue_cents"],
            "by_status": orders_by_status,
            "by_payment_status": orders_by_payment_status,
        },
        "low_stock_count": low_stock_row["count"],
        "orders_today": today_row["count"],
        "revenue_this_week_cents": week_revenue_row["revenue_cents"],
        "active_product_count": product_row["active"] or 0,
    }
