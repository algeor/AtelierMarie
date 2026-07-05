"""Tests for the health endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient):
    """GET /v1/health returns 200 with status ok."""
    response = await client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
