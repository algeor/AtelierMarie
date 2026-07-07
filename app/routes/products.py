"""Public product endpoints — listing and detail."""

from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.models.products import ProductListResponse, ProductResponse
from app.services import product_service
from app.services.product_service import NotFoundError

router = APIRouter()


@router.get("", response_model=ProductListResponse)
async def list_products(
    category: str | None = Query(default=None, description="Filter by category"),
    q: str | None = Query(default=None, description="Search query (FTS5)"),
    sort: Literal["price_asc", "price_desc", "name", "newest"] | None = Query(
        default=None, description="Sort order"
    ),
    in_stock: bool | None = Query(default=None, description="Filter to in-stock only"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
) -> ProductListResponse | JSONResponse:
    """List active products with optional filters, search, sort, and pagination."""
    # Cap limit at 100 (also enforced by Query constraint but explicit for clarity)
    limit = min(limit, 100)

    # If search query is provided, use FTS5 search
    if q:
        products = product_service.search_products(q, limit=limit)
        # Apply additional filters on search results
        if category:
            products = [p for p in products if p.get("category") == category]
        if in_stock:
            products = [p for p in products if p.get("stock", 0) > 0]

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

        # Paginate search results
        total = len(products)
        start = (page - 1) * limit
        page_products = products[start : start + limit]

        return ProductListResponse(
            products=[ProductResponse(**p) for p in page_products],
            total=total,
            page=page,
            limit=limit,
        )

    # Standard listing (no search query)
    products, total = product_service.list_products(
        category=category,
        sort=sort,
        in_stock=in_stock,
        page=page,
        limit=limit,
    )

    return ProductListResponse(
        products=[ProductResponse(**p) for p in products],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str) -> ProductResponse | JSONResponse:
    """Get a single active product by ID."""
    try:
        product = product_service.get_product(product_id)
    except NotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )

    return ProductResponse(**product)
