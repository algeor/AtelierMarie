"""Public product endpoints — listing, detail, and saved products."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.database import get_db
from app.dependencies.auth import require_auth
from app.models.products import (
    Locale,
    ProductListResponse,
    ProductResponse,
    SavedProductListResponse,
    SavedProductStatusResponse,
)
from app.models.users import UserResponse
from app.responses import error_response
from app.services import product_service, saved_products_service
from app.services.product_service import NotFoundError

router = APIRouter()

# Cap distinct label slugs accepted from the public filter (bounds query cost and
# keeps unauthenticated endpoint query cost bounded.
_MAX_LABEL_FILTERS = 50


def _parse_label_filters(labels: str | None, label: list[str] | None) -> list[str] | None:
    """Merge comma-separated and repeated label filters with stable de-duplication.

    Caps the number of distinct slugs (public, unauthenticated endpoint) so a
    request can't amplify query cost.
    """
    slugs: list[str] = []
    raw_values = [labels] if labels else []
    if label:
        raw_values.extend(label)

    for raw_value in raw_values:
        for raw in raw_value.split(","):
            slug = raw.strip()
            if slug and slug not in slugs:
                slugs.append(slug)
            if len(slugs) >= _MAX_LABEL_FILTERS:
                return slugs

    return slugs or None


@router.get(
    "",
    response_model=ProductListResponse,
    summary="List products",
    description="Browse active products with optional category filter, full-text search, "
    "sort order, and pagination. Search uses Postgres full-text search.",
)
async def list_products(
    product_type: str | None = Query(default=None, description="Filter by product type slug"),
    category: str | None = Query(default=None, description="Filter by category/tier slug"),
    labels: str | None = Query(
        default=None, description="Comma-separated label slugs (AND semantics)"
    ),
    label: list[str] | None = Query(
        default=None, description="Repeated label slug filter (AND semantics)"
    ),
    q: str | None = Query(default=None, description="Search query (FTS5)"),
    sort: Literal["price_asc", "price_desc", "name", "newest"] | None = Query(
        default=None, description="Sort order"
    ),
    in_stock: bool | None = Query(default=None, description="Filter to in-stock only"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    locale: Locale = Query(default="en", description="Content locale (en or bg)"),
) -> ProductListResponse | JSONResponse:
    """List active products with optional taxonomy filters, search, sort, pagination."""
    # Cap limit at 100 (also enforced by Query constraint but explicit for clarity)
    limit = min(limit, 100)

    label_list = _parse_label_filters(labels, label)

    # If search query is provided, use FTS5 search with SQL-level filtering (B.6)
    if q:
        offset = (page - 1) * limit
        products = product_service.search_products(
            q,
            product_type=product_type,
            category=category,
            labels=label_list,
            in_stock=in_stock,
            limit=limit,
            offset=offset,
            locale=locale,
            sort=sort,
        )

        # Price sorts are handled inside the service over effective price across
        # all matches. Name/newest sorts still order the returned page here
        # (search returns relevance-ordered results otherwise).
        if sort in ("name", "newest"):
            sort_key_map = {
                "name": lambda p: p.get("name", ""),
                "newest": lambda p: p.get("created_at", ""),
            }
            reverse = sort == "newest"
            products.sort(key=sort_key_map[sort], reverse=reverse)

        # Accurate total across all matches so pagination works on the search path.
        total = product_service.count_search_products(
            q,
            product_type=product_type,
            category=category,
            labels=label_list,
            in_stock=in_stock,
            locale=locale,
        )

        return ProductListResponse(
            products=[ProductResponse(**p) for p in products],
            total=total,
            page=page,
            limit=limit,
        )

    # Standard listing (no search query)
    products, total = product_service.list_products(
        product_type=product_type,
        category=category,
        labels=label_list,
        sort=sort,
        in_stock=in_stock,
        page=page,
        limit=limit,
        locale=locale,
    )

    return ProductListResponse(
        products=[ProductResponse(**p) for p in products],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/saved",
    response_model=SavedProductListResponse,
    summary="List saved products",
    description="List the current authenticated user's saved active products.",
)
async def list_saved_products(
    current_user: Annotated[UserResponse, Depends(require_auth)],
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=100, ge=1, le=100, description="Items per page (max 100)"),
    locale: Locale = Query(default="en", description="Content locale (en or bg)"),
) -> SavedProductListResponse:
    """List saved products for the current user."""
    with get_db() as conn:
        result = saved_products_service.list_saved_products(
            conn,
            user_id=current_user.id,
            page=page,
            limit=limit,
            locale=locale,
        )

    return SavedProductListResponse(
        products=[ProductResponse(**p) for p in result["products"]],
        product_ids=result["product_ids"],
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
    )


@router.post(
    "/{product_id}/saved",
    response_model=SavedProductStatusResponse,
    status_code=201,
    summary="Save product",
    description="Save an active product to the current authenticated user's shortlist.",
)
async def save_product(
    product_id: str,
    current_user: Annotated[UserResponse, Depends(require_auth)],
) -> SavedProductStatusResponse | JSONResponse:
    """Save a product for the current user."""
    try:
        with get_db() as conn:
            saved_products_service.save_product(
                conn,
                user_id=current_user.id,
                product_id=product_id,
            )
            conn.commit()
    except NotFoundError:
        return error_response(404, "NOT_FOUND", "Product not found")

    return SavedProductStatusResponse(product_id=product_id, saved=True)


@router.delete(
    "/{product_id}/saved",
    response_model=SavedProductStatusResponse,
    summary="Unsave product",
    description="Remove a product from the current authenticated user's shortlist.",
)
async def unsave_product(
    product_id: str,
    current_user: Annotated[UserResponse, Depends(require_auth)],
) -> SavedProductStatusResponse:
    """Unsave a product for the current user."""
    with get_db() as conn:
        saved_products_service.unsave_product(
            conn,
            user_id=current_user.id,
            product_id=product_id,
        )
        conn.commit()

    return SavedProductStatusResponse(product_id=product_id, saved=False)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product",
    description="Get a single active product by its slug ID. Returns 404 if the product "
    "does not exist or is inactive.",
)
async def get_product(
    product_id: str,
    locale: Locale = Query(default="en", description="Content locale (en or bg)"),
) -> ProductResponse | JSONResponse:
    """Get a single active product by ID."""
    try:
        product = product_service.get_product(product_id, locale=locale)
    except NotFoundError:
        return error_response(404, "NOT_FOUND", "Product not found")

    return ProductResponse(**product)
