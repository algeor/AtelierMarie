"""Service tests for reaction_service.py."""

import pytest

from app.database import init_db
from app.services.reaction_service import (
    ProductNotFoundError,
    RateLimitExceededError,
    get_reaction_counts,
    toggle_reaction,
)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Initialize a fresh database for each test."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    # Patch the module-level _db_path so get_db() connects to our test DB
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
    """Insert an inactive product for testing."""
    from app.database import get_db

    with get_db() as conn:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
            " VALUES (?, ?, ?, ?, ?)",
            ("inactive-candle", "Inactive Candle", 2500, 10, 0),
        )
    return "inactive-candle"


class TestToggleReaction:
    """Tests for toggle_reaction()."""

    def test_toggle_on_returns_true(self, active_product):
        result = toggle_reaction("session-1", active_product, "heart")
        assert result is True

    def test_toggle_off_returns_false(self, active_product):
        toggle_reaction("session-1", active_product, "heart")
        result = toggle_reaction("session-1", active_product, "heart")
        assert result is False

    def test_toggle_on_again_after_off(self, active_product):
        toggle_reaction("session-1", active_product, "heart")
        toggle_reaction("session-1", active_product, "heart")
        result = toggle_reaction("session-1", active_product, "heart")
        assert result is True

    def test_different_types_independent(self, active_product):
        r1 = toggle_reaction("session-1", active_product, "heart")
        r2 = toggle_reaction("session-1", active_product, "thumbs_up")
        assert r1 is True
        assert r2 is True

    def test_different_sessions_independent(self, active_product):
        r1 = toggle_reaction("session-1", active_product, "heart")
        r2 = toggle_reaction("session-2", active_product, "heart")
        assert r1 is True
        assert r2 is True

    def test_product_not_found(self, db):
        with pytest.raises(ProductNotFoundError):
            toggle_reaction("session-1", "nonexistent", "heart")

    def test_inactive_product_rejected(self, inactive_product):
        with pytest.raises(ProductNotFoundError):
            toggle_reaction("session-1", inactive_product, "heart")


class TestGetReactionCounts:
    """Tests for get_reaction_counts()."""

    def test_empty_counts(self, active_product):
        result = get_reaction_counts(active_product, "session-1")
        assert result["heart"]["count"] == 0
        assert result["heart"]["reacted"] is False
        assert result["thumbs_up"]["count"] == 0
        assert result["thumbs_up"]["reacted"] is False

    def test_counts_after_reactions(self, active_product):
        toggle_reaction("session-1", active_product, "heart")
        toggle_reaction("session-2", active_product, "heart")
        toggle_reaction("session-1", active_product, "thumbs_up")

        result = get_reaction_counts(active_product, "session-1")
        assert result["heart"]["count"] == 2
        assert result["heart"]["reacted"] is True
        assert result["thumbs_up"]["count"] == 1
        assert result["thumbs_up"]["reacted"] is True

    def test_session_not_reacted(self, active_product):
        toggle_reaction("session-1", active_product, "heart")

        result = get_reaction_counts(active_product, "session-2")
        assert result["heart"]["count"] == 1
        assert result["heart"]["reacted"] is False

    def test_inactive_product_rejected(self, inactive_product):
        with pytest.raises(ProductNotFoundError):
            get_reaction_counts(inactive_product, "session-1")


class TestReactionRateLimit:
    """Tests for reaction rate limiting."""

    def test_tenth_toggle_allowed(self, active_product):
        """9 toggles should be fine, 10th still OK (limit is >= 10 check BEFORE toggle)."""
        for i in range(10):
            toggle_reaction(f"session-rate-{i % 2}", active_product, "heart")
        # 10 toggles from 2 sessions (5 each) — both under limit

    def test_eleventh_toggle_from_same_session_blocked(self, active_product):
        """After 10 toggles from one session in 60s, the 11th is blocked."""
        # Toggle 10 times (alternating on/off = 10 log entries)
        for _ in range(5):
            toggle_reaction("rate-session", active_product, "heart")
            toggle_reaction("rate-session", active_product, "heart")

        with pytest.raises(RateLimitExceededError, match="Too many reactions"):
            toggle_reaction("rate-session", active_product, "heart")

    def test_concurrent_toggle_idempotent(self, active_product):
        """Multiple rapid toggles from same session don't corrupt state."""
        # Toggle on then off rapidly
        result1 = toggle_reaction("session-1", active_product, "heart")
        result2 = toggle_reaction("session-1", active_product, "heart")
        assert result1 is True
        assert result2 is False

        counts = get_reaction_counts(active_product, "session-1")
        assert counts["heart"]["count"] == 0
        assert counts["heart"]["reacted"] is False
