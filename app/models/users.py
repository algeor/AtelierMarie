"""User response model."""

from pydantic import BaseModel, field_validator


class UserResponse(BaseModel):
    """Public user profile representation."""

    id: str
    email: str
    name: str | None = None
    avatar_url: str | None = None
    is_admin: bool

    @field_validator("name", "avatar_url", mode="before")
    @classmethod
    def blank_optional_profile_field_to_none(cls, value: object) -> object:
        """Treat blank optional profile fields the same as omitted fields."""
        if isinstance(value, str) and not value.strip():
            return None
        return value
