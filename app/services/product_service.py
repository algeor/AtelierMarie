"""Product service — business logic for product CRUD, search, and listing."""

import sqlite3
from datetime import UTC, datetime
from typing import Literal

from app.constants import MAX_LIMIT, MAX_PAGE
from app.database import get_db
from app.models.common import calculate_offset
from app.services import pricing, product_image_service, product_video_service

Locale = Literal["en", "bg"]


class NotFoundError(Exception):
    """Raised when a requested product does not exist (or is inactive for public queries)."""


class DuplicateError(Exception):
    """Raised when attempting to create a product with an ID that already exists."""


class DiscountValidationError(Exception):
    """Raised when a merged discount update fails validation (route → 422).

    Update discount validation lives here (not in the Pydantic model) because it
    depends on merging the partial patch with the existing persisted row.
    """


class BulkTargetLimitError(Exception):
    """Raised when a bulk discount target resolves to more than the allowed cap.

    Routes translate this to a 422 with code `BULK_TARGET_LIMIT_EXCEEDED`.
    """


BULK_DISCOUNT_TARGET_LIMIT = 500


def _validate_merged_discount(
    percent: int | None, starts_at: str | None, ends_at: str | None
) -> None:
    """Validate the merged discount fields for an update (post-merge)."""
    if percent is None:
        # Percent cleared — any residual dates are cleared by the caller.
        return
    if not (1 <= percent <= 99):
        raise DiscountValidationError("discount_percent must be between 1 and 99")
    if starts_at is not None and ends_at is not None and starts_at >= ends_at:
        raise DiscountValidationError("discount_starts_at must be earlier than discount_ends_at")


def merge_discount_update(existing: dict | sqlite3.Row, data: dict) -> dict:
    """Merge a partial discount patch with the existing row and validate it.

    Shared by the single-product update path and the bulk discount path so both
    honor identical rules. Returns the merged, validated
    `{discount_percent, discount_starts_at, discount_ends_at}`. Passing
    `discount_percent=None` clears all three together. Raises
    `DiscountValidationError` on an invalid merged result.
    """
    if "discount_percent" in data and data["discount_percent"] is None:
        # Clearing the discount clears all three fields together.
        merged_percent = merged_starts = merged_ends = None
    else:
        merged_percent = (
            data["discount_percent"] if "discount_percent" in data else existing["discount_percent"]
        )
        merged_starts = (
            data["discount_starts_at"]
            if "discount_starts_at" in data
            else existing["discount_starts_at"]
        )
        merged_ends = (
            data["discount_ends_at"] if "discount_ends_at" in data else existing["discount_ends_at"]
        )
        # A date without a resulting percent is invalid.
        if merged_percent is None and (merged_starts is not None or merged_ends is not None):
            raise DiscountValidationError(
                "discount_percent is required when a discount date is set"
            )

    _validate_merged_discount(merged_percent, merged_starts, merged_ends)
    return {
        "discount_percent": merged_percent,
        "discount_starts_at": merged_starts,
        "discount_ends_at": merged_ends,
    }


def _annotate_admin_one(product: dict, now: str | None = None) -> dict:
    """Add admin discount preview fields (raw config + effective price)."""
    return pricing.annotate_product_pricing(product, now or pricing.now_utc(), public=False)


def _annotate_admin(products: list[dict], now: str | None = None) -> list[dict]:
    """Admin-annotate a list of products with a single shared `now`."""
    now = now or pricing.now_utc()
    return [pricing.annotate_product_pricing(p, now, public=False) for p in products]


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


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
    category: str | None = None,
    sort: str | None = None,
    in_stock: bool | None = None,
    page: int = 1,
    limit: int = 20,
    locale: Locale = "en",
) -> tuple[list[dict], int]:
    """List active products with optional filtering, sorting, and pagination.

    Returns (products, total_count). Products have locale-resolved name/description.
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

    now = pricing.now_utc()
    # Price sort must order by the computed effective price, which depends on
    # `now` and the discount window — it cannot be expressed in SQL. For price
    # sorts we fetch all matching rows, annotate, sort, then paginate in Python.
    price_sort = sort in ("price_asc", "price_desc")

    offset = (page - 1) * limit

    with get_db() as conn:
        # Get total count
        count_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM products WHERE {where_clause}",  # noqa: S608
            params,
        ).fetchone()
        total = count_row["cnt"]

        if price_sort:
            rows = conn.execute(
                f"SELECT * FROM products WHERE {where_clause}",  # noqa: S608
                params,
            ).fetchall()
        else:
            # Non-price sort — order and paginate in SQL as before.
            name_col = f"name_{locale}"
            sort_map = {
                "name": f"{name_col} ASC",
                "newest": "created_at DESC",
            }
            order_by = sort_map.get(sort or "", "created_at DESC")
            rows = conn.execute(
                f"SELECT * FROM products WHERE {where_clause} "  # noqa: S608
                f"ORDER BY {order_by} LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()

    products = [
        pricing.annotate_product_pricing(
            _resolve_locale_fields(_row_to_dict(r), locale), now, public=True
        )
        for r in rows
    ]

    if price_sort:
        products.sort(
            key=lambda p: p["effective_price_cents"],
            reverse=(sort == "price_desc"),
        )
        products = products[offset : offset + limit]

    products = product_image_service.attach_image_fields(products)
    products = product_video_service.attach_video_fields(products, public_only=True)
    return products, total


def get_product(product_id: str, *, locale: Locale = "en") -> dict:
    """Get a single active product by ID. Raises NotFoundError if missing or inactive.

    Returns locale-resolved name/description with fallback.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ? AND is_active = 1",
            (product_id,),
        ).fetchone()

    if row is None:
        raise NotFoundError(f"Product not found: {product_id}")

    product = pricing.annotate_product_pricing(
        _resolve_locale_fields(_row_to_dict(row), locale), pricing.now_utc(), public=True
    )
    product = product_image_service.attach_image_fields_one(product)
    return product_video_service.attach_video_fields_one(product, public_only=True)


def get_product_admin(product_id: str) -> dict:
    """Get any product (active or inactive) by ID. For admin use."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()

    if row is None:
        raise NotFoundError(f"Product not found: {product_id}")

    product = product_image_service.attach_image_fields_one(_annotate_admin_one(_row_to_dict(row)))
    return product_video_service.attach_video_fields_one(product, public_only=False)


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

    products = _annotate_admin([_row_to_dict(r) for r in rows])
    products = product_image_service.attach_image_fields(products)
    products = product_video_service.attach_video_fields(products, public_only=False)
    return products, total


def create_product(data: dict) -> dict:
    """Create a new product. Raises DuplicateError if ID already exists."""
    now = _now_utc()
    product_id = data["id"]

    columns = [
        "id",
        "name_en",
        "name_bg",
        "description_en",
        "description_bg",
        "materials",
        "days_to_craft",
        "price_cents",
        "category",
        "discount_percent",
        "discount_starts_at",
        "discount_ends_at",
        "stock",
        "weight_grams",
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
        data.get("category"),
        data.get("discount_percent"),
        data.get("discount_starts_at"),
        data.get("discount_ends_at"),
        data.get("stock", 0),
        data.get("weight_grams", 300),
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

    product = product_image_service.attach_image_fields_one(_annotate_admin_one(_row_to_dict(row)))
    return product_video_service.attach_video_fields_one(product, public_only=False)


def upsert_product(product_id: str, data: dict) -> dict:
    """Create or update a product using INSERT ... ON CONFLICT DO UPDATE.

    Only non-None fields in data are updated on conflict.
    """
    now = _now_utc()

    # Fields that can be set on insert/update
    field_map = {
        "name_en": data.get("name_en"),
        "name_bg": data.get("name_bg"),
        "description_en": data.get("description_en"),
        "description_bg": data.get("description_bg"),
        "materials": data.get("materials"),
        "days_to_craft": data.get("days_to_craft"),
        "price_cents": data.get("price_cents"),
        "category": data.get("category"),
        "stock": data.get("stock"),
        "weight_grams": data.get("weight_grams"),
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

    product = product_image_service.attach_image_fields_one(_annotate_admin_one(_row_to_dict(row)))
    return product_video_service.attach_video_fields_one(product, public_only=False)


def update_product(product_id: str, data: dict) -> dict:
    """Partially update a product. Only non-None fields are modified.

    Implements translation staleness logic:
    - If EN content changes, mark BG as stale (unless BG also updated in same request)
    - If BG content changes, mark EN as stale (unless EN also updated in same request)
    - Updating the stale side clears its staleness flag

    Raises NotFoundError if the product does not exist.
    """
    # Map field names to values, filtering out None
    field_map = {
        "name_en": data.get("name_en"),
        "name_bg": data.get("name_bg"),
        "description_en": data.get("description_en"),
        "description_bg": data.get("description_bg"),
        "materials": data.get("materials"),
        "days_to_craft": data.get("days_to_craft"),
        "price_cents": data.get("price_cents"),
        "category": data.get("category"),
        "stock": data.get("stock"),
        "weight_grams": data.get("weight_grams"),
        "is_active": (None if data.get("is_active") is None else (1 if data["is_active"] else 0)),
        "is_featured": (
            None if data.get("is_featured") is None else (1 if data["is_featured"] else 0)
        ),
    }

    updates = {k: v for k, v in field_map.items() if v is not None}

    # Discount fields need explicit NULL writes (to clear a discount), so they
    # can't go through the "non-None means update" field_map. Merge the patch
    # with the existing persisted row, then validate the merged result.
    discount_keys = {"discount_percent", "discount_starts_at", "discount_ends_at"}
    if discount_keys & data.keys():
        with get_db() as conn:
            existing = conn.execute(
                "SELECT discount_percent, discount_starts_at, discount_ends_at "
                "FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
        if existing is None:
            raise NotFoundError(f"Product not found: {product_id}")

        merged = merge_discount_update(existing, data)
        updates["discount_percent"] = merged["discount_percent"]
        updates["discount_starts_at"] = merged["discount_starts_at"]
        updates["discount_ends_at"] = merged["discount_ends_at"]

    if not updates:
        # Nothing to update, just return the existing product
        return get_product_admin(product_id)

    # Staleness logic
    en_fields = {"name_en", "description_en"}
    bg_fields = {"name_bg", "description_bg"}
    updated_en = bool(en_fields & updates.keys())
    updated_bg = bool(bg_fields & updates.keys())

    if updated_en and updated_bg:
        # Both sides updated together — neither is stale
        updates["translation_stale_bg"] = 0
        updates["translation_stale_en"] = 0
    elif updated_en:
        # Only EN changed → mark BG as stale, clear EN staleness
        updates["translation_stale_bg"] = 1
        updates["translation_stale_en"] = 0
    elif updated_bg:
        # Only BG changed → mark EN as stale, clear BG staleness
        updates["translation_stale_en"] = 1
        updates["translation_stale_bg"] = 0

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

    return get_product_admin(product_id)


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

    product_video_service.delete_video_if_exists(product_id)
    product = product_image_service.attach_image_fields_one(_annotate_admin_one(_row_to_dict(row)))
    return product_video_service.attach_video_fields_one(product, public_only=False)


def search_products(
    query: str,
    *,
    category: str | None = None,
    in_stock: bool | None = None,
    limit: int = 20,
    offset: int = 0,
    locale: Locale = "en",
    sort: str | None = None,
) -> list[dict]:
    """Full-text search on product name and description using FTS5.

    Searches the locale-appropriate FTS index (products_fts_en or products_fts_bg).
    Returns active products ranked by relevance with locale-resolved content and
    public discount pricing fields. Filters (category, in_stock) and LIMIT/OFFSET
    are pushed into SQL rather than applied in Python post-fetch.

    When `sort` is an explicit price sort, results are ordered by
    `effective_price_cents` across ALL matches (not just the current page) before
    pagination; otherwise FTS5 relevance order is preserved.
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

    if category:
        conditions.append("p.category = ?")
        params.append(category)

    if in_stock:
        conditions.append("p.stock > 0")

    where_clause = " AND ".join(conditions)

    now = pricing.now_utc()
    price_sort = sort in ("price_asc", "price_desc")

    with get_db() as conn:
        if price_sort:
            # Fetch all matches; effective-price sort + pagination happen below.
            rows = conn.execute(
                f"""
                SELECT p.*
                FROM {fts_table} fts
                JOIN products p ON p.rowid = fts.rowid
                WHERE {where_clause}
                ORDER BY rank
                """,  # noqa: S608
                params,
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT p.*
                FROM {fts_table} fts
                JOIN products p ON p.rowid = fts.rowid
                WHERE {where_clause}
                ORDER BY rank
                LIMIT ? OFFSET ?
                """,  # noqa: S608
                [*params, limit, offset],
            ).fetchall()

    products = [
        pricing.annotate_product_pricing(
            _resolve_locale_fields(_row_to_dict(r), locale), now, public=True
        )
        for r in rows
    ]

    if price_sort:
        products.sort(
            key=lambda p: p["effective_price_cents"],
            reverse=(sort == "price_desc"),
        )
        products = products[offset : offset + limit]

    products = product_image_service.attach_image_fields(products)
    return product_video_service.attach_video_fields(products, public_only=True)


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
    products = _annotate_admin([_row_to_dict(r) for r in rows])
    products = product_image_service.attach_image_fields(products)
    return product_video_service.attach_video_fields(products, public_only=False)


def _resolve_filter_target_ids(conn: sqlite3.Connection, filt: dict) -> list[str]:
    """Resolve an admin product-list filter descriptor to product IDs.

    Admin scope: all products (active and inactive) unless `is_active` is set.
    No pagination — every matching product is returned so a bulk/campaign apply
    can act on the whole match set (the caller enforces the target cap).
    """
    conditions: list[str] = []
    params: list = []

    q = (filt.get("q") or "").strip()
    if q:
        conditions.append(
            "(name_en LIKE ? ESCAPE '\\' OR name_bg LIKE ? ESCAPE '\\' OR id LIKE ? ESCAPE '\\')"
        )
        # Escape LIKE wildcards so a query like "50%" matches literally.
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        params.extend([like, like, like])
    if filt.get("category"):
        conditions.append("category = ?")
        params.append(filt["category"])
    if filt.get("is_active") is not None:
        conditions.append("is_active = ?")
        params.append(1 if filt["is_active"] else 0)
    if filt.get("in_stock"):
        conditions.append("stock > 0")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        f"SELECT id FROM products {where} ORDER BY created_at DESC",  # noqa: S608
        params,
    ).fetchall()
    return [r["id"] for r in rows]


def resolve_bulk_target(
    product_ids: list[str] | None = None,
    filter: dict | None = None,  # noqa: A002 - matches request field name
) -> list[str]:
    """Resolve a bulk/campaign target to a concrete, capped list of product IDs.

    Exactly one of `product_ids` or `filter` must be provided (the request model
    enforces this; asserted here defensively). Raises `BulkTargetLimitError` if
    the resolved set exceeds `BULK_DISCOUNT_TARGET_LIMIT` — before any write.
    """
    if (product_ids is None) == (filter is None):
        raise ValueError("exactly one of product_ids or filter must be provided")

    if product_ids is not None:
        # Preserve order, drop duplicates.
        resolved = list(dict.fromkeys(product_ids))
    else:
        with get_db() as conn:
            resolved = _resolve_filter_target_ids(conn, filter)

    if len(resolved) > BULK_DISCOUNT_TARGET_LIMIT:
        raise BulkTargetLimitError(
            f"target resolves to {len(resolved)} products; limit is {BULK_DISCOUNT_TARGET_LIMIT}"
        )
    return resolved


def bulk_update_discount(
    *,
    operation: Literal["apply", "remove"],
    product_ids: list[str],
    discount_percent: int | None = None,
    discount_starts_at: str | None = None,
    discount_ends_at: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict:
    """Apply or clear the discount on a resolved list of products.

    Runs on one connection with a per-product SAVEPOINT so a single product's
    failure (e.g. missing product) rolls back only that product while the rest
    commit. Reuses `merge_discount_update` for identical rules to the
    single-product path. Returns
    `{success_count, failure_count, results: [{id, status, error?}]}`.

    Callers must resolve/cap the target first via `resolve_bulk_target`. Pass an
    existing `conn` to run inside a caller-managed transaction (the caller then
    owns the commit); otherwise a connection is opened and committed here.
    """
    if operation == "apply" and discount_percent is None:
        raise DiscountValidationError("discount_percent is required for operation=apply")

    if operation == "apply":
        # Pass all three keys so the campaign window fully replaces any prior one.
        patch = {
            "discount_percent": discount_percent,
            "discount_starts_at": discount_starts_at,
            "discount_ends_at": discount_ends_at,
        }
    else:  # remove — clearing percent clears all three together
        patch = {"discount_percent": None}

    results: list[dict] = []
    success = 0

    def _run(conn: sqlite3.Connection) -> None:
        nonlocal success
        for pid in product_ids:
            conn.execute("SAVEPOINT bulk_item")
            try:
                existing = conn.execute(
                    "SELECT discount_percent, discount_starts_at, discount_ends_at "
                    "FROM products WHERE id = ?",
                    (pid,),
                ).fetchone()
                if existing is None:
                    raise NotFoundError(f"Product not found: {pid}")

                merged = merge_discount_update(existing, patch)
                conn.execute(
                    "UPDATE products SET discount_percent = ?, discount_starts_at = ?, "
                    "discount_ends_at = ? WHERE id = ?",
                    (
                        merged["discount_percent"],
                        merged["discount_starts_at"],
                        merged["discount_ends_at"],
                        pid,
                    ),
                )
            except (NotFoundError, DiscountValidationError) as e:
                conn.execute("ROLLBACK TO bulk_item")
                conn.execute("RELEASE bulk_item")
                results.append({"id": pid, "status": "failed", "error": str(e)})
            else:
                conn.execute("RELEASE bulk_item")
                results.append({"id": pid, "status": "updated"})
                success += 1

    if conn is not None:
        _run(conn)
    else:
        with get_db() as owned:
            _run(owned)

    return {
        "success_count": success,
        "failure_count": len(results) - success,
        "results": results,
    }


def conservative_clear_discount(
    targets: list[dict], conn: sqlite3.Connection | None = None
) -> dict:
    """Clear a discount only where a product's current fields still match.

    Each target: `{product_id, applied_percent, applied_starts_at, applied_ends_at}`
    — the values a campaign last wrote. A product is cleared only if its current
    discount fields still equal those; otherwise it is skipped (it was edited
    after apply) so a newer manual or campaign discount is never clobbered.
    Runs with per-product savepoints. Returns the same result shape as
    `bulk_update_discount`, with `status` in {updated, skipped, failed}. Pass an
    existing `conn` to run inside a caller-managed transaction.
    """
    results: list[dict] = []
    success = 0

    def _run(conn: sqlite3.Connection) -> None:
        nonlocal success
        for t in targets:
            pid = t["product_id"]
            conn.execute("SAVEPOINT clear_item")
            try:
                row = conn.execute(
                    "SELECT discount_percent, discount_starts_at, discount_ends_at "
                    "FROM products WHERE id = ?",
                    (pid,),
                ).fetchone()
                if row is None:
                    conn.execute("ROLLBACK TO clear_item")
                    conn.execute("RELEASE clear_item")
                    results.append({"id": pid, "status": "failed", "error": "Product not found"})
                    continue

                matches = (
                    row["discount_percent"] == t["applied_percent"]
                    and row["discount_starts_at"] == t["applied_starts_at"]
                    and row["discount_ends_at"] == t["applied_ends_at"]
                )
                if not matches:
                    conn.execute("RELEASE clear_item")
                    results.append(
                        {
                            "id": pid,
                            "status": "skipped",
                            "error": "discount changed after campaign apply; left unchanged",
                        }
                    )
                    continue

                conn.execute(
                    "UPDATE products SET discount_percent = NULL, "
                    "discount_starts_at = NULL, discount_ends_at = NULL WHERE id = ?",
                    (pid,),
                )
                conn.execute("RELEASE clear_item")
                results.append({"id": pid, "status": "updated"})
                success += 1
            except sqlite3.Error as e:
                conn.execute("ROLLBACK TO clear_item")
                conn.execute("RELEASE clear_item")
                results.append({"id": pid, "status": "failed", "error": str(e)})

    if conn is not None:
        _run(conn)
    else:
        with get_db() as owned:
            _run(owned)

    return {
        "success_count": success,
        "failure_count": len(results) - success,
        "results": results,
    }
