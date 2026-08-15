"""Product service — business logic for product CRUD, search, and listing."""

from datetime import UTC, datetime
from typing import Literal

import psycopg

from app.constants import MAX_LIMIT, MAX_PAGE
from app.database import DbConnection, get_db, require_row
from app.models.common import calculate_offset
from app.services import pricing, product_image_service, product_video_service, taxonomy_service

Locale = Literal["en", "bg"]

AdminProductStatusFilter = Literal["all", "active", "inactive"]
AdminProductMediaFilter = Literal["any", "ready", "missing_image", "has_video", "missing_video"]
AdminProductStockFilter = Literal["any", "in_stock", "out_of_stock", "low"]
AdminProductDiscountFilter = Literal["any", "active", "scheduled", "none"]
AdminProductInventoryModeFilter = Literal["legacy", "fallback", "ledger_managed"]
AdminProductRecipeStatusFilter = Literal["active", "missing", "draft", "archived"]
AdminProductSort = Literal[
    "created_desc",
    "created_asc",
    "updated_desc",
    "updated_asc",
    "name_asc",
    "name_desc",
    "price_asc",
    "price_desc",
    "stock_asc",
    "stock_desc",
]

DEFAULT_ADMIN_LOW_STOCK_THRESHOLD = 5

# Canonical UTC database timestamp string format shared across services.
# psycopg returns TIMESTAMPTZ columns as datetime; product response models and
# pricing.parse_discount_dt expect this string, so _row_to_dict normalises reads.
_DT_FMT = "%Y-%m-%d %H:%M:%S"
_TIMESTAMP_COLUMNS = ("created_at", "updated_at", "discount_starts_at", "discount_ends_at")


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


class LedgerManagedStockEditError(Exception):
    """Raised when direct stock editing is attempted for a ledger-managed product."""

    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        super().__init__("Ledger-managed product stock must be changed through inventory movements")


class ProductDeleteConflictError(Exception):
    """Raised when a product cannot be permanently deleted due to protected references."""


BULK_DISCOUNT_TARGET_LIMIT = 500


def _fmt_discount_ts(value: object) -> str | None:
    """Normalise a discount-bound read to the canonical ``_DT_FMT`` string.

    psycopg returns TIMESTAMPTZ columns as ``datetime``; ``None`` and existing
    strings pass through unchanged. Used to keep merge/window comparisons from
    mixing ``datetime`` (persisted) with ``str`` (patch).
    """
    if isinstance(value, datetime):
        return value.strftime(_DT_FMT)
    return value  # type: ignore[return-value]


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


def merge_discount_update(existing: dict, data: dict) -> dict:
    """Merge a partial discount patch with the existing row and validate it.

    Shared by the single-product update path and the bulk discount path so both
    honor identical rules. Returns the merged, validated
    `{discount_percent, discount_starts_at, discount_ends_at}`. Passing
    `discount_percent=None` clears all three together. Raises
    `DiscountValidationError` on an invalid merged result.
    """
    # ``existing`` is read straight from Postgres, so its TIMESTAMPTZ discount
    # bounds arrive as ``datetime``; the patch (``data``) carries canonical
    # ``_DT_FMT`` strings. Normalise the persisted bounds to the same string
    # shape so the merge and window comparison never mix datetime with str.
    existing_starts = _fmt_discount_ts(existing.get("discount_starts_at"))
    existing_ends = _fmt_discount_ts(existing.get("discount_ends_at"))
    if "discount_percent" in data and data["discount_percent"] is None:
        # Clearing the discount clears all three fields together.
        merged_percent = merged_starts = merged_ends = None
    else:
        merged_percent = (
            data["discount_percent"] if "discount_percent" in data else existing["discount_percent"]
        )
        merged_starts = (
            data["discount_starts_at"] if "discount_starts_at" in data else existing_starts
        )
        merged_ends = data["discount_ends_at"] if "discount_ends_at" in data else existing_ends
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


def _row_to_dict(row: dict) -> dict:
    """Convert a database row to a plain dict.

    Postgres TIMESTAMPTZ columns come back from psycopg (dict_row) as
    ``datetime`` objects, but the product response models declare every
    timestamp field as ``str`` (and ``pricing._parse_discount_dt`` parses the
    discount bounds as the canonical ``_DT_FMT`` string). Products are written
    with ``_now_utc()`` strings, so normalise reads through this single
    chokepoint to the same shape. ``None`` and existing strings pass through.
    """
    product = dict(row)
    for column in _TIMESTAMP_COLUMNS:
        value = product.get(column)
        if isinstance(value, datetime):
            product[column] = value.strftime(_DT_FMT)
    return product


def _flatten_admin_labels(product: dict) -> dict:
    """Collapse resolved label refs ([{slug, name}]) down to slugs for admin responses."""
    product["labels"] = [ref["slug"] for ref in product.get("labels", [])]
    return product


def _attach_admin_inventory_context(conn: DbConnection, products: list[dict]) -> None:
    """Attach admin-only inventory/recipe/batch context without changing public payloads."""
    if not products:
        return
    product_ids = [product["id"] for product in products]
    placeholders = ", ".join("%s" for _ in product_ids)

    profiles = {
        row["product_id"]: row
        for row in conn.execute(
            f"SELECT * FROM product_inventory_profiles WHERE product_id IN ({placeholders})",  # noqa: S608
            product_ids,
        ).fetchall()
    }

    active_recipes: dict[str, dict] = {}
    for row in conn.execute(
        f"""
        SELECT id, product_id, status, effective_date, review_state
        FROM recipe_versions
        WHERE product_id IN ({placeholders}) AND status = 'active'
        ORDER BY product_id, effective_date DESC, created_at DESC
        """,  # noqa: S608
        product_ids,
    ).fetchall():
        active_recipes.setdefault(row["product_id"], row)

    latest_batches: dict[str, dict] = {}
    for row in conn.execute(
        f"""
        SELECT id, product_id, batch_number, status, production_date
        FROM production_batches
        WHERE product_id IN ({placeholders})
        ORDER BY product_id, production_date DESC, created_at DESC
        """,  # noqa: S608
        product_ids,
    ).fetchall():
        latest_batches.setdefault(row["product_id"], row)

    exception_counts = {
        row["target_id"]: row["count"]
        for row in conn.execute(
            f"""
            SELECT target_id, COUNT(*) AS count
            FROM inventory_exceptions
            WHERE status = 'open'
              AND target_type = 'product'
              AND target_id IN ({placeholders})
            GROUP BY target_id
            """,  # noqa: S608
            product_ids,
        ).fetchall()
    }
    exceptions_by_product: dict[str, list[dict]] = {product_id: [] for product_id in product_ids}
    for row in conn.execute(
        f"""
        SELECT id, exception_type, severity, target_id, message, created_at
        FROM inventory_exceptions
        WHERE status = 'open'
          AND target_type = 'product'
          AND target_id IN ({placeholders})
        ORDER BY created_at DESC, id DESC
        """,  # noqa: S608
        product_ids,
    ).fetchall():
        exceptions_by_product.setdefault(row["target_id"], []).append(dict(row))

    for product in products:
        product_id = product["id"]
        profile = profiles.get(product_id)
        recipe = active_recipes.get(product_id)
        batch = latest_batches.get(product_id)
        inventory_mode = profile["inventory_mode"] if profile else "legacy"
        product["inventory_mode"] = inventory_mode
        product["stock_source"] = profile["stock_source"] if profile else "product_stock"
        product["ledger_managed"] = inventory_mode == "ledger_managed"
        product["valuation_readiness"] = (
            profile["valuation_readiness"] if profile else "setup_required"
        )
        product["active_recipe_id"] = recipe["id"] if recipe else None
        product["active_recipe_status"] = recipe["status"] if recipe else "missing"
        product["active_recipe_review_state"] = recipe["review_state"] if recipe else None
        product["latest_batch_id"] = batch["id"] if batch else None
        product["latest_batch_number"] = batch["batch_number"] if batch else None
        product["latest_batch_status"] = batch["status"] if batch else None
        product["latest_batch_date"] = (
            batch["production_date"].isoformat()
            if batch and hasattr(batch["production_date"], "isoformat")
            else (batch["production_date"] if batch else None)
        )
        product["inventory_exception_count"] = int(exception_counts.get(product_id, 0))
        product["inventory_exceptions"] = exceptions_by_product.get(product_id, [])
        product["inventory_links"] = {
            "recipes_href": f"/admin/inventory/recipes?product_id={product_id}",
            "batches_href": f"/admin/inventory/batches?product_id={product_id}",
            "movements_href": (
                f"/admin/inventory/movements?item_type=finished_good&item_id={product_id}"
            ),
            "valuation_href": (
                f"/admin/inventory/valuation/layers?item_type=finished_good&item_id={product_id}"
            ),
            "cogs_href": f"/admin/inventory/valuation/cogs?product_id={product_id}",
            "exceptions_href": (
                f"/admin/inventory/valuation/exceptions?target_type=product&target_id={product_id}"
            ),
        }


def _resolve_locale_fields(product: dict, locale: Locale) -> dict:
    """Resolve locale-specific name/description with fallback to other language.

    Returns a new dict with `name` and `description` fields set to the
    appropriate locale's content (or the fallback language if the preferred
    one is empty/NULL).
    """
    other = "bg" if locale == "en" else "en"

    name = product.get(f"name_{locale}") or product.get(f"name_{other}") or ""
    description = product.get(f"description_{locale}") or product.get(f"description_{other}")
    safety_warnings = product.get(f"safety_warnings_{locale}") or product.get(
        f"safety_warnings_{other}"
    )
    care_instructions = product.get(f"care_instructions_{locale}") or product.get(
        f"care_instructions_{other}"
    )

    result = dict(product)
    result["name"] = name
    result["description"] = description
    result["safety_warnings"] = safety_warnings
    result["care_instructions"] = care_instructions
    return result


def _apply_orderability_fields(product: dict) -> dict:
    """Annotate a public product payload with orderability metadata."""
    stock = max(0, int(product.get("stock") or 0))
    is_active = bool(product.get("is_active", True))
    result = dict(product)
    result["can_order"] = is_active
    result["available_now"] = stock > 0
    result["availability_status"] = "in_stock" if stock > 0 else "crafted_later"
    result["ships_when_complete"] = True
    return result


def _now_utc() -> str:
    """Return current UTC timestamp as 'YYYY-MM-DD HH:MM:SS'."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _sanitize_fts5_query(query: str) -> str:
    """Normalize user input for a Postgres ``plainto_tsquery`` search.

    ``plainto_tsquery`` tokenizes and AND-combines the terms itself and treats
    the argument purely as data (bound as a parameter), so no manual escaping of
    query operators is needed — we only collapse whitespace and return "" when
    there is nothing searchable.
    """
    return " ".join(query.split())


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards for literal admin search."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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


def _admin_label_condition(labels: list[str]) -> tuple[str, list]:
    """Return an AND-semantics label condition for admin product filters."""
    unique_labels = list(dict.fromkeys(labels))
    placeholders = ", ".join("%s" for _ in unique_labels)
    return (
        f"p.id IN (SELECT product_id FROM product_label_assignments "  # noqa: S608
        f"WHERE label_slug IN ({placeholders}) "
        "GROUP BY product_id HAVING COUNT(DISTINCT label_slug) = %s)",
        [*unique_labels, len(unique_labels)],
    )


def _build_admin_product_filters(
    *,
    q: str | None,
    status: AdminProductStatusFilter | None,
    media: AdminProductMediaFilter | None,
    stock: AdminProductStockFilter | None,
    product_type: str | None,
    category: str | None,
    labels: list[str] | None,
    featured: bool | None,
    discount: AdminProductDiscountFilter | None,
    inventory_mode: AdminProductInventoryModeFilter | None,
    recipe_status: AdminProductRecipeStatusFilter | None,
    has_inventory_exceptions: bool | None,
    low_stock_threshold: int,
    now: str,
) -> tuple[list[str], list]:
    """Build WHERE conditions + params for the admin product list."""
    conditions: list[str] = []
    params: list = []

    if q and q.strip():
        pattern = f"%{_escape_like(q.strip())}%"
        conditions.append(
            "(p.id ILIKE %s ESCAPE '\\' OR p.name_en ILIKE %s ESCAPE '\\' "
            "OR COALESCE(p.name_bg, '') ILIKE %s ESCAPE '\\' "
            "OR COALESCE(p.description_en, '') ILIKE %s ESCAPE '\\' "
            "OR COALESCE(p.description_bg, '') ILIKE %s ESCAPE '\\')"
        )
        params.extend([pattern, pattern, pattern, pattern, pattern])

    if status == "active":
        conditions.append("p.is_active = 1")
    elif status == "inactive":
        conditions.append("p.is_active = 0")

    if media == "ready":
        conditions.append("EXISTS (SELECT 1 FROM product_images pi WHERE pi.product_id = p.id)")
    elif media == "missing_image":
        conditions.append("NOT EXISTS (SELECT 1 FROM product_images pi WHERE pi.product_id = p.id)")
    elif media == "has_video":
        conditions.append("EXISTS (SELECT 1 FROM product_videos pv WHERE pv.product_id = p.id)")
    elif media == "missing_video":
        conditions.append("NOT EXISTS (SELECT 1 FROM product_videos pv WHERE pv.product_id = p.id)")

    if stock == "in_stock":
        conditions.append("p.stock > 0")
    elif stock == "out_of_stock":
        conditions.append("p.stock = 0")
    elif stock == "low":
        conditions.append("p.stock <= %s")
        params.append(low_stock_threshold)

    if product_type:
        conditions.append("p.product_type_slug = %s")
        params.append(product_type)

    if category:
        conditions.append("p.category_slug = %s")
        params.append(category)

    if labels:
        condition, label_params = _admin_label_condition(labels)
        conditions.append(condition)
        params.extend(label_params)

    if featured is not None:
        conditions.append("p.is_featured = %s")
        params.append(1 if featured else 0)

    if discount == "active":
        conditions.append(
            "(p.discount_percent IS NOT NULL "
            "AND (p.discount_starts_at IS NULL OR p.discount_starts_at <= %s) "
            "AND (p.discount_ends_at IS NULL OR p.discount_ends_at >= %s))"
        )
        params.extend([now, now])
    elif discount == "scheduled":
        conditions.append(
            "(p.discount_percent IS NOT NULL "
            "AND p.discount_starts_at IS NOT NULL "
            "AND p.discount_starts_at > %s)"
        )
        params.append(now)
    elif discount == "none":
        conditions.append("p.discount_percent IS NULL")

    if inventory_mode:
        conditions.append(
            "COALESCE((SELECT pip.inventory_mode FROM product_inventory_profiles pip "
            "WHERE pip.product_id = p.id), 'legacy') = %s"
        )
        params.append(inventory_mode)

    if recipe_status == "active":
        conditions.append(
            "EXISTS (SELECT 1 FROM recipe_versions rv "
            "WHERE rv.product_id = p.id AND rv.status = 'active')"
        )
    elif recipe_status == "missing":
        conditions.append(
            "NOT EXISTS (SELECT 1 FROM recipe_versions rv "
            "WHERE rv.product_id = p.id AND rv.status = 'active')"
        )
    elif recipe_status in {"draft", "archived"}:
        conditions.append(
            "EXISTS (SELECT 1 FROM recipe_versions rv "
            "WHERE rv.product_id = p.id AND rv.status = %s)"
        )
        params.append(recipe_status)

    if has_inventory_exceptions is True:
        conditions.append(
            "EXISTS (SELECT 1 FROM inventory_exceptions ie "
            "WHERE ie.target_type = 'product' AND ie.target_id = p.id AND ie.status = 'open')"
        )
    elif has_inventory_exceptions is False:
        conditions.append(
            "NOT EXISTS (SELECT 1 FROM inventory_exceptions ie "
            "WHERE ie.target_type = 'product' AND ie.target_id = p.id AND ie.status = 'open')"
        )

    return conditions, params


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
    total_count) with locale-resolved names, taxonomy display metadata, and
    public discount pricing fields.
    """
    page, limit = _clamp_pagination(page, limit)

    conditions = ["is_active = 1"]
    params: list = []

    if product_type:
        conditions.append("product_type_slug = %s")
        params.append(product_type)

    if category:
        conditions.append("category_slug = %s")
        params.append(category)

    if labels:
        # De-duplicate so the HAVING COUNT(DISTINCT) equality holds even if a
        # caller passes repeated slugs (the route already de-dupes; belt-and-braces).
        unique_labels = list(dict.fromkeys(labels))
        placeholders = ", ".join("%s" for _ in unique_labels)
        conditions.append(
            f"id IN (SELECT product_id FROM product_label_assignments "  # noqa: S608
            f"WHERE label_slug IN ({placeholders}) "
            "GROUP BY product_id HAVING COUNT(DISTINCT label_slug) = %s)"
        )
        params.extend(unique_labels)
        params.append(len(unique_labels))

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
        total = require_row(count_row)["cnt"]

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
                f"ORDER BY {order_by} LIMIT %s OFFSET %s",
                [*params, limit, offset],
            ).fetchall()

        products = [_resolve_locale_fields(_row_to_dict(r), locale) for r in rows]
        taxonomy_service.resolve_products_taxonomy(conn, products, locale)

    products = [
        _apply_orderability_fields(pricing.annotate_product_pricing(p, now, public=True))
        for p in products
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
            "SELECT * FROM products WHERE id = %s AND is_active = 1",
            (product_id,),
        ).fetchone()

        if row is None:
            raise NotFoundError(f"Product not found: {product_id}")

        product = _resolve_locale_fields(_row_to_dict(row), locale)
        taxonomy_service.resolve_products_taxonomy(conn, [product], locale)

    product = _apply_orderability_fields(
        pricing.annotate_product_pricing(product, pricing.now_utc(), public=True)
    )
    product = product_image_service.attach_image_fields_one(product)
    return product_video_service.attach_video_fields_one(product, public_only=True)


def get_product_admin(product_id: str) -> dict:
    """Get any product (active or inactive) by ID. For admin use.

    Taxonomy is exposed as slugs (`product_type`, `category`, `labels`) so admin
    form controls can prefill assignments.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = %s",
            (product_id,),
        ).fetchone()

        if row is None:
            raise NotFoundError(f"Product not found: {product_id}")

        product = _row_to_dict(row)
        taxonomy_service.resolve_products_taxonomy(conn, [product], "en")
        _attach_admin_inventory_context(conn, [product])

    product = _flatten_admin_labels(_annotate_admin_one(product))
    product = product_image_service.attach_image_fields_one(product)
    return product_video_service.attach_video_fields_one(product, public_only=False)


def product_exists(product_id: str) -> bool:
    """Lightweight existence check (no taxonomy/image/pricing resolution).

    For bulk paths like CSV import that only need created-vs-updated, not the
    full product payload.
    """
    with get_db() as conn:
        return (
            conn.execute("SELECT 1 FROM products WHERE id = %s", (product_id,)).fetchone()
            is not None
        )


def list_products_admin(
    *,
    q: str | None = None,
    status: AdminProductStatusFilter | None = None,
    media: AdminProductMediaFilter | None = None,
    stock: AdminProductStockFilter | None = None,
    product_type: str | None = None,
    category: str | None = None,
    labels: list[str] | None = None,
    featured: bool | None = None,
    discount: AdminProductDiscountFilter | None = None,
    inventory_mode: AdminProductInventoryModeFilter | None = None,
    recipe_status: AdminProductRecipeStatusFilter | None = None,
    has_inventory_exceptions: bool | None = None,
    low_stock_threshold: int = DEFAULT_ADMIN_LOW_STOCK_THRESHOLD,
    sort: AdminProductSort | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """List admin products with optional filters, sorting, and pagination."""
    offset = calculate_offset(page, limit)
    now = pricing.now_utc()

    conditions, params = _build_admin_product_filters(
        q=q,
        status=status,
        media=media,
        stock=stock,
        product_type=product_type,
        category=category,
        labels=labels,
        featured=featured,
        discount=discount,
        inventory_mode=inventory_mode,
        recipe_status=recipe_status,
        has_inventory_exceptions=has_inventory_exceptions,
        low_stock_threshold=low_stock_threshold,
        now=now,
    )
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    order_by_map = {
        "created_desc": "p.created_at DESC, p.id ASC",
        "created_asc": "p.created_at ASC, p.id ASC",
        "updated_desc": "p.updated_at DESC, p.id ASC",
        "updated_asc": "p.updated_at ASC, p.id ASC",
        "name_asc": "LOWER(p.name_en) ASC, p.id ASC",
        "name_desc": "LOWER(p.name_en) DESC, p.id ASC",
        "price_asc": "p.price_cents ASC, p.id ASC",
        "price_desc": "p.price_cents DESC, p.id ASC",
        "stock_asc": "p.stock ASC, p.id ASC",
        "stock_desc": "p.stock DESC, p.id ASC",
    }
    order_by = order_by_map.get(sort or "", "p.created_at DESC, p.id ASC")

    with get_db() as conn:
        count_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM products p {where_clause}",  # noqa: S608
            params,
        ).fetchone()
        total = require_row(count_row)["cnt"]

        rows = conn.execute(
            f"SELECT p.* FROM products p {where_clause} "  # noqa: S608
            f"ORDER BY {order_by} LIMIT %s OFFSET %s",
            [*params, limit, offset],
        ).fetchall()

        products = [_row_to_dict(r) for r in rows]
        taxonomy_service.resolve_products_taxonomy(conn, products, "en")
        _attach_admin_inventory_context(conn, products)

    products = [_flatten_admin_labels(p) for p in _annotate_admin(products, now=now)]
    products = product_image_service.attach_image_fields(products)
    products = product_video_service.attach_video_fields(products, public_only=False)
    return products, total


def create_product(data: dict) -> dict:
    """Create a new product. Raises DuplicateError if ID exists, TaxonomyValidationError
    if the product type / category / labels are unknown or inactive."""
    now = _now_utc()
    product_id = data["id"]
    # Normalize a blank category to NULL so it never persists as an empty-string slug.
    category_slug = data.get("category") or None
    label_slugs = data.get("labels") or []

    columns = [
        "id",
        "name_en",
        "name_bg",
        "description_en",
        "description_bg",
        "safety_warnings_en",
        "safety_warnings_bg",
        "care_instructions_en",
        "care_instructions_bg",
        "materials",
        "days_to_craft",
        "price_cents",
        "product_type_slug",
        "category_slug",
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

    with get_db() as conn:
        # Resolve the default product type (lowest sort_order active) when omitted,
        # rather than hardcoding a slug.
        product_type = data.get("product_type") or taxonomy_service.default_product_type(conn)

        # Validate taxonomy assignments against managed active terms before write.
        taxonomy_service.validate_product_type(conn, product_type)
        taxonomy_service.validate_category(conn, category_slug)
        taxonomy_service.validate_labels(conn, label_slugs)

        values = [
            product_id,
            data["name_en"],
            data.get("name_bg"),
            data.get("description_en"),
            data.get("description_bg"),
            data.get("safety_warnings_en"),
            data.get("safety_warnings_bg"),
            data.get("care_instructions_en"),
            data.get("care_instructions_bg"),
            data.get("materials"),
            data.get("days_to_craft"),
            data["price_cents"],
            product_type,
            category_slug,
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
        placeholders = ", ".join("%s" for _ in columns)
        col_str = ", ".join(columns)

        try:
            conn.execute(
                f"INSERT INTO products ({col_str}) VALUES ({placeholders})",  # noqa: S608
                values,
            )
        except psycopg.errors.UniqueViolation as e:
            raise DuplicateError(f"Product with this ID already exists: {product_id}") from e

        taxonomy_service.replace_product_labels(conn, product_id, label_slugs)

        row = conn.execute("SELECT * FROM products WHERE id = %s", (product_id,)).fetchone()
        product = _row_to_dict(require_row(row, "product row missing after create"))
        taxonomy_service.resolve_products_taxonomy(conn, [product], "en")
        _attach_admin_inventory_context(conn, [product])

    product = _flatten_admin_labels(_annotate_admin_one(product))
    product = product_image_service.attach_image_fields_one(product)
    return product_video_service.attach_video_fields_one(product, public_only=False)


def upsert_product(product_id: str, data: dict) -> dict:
    """Create or update a product using INSERT ... ON CONFLICT DO UPDATE.

    Only non-None fields in data are updated on conflict. Taxonomy values, when
    provided, are validated against existing ACTIVE terms (CSV import never
    auto-creates taxonomy and never preserves inactive terms).
    """
    now = _now_utc()
    labels = data.get("labels")  # None → leave assignments untouched

    with get_db() as conn:
        # Distinguish insert from update so a new row's product type is resolved
        # and validated like create_product. An update that omits product_type
        # must preserve the current (possibly inactive) assignment.
        existing_product = conn.execute(
            """
            SELECT p.stock, COALESCE(pip.inventory_mode, 'legacy') AS inventory_mode
            FROM products p
            LEFT JOIN product_inventory_profiles pip ON pip.product_id = p.id
            WHERE p.id = %s
            """,
            (product_id,),
        ).fetchone()
        is_insert = existing_product is None
        if (
            existing_product is not None
            and existing_product["inventory_mode"] == "ledger_managed"
            and data.get("stock") is not None
            and int(data["stock"]) != int(existing_product["stock"])
        ):
            raise LedgerManagedStockEditError(product_id)
        if data.get("product_type"):
            taxonomy_service.validate_product_type(conn, data["product_type"])
            product_type_slug = data["product_type"]
        elif is_insert:
            # No type supplied on a new product → assign the default active type.
            product_type_slug = taxonomy_service.default_product_type(conn)
        else:
            product_type_slug = None  # update path: leave the column untouched
        if data.get("category"):
            taxonomy_service.validate_category(conn, data["category"])
        if labels is not None:
            taxonomy_service.validate_labels(conn, labels)

        # Fields that can be set on insert/update (None → not supplied).
        field_map = {
            "name_en": data.get("name_en"),
            "name_bg": data.get("name_bg"),
            "description_en": data.get("description_en"),
            "description_bg": data.get("description_bg"),
            "safety_warnings_en": data.get("safety_warnings_en"),
            "safety_warnings_bg": data.get("safety_warnings_bg"),
            "care_instructions_en": data.get("care_instructions_en"),
            "care_instructions_bg": data.get("care_instructions_bg"),
            "materials": data.get("materials"),
            "days_to_craft": data.get("days_to_craft"),
            "price_cents": data.get("price_cents"),
            # Taxonomy slugs — only touched when supplied (or defaulted on insert).
            "product_type_slug": product_type_slug,
            "category_slug": (data.get("category") or None),
            "stock": data.get("stock"),
            "weight_grams": data.get("weight_grams"),
            "is_active": (
                None if data.get("is_active") is None else (1 if data["is_active"] else 0)
            ),
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
        placeholders = ", ".join("%s" for _ in insert_cols)
        update_str = ", ".join(update_parts)
        sql = (
            f"INSERT INTO products ({col_str}) VALUES ({placeholders}) "  # noqa: S608
            f"ON CONFLICT(id) DO UPDATE SET {update_str}"
        )

        conn.execute(sql, insert_vals)

        if labels is not None:
            taxonomy_service.replace_product_labels(conn, product_id, labels)

        row = conn.execute("SELECT * FROM products WHERE id = %s", (product_id,)).fetchone()
        product = _row_to_dict(require_row(row, "product row missing after update"))
        taxonomy_service.resolve_products_taxonomy(conn, [product], "en")
        _attach_admin_inventory_context(conn, [product])

    product = _flatten_admin_labels(_annotate_admin_one(product))
    product = product_image_service.attach_image_fields_one(product)
    return product_video_service.attach_video_fields_one(product, public_only=False)


def update_product(product_id: str, data: dict) -> dict:
    """Partially update a product. Only provided fields are modified.

    `data` should come from model_dump(exclude_unset=True) so presence is
    meaningful. Taxonomy reassignments validate against active terms while
    allowing the product to keep its current (possibly inactive) assignments;
    assigning a *different* inactive term is rejected. Category may be set NULL.
    Discount fields are merged with the persisted row and validated.

    Implements translation staleness logic:
    - If EN content changes, mark BG as stale (unless BG also updated in same request)
    - If BG content changes, mark EN as stale (unless EN also updated in same request)
    - Updating the stale side clears its staleness flag

    Raises NotFoundError if the product does not exist.
    """
    with get_db() as conn:
        current = conn.execute(
            """
            SELECT p.product_type_slug, p.category_slug, p.discount_percent,
                   p.discount_starts_at, p.discount_ends_at, p.stock,
                   COALESCE(pip.inventory_mode, 'legacy') AS inventory_mode
            FROM products p
            LEFT JOIN product_inventory_profiles pip ON pip.product_id = p.id
            WHERE p.id = %s
            """,
            (product_id,),
        ).fetchone()
        if current is None:
            raise NotFoundError(f"Product not found: {product_id}")

        if (
            current["inventory_mode"] == "ledger_managed"
            and "stock" in data
            and data["stock"] is not None
            and int(data["stock"]) != int(current["stock"])
        ):
            raise LedgerManagedStockEditError(product_id)

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
            "safety_warnings_en": data.get("safety_warnings_en"),
            "safety_warnings_bg": data.get("safety_warnings_bg"),
            "care_instructions_en": data.get("care_instructions_en"),
            "care_instructions_bg": data.get("care_instructions_bg"),
            "materials": data.get("materials"),
            "days_to_craft": data.get("days_to_craft"),
            "price_cents": data.get("price_cents"),
            "stock": data.get("stock"),
            "weight_grams": data.get("weight_grams"),
            "is_active": (
                None if data.get("is_active") is None else (1 if data["is_active"] else 0)
            ),
            "is_featured": (
                None if data.get("is_featured") is None else (1 if data["is_featured"] else 0)
            ),
        }
        updates = {k: v for k, v in field_map.items() if v is not None}

        # Discount fields need explicit NULL writes (to clear a discount), so they
        # merge the patch with the persisted row, then validate the merged result.
        discount_keys = {"discount_percent", "discount_starts_at", "discount_ends_at"}
        if discount_keys & data.keys():
            merged = merge_discount_update(current, data)
            updates["discount_percent"] = merged["discount_percent"]
            updates["discount_starts_at"] = merged["discount_starts_at"]
            updates["discount_ends_at"] = merged["discount_ends_at"]

        # Taxonomy column updates (category may be explicitly NULL).
        if type_update:
            updates["product_type_slug"] = data["product_type"]
        if category_update:
            # Blank category clears to NULL rather than persisting an empty slug.
            updates["category_slug"] = data["category"] or None

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
            set_clause = ", ".join(f"{col} = %s" for col in updates)
            conn.execute(
                f"UPDATE products SET {set_clause} WHERE id = %s",  # noqa: S608
                [*updates.values(), product_id],
            )

        if labels_update:
            taxonomy_service.replace_product_labels(conn, product_id, data["labels"])
            if not updates:
                # A label-only change still modifies the product; touch the row so
                # the products_updated_at trigger refreshes updated_at.
                conn.execute(
                    "UPDATE products SET updated_at = updated_at WHERE id = %s",
                    (product_id,),
                )

        row = conn.execute("SELECT * FROM products WHERE id = %s", (product_id,)).fetchone()
        product = _row_to_dict(require_row(row, "product row missing after image update"))
        taxonomy_service.resolve_products_taxonomy(conn, [product], "en")
        _attach_admin_inventory_context(conn, [product])

    product = _flatten_admin_labels(_annotate_admin_one(product))
    product = product_image_service.attach_image_fields_one(product)
    return product_video_service.attach_video_fields_one(product, public_only=False)


def deactivate_product(product_id: str) -> dict:
    """Soft-delete a product by setting is_active=0. Idempotent.

    Raises NotFoundError if the product does not exist.
    """
    with get_db() as conn:
        # Check existence first (for 404)
        row = conn.execute("SELECT * FROM products WHERE id = %s", (product_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Product not found: {product_id}")

    product_video_service.delete_video_if_exists(product_id)
    # Soft-delete removes the product's images entirely (rows + backing objects),
    # not just the objects: leaving rows while deleting objects would let a later
    # reactivation point at media that no longer exists.
    product_image_service.delete_images_for_product(product_id)

    with get_db() as conn:
        conn.execute(
            "UPDATE products SET is_active = 0 WHERE id = %s",
            (product_id,),
        )

        row = conn.execute("SELECT * FROM products WHERE id = %s", (product_id,)).fetchone()
        product = _row_to_dict(require_row(row, "product row missing after deactivate"))
        taxonomy_service.resolve_products_taxonomy(conn, [product], "en")
        _attach_admin_inventory_context(conn, [product])

    product = _flatten_admin_labels(_annotate_admin_one(product))
    product = product_image_service.attach_image_fields_one(product)
    return product_video_service.attach_video_fields_one(product, public_only=False)


def delete_product(product_id: str) -> None:
    """Permanently delete a product when no protected references remain.

    Product media is cleaned up first, cart rows are removed explicitly, and the
    product row is then deleted. Foreign-key-restricted references (for example
    production records) surface as ProductDeleteConflictError so the route can
    return a clear 409 instead of a generic 500.
    """
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM products WHERE id = %s", (product_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Product not found: {product_id}")

    product_video_service.delete_video_if_exists(product_id)
    product_image_service.delete_images_for_product(product_id)

    try:
        with get_db() as conn:
            conn.execute("DELETE FROM cart_items WHERE product_id = %s", (product_id,))
            cursor = conn.execute("DELETE FROM products WHERE id = %s", (product_id,))
            if cursor.rowcount == 0:
                raise NotFoundError(f"Product not found: {product_id}")
    except psycopg.errors.ForeignKeyViolation as exc:
        raise ProductDeleteConflictError(
            f"Product {product_id} is still referenced by protected records"
        ) from exc


def _fts_expression(locale: Locale) -> str:
    """Postgres tsvector expression matching the GIN search index for a locale.

    Mirrors idx_products_search_{en,bg} exactly so the index is usable.
    """
    return (
        f"to_tsvector('simple', COALESCE(p.name_{locale}, '') || ' ' "
        f"|| COALESCE(p.description_{locale}, ''))"
    )


def _build_search_conditions(
    sanitized: str,
    locale: Locale,
    *,
    product_type: str | None,
    category: str | None,
    labels: list[str] | None,
    in_stock: bool | None,
) -> tuple[list[str], list]:
    """Build the shared WHERE conditions + params for FTS search and its count.

    Returns (conditions, params) covering only the WHERE clause (no LIMIT/OFFSET).
    """
    conditions = [
        f"{_fts_expression(locale)} @@ plainto_tsquery('simple', %s)",
        "p.is_active = 1",
    ]
    params: list = [sanitized]

    if product_type:
        conditions.append("p.product_type_slug = %s")
        params.append(product_type)

    if category:
        conditions.append("p.category_slug = %s")
        params.append(category)

    if labels:
        unique_labels = list(dict.fromkeys(labels))
        placeholders = ", ".join("%s" for _ in unique_labels)
        conditions.append(
            f"p.id IN (SELECT product_id FROM product_label_assignments "  # noqa: S608
            f"WHERE label_slug IN ({placeholders}) "
            "GROUP BY product_id HAVING COUNT(DISTINCT label_slug) = %s)"
        )
        params.extend(unique_labels)
        params.append(len(unique_labels))

    if in_stock:
        conditions.append("p.stock > 0")

    return conditions, params


def count_search_products(
    query: str,
    *,
    product_type: str | None = None,
    category: str | None = None,
    labels: list[str] | None = None,
    in_stock: bool | None = None,
    locale: Locale = "en",
) -> int:
    """Total matches for an FTS search with the same filters as search_products.

    Lets the search route return an accurate paginated `total` instead of the
    current page size. Returns 0 for empty/blank queries.
    """
    if not query or not query.strip():
        return 0
    sanitized = _sanitize_fts5_query(query)
    if not sanitized:
        return 0

    conditions, params = _build_search_conditions(
        sanitized,
        locale,
        product_type=product_type,
        category=category,
        labels=labels,
        in_stock=in_stock,
    )
    where_clause = " AND ".join(conditions)
    with get_db() as conn:
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS cnt
            FROM products p
            WHERE {where_clause}
            """,  # noqa: S608
            params,
        ).fetchone()
    return require_row(row)["cnt"]


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
    sort: str | None = None,
) -> list[dict]:
    """Full-text search on product name and description using FTS5.

    Searches the locale-appropriate FTS index (products_fts_en or products_fts_bg).
    Returns active products ranked by relevance with locale-resolved content,
    taxonomy display metadata, and public discount pricing fields. Taxonomy
    filters (product_type, category slug, labels) and in_stock/LIMIT/OFFSET are
    pushed into SQL.

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

    conditions, params = _build_search_conditions(
        sanitized,
        locale,
        product_type=product_type,
        category=category,
        labels=labels,
        in_stock=in_stock,
    )
    where_clause = " AND ".join(conditions)
    rank_expr = f"ts_rank({_fts_expression(locale)}, plainto_tsquery('simple', %s))"

    now = pricing.now_utc()
    price_sort = sort in ("price_asc", "price_desc")

    with get_db() as conn:
        if price_sort:
            # Fetch all matches; effective-price sort + pagination happen below.
            rows = conn.execute(
                f"""
                SELECT p.*
                FROM products p
                WHERE {where_clause}
                ORDER BY {rank_expr} DESC, p.id
                """,  # noqa: S608
                [*params, sanitized],
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT p.*
                FROM products p
                WHERE {where_clause}
                ORDER BY {rank_expr} DESC, p.id
                LIMIT %s OFFSET %s
                """,  # noqa: S608
                [*params, sanitized, limit, offset],
            ).fetchall()

        products = [_resolve_locale_fields(_row_to_dict(r), locale) for r in rows]
        taxonomy_service.resolve_products_taxonomy(conn, products, locale)

    products = [
        _apply_orderability_fields(pricing.annotate_product_pricing(p, now, public=True))
        for p in products
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
            "SELECT * FROM products WHERE stock <= %s AND is_active = 1",
            (threshold,),
        ).fetchall()
        products = [_row_to_dict(r) for r in rows]
        taxonomy_service.resolve_products_taxonomy(conn, products, "en")
        _attach_admin_inventory_context(conn, products)
    products = [_flatten_admin_labels(p) for p in _annotate_admin(products)]
    products = product_image_service.attach_image_fields(products)
    return product_video_service.attach_video_fields(products, public_only=False)


def _resolve_filter_target_ids(conn: DbConnection, filt: dict) -> list[str]:
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
            "(name_en ILIKE %s ESCAPE '\\' "
            "OR name_bg ILIKE %s ESCAPE '\\' "
            "OR id ILIKE %s ESCAPE '\\')"
        )
        # Escape LIKE wildcards so a query like "50%" matches literally.
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        params.extend([like, like, like])
    if filt.get("category"):
        conditions.append("category_slug = %s")
        params.append(filt["category"])
    if filt.get("is_active") is not None:
        conditions.append("is_active = %s")
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
        if filter is None:
            raise ValueError("filter must be provided")
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
    conn: DbConnection | None = None,
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

    def _run(conn: DbConnection) -> None:
        nonlocal success
        for pid in product_ids:
            conn.execute("SAVEPOINT bulk_item")
            try:
                existing = conn.execute(
                    "SELECT discount_percent, discount_starts_at, discount_ends_at "
                    "FROM products WHERE id = %s",
                    (pid,),
                ).fetchone()
                if existing is None:
                    raise NotFoundError(f"Product not found: {pid}")

                merged = merge_discount_update(existing, patch)
                conn.execute(
                    "UPDATE products SET discount_percent = %s, discount_starts_at = %s, "
                    "discount_ends_at = %s WHERE id = %s",
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


def conservative_clear_discount(targets: list[dict], conn: DbConnection | None = None) -> dict:
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

    def _run(conn: DbConnection) -> None:
        nonlocal success
        for t in targets:
            pid = t["product_id"]
            conn.execute("SAVEPOINT clear_item")
            try:
                row = conn.execute(
                    "SELECT discount_percent, discount_starts_at, discount_ends_at "
                    "FROM products WHERE id = %s",
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
                    "discount_starts_at = NULL, discount_ends_at = NULL WHERE id = %s",
                    (pid,),
                )
                conn.execute("RELEASE clear_item")
                results.append({"id": pid, "status": "updated"})
                success += 1
            except psycopg.Error as e:
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
