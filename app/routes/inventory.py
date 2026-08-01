"""Admin inventory endpoints for materials and movement-ledger setup."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.dependencies.auth import require_admin
from app.models.inventory import (
    InventoryMovementListResponse,
    InventoryMovementResponse,
    MaterialAdjustmentRequest,
    MaterialCreateRequest,
    MaterialDetailResponse,
    MaterialListResponse,
    MaterialLotListResponse,
    MaterialReceiptRequest,
    MaterialReceiptResponse,
    MaterialResponse,
    MaterialUpdateRequest,
    RecipeCostSnapshotRequest,
    RecipeCostSnapshotResponse,
    RecipeDiagnosticsListResponse,
    RecipeReviewRequest,
    RecipeVersionCreateRequest,
    RecipeVersionListResponse,
    RecipeVersionResponse,
    RecipeVersionUpdateRequest,
    ProductionBatchCorrectionRequest,
    ProductionBatchCreateRequest,
    ProductionBatchListResponse,
    ProductionBatchPostRequest,
    ProductionBatchResponse,
    ProductionBatchUpdateRequest,
    ProductionTraceabilityResponse,
    COGSLedgerListResponse,
    InventoryClosePreviewResponse,
    InventoryExceptionResponse,
    InventoryValuationSettingsRequest,
    InventoryValuationSettingsResponse,
    OpeningBalanceRequest,
    ValuationLayerListResponse,
    ValuationLayerResponse,
)
from app.models.users import UserResponse
from app.responses import error_response
from app.services import inventory_service
from app.services.inventory_service import (
    InventoryValidationError,
    MaterialNotFoundError,
    ProductionBatchNotFoundError,
    RecipeNotFoundError,
)

admin_router = APIRouter()


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, no-cache"


def _actor(current_admin: UserResponse | None) -> tuple[str | None, str | None]:
    if current_admin is None:
        return None, None
    return current_admin.id, current_admin.email


def _not_found(message: str) -> JSONResponse:
    return error_response(404, "NOT_FOUND", message)


def _validation(message: str) -> JSONResponse:
    return error_response(422, "INVALID_INVENTORY", message)


@admin_router.get("/materials", response_model=MaterialListResponse)
async def list_materials(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    active: bool | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=100),
    needs_reorder: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> MaterialListResponse:
    _no_store(response)
    return inventory_service.list_materials(
        active=active,
        category=category,
        needs_reorder=needs_reorder,
        limit=limit,
        offset=offset,
    )


@admin_router.get("/reorder", response_model=MaterialListResponse)
async def list_reorder_materials(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> MaterialListResponse:
    _no_store(response)
    return inventory_service.list_materials(active=True, needs_reorder=True)


@admin_router.get("/movements", response_model=InventoryMovementListResponse)
async def list_inventory_movements(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    item_type: str | None = Query(default=None, pattern="^(material|finished_good)$"),
    item_id: str | None = Query(default=None, min_length=1, max_length=100),
    source_type: str | None = Query(default=None, min_length=1, max_length=100),
    source_id: str | None = Query(default=None, min_length=1, max_length=100),
    order_id: str | None = Query(default=None, min_length=1, max_length=100),
    movement_type: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> InventoryMovementListResponse:
    _no_store(response)
    movements, total = inventory_service.list_inventory_movements(
        item_type=item_type,
        item_id=item_id,
        source_type=source_type,
        source_id=source_id,
        order_id=order_id,
        movement_type=movement_type,
        limit=limit,
        offset=offset,
    )
    return InventoryMovementListResponse(movements=movements, total=total)


@admin_router.post("/materials", response_model=MaterialResponse, status_code=201)
async def create_material(
    body: MaterialCreateRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> MaterialResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.create_material(body, actor_user_id=actor_user_id)
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.get("/materials/{material_id}", response_model=MaterialDetailResponse)
async def get_material(
    material_id: str,
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> MaterialDetailResponse | JSONResponse:
    _no_store(response)
    try:
        return inventory_service.get_material(material_id)
    except MaterialNotFoundError:
        return _not_found("Material not found")


@admin_router.patch("/materials/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: str,
    body: MaterialUpdateRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> MaterialResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.update_material(material_id, body, actor_user_id=actor_user_id)
    except MaterialNotFoundError:
        return _not_found("Material not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.post("/materials/{material_id}/receipts", response_model=MaterialReceiptResponse, status_code=201)
async def create_material_receipt(
    material_id: str,
    body: MaterialReceiptRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> MaterialReceiptResponse | JSONResponse:
    _no_store(response)
    actor_user_id, actor_email = _actor(current_admin)
    try:
        return inventory_service.create_material_receipt(
            material_id,
            body,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
        )
    except MaterialNotFoundError:
        return _not_found("Material not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.post("/materials/{material_id}/adjustments", response_model=InventoryMovementResponse, status_code=201)
async def create_material_adjustment(
    material_id: str,
    body: MaterialAdjustmentRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> InventoryMovementResponse | JSONResponse:
    _no_store(response)
    actor_user_id, actor_email = _actor(current_admin)
    try:
        return inventory_service.create_material_adjustment(
            material_id,
            body,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
        )
    except MaterialNotFoundError:
        return _not_found("Material not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.get("/materials/{material_id}/lots", response_model=MaterialLotListResponse)
async def list_material_lots(
    material_id: str,
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    production_date: str | None = Query(default=None, min_length=10, max_length=32),
    near_expiry_days: int = Query(default=30, ge=0, le=365),
) -> MaterialLotListResponse | JSONResponse:
    _no_store(response)
    try:
        return inventory_service.list_material_lots(
            material_id,
            production_date=production_date,
            near_expiry_days=near_expiry_days,
        )
    except MaterialNotFoundError:
        return _not_found("Material not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.get("/materials/{material_id}/movements", response_model=InventoryMovementListResponse)
async def list_material_movements(
    material_id: str,
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    limit: int = Query(default=100, ge=1, le=500),
) -> InventoryMovementListResponse | JSONResponse:
    _no_store(response)
    try:
        movements = inventory_service.list_material_movements(material_id, limit=limit)
    except MaterialNotFoundError:
        return _not_found("Material not found")
    return InventoryMovementListResponse(movements=movements, total=len(movements))


@admin_router.get("/recipes", response_model=RecipeVersionListResponse)
async def list_recipes(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    product_id: str | None = Query(default=None, min_length=1, max_length=100),
    status: str | None = Query(default=None, pattern="^(draft|active|archived)$"),
) -> RecipeVersionListResponse:
    _no_store(response)
    return inventory_service.list_recipe_versions(product_id=product_id, status=status)


@admin_router.post("/recipes", response_model=RecipeVersionResponse, status_code=201)
async def create_recipe(
    body: RecipeVersionCreateRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> RecipeVersionResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.create_recipe_version(body, actor_user_id=actor_user_id)
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.get("/recipes/{recipe_id}", response_model=RecipeVersionResponse)
async def get_recipe(
    recipe_id: str,
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> RecipeVersionResponse | JSONResponse:
    _no_store(response)
    try:
        return inventory_service.get_recipe_version(recipe_id)
    except RecipeNotFoundError:
        return _not_found("Recipe not found")


@admin_router.patch("/recipes/{recipe_id}", response_model=RecipeVersionResponse)
async def update_recipe(
    recipe_id: str,
    body: RecipeVersionUpdateRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> RecipeVersionResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.update_recipe_version(recipe_id, body, actor_user_id=actor_user_id)
    except RecipeNotFoundError:
        return _not_found("Recipe not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.post("/recipes/{recipe_id}/activate", response_model=RecipeVersionResponse)
async def activate_recipe(
    recipe_id: str,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> RecipeVersionResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.activate_recipe_version(recipe_id, actor_user_id=actor_user_id)
    except RecipeNotFoundError:
        return _not_found("Recipe not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.post("/recipes/{recipe_id}/archive", response_model=RecipeVersionResponse)
async def archive_recipe(
    recipe_id: str,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> RecipeVersionResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.archive_recipe_version(recipe_id, actor_user_id=actor_user_id)
    except RecipeNotFoundError:
        return _not_found("Recipe not found")


@admin_router.post(
    "/recipes/{recipe_id}/cost-snapshots",
    response_model=RecipeCostSnapshotResponse,
    status_code=201,
)
async def create_recipe_cost_snapshot(
    recipe_id: str,
    body: RecipeCostSnapshotRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> RecipeCostSnapshotResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.create_recipe_cost_snapshot(
            recipe_id,
            body,
            actor_user_id=actor_user_id,
        )
    except RecipeNotFoundError:
        return _not_found("Recipe not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.post("/recipes/{recipe_id}/review", response_model=RecipeVersionResponse)
async def review_recipe(
    recipe_id: str,
    body: RecipeReviewRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> RecipeVersionResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.review_recipe_version(recipe_id, body, actor_user_id=actor_user_id)
    except RecipeNotFoundError:
        return _not_found("Recipe not found")


@admin_router.get("/recipes/{recipe_id}/diagnostics", response_model=RecipeDiagnosticsListResponse)
async def get_recipe_diagnostics(
    recipe_id: str,
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> RecipeDiagnosticsListResponse | JSONResponse:
    _no_store(response)
    try:
        return inventory_service.recipe_diagnostics(recipe_id)
    except RecipeNotFoundError:
        return _not_found("Recipe not found")


@admin_router.get("/products/{product_id}/active-recipe", response_model=RecipeVersionResponse)
async def get_active_product_recipe(
    product_id: str,
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    as_of_date: str | None = Query(default=None, min_length=10, max_length=32),
) -> RecipeVersionResponse | JSONResponse:
    _no_store(response)
    try:
        return inventory_service.get_active_recipe_for_product(product_id, as_of_date=as_of_date)
    except RecipeNotFoundError:
        return _not_found("Active recipe not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.get(
    "/products/{product_id}/recipe-diagnostics",
    response_model=RecipeDiagnosticsListResponse,
)
async def get_product_recipe_diagnostics(
    product_id: str,
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> RecipeDiagnosticsListResponse | JSONResponse:
    _no_store(response)
    try:
        return inventory_service.product_recipe_diagnostics(product_id)
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.get("/batches", response_model=ProductionBatchListResponse)
async def list_batches(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    product_id: str | None = Query(default=None, min_length=1, max_length=100),
    status: str | None = Query(default=None, pattern="^(draft|produced|cancelled)$"),
) -> ProductionBatchListResponse:
    _no_store(response)
    return inventory_service.list_production_batches(product_id=product_id, status=status)


@admin_router.post("/batches", response_model=ProductionBatchResponse, status_code=201)
async def create_batch(
    body: ProductionBatchCreateRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ProductionBatchResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.create_production_batch(body, actor_user_id=actor_user_id)
    except RecipeNotFoundError:
        return _not_found("Active recipe not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.get("/batches/{batch_id}", response_model=ProductionBatchResponse)
async def get_batch(
    batch_id: str,
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ProductionBatchResponse | JSONResponse:
    _no_store(response)
    try:
        return inventory_service.get_production_batch(batch_id)
    except ProductionBatchNotFoundError:
        return _not_found("Production batch not found")


@admin_router.patch("/batches/{batch_id}", response_model=ProductionBatchResponse)
async def update_batch(
    batch_id: str,
    body: ProductionBatchUpdateRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ProductionBatchResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.update_production_batch(
            batch_id,
            body,
            actor_user_id=actor_user_id,
        )
    except ProductionBatchNotFoundError:
        return _not_found("Production batch not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.post("/batches/{batch_id}/post", response_model=ProductionBatchResponse)
async def post_batch(
    batch_id: str,
    body: ProductionBatchPostRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ProductionBatchResponse | JSONResponse:
    _no_store(response)
    actor_user_id, actor_email = _actor(current_admin)
    try:
        return inventory_service.post_production_batch(
            batch_id,
            body,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
        )
    except ProductionBatchNotFoundError:
        return _not_found("Production batch not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.post("/batches/{batch_id}/cancel", response_model=ProductionBatchResponse)
async def cancel_batch(
    batch_id: str,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ProductionBatchResponse | JSONResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    try:
        return inventory_service.cancel_production_batch(batch_id, actor_user_id=actor_user_id)
    except ProductionBatchNotFoundError:
        return _not_found("Production batch not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.post("/batches/{batch_id}/correct", response_model=InventoryMovementResponse, status_code=201)
async def correct_batch(
    batch_id: str,
    body: ProductionBatchCorrectionRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> InventoryMovementResponse | JSONResponse:
    _no_store(response)
    actor_user_id, actor_email = _actor(current_admin)
    try:
        return inventory_service.correct_production_batch(
            batch_id,
            body,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
        )
    except ProductionBatchNotFoundError:
        return _not_found("Production batch not found")
    except InventoryValidationError as exc:
        return _validation(str(exc))


@admin_router.get("/batches/{batch_id}/traceability", response_model=ProductionTraceabilityResponse)
async def get_batch_traceability(
    batch_id: str,
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ProductionTraceabilityResponse | JSONResponse:
    _no_store(response)
    try:
        return inventory_service.production_traceability(batch_id)
    except ProductionBatchNotFoundError:
        return _not_found("Production batch not found")


@admin_router.get("/valuation/settings", response_model=InventoryValuationSettingsResponse)
async def get_valuation_settings(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> InventoryValuationSettingsResponse:
    _no_store(response)
    return inventory_service.get_inventory_valuation_settings()


@admin_router.put("/valuation/settings", response_model=InventoryValuationSettingsResponse)
async def update_valuation_settings(
    body: InventoryValuationSettingsRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> InventoryValuationSettingsResponse:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    return inventory_service.update_inventory_valuation_settings(
        body,
        actor_user_id=actor_user_id,
    )


@admin_router.post("/valuation/opening-balances", response_model=ValuationLayerResponse | None)
async def record_opening_balance(
    body: OpeningBalanceRequest,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ValuationLayerResponse | None:
    _no_store(response)
    actor_user_id, _actor_email = _actor(current_admin)
    return inventory_service.record_opening_balance(body, actor_user_id=actor_user_id)


@admin_router.post("/valuation/layers/generate", response_model=ValuationLayerListResponse)
async def generate_valuation_layers(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ValuationLayerListResponse:
    _no_store(response)
    return inventory_service.generate_valuation_layers()


@admin_router.get("/valuation/layers", response_model=ValuationLayerListResponse)
async def list_valuation_layers(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    item_type: str | None = Query(default=None, pattern="^(material|finished_good)$"),
    item_id: str | None = Query(default=None, min_length=1, max_length=100),
) -> ValuationLayerListResponse:
    _no_store(response)
    return inventory_service.list_valuation_layers(item_type=item_type, item_id=item_id)


@admin_router.post("/valuation/cogs/generate", response_model=COGSLedgerListResponse)
async def generate_cogs_rows(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> COGSLedgerListResponse:
    _no_store(response)
    return inventory_service.generate_cogs_rows()


@admin_router.get("/valuation/cogs", response_model=COGSLedgerListResponse)
async def list_cogs_rows(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    product_id: str | None = Query(default=None, min_length=1, max_length=100),
    order_id: str | None = Query(default=None, min_length=1, max_length=100),
) -> COGSLedgerListResponse:
    _no_store(response)
    return inventory_service.list_cogs_rows(product_id=product_id, order_id=order_id)


@admin_router.get("/valuation/close-preview", response_model=InventoryClosePreviewResponse)
async def inventory_close_preview(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    period_start: str = Query(..., min_length=10, max_length=32),
    period_end: str = Query(..., min_length=10, max_length=32),
) -> InventoryClosePreviewResponse:
    _no_store(response)
    return inventory_service.inventory_close_preview(period_start, period_end)


@admin_router.get("/valuation/exceptions", response_model=list[InventoryExceptionResponse])
async def valuation_exceptions(
    response: Response,
    _current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    target_type: str | None = Query(default=None, min_length=1, max_length=100),
    target_id: str | None = Query(default=None, min_length=1, max_length=100),
    source_type: str | None = Query(default=None, min_length=1, max_length=100),
    source_id: str | None = Query(default=None, min_length=1, max_length=100),
    order_id: str | None = Query(default=None, min_length=1, max_length=100),
) -> list[InventoryExceptionResponse]:
    _no_store(response)
    return [
        InventoryExceptionResponse.model_validate(item)
        for item in inventory_service.valuation_exceptions(
            target_type=target_type,
            target_id=target_id,
            source_type=source_type,
            source_id=source_id,
            order_id=order_id,
        )
    ]
