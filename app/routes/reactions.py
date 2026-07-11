"""Reaction endpoints — toggle and get counts for product reactions."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies.session import require_session
from app.models.reactions import (
    ReactionCountsResponse,
    ReactionToggleRequest,
    ReactionToggleResponse,
    ReactionTypeCount,
)
from app.services.reaction_service import (
    ProductNotFoundError,
    RateLimitExceededError,
    get_reaction_counts,
    toggle_reaction,
)

router = APIRouter()


@router.post(
    "/{product_id}/reactions",
    response_model=ReactionToggleResponse,
    summary="Toggle reaction",
    description="Toggle a reaction (heart or thumbs_up) on a product. "
    "If the reaction doesn't exist, it's added. If it already exists, it's removed.",
)
async def toggle_product_reaction(
    product_id: str,
    body: ReactionToggleRequest,
    session_id: Annotated[str, Depends(require_session)],
) -> ReactionToggleResponse | JSONResponse:
    """Toggle a reaction on a product."""
    try:
        active = toggle_reaction(session_id, product_id, body.reaction_type)
    except ProductNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )
    except RateLimitExceededError as e:
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "RATE_LIMITED", "message": str(e)}},
        )

    status_code = 201 if active else 200
    return JSONResponse(
        status_code=status_code,
        content=ReactionToggleResponse(
            reaction_type=body.reaction_type, active=active
        ).model_dump(),
    )


@router.get(
    "/{product_id}/reactions",
    response_model=ReactionCountsResponse,
    summary="Get reaction counts",
    description="Get aggregate reaction counts for a product, "
    "including whether the current session has reacted.",
)
async def get_product_reactions(
    product_id: str,
    session_id: Annotated[str, Depends(require_session)],
) -> ReactionCountsResponse | JSONResponse:
    """Get aggregate reaction counts for a product."""
    try:
        data = get_reaction_counts(product_id, session_id)
    except ProductNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )

    return ReactionCountsResponse(
        heart=ReactionTypeCount(**data["heart"]),
        thumbs_up=ReactionTypeCount(**data["thumbs_up"]),
    )
