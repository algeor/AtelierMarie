"""Saved product service for account shortlists."""

import sqlite3

from app.services import pricing, product_image_service, product_video_service, taxonomy_service
from app.services.product_service import (
    Locale,
    NotFoundError,
    _clamp_pagination,
    _resolve_locale_fields,
    _row_to_dict,
)


def _ensure_public_product_exists(conn: sqlite3.Connection, product_id: str) -> None:
    row = conn.execute(
        "SELECT 1 FROM products WHERE id = ? AND is_active = 1",
        (product_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Product not found: {product_id}")


def save_product(conn: sqlite3.Connection, *, user_id: str, product_id: str) -> None:
    """Save an active product for a user."""
    _ensure_public_product_exists(conn, product_id)
    conn.execute(
        """
        INSERT OR IGNORE INTO user_saved_products (user_id, product_id)
        VALUES (?, ?)
        """,
        (user_id, product_id),
    )


def unsave_product(conn: sqlite3.Connection, *, user_id: str, product_id: str) -> None:
    """Remove a product from a user's saved products."""
    conn.execute(
        "DELETE FROM user_saved_products WHERE user_id = ? AND product_id = ?",
        (user_id, product_id),
    )


def get_saved_product_ids(conn: sqlite3.Connection, *, user_id: str) -> list[str]:
    """Return saved active product IDs, newest save first."""
    rows = conn.execute(
        """
        SELECT sp.product_id
        FROM user_saved_products sp
        JOIN products p ON p.id = sp.product_id
        WHERE sp.user_id = ? AND p.is_active = 1
        ORDER BY sp.saved_at DESC, sp.product_id ASC
        """,
        (user_id,),
    ).fetchall()
    return [row["product_id"] for row in rows]


def is_product_saved(conn: sqlite3.Connection, *, user_id: str, product_id: str) -> bool:
    """Return whether a user has saved a product."""
    row = conn.execute(
        "SELECT 1 FROM user_saved_products WHERE user_id = ? AND product_id = ?",
        (user_id, product_id),
    ).fetchone()
    return row is not None


def list_saved_products(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    page: int = 1,
    limit: int = 20,
    locale: Locale = "en",
) -> dict:
    """List a user's saved active products with public product payloads."""
    page, limit = _clamp_pagination(page, limit)
    offset = (page - 1) * limit

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM user_saved_products sp
        JOIN products p ON p.id = sp.product_id
        WHERE sp.user_id = ? AND p.is_active = 1
        """,
        (user_id,),
    ).fetchone()[0]

    rows = conn.execute(
        """
        SELECT p.*
        FROM user_saved_products sp
        JOIN products p ON p.id = sp.product_id
        WHERE sp.user_id = ? AND p.is_active = 1
        ORDER BY sp.saved_at DESC, sp.product_id ASC
        LIMIT ? OFFSET ?
        """,
        (user_id, limit, offset),
    ).fetchall()

    products = [_resolve_locale_fields(_row_to_dict(row), locale) for row in rows]
    taxonomy_service.resolve_products_taxonomy(conn, products, locale)
    now = pricing.now_utc()
    products = [pricing.annotate_product_pricing(product, now, public=True) for product in products]
    products = product_image_service.attach_image_fields(products)
    products = product_video_service.attach_video_fields(products, public_only=True)

    return {
        "products": products,
        "product_ids": get_saved_product_ids(conn, user_id=user_id),
        "total": total,
        "page": page,
        "limit": limit,
    }
