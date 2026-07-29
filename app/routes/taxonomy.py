"""Taxonomy endpoints — public listing + admin CRUD for managed taxonomy.

The public router exposes `GET /v1/taxonomy` for storefront filter menus. The
admin router exposes CRUD for product types, categories/tiers, and labels under
`/v1/admin/taxonomy/*` behind admin auth. The three kinds share one shape, so
handlers delegate to kind-parameterized helpers.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.dependencies.auth import require_admin
from app.models.products import Locale
from app.models.taxonomy import (
    AdminTaxonomyTerm,
    CreateTaxonomyTermRequest,
    TaxonomyResponse,
    UpdateTaxonomyTermRequest,
)
from app.responses import error_response
from app.services import taxonomy_service
from app.services.taxonomy_service import (
    Kind,
    TaxonomyInUseError,
    TaxonomyNotFoundError,
    TaxonomyValidationError,
)

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get(
    "",
    response_model=TaxonomyResponse,
    summary="List active taxonomy",
    description="Return active product types, categories/tiers, and labels ordered by "
    "sort_order, localized by the optional `locale` query parameter.",
)
async def get_taxonomy(
    locale: Locale = Query(default="en", description="Content locale (en or bg)"),
) -> TaxonomyResponse:
    """Public taxonomy for building storefront sidebar filters."""
    return TaxonomyResponse(**taxonomy_service.list_public_taxonomy(locale))


# --- Shared admin handlers (kind-parameterized) ---


def _list_terms(kind: Kind) -> list[AdminTaxonomyTerm]:
    return [AdminTaxonomyTerm(**t) for t in taxonomy_service.list_admin_terms(kind)]


def _create_term(kind: Kind, body: CreateTaxonomyTermRequest) -> AdminTaxonomyTerm:
    term = taxonomy_service.create_term(kind, body.name_en, body.name_bg, body.sort_order)
    return AdminTaxonomyTerm(**term)


def _get_term(kind: Kind, slug: str) -> AdminTaxonomyTerm | JSONResponse:
    try:
        return AdminTaxonomyTerm(**taxonomy_service.get_admin_term(kind, slug))
    except TaxonomyNotFoundError:
        return _not_found(kind)


def _update_term(
    kind: Kind, slug: str, body: UpdateTaxonomyTermRequest
) -> AdminTaxonomyTerm | JSONResponse:
    try:
        term = taxonomy_service.update_term(kind, slug, body.model_dump(exclude_unset=True))
    except TaxonomyNotFoundError:
        return _not_found(kind)
    except TaxonomyValidationError as e:
        return error_response(422, "INVALID_TAXONOMY", str(e))
    return AdminTaxonomyTerm(**term)


def _delete_term(kind: Kind, slug: str) -> Response:
    try:
        taxonomy_service.delete_term(kind, slug)
    except TaxonomyNotFoundError:
        return _not_found(kind)
    except TaxonomyInUseError as e:
        return error_response(409, "TAXONOMY_IN_USE", str(e))
    return Response(status_code=204)


def _not_found(kind: Kind) -> JSONResponse:
    return error_response(404, "NOT_FOUND", f"{kind} term not found")


# --- Product types ---


@admin_router.get("/product-types", response_model=list[AdminTaxonomyTerm])
async def admin_list_product_types() -> list[AdminTaxonomyTerm]:
    return _list_terms("product-types")


@admin_router.post("/product-types", response_model=AdminTaxonomyTerm, status_code=201)
async def admin_create_product_type(body: CreateTaxonomyTermRequest) -> AdminTaxonomyTerm:
    return _create_term("product-types", body)


@admin_router.get("/product-types/{slug}", response_model=AdminTaxonomyTerm)
async def admin_get_product_type(slug: str) -> AdminTaxonomyTerm | JSONResponse:
    return _get_term("product-types", slug)


@admin_router.patch("/product-types/{slug}", response_model=AdminTaxonomyTerm)
async def admin_update_product_type(
    slug: str, body: UpdateTaxonomyTermRequest
) -> AdminTaxonomyTerm | JSONResponse:
    return _update_term("product-types", slug, body)


@admin_router.delete("/product-types/{slug}", status_code=204, response_class=Response)
async def admin_delete_product_type(slug: str) -> Response:
    return _delete_term("product-types", slug)


# --- Categories / tiers ---


@admin_router.get("/categories", response_model=list[AdminTaxonomyTerm])
async def admin_list_categories() -> list[AdminTaxonomyTerm]:
    return _list_terms("categories")


@admin_router.post("/categories", response_model=AdminTaxonomyTerm, status_code=201)
async def admin_create_category(body: CreateTaxonomyTermRequest) -> AdminTaxonomyTerm:
    return _create_term("categories", body)


@admin_router.get("/categories/{slug}", response_model=AdminTaxonomyTerm)
async def admin_get_category(slug: str) -> AdminTaxonomyTerm | JSONResponse:
    return _get_term("categories", slug)


@admin_router.patch("/categories/{slug}", response_model=AdminTaxonomyTerm)
async def admin_update_category(
    slug: str, body: UpdateTaxonomyTermRequest
) -> AdminTaxonomyTerm | JSONResponse:
    return _update_term("categories", slug, body)


@admin_router.delete("/categories/{slug}", status_code=204, response_class=Response)
async def admin_delete_category(slug: str) -> Response:
    return _delete_term("categories", slug)


# --- Labels ---


@admin_router.get("/labels", response_model=list[AdminTaxonomyTerm])
async def admin_list_labels() -> list[AdminTaxonomyTerm]:
    return _list_terms("labels")


@admin_router.post("/labels", response_model=AdminTaxonomyTerm, status_code=201)
async def admin_create_label(body: CreateTaxonomyTermRequest) -> AdminTaxonomyTerm:
    return _create_term("labels", body)


@admin_router.get("/labels/{slug}", response_model=AdminTaxonomyTerm)
async def admin_get_label(slug: str) -> AdminTaxonomyTerm | JSONResponse:
    return _get_term("labels", slug)


@admin_router.patch("/labels/{slug}", response_model=AdminTaxonomyTerm)
async def admin_update_label(
    slug: str, body: UpdateTaxonomyTermRequest
) -> AdminTaxonomyTerm | JSONResponse:
    return _update_term("labels", slug, body)


@admin_router.delete("/labels/{slug}", status_code=204, response_class=Response)
async def admin_delete_label(slug: str) -> Response:
    return _delete_term("labels", slug)
