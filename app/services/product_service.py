"""Product service — business logic for product CRUD, search, and listing."""

import sqlite3
from datetime import UTC, datetime
from typing import Literal

from app.constants import MAX_LIMIT, MAX_PAGE
from app.database import get_db
from app.models.common import calculate_offset
from app.services import product_image_service, taxonomy_service

Locale = Literal["en", "bg"]


class NotFoundError(Exception):
    """Raised when a requested product does not exist (or is inactive for public queries)."""


class DuplicateError(Exception):
    """Raised when attempting to create a product with an ID that already exists."""


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


def _flatten_admin_labels(product: dict) -> dict:
    """Collapse resolved label refs ([{slug, name}]) down to slugs for admin responses."""
    product["labels"] = [ref["slug"] for ref in product.get("labels", [])]
    return product


def _resolve_locale_fields(product: dict, locale: Locale) -> dict:
    """Resolve locale-specific name/description with fallback to other language.

    Returns a new dict with `name` and `description` fields set to the
    appropriate locale's content (or the fallback language if the preferred
    one is empty/NULL).
    """
    other = "bg" if locale == "en" else "en"

    name = product.get(f"name_{locale}") or product.get(f"name_{other}") or ""
    description = product.get(f"description_{locale}") or product.get(f"description_{other}")

    result = dict(product)
    result["name"] = name
    result["description"] = description
    return result


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
    product_type: str | None = None,
    category: str | None = None,
    labels: list[str] | None = None,
    sort: str | None = None,
    in_stock: bool | None = None,
    page: int = 1,
    limit: int = 20,
    locale: Locale = "en",
) -> tuple[list[dict], int]:
    """List active products with optional taxonomy filtering, sorting, pagination.

    `category` filters on the managed category/tier slug. `labels` uses AND
    semantics — a product must carry every selected label. Returns (products,
    total_count) with locale-resolved names and taxonomy display metadata.
    """
    page, limit = _clamp_pagination(page, limit)

    conditions = ["is_active = 1"]
    params: list = []

    if product_type:
        conditions.append("product_type_slug = ?")
        params.append(product_type)

    if category:
        conditions.append("category_slug = ?")
        params.append(category)

    if labels:
        placeholders = ", ".join("?" for _ in labels)
        conditions.append(
            f"id IN (SELECT product_id FROM product_label_assignments "  # noqa: S608
            f"WHERE label_slug IN ({placeholders}) "
            "GROUP BY product_id HAVING COUNT(DISTINCT label_slug) = ?)"
        )
        params.extend(labels)
        params.append(len(labels))

    if in_stock:
        conditions.append("stock > 0")

    where_clause = " AND ".join(conditions)

    # Sort mapping — use locale-appropriate name column for name sort
    name_col = f"name_{locale}"
    sort_map = {
        "price_asc": "price_cents ASC",
        "price_desc": "price_cents DESC",
        "name": f"{name_col} ASC",
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

        products = [_resolve_locale_fields(_row_to_dict(r), locale) for r in rows]
        taxonomy_service.resolve_products_taxonomy(conn, products, locale)

    products = product_image_service.attach_image_fields(products)
    return products, total


def get_product(product_id: str, *, locale: Locale = "en") -> dict:
    """Get a single active product by ID. Raises NotFoundError if missing or inactive.

    Returns locale-resolved name/description plus taxonomy display metadata.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ? AND is_active = 1",
            (product_id,),
        ).fetchone()

        if row is None:
            raise NotFoundError(f"Product not found: {product_id}")

        product = _resolve_locale_fields(_row_to_dict(row), locale)
        taxonomy_service.resolve_products_taxonomy(conn, [product], locale)

    return product_image_service.attach_image_fields_one(product)


def get_product_admin(product_id: str) -> dict:
    """Get any product (active or inactive) by ID. For admin use.

    Taxonomy is exposed as slugs (`product_type`, `category`, `labels`) so admin
    form controls can prefill assignments.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()

        if row is None:
            raise NotFoundError(f"Product not found: {product_id}")

        product = _row_to_dict(row)
        taxonomy_service.resolve_products_taxonomy(conn, [product], "en")

    return _flatten_admin_labels(product_image_service.attach_image_fields_one(product))


def list_products_admin(
    *,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """List all products (active and inactive) with pagination. For admin use."""
    offset = calculate_offset(page, limit)

    with get_db() as conn:
        count_row = conn.execute("SELECT COUNT(*) as cnt FROM products").fetchone()
        total = count_row["cnt"]

        rows = conn.execute(
            "SELECT * FROM products ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()

        products = [_row_to_dict(r) for r in rows]
        taxonomy_service.resolve_products_taxonomy(conn, products, "en")

    products = [_flatten_admin_labels(p) for p in products]
    return product_image_service.attach_image_fields(products), total


def create_product(data: dict) -> dict:
    """Create a new product. Raises DuplicateError if ID exists, TaxonomyValidationError
    if the product type / category / labels are unknown or inactive."""
    now = _now_utc()
    product_id = data["id"]
    product_type = data.get("product_type") or "candles"
    category_slug = data.get("category")
    labels = data.get("labels") or []

    columns = [
        "id",
        "name_en",
        "name_bg",
        "description_en",
        "description_bg",
        "materials",
        "days_to_craft",
        "price_cents",
        "product_type_slug",
        "category_slug",
        "stock",
        "is_active",
        "is_featured",
        "translation_stale_bg",
        "translation_stale_en",
        "created_at",
        "updated_at",
    ]

    values = [
        product_id,
        data["name_en"],
        data.get("name_bg"),
        data.get("description_en"),
        data.get("description_bg"),
        data.get("materials"),
        data.get("days_to_craft"),
        data["price_cents"],
        product_type,
        category_slug,
        data.get("stock", 0),
        1 if data.get("is_active", True) else 0,
        1 if data.get("is_featured", False) else 0,
        0,  # translation_stale_bg
        0,  # translation_stale_en
        now,
        now,
    ]

    placeholders = ", ".join("?" for _ in columns)
    col_str = ", ".join(columns)

    with get_db() as conn:
        # Validate taxonomy assignments against managed active terms before write.
        taxonomy_service.validate_product_type(conn, product_type)
        taxonomy_service.validate_category(conn, category_slug)
        taxonomy_service.validate_labels(conn, labels)

        try:
            conn.execute(
                f"INSERT INTO products ({col_str}) VALUES ({placeholders})",  # noqa: S608
                values,
            )
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateError(f"Product with this ID already exists: {product_id}") from e
            raise

        taxonomy_service.replace_product_labels(conn, product_id, labels)

        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        product = _row_to_dict(row)
        taxonomy_service.resolve_products_taxonomy(conn, [product], "en")

    return _flatten_admin_labels(product_image_service.attach_image_fields_one(product))


def upsert_product(product_id: str, data: dict) -> dict:
    """Create or update a product using INSERT ... ON CONFLICT DO UPDATE.

    Only non-None fields in data are updated on conflict. Taxonomy values, when
    provided, are validated against existing ACTIVE terms (CSV import never
    auto-creates taxonomy and never preserves inactive terms).
    """
    now = _now_utc()
    labels = data.get("labels")  # None → leave assignments untouched

    # Fields that can be set on insert/update
    field_map = {
        "name_en": data.get("name_en"),
        "name_bg": data.get("name_bg"),
        "description_en": data.get("description_en"),
        "description_bg": data.get("description_bg"),
        "materials": data.get("materials"),
        "days_to_craft": data.get("days_to_craft"),
        "price_cents": data.get("price_cents"),
        # Taxonomy slugs — only touched when the CSV row supplied them.
        "product_type_slug": data.get("product_type"),
        "category_slug": data.get("category"),
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
        if data.get("product_type"):
            taxonomy_service.validate_product_type(conn, data["product_type"])
        if data.get("category"):
            taxonomy_service.validate_category(conn, data["category"])
        if labels is not None:
            taxonomy_service.validate_labels(conn, labels)

        conn.execute(sql, insert_vals)

        if labels is not None:
            taxonomy_service.replace_product_labels(conn, product_id, labels)

        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        product = _row_to_dict(row)
        taxonomy_service.resolve_products_taxonomy(conn, [product], "en")

    return _flatten_admin_labels(product_image_service.attach_image_fields_one(product))


def update_product(product_id: str, data: dict) -> dict:
    """Partially update a product. Only provided fields are modified.

    `data` should come from model_dump(exclude_unset=True) so presence is
    meaningful. Taxonomy reassignments validate against active terms while
    allowing the product to keep its current (possibly inactive) assignments;
    assigning a *different* inactive term is rejected. Category may be set NULL.

    Implements translation staleness logic:
    - If EN content changes, mark BG as stale (unless BG also updated in same request)
    - If BG content changes, mark EN as stale (unless EN also updated in same request)
    - Updating the stale side clears its staleness flag

    Raises NotFoundError if the product does not exist.
    """
    with get_db() as conn:
        current = conn.execute(
            "SELECT product_type_slug, category_slug FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        if current is None:
            raise NotFoundError(f"Product not found: {product_id}")

        current_type = current["product_type_slug"]
        current_category = current["category_slug"]
        current_labels = set(taxonomy_service.get_product_label_slugs(conn, product_id))

        # Validate only actual reassignments (preserve-current allowed for inactive).
        type_update = "product_type" in data and data["product_type"] is not None
        category_update = "category" in data
        labels_update = "labels" in data and data["labels"] is not None

        if type_update:
            taxonomy_service.validate_product_type(conn, data["product_type"], current=current_type)
        if category_update:
            taxonomy_service.validate_category(conn, data["category"], current=current_category)
        if labels_update:
            taxonomy_service.validate_labels(conn, data["labels"], current=current_labels)

        # Generic scalar fields (None → not provided; filtered out).
        field_map = {
            "name_en": data.get("name_en"),
            "name_bg": data.get("name_bg"),
            "description_en": data.get("description_en"),
            "description_bg": data.get("description_bg"),
            "materials": data.get("materials"),
            "days_to_craft": data.get("days_to_craft"),
            "price_cents": data.get("price_cents"),
            "stock": data.get("stock"),
            "is_active": (
                None if data.get("is_active") is None else (1 if data["is_active"] else 0)
            ),
            "is_featured": (
                None if data.get("is_featured") is None else (1 if data["is_featured"] else 0)
            ),
        }
        updates = {k: v for k, v in field_map.items() if v is not None}

        # Taxonomy column updates (category may be explicitly NULL).
        if type_update:
            updates["product_type_slug"] = data["product_type"]
        if category_update:
            updates["category_slug"] = data["category"]

        # Staleness logic (only name/description fields count).
        en_fields = {"name_en", "description_en"}
        bg_fields = {"name_bg", "description_bg"}
        updated_en = bool(en_fields & updates.keys())
        updated_bg = bool(bg_fields & updates.keys())
        if updated_en and updated_bg:
            updates["translation_stale_bg"] = 0
            updates["translation_stale_en"] = 0
        elif updated_en:
            updates["translation_stale_bg"] = 1
            updates["translation_stale_en"] = 0
        elif updated_bg:
            updates["translation_stale_en"] = 1
            updates["translation_stale_bg"] = 0

        if updates:
            set_clause = ", ".join(f"{col} = ?" for col in updates)
            conn.execute(
                f"UPDATE products SET {set_clause} WHERE id = ?",  # noqa: S608
                [*updates.values(), product_id],
            )

        if labels_update:
            taxonomy_service.replace_product_labels(conn, product_id, data["labels"])

        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        product = _row_to_dict(row)
        taxonomy_service.resolve_products_taxonomy(conn, [product], "en")

    return _flatten_admin_labels(product_image_service.attach_image_fields_one(product))


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
        product = _row_to_dict(row)
        taxonomy_service.resolve_products_taxonomy(conn, [product], "en")

    return _flatten_admin_labels(product_image_service.attach_image_fields_one(product))


def search_products(
    query: str,
    *,
    product_type: str | None = None,
    category: str | None = None,
    labels: list[str] | None = None,
    in_stock: bool | None = None,
    limit: int = 20,
    offset: int = 0,
    locale: Locale = "en",
) -> list[dict]:
    """Full-text search on product name and description using FTS5.

    Searches the locale-appropriate FTS index (products_fts_en or products_fts_bg).
    Returns active products ranked by relevance with locale-resolved content and
    taxonomy display metadata. Taxonomy filters (product_type, category slug,
    labels) and in_stock/LIMIT/OFFSET are pushed into SQL.
    """
    if not query or not query.strip():
        return []

    # B.4/B.5: Sanitize input for safe FTS5 MATCH
    sanitized = _sanitize_fts5_query(query)
    if not sanitized:
        return []

    fts_table = f"products_fts_{locale}"

    # Build dynamic WHERE conditions pushed into SQL (B.6)
    conditions = [f"{fts_table} MATCH ?", "p.is_active = 1"]
    params: list = [sanitized]

    if product_type:
        conditions.append("p.product_type_slug = ?")
        params.append(product_type)

    if category:
        conditions.append("p.category_slug = ?")
        params.append(category)

    if labels:
        placeholders = ", ".join("?" for _ in labels)
        conditions.append(
            f"p.id IN (SELECT product_id FROM product_label_assignments "  # noqa: S608
            f"WHERE label_slug IN ({placeholders}) "
            "GROUP BY product_id HAVING COUNT(DISTINCT label_slug) = ?)"
        )
        params.extend(labels)
        params.append(len(labels))

    if in_stock:
        conditions.append("p.stock > 0")

    where_clause = " AND ".join(conditions)
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT p.*
            FROM {fts_table} fts
            JOIN products p ON p.rowid = fts.rowid
            WHERE {where_clause}
            ORDER BY rank
            LIMIT ? OFFSET ?
            """,  # noqa: S608
            params,
        ).fetchall()

        products = [_resolve_locale_fields(_row_to_dict(r), locale) for r in rows]
        taxonomy_service.resolve_products_taxonomy(conn, products, locale)

    return product_image_service.attach_image_fields(products)


def get_low_stock_products(threshold: int = 5) -> list[dict]:
    """Return active products whose stock is at or below the threshold.

    Intended for admin low-stock reports. Returns [] if nothing matches.
    """
    if threshold < 0:
        raise ValueError("Threshold must be non-negative")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE stock <= ? AND is_active = 1",
            (threshold,),
        ).fetchall()
        products = [_row_to_dict(r) for r in rows]
        taxonomy_service.resolve_products_taxonomy(conn, products, "en")
    products = [_flatten_admin_labels(p) for p in products]
    return product_image_service.attach_image_fields(products)
