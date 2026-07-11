"""Comment service — business logic for product comments (create, list, delete, moderation)."""

import uuid

from app.database import get_db
from app.utils.sanitize import contains_blocked_word, is_url_only, sanitize_text


class ProductNotFoundError(Exception):
    """Raised when the target product does not exist or is inactive."""


class CommentNotFoundError(Exception):
    """Raised when a comment ID does not exist."""


class RateLimitExceededError(Exception):
    """Raised when a session exceeds comment rate limits."""


class ValidationError(Exception):
    """Raised when comment input fails business validation."""


# Rate limits
_MAX_COMMENTS_PER_PRODUCT = 3
_MAX_COMMENTS_PER_HOUR = 10


def _validate_product_active(product_id: str) -> None:
    """Verify product exists and is active. Raises ProductNotFoundError otherwise."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM products WHERE id = ? AND is_active = 1",
            (product_id,),
        ).fetchone()
    if row is None:
        raise ProductNotFoundError(f"Product not found: {product_id}")


def _check_product_limit(session_id: str, product_id: str) -> None:
    """Check per-product comment limit (max 3 per session per product)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM comments WHERE session_id = ? AND product_id = ?",
            (session_id, product_id),
        ).fetchone()
    if row["cnt"] >= _MAX_COMMENTS_PER_PRODUCT:
        raise RateLimitExceededError("Comment limit reached for this product")


def _check_hourly_limit(session_id: str) -> None:
    """Check hourly global comment limit (max 10 per session per hour)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM comments "
            "WHERE session_id = ? AND created_at > datetime('now', '-1 hour')",
            (session_id,),
        ).fetchone()
    if row["cnt"] >= _MAX_COMMENTS_PER_HOUR:
        raise RateLimitExceededError("Too many comments. Please try again later.")


def create_comment(
    session_id: str,
    user_id: str | None,
    product_id: str,
    display_name: str,
    body: str,
) -> dict:
    """Create a comment on a product.

    Processing order per design Decision 8:
    1. Trim whitespace
    2. Validate lengths (2-50 name, 1-500 body) on raw text
    3. Check display_name has at least one letter
    4. Check blocklist
    5. Check URL-only (body only)
    6. Check rate limits
    7. html.escape() inputs
    8. INSERT

    display_name is always a resolved non-null string (route layer handles hybrid identity).
    """
    _validate_product_active(product_id)

    # Step 1: Trim whitespace
    display_name = display_name.strip()
    body = body.strip()

    # Step 2: Validate lengths on raw text
    if len(display_name) < 2:
        raise ValidationError("Display name must be at least 2 characters")
    if len(display_name) > 50:
        raise ValidationError("Display name must not exceed 50 characters")
    if len(body) < 1:
        raise ValidationError("Comment body must not be empty")
    if len(body) > 500:
        raise ValidationError("Comment body must not exceed 500 characters")

    # Step 3: Display name must contain at least one letter
    if not any(c.isalpha() for c in display_name):
        raise ValidationError("Display name must contain at least one letter")

    # Step 4: Check blocklist (both fields)
    if contains_blocked_word(display_name):
        raise ValidationError("Display name contains inappropriate content")
    if contains_blocked_word(body):
        raise ValidationError("Comment contains inappropriate content")

    # Step 5: Check URL-only (body only, on raw text)
    if is_url_only(body):
        raise ValidationError("URL-only comments are not allowed")

    # Step 6: Check rate limits (both, reject if either exceeded)
    _check_product_limit(session_id, product_id)
    _check_hourly_limit(session_id)

    # Step 7: html.escape() inputs for storage
    display_name = sanitize_text(display_name)
    body = sanitize_text(body)

    # Step 8: INSERT
    comment_id = str(uuid.uuid4())

    with get_db() as conn:
        conn.execute(
            "INSERT INTO comments (id, product_id, session_id, user_id, display_name, body) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (comment_id, product_id, session_id, user_id, display_name, body),
        )

    return {
        "id": comment_id,
        "display_name": display_name,
        "body": body,
        "created_at": _get_comment_created_at(comment_id),
    }


def _get_comment_created_at(comment_id: str) -> str:
    """Fetch the created_at timestamp for a just-inserted comment."""
    with get_db() as conn:
        row = conn.execute("SELECT created_at FROM comments WHERE id = ?", (comment_id,)).fetchone()
    return row["created_at"] if row else ""


def list_comments(
    product_id: str,
    sort: str = "newest",
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """List comments for a product with pagination and sorting.

    Returns (comments, total_count). Clamps limit to max 100.
    Sort is mapped to hardcoded SQL — NEVER concatenated.
    """
    _validate_product_active(product_id)

    # Clamp limit
    limit = min(limit, 100)
    if limit < 1:
        limit = 1
    if page < 1:
        page = 1

    # Hardcoded sort mapping — never concatenate user input into SQL
    sort_sql = {"newest": "DESC", "oldest": "ASC"}
    order_direction = sort_sql.get(sort, "DESC")

    offset = (page - 1) * limit

    with get_db() as conn:
        # Total count
        count_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM comments WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        total = count_row["cnt"]

        # Paginated results
        rows = conn.execute(
            f"SELECT id, display_name, body, created_at FROM comments "  # noqa: S608
            f"WHERE product_id = ? ORDER BY created_at {order_direction} LIMIT ? OFFSET ?",
            (product_id, limit, offset),
        ).fetchall()

    return [dict(row) for row in rows], total


def delete_comment(comment_id: str) -> None:
    """Hard delete a comment by ID. Raises CommentNotFoundError if missing."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        if cursor.rowcount == 0:
            raise CommentNotFoundError(f"Comment not found: {comment_id}")


def list_all_comments(
    page: int = 1,
    limit: int = 20,
    product_id: str | None = None,
) -> tuple[list[dict], int]:
    """List all comments for admin moderation with product context.

    JOINs with products to include product_name. Clamps limit to 100.
    """
    limit = min(limit, 100)
    if limit < 1:
        limit = 1
    if page < 1:
        page = 1

    offset = (page - 1) * limit
    conditions = []
    params: list = []

    if product_id:
        conditions.append("c.product_id = ?")
        params.append(product_id)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    with get_db() as conn:
        count_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM comments c {where_clause}",  # noqa: S608
            params,
        ).fetchone()
        total = count_row["cnt"]

        rows = conn.execute(
            f"SELECT c.id, c.product_id, "  # noqa: S608
            f"COALESCE(NULLIF(p.name_en, ''), p.name_bg, '') as product_name, "
            f"c.display_name, c.body, c.created_at "
            f"FROM comments c JOIN products p ON c.product_id = p.id "
            f"{where_clause} ORDER BY c.created_at DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()

    return [dict(row) for row in rows], total
