"""Route tests for admin comment moderation endpoints."""

import uuid
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
async def admin_client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {ADMIN_API_KEY}"
        yield c


@pytest.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture()
def active_product(db_path):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
            " VALUES (?, ?, ?, ?, ?)",
            ("test-candle", "Test Candle", 2500, 10, 1),
        )
    return "test-candle"


@pytest.fixture()
def sample_comment(active_product):
    comment_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO comments (id, product_id, session_id, display_name, body) "
            "VALUES (?, ?, ?, ?, ?)",
            (comment_id, active_product, "session-1", "Marie", "Great candle!"),
        )
    return comment_id


class TestAdminDeleteComment:
    """DELETE /v1/admin/comments/{comment_id}"""

    async def test_deletes_comment_204(self, admin_client, sample_comment):
        resp = await admin_client.delete(f"/v1/admin/comments/{sample_comment}")
        assert resp.status_code == 204

    async def test_non_admin_403(self, client, sample_comment):
        resp = await client.delete(f"/v1/admin/comments/{sample_comment}")
        assert resp.status_code == 401

    async def test_not_found_404(self, admin_client, active_product):
        resp = await admin_client.delete("/v1/admin/comments/nonexistent-id")
        assert resp.status_code == 404


class TestAdminListComments:
    """GET /v1/admin/comments"""

    async def test_lists_comments(self, admin_client, sample_comment, active_product):
        resp = await admin_client.get("/v1/admin/comments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["product_name"] == "Test Candle"

    async def test_non_admin_401(self, client, sample_comment):
        resp = await client.get("/v1/admin/comments")
        assert resp.status_code == 401

    async def test_limit_clamped_to_100(self, admin_client, active_product):
        # Service layer clamps limit to 100 (does not reject)
        resp = await admin_client.get("/v1/admin/comments?limit=500")
        assert resp.status_code == 200
        assert resp.json()["limit"] == 100  # clamped from 500 to 100


class TestIntegration:
    """Full flow integration test."""

    async def test_full_flow(self, client, admin_client, active_product):
        # 1. Post a comment
        resp = await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Marie", "body": "Beautiful candle!"},
        )
        assert resp.status_code == 201
        comment_id = resp.json()["id"]

        # 2. List it
        resp = await client.get(f"/v1/products/{active_product}/comments")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        # 3. React to product
        resp = await client.post(
            f"/v1/products/{active_product}/reactions",
            json={"reaction_type": "heart"},
        )
        assert resp.status_code == 201

        # 4. Verify counts
        resp = await client.get(f"/v1/products/{active_product}/reactions")
        assert resp.status_code == 200
        assert resp.json()["heart"]["count"] == 1

        # 5. Admin deletes comment
        resp = await admin_client.delete(f"/v1/admin/comments/{comment_id}")
        assert resp.status_code == 204

        # 6. Verify comment gone
        resp = await client.get(f"/v1/products/{active_product}/comments")
        assert resp.json()["total"] == 0

    async def test_cascade_on_product_delete(self, admin_client, client, active_product):
        """Reactions and comments cascade-delete when product is deleted."""
        # Add reaction and comment
        await client.post(
            f"/v1/products/{active_product}/reactions",
            json={"reaction_type": "heart"},
        )
        await client.post(
            f"/v1/products/{active_product}/comments",
            json={"display_name": "Marie", "body": "Love it!"},
        )

        # Hard delete the product (direct DB since we only soft-delete via API)
        with get_db() as conn:
            conn.execute("DELETE FROM products WHERE id = ?", (active_product,))

        # Verify reactions and comments are gone
        with get_db() as conn:
            r_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM reactions WHERE product_id = ?",
                (active_product,),
            ).fetchone()["cnt"]
            c_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM comments WHERE product_id = ?",
                (active_product,),
            ).fetchone()["cnt"]

        assert r_count == 0
        assert c_count == 0
