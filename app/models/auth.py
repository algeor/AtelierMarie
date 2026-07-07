"""Authentication request and response models."""

from pydantic import BaseModel

from app.models.users import UserResponse


class AuthTokenResponse(BaseModel):
    """Returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class GoogleAuthRequest(BaseModel):
    """Input for Google OAuth callback."""

    code: str
    # TODO: Validate redirect_uri against an allowlist of permitted callback URLs
    # when OAuth is implemented. Must reject arbitrary URIs to prevent open redirector.
    redirect_uri: str
