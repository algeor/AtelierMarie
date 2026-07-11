"""Authentication response models."""

from app.models.users import UserResponse

# Re-export UserResponse for use in auth routes
__all__ = ["UserResponse"]
