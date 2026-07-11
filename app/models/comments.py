"""Comment request and response models."""

from typing import Literal

from pydantic import BaseModel, Field

CommentSort = Literal["newest", "oldest"]


class CommentCreateRequest(BaseModel):
    """Request body for posting a comment."""

    display_name: str | None = Field(default=None, max_length=50)
    body: str = Field(..., min_length=1, max_length=500)


class CommentResponse(BaseModel):
    """Public comment representation (excludes internal IDs)."""

    id: str
    display_name: str
    body: str
    created_at: str


class AdminCommentResponse(BaseModel):
    """Admin comment view with product context for moderation."""

    id: str
    product_id: str
    product_name: str
    display_name: str
    body: str
    created_at: str


class CommentListResponse(BaseModel):
    """Paginated list of comments."""

    items: list[CommentResponse]
    total: int
    page: int
    limit: int


class AdminCommentListResponse(BaseModel):
    """Paginated list of comments for admin moderation."""

    items: list[AdminCommentResponse]
    total: int
    page: int
    limit: int
