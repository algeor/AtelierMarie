"""Locale preference endpoint — update session's preferred locale."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.products import Locale

router = APIRouter()


class UpdateLocaleRequest(BaseModel):
    """Request body for updating locale preference."""

    locale: Locale = Field(..., description="Preferred locale ('en' or 'bg')")


@router.patch(
    "",
    summary="Update locale preference",
    description="Update the session's preferred locale. "
    "Used by the language toggle to persist user choice.",
)
async def update_locale(body: UpdateLocaleRequest, request: Request) -> JSONResponse:
    """Update the preferred locale stored in the session row."""
    session_id = request.state.session_id
    if not session_id:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "NO_SESSION", "message": "No active session"}},
        )

    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET preferred_locale = ? WHERE id = ?",
            (body.locale, session_id),
        )

    return JSONResponse(content={"locale": body.locale})
