"""Cart endpoints (stub)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


def _not_implemented() -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": "Cart endpoints not yet implemented",
                "details": None,
            }
        },
    )


@router.get("")
async def get_cart() -> JSONResponse:
    return _not_implemented()


@router.post("")
async def add_to_cart() -> JSONResponse:
    return _not_implemented()


@router.patch("/{product_id}")
async def update_cart_item(product_id: str) -> JSONResponse:
    return _not_implemented()


@router.delete("/{product_id}")
async def remove_cart_item(product_id: str) -> JSONResponse:
    return _not_implemented()
