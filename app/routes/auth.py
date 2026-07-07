"""Auth endpoints (stub)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


def _not_implemented() -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": "Auth endpoints not yet implemented",
                "details": None,
            }
        },
    )


@router.post("/google")
async def google_auth() -> JSONResponse:
    return _not_implemented()


@router.get("/me")
async def get_current_user() -> JSONResponse:
    return _not_implemented()
