"""Service tests for comment_service.py."""

import pytest

from app.database import init_db
from app.services.comment_service import (
    CommentNotFoundError,
    ProductNotFoundError,
    RateLimitExceededError,
    ValidationError,
    create_comment,
    delete_comment,
    list_all_comments,
    list_comments,
)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Initialize a fresh database for each test."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    monkeypatch.setattr("app.database._db_path", db_path)
    return db_path


@pytest.fixture()
def active_product(db):
    """Insert an active product for testing."""
    from app.database import get_db

    with get_db() as conn:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
            " VALUES (?, ?, ?, ?, ?)",
            ("test-candle", "Test Candle", 2500, 10, 1),
        )
    return "test-candle"


@pytest.fixture()
def inactive_product(db):
    """Insert an inactive product."""
    from app.database import get_db

    with get_db() as conn:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
            " VALUES (?, ?, ?, ?, ?)",
            ("inactive-candle", "Inactive Candle", 2500, 10, 0),
        )
    return "inactive-candle"


class TestCreateComment:
    """Tests for create_comment()."""

    def test_creates_comment_successfully(self, active_product):
        result = create_comment("session-1", None, active_product, "Marie", "Love this!")
        assert result["display_name"] == "Marie"
        assert result["body"] == "Love this!"
        assert result["id"]
        assert result["created_at"]

    def test_trims_whitespace(self, active_product):
        result = create_comment("session-1", None, active_product, "  Marie  ", "  Nice!  ")
        assert result["display_name"] == "Marie"
        assert result["body"] == "Nice!"

    def test_html_escapes_inputs(self, active_product):
        result = create_comment(
            "session-1", None, active_product, "<b>User</b>", "<script>alert('x')</script>Nice"
        )
        assert "&lt;b&gt;" in result["display_name"]
        assert "&lt;script&gt;" in result["body"]

    def test_display_name_too_short(self, active_product):
        with pytest.raises(ValidationError, match="at least 2"):
            create_comment("session-1", None, active_product, "A", "Great candle!")

    def test_display_name_too_long(self, active_product):
        with pytest.raises(ValidationError, match="50 characters"):
            create_comment("session-1", None, active_product, "A" * 51, "Great candle!")

    def test_body_empty_after_trim(self, active_product):
        with pytest.raises(ValidationError, match="must not be empty"):
            create_comment("session-1", None, active_product, "Marie", "   ")

    def test_body_too_long(self, active_product):
        with pytest.raises(ValidationError, match="500 characters"):
            create_comment("session-1", None, active_product, "Marie", "A" * 501)

    def test_display_name_must_contain_letter(self, active_product):
        with pytest.raises(ValidationError, match="at least one letter"):
            create_comment("session-1", None, active_product, "123!!", "Great candle!")

    def test_display_name_with_mixed_chars_ok(self, active_product):
        result = create_comment("session-1", None, active_product, "User123", "Nice!")
        assert "User123" in result["display_name"]

    def test_blocklist_rejects_display_name(self, active_product):
        with pytest.raises(ValidationError, match="inappropriate"):
            create_comment("session-1", None, active_product, "Admin User", "Hello!")

    def test_blocklist_rejects_body(self, active_product):
        with pytest.raises(ValidationError, match="inappropriate"):
            create_comment("session-1", None, active_product, "Marie", "I am the admin here")

    def test_url_only_body_rejected(self, active_product):
        with pytest.raises(ValidationError, match="URL-only"):
            create_comment("session-1", None, active_product, "Marie", "https://spam.com/buy")

    def test_url_in_text_allowed(self, active_product):
        result = create_comment(
            "session-1", None, active_product, "Marie", "Check https://example.com for details"
        )
        assert "https://example.com" in result["body"]

    def test_product_not_found(self, db):
        with pytest.raises(ProductNotFoundError):
            create_comment("session-1", None, "nonexistent", "Marie", "Hello!")

    def test_inactive_product_rejected(self, inactive_product):
        with pytest.raises(ProductNotFoundError):
            create_comment("session-1", None, inactive_product, "Marie", "Hello!")

    def test_stores_user_id(self, active_product):
        from app.database import get_db

        # Need a user in the DB for the FK
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (id, google_id, email, name) VALUES (?, ?, ?, ?)",
                ("user-123", "google-123", "user@test.com", "Test User"),
            )

        create_comment("session-1", "user-123", active_product, "Marie", "Hello!")
        with get_db() as conn:
            row = conn.execute("SELECT user_id FROM comments LIMIT 1").fetchone()
        assert row["user_id"] == "user-123"


class TestCommentRateLimits:
    """Tests for rate limit enforcement."""

    def test_per_product_limit_blocks_fourth_comment(self, active_product):
        for i in range(3):
            create_comment("session-1", None, active_product, "Marie", f"Comment {i}")

        with pytest.raises(RateLimitExceededError, match="limit reached for this product"):
            create_comment("session-1", None, active_product, "Marie", "Fourth attempt")

    def test_different_products_within_limit(self, db):
        from app.database import get_db

        # Create 3 products
        with get_db() as conn:
            for i in range(3):
                conn.execute(
                    "INSERT INTO products (id, name_en, price_cents, stock, is_active) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (f"candle-{i}", f"Candle {i}", 2500, 10, 1),
                )

        # 3 comments each on 3 products (9 total, <10/hour)
        for i in range(3):
            for j in range(3):
                create_comment("session-1", None, f"candle-{i}", "Marie", f"Comment {j}")

    def test_hourly_limit_blocks_eleventh_comment(self, db):
        from app.database import get_db

        # Create 11 products
        with get_db() as conn:
            for i in range(11):
                conn.execute(
                    "INSERT INTO products (id, name_en, price_cents, stock, is_active) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (f"candle-{i}", f"Candle {i}", 2500, 10, 1),
                )

        # 1 comment each on 10 products (hitting hourly limit of 10)
        for i in range(10):
            create_comment("session-1", None, f"candle-{i}", "Marie", "Comment!")

        with pytest.raises(RateLimitExceededError, match="Too many comments"):
            create_comment("session-1", None, "candle-10", "Marie", "One more")


class TestListComments:
    """Tests for list_comments()."""

    def test_lists_comments_newest_first(self, active_product):
        create_comment("session-1", None, active_product, "Alice", "First")
        create_comment("session-2", None, active_product, "Bob", "Second")

        comments, total = list_comments(active_product, sort="newest")
        assert total == 2
        assert comments[0]["display_name"] == "Bob"
        assert comments[1]["display_name"] == "Alice"

    def test_lists_comments_oldest_first(self, active_product):
        create_comment("session-1", None, active_product, "Alice", "First")
        create_comment("session-2", None, active_product, "Bob", "Second")

        comments, total = list_comments(active_product, sort="oldest")
        assert total == 2
        assert comments[0]["display_name"] == "Alice"
        assert comments[1]["display_name"] == "Bob"

    def test_pagination(self, active_product):
        for i in range(5):
            create_comment(f"session-{i}", None, active_product, f"User{i}", f"Comment {i}")

        comments, total = list_comments(active_product, page=1, limit=2)
        assert total == 5
        assert len(comments) == 2

        comments2, _ = list_comments(active_product, page=2, limit=2)
        assert len(comments2) == 2

    def test_limit_clamped_to_100(self, active_product):
        # Should not raise, just clamp
        comments, total = list_comments(active_product, limit=200)
        assert total == 0

    def test_inactive_product_rejected(self, inactive_product):
        with pytest.raises(ProductNotFoundError):
            list_comments(inactive_product)


class TestDeleteComment:
    """Tests for delete_comment()."""

    def test_deletes_existing_comment(self, active_product):
        result = create_comment("session-1", None, active_product, "Marie", "Hello!")
        delete_comment(result["id"])

        comments, total = list_comments(active_product)
        assert total == 0

    def test_raises_for_nonexistent(self, db):
        with pytest.raises(CommentNotFoundError):
            delete_comment("nonexistent-id")


class TestListAllComments:
    """Tests for list_all_comments() — admin moderation view."""

    def test_lists_with_product_name(self, active_product):
        create_comment("session-1", None, active_product, "Marie", "Hello!")

        comments, total = list_all_comments()
        assert total == 1
        assert comments[0]["product_name"] == "Test Candle"
        assert comments[0]["product_id"] == active_product

    def test_filters_by_product_id(self, db):
        from app.database import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock, is_active) "
                "VALUES (?, ?, ?, ?, ?)",
                ("candle-a", "Candle A", 2500, 10, 1),
            )
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock, is_active) "
                "VALUES (?, ?, ?, ?, ?)",
                ("candle-b", "Candle B", 2500, 10, 1),
            )

        create_comment("session-1", None, "candle-a", "Alice", "Comment A")
        create_comment("session-2", None, "candle-b", "Bob", "Comment B")

        comments, total = list_all_comments(product_id="candle-a")
        assert total == 1
        assert comments[0]["display_name"] == "Alice"

    def test_limit_clamped_to_100(self, active_product):
        comments, total = list_all_comments(limit=500)
        assert total == 0  # No comments, but limit was clamped silently
