"""Public product endpoints — listing and detail."""

from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.models.products import Locale, ProductListResponse, ProductResponse
from app.services import product_service
from app.services.product_service import NotFoundError

router = APIRouter()


@router.get(
    "",
    response_model=ProductListResponse,
    summary="List products",
    description="Browse active products with optional category filter, full-text search, "
    "sort order, and pagination. Search uses SQLite FTS5 for relevance-ranked results.",
)
async def list_products(
    product_type: str | None = Query(default=None, description="Filter by product type slug"),
    category: str | None = Query(default=None, description="Filter by category/tier slug"),
    labels: str | None = Query(
        default=None, description="Comma-separated label slugs (AND semantics)"
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

    # Parse comma-separated label slugs into a list.
    label_list = [s.strip() for s in labels.split(",") if s.strip()] if labels else None

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
        )

        # Apply sort override if specified (otherwise FTS5 relevance is used)
        if sort:
            sort_key_map = {
                "price_asc": lambda p: p.get("price_cents", 0),
                "price_desc": lambda p: p.get("price_cents", 0),
                "name": lambda p: p.get("name", ""),
                "newest": lambda p: p.get("created_at", ""),
            }
            reverse = sort in ("price_desc", "newest")
            products.sort(key=sort_key_map[sort], reverse=reverse)

        # Total is approximate for FTS — return what we have
        total = len(products)

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
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )

    return ProductResponse(**product)
