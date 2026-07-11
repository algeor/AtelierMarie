"""Route tests for comment endpoints."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import get_db, init_db

ADMIN_API_KEY = "test-admin-key"  # pragma: allowlist secret


@pytest.fixture()
def db_path(tmp_path) -> str:
    return str(tmp_path / "test.db")


@pytest.fixture()
def app(db_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_API_KEY)
    get_settings.cache_clear()
    init_db(db_path)

    from app.main import create_app

    test_app = create_app()
    yield test_app
    get_settings.cache_clear()


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture()
def active_product(db_path):
    """Insert an active product."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
            " VALUES (?, ?, ?, ?, ?)",
            ("test-candle", "Test Candle", 2500, 10, 1),
        )
    return "test-candle"


@pytest.fixture()
def inactive_product(db_path):
    """Insert an inactive product."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
            " VALUES (?, ?, ?, ?, ?)",
            ("inactive-candle", "Inactive Candle", 2500, 10, 0),
        )
    return "inactive-candle"


class TestPostCommentRoute:
    """POST /v1/products/{product_id}/comments"""

    async def test_creates_comment_201(self, client, active_product):
        resp = await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Marie", "body": "Love this candle!"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["display_name"] == "Marie"
        assert data["body"] == "Love this candle!"
        assert "id" in data
        assert "created_at" in data

    async def test_missing_display_name_anonymous_422(self, client, active_product):
        resp = await client.post(
            f"/v1/products/{active_product}/comments",
            json={"body": "Hello!"},
        )
        assert resp.status_code == 422
        assert "display_name" in resp.json()["error"]["message"].lower()

    async def test_validation_error_short_name_422(self, client, active_product):
        resp = await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "A", "body": "Hello!"},
        )
        assert resp.status_code == 422

    async def test_validation_error_empty_body_422(self, client, active_product):
        resp = await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Marie", "body": "   "},
        )
        assert resp.status_code == 422

    async def test_url_only_body_422(self, client, active_product):
        resp = await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Marie", "body": "https://spam.com"},
        )
        assert resp.status_code == 422

    async def test_product_not_found_404(self, client):
        resp = await client.post(
            "/v1/products/nonexistent/comments",
            json={"display_name": "Marie", "body": "Hello!"},
        )
        assert resp.status_code == 404

    async def test_rate_limit_per_product_429(self, client, active_product):
        for i in range(3):
            resp = await client.post(
                f"/v1/products/{active_product}/comments",
                json={"display_name": "Marie", "body": f"Comment {i}"},
            )
            assert resp.status_code == 201

        resp = await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Marie", "body": "Fourth attempt"},
        )
        assert resp.status_code == 429

    async def test_hybrid_identity_logged_in_user(self, client, active_product):
        """Logged-in user with name doesn't need display_name in request."""
        # Create user and link to session
        # First make a request to establish session
        resp = await client.get(f"/v1/products/{active_product}/reactions")
        session_cookie = resp.cookies.get("session_id")

        # Link session to a user
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (id, google_id, email, name) VALUES (?, ?, ?, ?)",
                ("user-1", "google-1", "user@test.com", "Logged In User"),
            )
            conn.execute(
                "UPDATE sessions SET user_id = ? WHERE id = ?",
                ("user-1", session_cookie),
            )

        # Post without display_name — should use profile name
        resp = await client.post(
            f"/v1/products/{active_product}/comments",
            json={"body": "Hello from logged in user!"},
            cookies={"session_id": session_cookie},
        )
        assert resp.status_code == 201
        assert resp.json()["display_name"] == "Logged In User"

    async def test_hybrid_identity_null_name_requires_display_name(self, client, active_product):
        """Logged-in user with NULL name must provide display_name."""
        resp = await client.get(f"/v1/products/{active_product}/reactions")
        session_cookie = resp.cookies.get("session_id")

        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (id, google_id, email, name) VALUES (?, ?, ?, ?)",
                ("user-2", "google-2", "user2@test.com", None),
            )
            conn.execute(
                "UPDATE sessions SET user_id = ? WHERE id = ?",
                ("user-2", session_cookie),
            )

        resp = await client.post(
            f"/v1/products/{active_product}/comments",
            json={"body": "Hello!"},
            cookies={"session_id": session_cookie},
        )
        assert resp.status_code == 422


class TestListCommentsRoute:
    """GET /v1/products/{product_id}/comments"""

    async def test_lists_comments(self, client, active_product):
        await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Alice", "body": "First comment"},
        )
        await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Bob", "body": "Second comment"},
        )

        resp = await client.get(f"/v1/products/{active_product}/comments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_sort_newest(self, client, active_product):
        await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Alice", "body": "First"},
        )
        await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Bob", "body": "Second"},
        )

        resp = await client.get(f"/v1/products/{active_product}/comments?sort=newest")
        data = resp.json()
        assert data["items"][0]["display_name"] == "Bob"

    async def test_sort_oldest(self, client, active_product):
        await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Alice", "body": "First"},
        )
        await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Bob", "body": "Second"},
        )

        resp = await client.get(f"/v1/products/{active_product}/comments?sort=oldest")
        data = resp.json()
        assert data["items"][0]["display_name"] == "Alice"

    async def test_pagination(self, client, active_product):
        # Use different sessions (via direct DB insert) to avoid rate limit
        with get_db() as conn:
            import uuid

            for i in range(5):
                conn.execute(
                    "INSERT INTO comments (id, product_id, session_id, display_name, body) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), active_product, f"session-{i}", f"User{i}", f"Comment {i}"),
                )

        resp = await client.get(f"/v1/products/{active_product}/comments?page=1&limit=2")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["limit"] == 2

    async def test_inactive_product_404(self, client, inactive_product):
        resp = await client.get(f"/v1/products/{inactive_product}/comments")
        assert resp.status_code == 404
