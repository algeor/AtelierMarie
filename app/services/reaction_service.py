"""Reaction service — business logic for product reactions (toggle, counts, rate limiting)."""

from app.database import get_db


class ProductNotFoundError(Exception):
    """Raised when the target product does not exist or is inactive."""


class RateLimitExceededError(Exception):
    """Raised when a session exceeds the reaction toggle rate limit."""


def _validate_product_active(product_id: str) -> None:
    """Verify product exists and is active. Raises ProductNotFoundError otherwise."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM products WHERE id = ? AND is_active = 1",
            (product_id,),
        ).fetchone()
    if row is None:
        raise ProductNotFoundError(f"Product not found: {product_id}")


def toggle_reaction(session_id: str, product_id: str, reaction_type: str) -> bool:
    """Toggle a reaction on a product. Returns True if added, False if removed.

    Uses INSERT OR IGNORE + rowcount check for atomic, idempotent operation.
    Rate limit check, toggle, and log all happen within a single connection
    to eliminate TOCTOU race conditions.
    """
    _validate_product_active(product_id)

    with get_db() as conn:
        # Check rate limit within same transaction
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM reaction_toggle_log "
            "WHERE session_id = ? AND toggled_at > datetime('now', '-60 seconds')",
            (session_id,),
        ).fetchone()
        if row["cnt"] >= 10:
            raise RateLimitExceededError("Too many reactions. Please slow down.")

        # Toggle reaction
        cursor = conn.execute(
            "INSERT OR IGNORE INTO reactions (session_id, product_id, reaction_type) "
            "VALUES (?, ?, ?)",
            (session_id, product_id, reaction_type),
        )
        if cursor.rowcount == 1:
            active = True
        else:
            # Already existed — remove it (toggle off)
            conn.execute(
                "DELETE FROM reactions "
                "WHERE session_id = ? AND product_id = ? AND reaction_type = ?",
                (session_id, product_id, reaction_type),
            )
            active = False

        # Log toggle for rate limiting
        conn.execute(
            "INSERT INTO reaction_toggle_log (session_id, product_id) VALUES (?, ?)",
            (session_id, product_id),
        )
        # Lazy cleanup: remove rows older than 1 hour for this session
        conn.execute(
            "DELETE FROM reaction_toggle_log "
            "WHERE session_id = ? AND toggled_at < datetime('now', '-1 hour')",
            (session_id,),
        )

    return active


def get_reaction_counts(product_id: str, session_id: str) -> dict:
    """Get aggregate reaction counts and current session's reaction state.

    Returns dict with keys 'heart' and 'thumbs_up', each having 'count' and 'reacted'.
    """
    _validate_product_active(product_id)

    with get_db() as conn:
        # Aggregate counts per type
        rows = conn.execute(
            "SELECT reaction_type, COUNT(*) as cnt FROM reactions "
            "WHERE product_id = ? GROUP BY reaction_type",
            (product_id,),
        ).fetchall()

        counts = {"heart": 0, "thumbs_up": 0}
        for row in rows:
            if row["reaction_type"] in counts:
                counts[row["reaction_type"]] = row["cnt"]

        # Current session's reactions
        session_rows = conn.execute(
            "SELECT reaction_type FROM reactions WHERE product_id = ? AND session_id = ?",
            (product_id, session_id),
        ).fetchall()

    session_reactions = {row["reaction_type"] for row in session_rows}

    return {
        "heart": {"count": counts["heart"], "reacted": "heart" in session_reactions},
        "thumbs_up": {
            "count": counts["thumbs_up"],
            "reacted": "thumbs_up" in session_reactions,
        },
    }
