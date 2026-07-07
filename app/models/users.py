"""User response model."""

from pydantic import BaseModel


class UserResponse(BaseModel):
    """Public user profile representation."""

    id: str
    email: str
    name: str | None = None
    avatar_url: str | None = None
    is_admin: bool
