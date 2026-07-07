"""Order endpoints (stub)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


def _not_implemented() -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": "Order endpoints not yet implemented",
                "details": None,
            }
        },
    )


@router.get("")
async def list_orders() -> JSONResponse:
    return _not_implemented()


@router.post("")
async def create_order() -> JSONResponse:
    return _not_implemented()


@router.get("/{order_id}")
async def get_order(order_id: str) -> JSONResponse:
    return _not_implemented()


@router.patch("/{order_id}/status")
async def update_order_status(order_id: str) -> JSONResponse:
    return _not_implemented()
