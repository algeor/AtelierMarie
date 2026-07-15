"""Tests for global exception handlers in app/exceptions.py.

Covers the reconciled handlers from admin-polish-edge-cases:
  - RequestValidationError → 422 envelope with field details
  - StarletteHTTPException with string detail → status-derived code + message
  - StarletteHTTPException with dict detail (code + message keys) → passthrough
  - OrderNotFoundError / InvalidStateTransitionError → global handler (not per-route)
  - Unhandled RuntimeError → 500 with no leaked internals
"""

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from app.exceptions import register_exception_handlers


class _ProbePayload(BaseModel):
    """Minimal request model used to trigger a RequestValidationError."""

    n: int = Field(..., ge=0)


def _build_probe_app() -> FastAPI:
    """Minimal app that exposes routes exercising each handler branch."""
    app = FastAPI()
    register_exception_handlers(app)

    from app.services.order_service import InvalidStateTransitionError, OrderNotFoundError

    @app.get("/raise/order-not-found")
    async def _order_not_found() -> None:
        raise OrderNotFoundError("ord_missing")

    @app.get("/raise/invalid-transition")
    async def _invalid_transition() -> None:
        raise InvalidStateTransitionError(
            order_id="ord_123",
            current_status="delivered",
            requested_status="pending",
        )

    @app.get("/raise/http-string")
    async def _http_string() -> None:
        raise HTTPException(status_code=403, detail="Forbidden zone")

    @app.get("/raise/http-dict")
    async def _http_dict() -> None:
        raise HTTPException(
            status_code=409,
            detail={"code": "CUSTOM_CONFLICT", "message": "Boom", "extra": 1},
        )

    @app.get("/raise/http-dict-bare")
    async def _http_dict_bare() -> None:
        # Dict without both code+message → falls back to status-derived envelope
        raise HTTPException(status_code=400, detail={"why": "no code/message keys"})

    @app.get("/raise/runtime")
    async def _runtime() -> None:
        raise RuntimeError("secret internal detail — must not leak")

    @app.post("/raise/validation")
    async def _validation(payload: _ProbePayload) -> _ProbePayload:
        return payload

    return app


@pytest.fixture()
def probe_app() -> FastAPI:
    return _build_probe_app()


@pytest.mark.asyncio
async def test_validation_error_returns_envelope(probe_app):
    """RequestValidationError → 422 with VALIDATION_ERROR and field details."""
    transport = ASGITransport(app=probe_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.post("/raise/validation", json={"n": "not-an-int"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "errors" in body["error"]["details"]
    assert body["error"]["details"]["errors"]  # non-empty


@pytest.mark.asyncio
async def test_http_exception_string_detail(probe_app):
    """HTTPException(403, 'msg') → 403 with FORBIDDEN code and detail as message."""
    transport = ASGITransport(app=probe_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/raise/http-string")
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert body["error"]["message"] == "Forbidden zone"
    assert body["error"]["details"] is None


@pytest.mark.asyncio
async def test_http_exception_dict_detail_passthrough(probe_app):
    """HTTPException(409, {code, message, extra}) → envelope uses code+message,
    extra keys go to details."""
    transport = ASGITransport(app=probe_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/raise/http-dict")
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "CUSTOM_CONFLICT"
    assert body["error"]["message"] == "Boom"
    assert body["error"]["details"] == {"extra": 1}


@pytest.mark.asyncio
async def test_http_exception_dict_without_code_key_falls_back(probe_app):
    """Dict detail missing 'code'/'message' → status-derived envelope, dict → details."""
    transport = ASGITransport(app=probe_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/raise/http-dict-bare")
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "BAD_REQUEST"
    assert body["error"]["details"] == {"why": "no code/message keys"}


@pytest.mark.asyncio
async def test_order_not_found_handled_globally(probe_app):
    """OrderNotFoundError raised in a route → 404 with ORDER_NOT_FOUND envelope."""
    transport = ASGITransport(app=probe_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/raise/order-not-found")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "ORDER_NOT_FOUND"
    assert body["error"]["details"] == {"order_id": "ord_missing"}


@pytest.mark.asyncio
async def test_invalid_state_transition_handled_globally(probe_app):
    """InvalidStateTransitionError → 422 with INVALID_TRANSITION envelope."""
    transport = ASGITransport(app=probe_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/raise/invalid-transition")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_TRANSITION"
    assert body["error"]["details"] == {
        "order_id": "ord_123",
        "current_status": "delivered",
        "requested_status": "pending",
    }


@pytest.mark.asyncio
async def test_unhandled_exception_does_not_leak(probe_app):
    """RuntimeError → 500 with generic message, no leaked traceback/class/message."""
    transport = ASGITransport(app=probe_app)
    # Starlette's default behavior for unhandled exceptions in tests is to raise.
    # Our catch-all handler intercepts BEFORE that; but AsyncClient will propagate
    # if the handler didn't run. Wrap in raises=False by using raise_app_exceptions.
    async with AsyncClient(
        transport=ASGITransport(app=probe_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as c:
        response = await c.get("/raise/runtime")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred"
    assert body["error"]["details"] is None
    # No leaked internals
    raw = response.text
    assert "secret internal detail" not in raw
    assert "RuntimeError" not in raw
    assert "Traceback" not in raw
