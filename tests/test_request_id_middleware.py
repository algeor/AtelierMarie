"""Tests for request ID middleware."""

import re

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.middleware.request_id import RequestIdMiddleware, request_id_var

UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


async def _request_id_endpoint(request):
    return JSONResponse({"request_id": request_id_var.get()})


def _app() -> Starlette:
    app = Starlette(routes=[Route("/request-id", _request_id_endpoint)])
    app.add_middleware(RequestIdMiddleware)
    return app


@pytest.mark.asyncio
async def test_request_id_middleware_uses_valid_header():
    request_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    transport = ASGITransport(app=_app())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/request-id", headers={"X-Request-ID": request_id.upper()})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
    assert response.json() == {"request_id": request_id}


@pytest.mark.asyncio
async def test_request_id_middleware_generates_uuid4_for_invalid_header():
    transport = ASGITransport(app=_app())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/request-id", headers={"X-Request-ID": "not-a-uuid"})

    generated_id = response.headers["X-Request-ID"]
    assert response.status_code == 200
    assert UUID4_RE.match(generated_id)
    assert response.json() == {"request_id": generated_id}
