"""Comment endpoints — create and list comments for products."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.database import get_db
from app.dependencies.session import require_session
from app.models.comments import (
    CommentCreateRequest,
    CommentListResponse,
    CommentResponse,
)
from app.services.comment_service import (
    ProductNotFoundError,
    RateLimitExceededError,
    ValidationError,
    create_comment,
    list_comments,
)

router = APIRouter()


def _resolve_display_name(
    session_id: str, request_display_name: str | None
) -> tuple[str, str | None]:
    """Resolve display name using hybrid identity.

    Returns (display_name, user_id).
    - If session has a linked user with non-null name → use that name
    - If session has a linked user with null name → require request display_name
    - If anonymous → require request display_name
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT s.user_id, u.name FROM sessions s "
            "LEFT JOIN users u ON s.user_id = u.id "
            "WHERE s.id = ?",
            (session_id,),
        ).fetchone()

    if row is None:
        # Session not found (shouldn't happen with middleware, but defensive)
        if not request_display_name:
            return "", None
        return request_display_name, None

    user_id = row["user_id"]
    user_name = row["name"] if user_id else None

    if user_name and not request_display_name:
        # Logged-in user with name — use profile name
        return user_name, user_id
    elif request_display_name:
        # Explicit display_name provided (anonymous or user override)
        return request_display_name, user_id
    else:
        # No name available and none provided
        return "", user_id


@router.post(
    "/{product_id}/comments",
    response_model=CommentResponse,
    status_code=201,
    summary="Post comment",
    description="Post a comment on a product. Anonymous users must provide display_name. "
    "Logged-in users have display_name auto-filled from profile.",
)
async def post_comment(
    product_id: str,
    body: CommentCreateRequest,
    session_id: Annotated[str, Depends(require_session)],
) -> CommentResponse | JSONResponse:
    """Post a comment on a product."""
    # Hybrid identity resolution (route layer responsibility)
    display_name, user_id = _resolve_display_name(session_id, body.display_name)

    if not display_name:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "display_name is required",
                }
            },
        )

    try:
        comment = create_comment(
            session_id=session_id,
            user_id=user_id,
            product_id=product_id,
            display_name=display_name,
            body=body.body,
        )
    except ProductNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )
    except ValidationError as e:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": str(e)}},
        )
    except RateLimitExceededError as e:
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "RATE_LIMITED", "message": str(e)}},
        )

    return JSONResponse(
        status_code=201,
        content=CommentResponse(**comment).model_dump(),
    )


@router.get(
    "/{product_id}/comments",
    response_model=CommentListResponse,
    summary="List comments",
    description="List comments for a product with sort (newest/oldest) and pagination.",
)
async def list_product_comments(
    product_id: str,
    sort: Literal["newest", "oldest"] = Query(default="newest", description="Sort order"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, description="Items per page (max 100)"),
) -> CommentListResponse | JSONResponse:
    """List comments for a product."""
    limit = min(limit, 100)
    try:
        comments, total = list_comments(product_id, sort=sort, page=page, limit=limit)
    except ProductNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )

    return CommentListResponse(
        items=[CommentResponse(**c) for c in comments],
        total=total,
        page=page,
        limit=limit,
    )
