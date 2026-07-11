"""Product service — business logic for product CRUD, search, and listing."""

import sqlite3
from datetime import UTC, datetime

from app.constants import MAX_LIMIT, MAX_PAGE
from app.database import get_db


class NotFoundError(Exception):
    """Raised when a requested product does not exist (or is inactive for public queries)."""


class DuplicateError(Exception):
    """Raised when attempting to create a product with an ID that already exists."""


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def _now_utc() -> str:
    """Return current UTC timestamp as 'YYYY-MM-DD HH:MM:SS'."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _sanitize_fts5_query(query: str) -> str:
    """Sanitize user input for FTS5 MATCH expressions.

    Strategy: Split on whitespace, wrap each token in double quotes to
    escape all FTS5 special characters (*, OR, AND, NOT, NEAR, etc.),
    then rejoin with spaces (implicit AND).

    Returns an empty string if no valid tokens remain.
    """
    tokens = query.strip().split()
    if not tokens:
        return ""
    # Remove any embedded double quotes from individual tokens
    sanitized = [f'"{token.replace(chr(34), "")}"' for token in tokens if token.replace('"', "")]
    return " ".join(sanitized)


def _clamp_pagination(page: int, limit: int) -> tuple[int, int]:
    """Clamp pagination values to configured bounds.

    Values exceeding MAX_PAGE/MAX_LIMIT are reduced (not rejected).
    """
    if page < 1:
        page = 1
    page = min(page, MAX_PAGE)
    if limit < 1:
        limit = 1
    limit = min(limit, MAX_LIMIT)
    return page, limit


def list_products(
    *,
    category: str | None = None,
    sort: str | None = None,
    in_stock: bool | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """List active products with optional filtering, sorting, and pagination.

    Returns (products, total_count).
    """
    page, limit = _clamp_pagination(page, limit)

    conditions = ["is_active = 1"]
    params: list = []

    if category:
        conditions.append("category = ?")
        params.append(category)

    if in_stock:
        conditions.append("stock > 0")

    where_clause = " AND ".join(conditions)

    # Sort mapping
    sort_map = {
        "price_asc": "price_cents ASC",
        "price_desc": "price_cents DESC",
        "name": "name ASC",
        "newest": "created_at DESC",
    }
    order_by = sort_map.get(sort or "", "created_at DESC")

    offset = (page - 1) * limit

    with get_db() as conn:
        # Get total count
        count_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM products WHERE {where_clause}",  # noqa: S608
            params,
        ).fetchone()
        total = count_row["cnt"]

        # Get page of results
        rows = conn.execute(
            f"SELECT * FROM products WHERE {where_clause} ORDER BY {order_by} LIMIT ? OFFSET ?",  # noqa: S608
            [*params, limit, offset],
        ).fetchall()

    return [_row_to_dict(r) for r in rows], total


def get_product(product_id: str) -> dict:
    """Get a single active product by ID. Raises NotFoundError if missing or inactive."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ? AND is_active = 1",
            (product_id,),
        ).fetchone()

    if row is None:
        raise NotFoundError(f"Product not found: {product_id}")

    return _row_to_dict(row)


def get_product_admin(product_id: str) -> dict:
    """Get any product (active or inactive) by ID. For admin use."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()

    if row is None:
        raise NotFoundError(f"Product not found: {product_id}")

    return _row_to_dict(row)


def list_products_admin(
    *,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """List all products (active and inactive) with pagination. For admin use."""
    offset = (page - 1) * limit

    with get_db() as conn:
        count_row = conn.execute("SELECT COUNT(*) as cnt FROM products").fetchone()
        total = count_row["cnt"]

        rows = conn.execute(
            "SELECT * FROM products ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()

    return [_row_to_dict(r) for r in rows], total


def create_product(data: dict) -> dict:
    """Create a new product. Raises DuplicateError if ID already exists."""
    now = _now_utc()
    product_id = data["id"]

    columns = [
        "id",
        "name",
        "description",
        "materials",
        "days_to_craft",
        "price_cents",
        "category",
        "image_url",
        "stock",
        "is_active",
        "is_featured",
        "created_at",
        "updated_at",
    ]

    values = [
        product_id,
        data["name"],
        data.get("description"),
        data.get("materials"),
        data.get("days_to_craft"),
        data["price_cents"],
        data.get("category"),
        data.get("image_url"),
        data.get("stock", 0),
        1 if data.get("is_active", True) else 0,
        1 if data.get("is_featured", False) else 0,
        now,
        now,
    ]

    placeholders = ", ".join("?" for _ in columns)
    col_str = ", ".join(columns)

    with get_db() as conn:
        try:
            conn.execute(
                f"INSERT INTO products ({col_str}) VALUES ({placeholders})",  # noqa: S608
                values,
            )
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateError(f"Product with this ID already exists: {product_id}") from e
            raise

        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    return _row_to_dict(row)


def upsert_product(product_id: str, data: dict) -> dict:
    """Create or update a product using INSERT ... ON CONFLICT DO UPDATE.

    Only non-None fields in data are updated on conflict.
    """
    now = _now_utc()

    # Fields that can be set on insert/update
    field_map = {
        "name": data.get("name"),
        "description": data.get("description"),
        "materials": data.get("materials"),
        "days_to_craft": data.get("days_to_craft"),
        "price_cents": data.get("price_cents"),
        "category": data.get("category"),
        "image_url": data.get("image_url"),
        "stock": data.get("stock"),
        "is_active": (None if data.get("is_active") is None else (1 if data["is_active"] else 0)),
        "is_featured": (
            None if data.get("is_featured") is None else (1 if data["is_featured"] else 0)
        ),
    }

    # For INSERT: include all provided fields + id + timestamps
    insert_cols = ["id", "created_at", "updated_at"]
    insert_vals: list = [product_id, now, now]

    for col, val in field_map.items():
        if val is not None:
            insert_cols.append(col)
            insert_vals.append(val)

    # For UPDATE: only update provided (non-None) fields + updated_at
    update_parts = ["updated_at = excluded.updated_at"]
    for col, val in field_map.items():
        if val is not None:
            update_parts.append(f"{col} = excluded.{col}")

    col_str = ", ".join(insert_cols)
    placeholders = ", ".join("?" for _ in insert_cols)
    update_str = ", ".join(update_parts)

    sql = (
        f"INSERT INTO products ({col_str}) VALUES ({placeholders}) "  # noqa: S608
        f"ON CONFLICT(id) DO UPDATE SET {update_str}"
    )

    with get_db() as conn:
        conn.execute(sql, insert_vals)
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    return _row_to_dict(row)


def update_product(product_id: str, data: dict) -> dict:
    """Partially update a product. Only non-None fields are modified.

    Raises NotFoundError if the product does not exist.
    """
    # Map field names to values, filtering out None
    field_map = {
        "name": data.get("name"),
        "description": data.get("description"),
        "materials": data.get("materials"),
        "days_to_craft": data.get("days_to_craft"),
        "price_cents": data.get("price_cents"),
        "category": data.get("category"),
        "image_url": data.get("image_url"),
        "stock": data.get("stock"),
        "is_active": (None if data.get("is_active") is None else (1 if data["is_active"] else 0)),
        "is_featured": (
            None if data.get("is_featured") is None else (1 if data["is_featured"] else 0)
        ),
    }

    updates = {k: v for k, v in field_map.items() if v is not None}

    if not updates:
        # Nothing to update, just return the existing product
        return get_product_admin(product_id)

    set_parts = [f"{col} = ?" for col in updates]
    values = list(updates.values())

    set_clause = ", ".join(set_parts)
    values.append(product_id)

    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE products SET {set_clause} WHERE id = ?",  # noqa: S608
            values,
        )
        if cursor.rowcount == 0:
            raise NotFoundError(f"Product not found: {product_id}")

        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    return _row_to_dict(row)


def deactivate_product(product_id: str) -> dict:
    """Soft-delete a product by setting is_active=0. Idempotent.

    Raises NotFoundError if the product does not exist.
    """
    with get_db() as conn:
        # Check existence first (for 404)
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Product not found: {product_id}")

        conn.execute(
            "UPDATE products SET is_active = 0 WHERE id = ?",
            (product_id,),
        )

        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    return _row_to_dict(row)


def search_products(
    query: str,
    *,
    category: str | None = None,
    in_stock: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Full-text search on product name and description using FTS5.

    Returns active products ranked by relevance.
    Filters (category, in_stock) and LIMIT/OFFSET are pushed into SQL
    rather than applied in Python post-fetch.
    """
    if not query or not query.strip():
        return []

    # B.4/B.5: Sanitize input for safe FTS5 MATCH
    sanitized = _sanitize_fts5_query(query)
    if not sanitized:
        return []

    # Build dynamic WHERE conditions pushed into SQL (B.6)
    conditions = ["products_fts MATCH ?", "p.is_active = 1"]
    params: list = [sanitized]

    if category:
        conditions.append("p.category = ?")
        params.append(category)

    if in_stock:
        conditions.append("p.stock > 0")

    where_clause = " AND ".join(conditions)
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*
            FROM products_fts fts
            JOIN products p ON p.rowid = fts.rowid
            WHERE {where_clause}
            ORDER BY rank
            LIMIT ? OFFSET ?
            """,  # noqa: S608
            params,
        ).fetchall()

    return [_row_to_dict(r) for r in rows]
