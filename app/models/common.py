"""Shared models: error responses, pagination, constants."""

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field

# Shared validation constants
PRODUCT_ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class ErrorDetail(BaseModel):
    """Structured error detail for API error responses."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict | None = Field(
        default=None, description="Additional context (e.g. validation errors)"
    )


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all endpoints on failure."""

    error: ErrorDetail


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")


# FastAPI-compatible dependency for pagination query params
PageParam = Annotated[int, Query(ge=1, description="Page number (1-based)")]
LimitParam = Annotated[int, Query(ge=1, le=100, description="Items per page (max 100)")]
