"""Contact form request and response models."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactRequest(BaseModel):
    """Public contact form submission."""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    message: str = Field(..., min_length=1, max_length=2000)
    locale: Literal["en", "bg"] = "en"
    website: str | None = Field(default=None, max_length=200)

    @field_validator("name", "message", "website", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Trim user-provided strings before required/max-length validation."""
        if isinstance(value, str):
            return value.strip()
        return value


class ContactResponse(BaseModel):
    """Response returned after accepting or silently dropping a contact form."""

    status: Literal["received"] = "received"
    message_id: int | None = None
