"""Reaction request and response models."""

from typing import Literal

from pydantic import BaseModel


class ReactionToggleRequest(BaseModel):
    """Request body for toggling a reaction on a product."""

    reaction_type: Literal["heart", "thumbs_up"]


class ReactionToggleResponse(BaseModel):
    """Response after toggling a reaction."""

    reaction_type: str
    active: bool


class ReactionTypeCount(BaseModel):
    """Count and current-session state for one reaction type."""

    count: int
    reacted: bool


class ReactionCountsResponse(BaseModel):
    """Aggregate reaction counts for a product with current session's state."""

    heart: ReactionTypeCount
    thumbs_up: ReactionTypeCount
