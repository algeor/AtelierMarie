"""Public legal identity endpoint."""

from fastapi import APIRouter, Response

from app.legal import get_public_legal_identity
from app.models.legal import LegalIdentityResponse

router = APIRouter()


@router.get("/identity", response_model=LegalIdentityResponse, summary="Get public legal identity")
async def get_legal_identity(response: Response) -> LegalIdentityResponse:
    """Return the latest admin-managed legal identity for public pages."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return LegalIdentityResponse(**get_public_legal_identity())
