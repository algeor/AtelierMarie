"""Cart service — business logic for cart operations.

Pure functions taking explicit DbConnection parameter.
No HTTP concerns — testable without FastAPI/Starlette.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, NotRequired, TypedDict, cast

import psycopg
import structlog

from app.config import get_settings
from app.database import DbConnection, require_row
from app.services import pricing, taxonomy_service
from app.services.product_image_service import images_for_products, with_image_fields

logger = structlog.get_logger(__name__)

Locale = Literal["en", "bg"]

# psycopg returns TIMESTAMPTZ columns as datetime; ProductDict/ProductResponse
# declare timestamp fields as str and pricing parses discount bounds as this
# canonical string. Products are written as _DT_FMT strings, so normalise reads.
_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _fmt_ts(value: object) -> str | None:
    """Render a timestamp column read as the canonical `_DT_FMT` string."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime(_DT_FMT)
    return str(value)


def _localized_product_columns(locale: Locale) -> tuple[str, str]:
    """Return safe SQL expressions for locale-resolved product content."""
    if locale == "bg":
        return (
            "COALESCE(NULLIF(p.name_bg, ''), p.name_en, '') AS name",
            "COALESCE(NULLIF(p.description_bg, ''), p.description_en) AS description",
        )
    return (
        "COALESCE(NULLIF(p.name_en, ''), p.name_bg, '') AS name",
        "COALESCE(NULLIF(p.description_en, ''), p.description_bg) AS description",
    )


def _apply_orderability_fields(product: dict) -> dict:
    """Annotate embedded cart product payloads with orderability metadata."""
    stock = max(0, int(product.get("stock") or 0))
    result = dict(product)
    result["can_order"] = bool(product.get("is_active", True))
    result["available_now"] = stock > 0
    result["availability_status"] = "in_stock" if stock > 0 else "crafted_later"
    result["ships_when_complete"] = True
    return result


# --- Custom Exceptions ---


class ProductNotFoundError(Exception):
    """Raised when a product does not exist or is inactive."""

    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        super().__init__(f"Product not found: {product_id}")


class CartItemNotFoundError(Exception):
    """Raised when attempting to modify an item not in the cart."""

    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        super().__init__(f"Cart item not found: {product_id}")


class InsufficientStockError(Exception):
    """Raised when requested quantity exceeds available stock."""

    def __init__(self, product_id: str, requested: int, available: int) -> None:
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for {product_id}: requested {requested}, available {available}"
        )


class QuantityLimitError(Exception):
    """Raised when per-item quantity limit is exceeded."""

    def __init__(self, max_quantity: int) -> None:
        self.max_quantity = max_quantity
        super().__init__(f"Per-item quantity limit exceeded: max {max_quantity}")


class CartFullError(Exception):
    """Raised when the cart already has the maximum number of distinct items."""

    def __init__(self, max_items: int) -> None:
        self.max_items = max_items
        super().__init__(f"Cart full: max {max_items} distinct items")


# --- Data Structures ---


class ProductDict(TypedDict):
    """Typed dictionary for product data returned in cart items."""

    id: str
    name: str
    description: str | None
    materials: str | None
    days_to_craft: int | None
    price_cents: int
    effective_price_cents: int
    discount_percent: int | None
    discount_active: bool
    category: str | None
    category_name: str | None
    product_type: str
    product_type_name: str
    labels: list[dict]
    product_type_slug: NotRequired[str]
    category_slug: NotRequired[str | None]
    images: list[dict]
    primary_image_url: str | None
    primary_thumbnail_url: str | None
    stock: int
    is_active: bool
    is_featured: bool
    created_at: str
    updated_at: str


@dataclass
class UnavailableItem:
    """A cart item referencing a product that is no longer available."""

    product_id: str
    product_name: str
    reason: str


@dataclass
class CartItem:
    """A single active cart item with product details."""

    product_id: str
    product: ProductDict
    quantity: int
    added_at: str


@dataclass
class CartData:
    """Complete cart state returned by service functions."""

    items: list[CartItem] = field(default_factory=list)
    unavailable_items: list[UnavailableItem] = field(default_factory=list)
    total_cents: int = 0
    item_count: int = 0


@dataclass
class AddItemResult:
    """Result of add_item — includes whether the item was newly created."""

    cart: CartData
    created: bool


# --- Service Functions ---


def get_cart(conn: DbConnection, session_id: str, locale: Locale = "en") -> CartData:
    """Retrieve the cart for a session, separating active and unavailable items.

    Line and total pricing use each product's effective (discounted) price. A
    single `now` is captured for the whole read so every line and the total
    agree on discount active-state.
    """
    name_expr, description_expr = _localized_product_columns(locale)
    rows = conn.execute(
        f"""
        SELECT ci.product_id, ci.quantity, ci.added_at,
               p.id AS p_id, {name_expr}, {description_expr}, p.materials,
               p.days_to_craft, p.price_cents, p.product_type_slug, p.category_slug,
               p.discount_percent, p.discount_starts_at, p.discount_ends_at,
               p.stock, p.is_active, p.is_featured,
               p.created_at, p.updated_at
        FROM cart_items ci
        LEFT JOIN products p ON ci.product_id = p.id
        WHERE ci.session_id = %s
        ORDER BY ci.added_at
        """,  # noqa: S608 - locale selects fixed SQL expressions above.
        (session_id,),
    ).fetchall()

    now = pricing.now_utc()

    items: list[CartItem] = []
    unavailable_items: list[UnavailableItem] = []
    total_cents = 0
    item_count = 0

    active_product_ids = [row["p_id"] for row in rows if row["p_id"] is not None]
    image_map = images_for_products(conn, active_product_ids)
    active_entries: list[tuple[dict, dict]] = []

    for row in rows:
        if row["p_id"] is None:
            # Product was hard-deleted — show in unavailable
            unavailable_items.append(
                UnavailableItem(
                    product_id=row["product_id"],
                    product_name="[deleted]",
                    reason="deleted",
                )
            )
        elif not row["is_active"]:
            unavailable_items.append(
                UnavailableItem(
                    product_id=row["product_id"],
                    product_name=row["name"],
                    reason="deactivated",
                )
            )
        else:
            active_entries.append(
                (
                    row,
                    {
                        "id": row["p_id"],
                        "name": row["name"],
                        "description": row["description"],
                        "materials": row["materials"],
                        "days_to_craft": row["days_to_craft"],
                        "price_cents": row["price_cents"],
                        "discount_percent": row["discount_percent"],
                        "discount_starts_at": _fmt_ts(row["discount_starts_at"]),
                        "discount_ends_at": _fmt_ts(row["discount_ends_at"]),
                        "product_type_slug": row["product_type_slug"],
                        "category_slug": row["category_slug"],
                        "stock": row["stock"],
                        "is_active": bool(row["is_active"]),
                        "is_featured": bool(row["is_featured"]),
                        "created_at": _fmt_ts(row["created_at"]),
                        "updated_at": _fmt_ts(row["updated_at"]),
                    },
                )
            )

    # Batch-resolve taxonomy display metadata for all active products at once.
    taxonomy_service.resolve_products_taxonomy(
        conn,
        [product_data for _, product_data in active_entries],
        locale,
    )

    for row, product_data in active_entries:
        # Public pricing: effective_price_cents + active display percent;
        # window timestamps are stripped and never returned to the client.
        product_data = _apply_orderability_fields(
            pricing.annotate_product_pricing(product_data, now, public=True)
        )
        effective_price = product_data["effective_price_cents"]
        product = cast(
            ProductDict,
            with_image_fields(
                product_data,
                image_map.get(row["p_id"], []),
            ),
        )
        items.append(
            CartItem(
                product_id=row["product_id"],
                product=product,
                quantity=row["quantity"],
                added_at=_fmt_ts(row["added_at"]) or "",
            )
        )
        total_cents += effective_price * row["quantity"]
        item_count += row["quantity"]

    return CartData(
        items=items,
        unavailable_items=unavailable_items,
        total_cents=total_cents,
        item_count=item_count,
    )


def add_item(
    conn: DbConnection,
    session_id: str,
    product_id: str,
    quantity: int,
    locale: Locale = "en",
) -> AddItemResult:
    """Add a product to the cart or increment existing quantity.

    Runs the validate-and-write path inside a single transaction to prevent
    TOCTOU races on stock/quantity checks.
    """
    if quantity <= 0:
        msg = "Quantity must be at least 1"
        raise ValueError(msg)

    settings = get_settings()

    try:
        with conn.transaction():
            # Validate product exists and is active
            product = conn.execute(
                "SELECT id, is_active FROM products WHERE id = %s",
                (product_id,),
            ).fetchone()

            if not product or not product["is_active"]:
                raise ProductNotFoundError(product_id)

            # Check existing cart quantity
            existing = conn.execute(
                "SELECT quantity FROM cart_items WHERE session_id = %s AND product_id = %s",
                (session_id, product_id),
            ).fetchone()

            existing_qty = existing["quantity"] if existing else 0
            new_total_qty = existing_qty + quantity

            # Per-item quantity limit
            if new_total_qty > settings.cart_max_quantity_per_item:
                raise QuantityLimitError(max_quantity=settings.cart_max_quantity_per_item)

            # Cart full check (only for new items)
            if not existing:
                distinct_count = require_row(
                    conn.execute(
                        "SELECT COUNT(*) AS count FROM cart_items WHERE session_id = %s",
                        (session_id,),
                    ).fetchone()
                )["count"]

                if distinct_count >= settings.cart_max_distinct_items:
                    raise CartFullError(max_items=settings.cart_max_distinct_items)

            # INSERT or UPDATE
            created = existing is None
            if created:
                conn.execute(
                    "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, %s, %s)",
                    (session_id, product_id, quantity),
                )
            else:
                conn.execute(
                    "UPDATE cart_items SET quantity = %s WHERE session_id = %s AND product_id = %s",
                    (new_total_qty, session_id, product_id),
                )
    except (ProductNotFoundError, InsufficientStockError, QuantityLimitError, CartFullError):
        raise
    except psycopg.Error:
        logger.exception(
            "Cart add_item failed",
            session_id=session_id,
            product_id=product_id,
        )
        raise

    # Read cart AFTER the transaction is complete — a failure here does not mask the write.
    # The caller (route) handles read errors at the HTTP layer.
    cart = get_cart(conn, session_id, locale=locale)
    return AddItemResult(cart=cart, created=created)


def update_quantity(
    conn: DbConnection,
    session_id: str,
    product_id: str,
    quantity: int,
    locale: Locale = "en",
) -> CartData:
    """Set the absolute quantity for a cart item. Quantity 0 removes the item."""
    # Handle quantity=0 BEFORE any SQL — avoid violating CHECK (quantity >= 1)
    if quantity == 0:
        return remove_item(conn, session_id, product_id, locale=locale)

    settings = get_settings()

    try:
        with conn.transaction():
            # Validate item exists in cart
            existing = conn.execute(
                "SELECT quantity FROM cart_items WHERE session_id = %s AND product_id = %s",
                (session_id, product_id),
            ).fetchone()

            if not existing:
                raise CartItemNotFoundError(product_id)

            # Per-item quantity limit
            if quantity > settings.cart_max_quantity_per_item:
                raise QuantityLimitError(max_quantity=settings.cart_max_quantity_per_item)

            # Stock validation (absolute qty vs stock) — also reject deleted/inactive products
            product = conn.execute(
                "SELECT is_active FROM products WHERE id = %s",
                (product_id,),
            ).fetchone()

            if not product or not product["is_active"]:
                raise ProductNotFoundError(product_id)

            conn.execute(
                "UPDATE cart_items SET quantity = %s WHERE session_id = %s AND product_id = %s",
                (quantity, session_id, product_id),
            )
    except (
        CartItemNotFoundError,
        QuantityLimitError,
        InsufficientStockError,
        ProductNotFoundError,
    ):
        raise
    except psycopg.Error:
        logger.exception(
            "Cart update_quantity failed",
            session_id=session_id,
            product_id=product_id,
        )
        raise

    # Read cart AFTER the transaction is complete — a failure here does not mask the write.
    return get_cart(conn, session_id, locale=locale)


def remove_item(
    conn: DbConnection,
    session_id: str,
    product_id: str,
    locale: Locale = "en",
) -> CartData:
    """Remove an item from the cart entirely.

    Uses a single DELETE + rowcount check for atomicity (no TOCTOU window).
    """
    cursor = conn.execute(
        "DELETE FROM cart_items WHERE session_id = %s AND product_id = %s",
        (session_id, product_id),
    )

    if cursor.rowcount == 0:
        raise CartItemNotFoundError(product_id)

    return get_cart(conn, session_id, locale=locale)
