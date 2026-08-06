"""Material inventory services backed by the immutable movement ledger."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.database import DbConnection, IntegrityError, get_db
from app.models.inventory import (
    COGSLedgerListResponse,
    COGSLedgerResponse,
    InventoryClosePreviewResponse,
    InventoryMovementResponse,
    InventoryValuationSettingsRequest,
    InventoryValuationSettingsResponse,
    MaterialAdjustmentRequest,
    MaterialCreateRequest,
    MaterialDetailResponse,
    MaterialListResponse,
    MaterialLotListResponse,
    MaterialLotResponse,
    MaterialReceiptRequest,
    MaterialReceiptResponse,
    MaterialResponse,
    MaterialUpdateRequest,
    OpeningBalanceRequest,
    ProductionBatchConsumptionResponse,
    ProductionBatchCorrectionRequest,
    ProductionBatchCreateRequest,
    ProductionBatchListResponse,
    ProductionBatchOutputResponse,
    ProductionBatchPostRequest,
    ProductionBatchResponse,
    ProductionBatchUpdateRequest,
    ProductionTraceabilityResponse,
    RecipeComponentRequest,
    RecipeComponentResponse,
    RecipeCostSnapshotRequest,
    RecipeCostSnapshotResponse,
    RecipeDiagnosticResponse,
    RecipeDiagnosticsListResponse,
    RecipeReviewRequest,
    RecipeVersionCreateRequest,
    RecipeVersionListResponse,
    RecipeVersionResponse,
    RecipeVersionUpdateRequest,
    ValuationLayerListResponse,
    ValuationLayerResponse,
)
from app.services.pricing import now_utc


class InventoryValidationError(Exception):
    """Raised when an inventory request fails domain validation."""


class MaterialNotFoundError(Exception):
    """Raised when a material id does not exist."""


class RecipeNotFoundError(Exception):
    """Raised when a recipe/BOM version id does not exist."""


class ProductionBatchNotFoundError(Exception):
    """Raised when a production batch id does not exist."""


_RECEIPT_REVIEW_MESSAGES = {
    "missing_receipt_evidence": "Receipt is missing required supplier evidence.",
    "missing_supplier_lot": "Receipt is missing required supplier lot metadata.",
    "missing_expiry_metadata": "Receipt is missing required expiry or use-by metadata.",
    "missing_unit_cost": "Receipt is missing unit cost needed for official valuation.",
}


def _uuid() -> str:
    return str(uuid.uuid4())


def _decimal(value: str | int | float | Decimal, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InventoryValidationError(f"{field} must be a decimal number") from exc
    if parsed.is_nan() or parsed.is_infinite():
        raise InventoryValidationError(f"{field} must be finite")
    return parsed


def _decimal_amount(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = _decimal(value, "unit_cost_amount")
    if parsed < 0:
        raise InventoryValidationError("unit_cost_amount must not be negative")
    return str(parsed.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def _unit_cost_from_total(total_cost_cents: int | None, stock_quantity: float) -> str | None:
    if total_cost_cents is None:
        return None
    if stock_quantity <= 0:
        raise InventoryValidationError("stock_quantity must be positive")
    total = Decimal(total_cost_cents) / Decimal(100)
    unit = total / _decimal(stock_quantity, "stock_quantity")
    return str(unit.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def _bool_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


# TIMESTAMPTZ/DATE read policy (Decision 15): psycopg returns ``datetime``/``date``
# objects for these columns, but the inventory response models declare the fields
# as ``str``. Coerce reads to the canonical string shape they were written with so
# Pydantic validation passes; ``None`` and existing strings pass through unchanged.
_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _s(value: Any) -> Any:
    """Render a DATE/TIMESTAMPTZ column value as its canonical string form."""
    if isinstance(value, datetime):
        return value.strftime(_DT_FMT)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _coerce_row_dates(row: Any) -> dict[str, Any]:
    """Copy a row to a plain dict, coercing DATE/TIMESTAMPTZ values to strings."""
    return {key: _s(value) for key, value in dict(row).items()}


def _validate_material_units(
    *,
    stock_uom: str,
    purchase_uom: str | None,
    purchase_to_stock_factor: float | None,
) -> float | None:
    if purchase_uom is None:
        return None
    if purchase_uom == stock_uom and purchase_to_stock_factor is None:
        return 1.0
    if purchase_uom != stock_uom and purchase_to_stock_factor is None:
        raise InventoryValidationError(
            "purchase_to_stock_factor is required when purchase_uom differs from stock_uom"
        )
    return purchase_to_stock_factor


def _material_on_hand_expr() -> str:
    return """
        COALESCE((
            SELECT SUM(im.quantity_delta)
            FROM inventory_movements im
            WHERE im.item_type = 'material' AND im.item_id = m.id
        ), 0) AS on_hand_quantity,
        (
            SELECT MAX(im.occurred_at)
            FROM inventory_movements im
            WHERE im.item_type = 'material' AND im.item_id = m.id
        ) AS latest_movement_at,
        (
            SELECT COUNT(*)
            FROM inventory_exceptions e
            WHERE e.status = 'open'
              AND (
                (e.target_type = 'material' AND e.target_id = m.id)
                OR (e.source_type = 'material' AND e.source_id = m.id)
              )
        ) AS open_exception_count
    """


def _reorder_status(row: dict[str, Any]) -> str:
    if not bool(row["active"]):
        return "inactive"
    threshold = row["reorder_threshold"]
    if threshold is None:
        return "not_configured"
    return "below_threshold" if float(row["on_hand_quantity"] or 0) <= float(threshold) else "ok"


def _material_response_from_row(row: dict) -> MaterialResponse:
    return MaterialResponse(
        id=row["id"],
        sku=row["sku"],
        name=row["name"],
        category=row["category"],
        stock_uom=row["stock_uom"],
        purchase_uom=row["purchase_uom"],
        purchase_to_stock_factor=row["purchase_to_stock_factor"],
        preferred_supplier_name=row["preferred_supplier_name"],
        preferred_supplier_sku=row["preferred_supplier_sku"],
        reorder_threshold=row["reorder_threshold"],
        active=bool(row["active"]),
        lot_tracked=bool(row["lot_tracked"]),
        expiry_tracked=bool(row["expiry_tracked"]),
        evidence_required=bool(row["evidence_required"]),
        on_hand_quantity=float(row["on_hand_quantity"] or 0),
        reorder_status=_reorder_status(row),
        open_exception_count=int(row["open_exception_count"] or 0),
        latest_movement_at=_s(row["latest_movement_at"]),
        notes=row["notes"],
        created_at=_s(row["created_at"]),
        updated_at=_s(row["updated_at"]),
    )


def _movement_response_from_row(row: dict) -> InventoryMovementResponse:
    return InventoryMovementResponse(
        id=row["id"],
        item_type=row["item_type"],
        item_id=row["item_id"],
        movement_type=row["movement_type"],
        quantity_delta=float(row["quantity_delta"]),
        uom=row["uom"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        material_lot_id=row["material_lot_id"],
        actor_user_id=row["actor_user_id"],
        actor_email=row["actor_email"],
        reason=row["reason"],
        notes=row["notes"],
        review_state=row["review_state"],
        occurred_at=_s(row["occurred_at"]),
        created_at=_s(row["created_at"]),
    )


def _exception_response_from_row(row: dict) -> dict[str, object]:
    return {
        "id": row["id"],
        "exception_type": row["exception_type"],
        "severity": row["severity"],
        "target_type": row["target_type"],
        "target_id": row["target_id"],
        "source_type": row["source_type"],
        "source_id": row["source_id"],
        "status": row["status"],
        "message": row["message"],
        "created_at": _s(row["created_at"]),
    }


def _lot_status(row: dict, production_date: date | None, near_expiry_days: int) -> str:
    expiry_value = _s(row["use_by_date"]) or _s(row["expiry_date"])
    if not expiry_value or production_date is None:
        return "unknown"
    if isinstance(expiry_value, date):
        expiry = expiry_value
    else:
        try:
            expiry = date.fromisoformat(str(expiry_value)[:10])
        except ValueError:
            return "unknown"
    if expiry < production_date:
        return "expired"
    if expiry <= production_date + timedelta(days=near_expiry_days):
        return "near_expiry"
    return "ok"


def _lot_response_from_row(
    row: dict,
    *,
    production_date: date | None = None,
    near_expiry_days: int = 30,
) -> MaterialLotResponse:
    return MaterialLotResponse(
        id=row["id"],
        material_id=row["material_id"],
        receipt_id=row["receipt_id"],
        supplier_lot=row["supplier_lot"],
        expiry_date=_s(row["expiry_date"]),
        use_by_date=_s(row["use_by_date"]),
        received_quantity=float(row["received_quantity"]),
        stock_uom=row["stock_uom"],
        remaining_quantity_snapshot=row["remaining_quantity_snapshot"],
        unit_cost_amount=row["unit_cost_amount"],
        currency=row["currency"],
        supplier_name=row["supplier_name"],
        review_state=row["review_state"],
        lot_status=_lot_status(row, production_date, near_expiry_days),
        created_at=_s(row["created_at"]),
        updated_at=_s(row["updated_at"]),
    )


def _get_material_row(conn: DbConnection, material_id: str) -> dict:
    row = conn.execute("SELECT * FROM materials WHERE id = %s", (material_id,)).fetchone()
    if row is None:
        raise MaterialNotFoundError(f"Material not found: {material_id}")
    return row


def _get_material_with_metrics(conn: DbConnection, material_id: str) -> dict:
    row = conn.execute(
        f"""
        SELECT m.*, {_material_on_hand_expr()}
        FROM materials m
        WHERE m.id = %s
        """,  # noqa: S608
        (material_id,),
    ).fetchone()
    if row is None:
        raise MaterialNotFoundError(f"Material not found: {material_id}")
    return row


def list_materials(
    *,
    active: bool | None = None,
    category: str | None = None,
    needs_reorder: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> MaterialListResponse:
    """List materials with on-hand quantity derived from inventory movements."""
    where: list[str] = []
    params: list[object] = []
    if active is not None:
        where.append("m.active = %s")
        params.append(1 if active else 0)
    if category:
        where.append("m.category = %s")
        params.append(category)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with get_db() as conn:
        limit_sql = "" if needs_reorder else "LIMIT %s OFFSET %s"
        query_params = tuple(params) if needs_reorder else (*params, limit, offset)
        rows = conn.execute(
            f"""
            SELECT m.*, {_material_on_hand_expr()}
            FROM materials m
            {where_sql}
            ORDER BY m.category, m.name, m.id
            {limit_sql}
            """,  # noqa: S608
            query_params,
        ).fetchall()
        materials = [_material_response_from_row(row) for row in rows]
        if needs_reorder:
            materials = [m for m in materials if m.reorder_status == "below_threshold"]
            total = len(materials)
            materials = materials[offset : offset + limit]
        else:
            total = conn.execute(
                f"SELECT COUNT(*) AS n FROM materials m {where_sql}",  # noqa: S608
                params,
            ).fetchone()["n"]
    return MaterialListResponse(materials=materials, total=total)


def get_material(material_id: str) -> MaterialDetailResponse:
    """Return one material with lots, recent movements, and open exceptions."""
    with get_db() as conn:
        material = _material_response_from_row(_get_material_with_metrics(conn, material_id))
        lots = [
            _lot_response_from_row(row)
            for row in conn.execute(
                """
                SELECT * FROM material_lots
                WHERE material_id = %s
                ORDER BY COALESCE(expiry_date, use_by_date, '9999-12-31'), created_at DESC
                """,
                (material_id,),
            ).fetchall()
        ]
        movements = [
            _movement_response_from_row(row)
            for row in conn.execute(
                """
                SELECT * FROM inventory_movements
                WHERE item_type = 'material' AND item_id = %s
                ORDER BY occurred_at DESC, created_at DESC
                LIMIT 25
                """,
                (material_id,),
            ).fetchall()
        ]
        exceptions = [
            _exception_response_from_row(row)
            for row in conn.execute(
                """
                SELECT * FROM inventory_exceptions
                WHERE status = 'open'
                  AND target_type = 'material'
                  AND target_id = %s
                ORDER BY created_at DESC
                """,
                (material_id,),
            ).fetchall()
        ]

    return MaterialDetailResponse(
        **material.model_dump(),
        lots=lots,
        recent_movements=movements,
        exceptions=exceptions,
    )


def create_material(
    request: MaterialCreateRequest,
    *,
    actor_user_id: str | None = None,
) -> MaterialResponse:
    """Create a material catalog row."""
    data = request.model_dump()
    data["purchase_to_stock_factor"] = _validate_material_units(
        stock_uom=data["stock_uom"],
        purchase_uom=data["purchase_uom"],
        purchase_to_stock_factor=data["purchase_to_stock_factor"],
    )
    material_id = _uuid()
    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO materials (
                    id, sku, name, category, stock_uom, purchase_uom,
                    purchase_to_stock_factor, preferred_supplier_name,
                    preferred_supplier_sku, reorder_threshold, active, lot_tracked,
                    expiry_tracked, evidence_required, notes, created_by_admin_id,
                    updated_by_admin_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    material_id,
                    data["sku"],
                    data["name"],
                    data["category"],
                    data["stock_uom"],
                    data["purchase_uom"],
                    data["purchase_to_stock_factor"],
                    data["preferred_supplier_name"],
                    data["preferred_supplier_sku"],
                    data["reorder_threshold"],
                    _bool_int(data["active"]),
                    _bool_int(data["lot_tracked"]),
                    _bool_int(data["expiry_tracked"]),
                    _bool_int(data["evidence_required"]),
                    data["notes"],
                    actor_user_id,
                    actor_user_id,
                ),
            )
            row = _get_material_with_metrics(conn, material_id)
            return _material_response_from_row(row)
    except IntegrityError as exc:
        raise InventoryValidationError("Material SKU or data violates schema constraints") from exc


def update_material(
    material_id: str,
    request: MaterialUpdateRequest,
    *,
    actor_user_id: str | None = None,
) -> MaterialResponse:
    """Update editable material catalog fields."""
    updates = request.model_dump(exclude_unset=True)
    with get_db() as conn:
        existing = _get_material_row(conn, material_id)
        merged = {key: existing[key] for key in existing.keys()}
        merged.update(updates)
        merged["purchase_to_stock_factor"] = _validate_material_units(
            stock_uom=merged["stock_uom"],
            purchase_uom=merged["purchase_uom"],
            purchase_to_stock_factor=merged["purchase_to_stock_factor"],
        )
        updates["purchase_to_stock_factor"] = merged["purchase_to_stock_factor"]
        if actor_user_id is not None:
            updates["updated_by_admin_id"] = actor_user_id
        for key in ("active", "lot_tracked", "expiry_tracked", "evidence_required"):
            if key in updates:
                updates[key] = _bool_int(updates[key])
        if updates:
            set_clause = ", ".join(f"{key} = %s" for key in updates)
            try:
                conn.execute(
                    f"UPDATE materials SET {set_clause} WHERE id = %s",  # noqa: S608
                    (*updates.values(), material_id),
                )
            except IntegrityError as exc:
                raise InventoryValidationError(
                    "Material SKU or data violates schema constraints"
                ) from exc
        return _material_response_from_row(_get_material_with_metrics(conn, material_id))


def _stock_quantity(material: dict, quantity: float, uom: str) -> float:
    if uom == material["stock_uom"]:
        return quantity
    if uom == material["purchase_uom"] and material["purchase_to_stock_factor"]:
        return float(
            _decimal(quantity, "quantity")
            * _decimal(material["purchase_to_stock_factor"], "purchase_to_stock_factor")
        )
    raise InventoryValidationError("Receipt unit cannot be converted to the material stock unit")


def _receipt_issue_codes(material: dict, data: dict[str, object]) -> list[str]:
    issues: list[str] = []
    if bool(material["evidence_required"]) and not (
        data.get("expense_evidence_id") or data.get("document_reference")
    ):
        issues.append("missing_receipt_evidence")
    if bool(material["lot_tracked"]) and not data.get("supplier_lot"):
        issues.append("missing_supplier_lot")
    if bool(material["expiry_tracked"]) and not (
        data.get("expiry_date") or data.get("use_by_date")
    ):
        issues.append("missing_expiry_metadata")
    if data.get("unit_cost_amount") is None and data.get("total_cost_cents") is None:
        issues.append("missing_unit_cost")
    return issues


def _insert_exception(
    conn: DbConnection,
    *,
    exception_type: str,
    material_id: str,
    source_type: str,
    source_id: str,
    created_by_admin_id: str | None,
) -> str:
    exception_id = _uuid()
    severity = (
        "blocking"
        if exception_type in {"missing_unit_cost", "missing_receipt_evidence"}
        else "warning"
    )
    conn.execute(
        """
        INSERT INTO inventory_exceptions (
            id, exception_type, severity, target_type, target_id,
            source_type, source_id, message, created_by_admin_id
        ) VALUES (%s, %s, %s, 'material', %s, %s, %s, %s, %s)
        """,
        (
            exception_id,
            exception_type,
            severity,
            material_id,
            source_type,
            source_id,
            _RECEIPT_REVIEW_MESSAGES[exception_type],
            created_by_admin_id,
        ),
    )
    return exception_id


def create_material_receipt(
    material_id: str,
    request: MaterialReceiptRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
) -> MaterialReceiptResponse:
    """Record a material receipt, lot row, positive movement, and review exceptions."""
    data = request.model_dump()
    data["unit_cost_amount"] = _decimal_amount(data["unit_cost_amount"])
    with get_db() as conn:
        material = _get_material_row(conn, material_id)
        stock_quantity = _stock_quantity(material, data["quantity"], data["uom"])
        unit_cost_amount = data["unit_cost_amount"] or _unit_cost_from_total(
            data["total_cost_cents"], stock_quantity
        )
        receipt_id = _uuid()
        lot_id = _uuid()
        movement_id = _uuid()
        data["receipt_date"] = data["receipt_date"] or date.today().isoformat()
        data["unit_cost_amount"] = unit_cost_amount
        issues = _receipt_issue_codes(material, data)
        review_state = "needs_review" if issues else "reviewed"

        conn.execute(
            """
            INSERT INTO material_receipts (
                id, material_id, receipt_date, quantity, uom, stock_quantity,
                stock_uom, unit_cost_amount, total_cost_cents, currency,
                supplier_name, supplier_lot, expiry_date, use_by_date,
                expense_evidence_id, document_reference, review_state,
                created_by_admin_id, updated_by_admin_id, notes
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                receipt_id,
                material_id,
                data["receipt_date"],
                data["quantity"],
                data["uom"],
                stock_quantity,
                material["stock_uom"],
                unit_cost_amount,
                data["total_cost_cents"],
                data["currency"],
                data["supplier_name"],
                data["supplier_lot"],
                data["expiry_date"],
                data["use_by_date"],
                data["expense_evidence_id"],
                data["document_reference"],
                review_state,
                actor_user_id,
                actor_user_id,
                data["notes"],
            ),
        )
        conn.execute(
            """
            INSERT INTO material_lots (
                id, material_id, receipt_id, supplier_lot, expiry_date, use_by_date,
                received_quantity, stock_uom, remaining_quantity_snapshot,
                unit_cost_amount, currency, supplier_name, review_state
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                lot_id,
                material_id,
                receipt_id,
                data["supplier_lot"],
                data["expiry_date"],
                data["use_by_date"],
                stock_quantity,
                material["stock_uom"],
                stock_quantity,
                unit_cost_amount,
                data["currency"],
                data["supplier_name"],
                review_state,
            ),
        )
        conn.execute(
            """
            INSERT INTO inventory_movements (
                id, item_type, item_id, movement_type, quantity_delta, uom,
                source_type, source_id, material_lot_id, actor_user_id,
                actor_email, notes, review_state, occurred_at
            ) VALUES (
                %s, 'material', %s, 'receipt', %s, %s, 'material_receipt',
                %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                movement_id,
                material_id,
                stock_quantity,
                material["stock_uom"],
                receipt_id,
                lot_id,
                actor_user_id,
                actor_email,
                data["notes"],
                "reviewed" if review_state == "reviewed" else "unreviewed",
                now_utc(),
            ),
        )
        exception_ids = [
            _insert_exception(
                conn,
                exception_type=issue,
                material_id=material_id,
                source_type="material_receipt",
                source_id=receipt_id,
                created_by_admin_id=actor_user_id,
            )
            for issue in issues
        ]
        receipt = conn.execute(
            "SELECT * FROM material_receipts WHERE id = %s", (receipt_id,)
        ).fetchone()
        exceptions = []
        if exception_ids:
            placeholders = ",".join("%s" for _ in exception_ids)
            exceptions = [
                _exception_response_from_row(row)
                for row in conn.execute(
                    f"SELECT * FROM inventory_exceptions WHERE id IN ({placeholders})",  # noqa: S608
                    exception_ids,
                ).fetchall()
            ]

    return MaterialReceiptResponse(
        **_coerce_row_dates(receipt),
        movement_id=movement_id,
        lot_id=lot_id,
        exceptions=exceptions,
    )


def create_material_adjustment(
    material_id: str,
    request: MaterialAdjustmentRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
) -> InventoryMovementResponse:
    """Create an immutable manual material adjustment/write-off movement."""
    data = request.model_dump()
    with get_db() as conn:
        material = _get_material_row(conn, material_id)
        uom = data["uom"] or material["stock_uom"]
        if uom != material["stock_uom"]:
            raise InventoryValidationError("Manual material movements must use the stock unit")
        movement_id = _uuid()
        conn.execute(
            """
            INSERT INTO inventory_movements (
                id, item_type, item_id, movement_type, quantity_delta, uom,
                source_type, source_id, actor_user_id, actor_email, reason,
                notes, review_state, occurred_at
            ) VALUES (
                %s, 'material', %s, %s, %s, %s, 'manual_material_adjustment',
                %s, %s, %s, %s, %s, 'reviewed', %s
            )
            """,
            (
                movement_id,
                material_id,
                data["movement_type"],
                data["quantity_delta"],
                uom,
                movement_id,
                actor_user_id,
                actor_email,
                data["reason"],
                data["notes"],
                data["occurred_at"] or now_utc(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM inventory_movements WHERE id = %s", (movement_id,)
        ).fetchone()
    return _movement_response_from_row(row)


def list_material_lots(
    material_id: str,
    *,
    production_date: str | None = None,
    near_expiry_days: int = 30,
) -> MaterialLotListResponse:
    """List material lots with expired/near-expiry diagnostics."""
    parsed_date: date | None = None
    if production_date:
        try:
            parsed_date = date.fromisoformat(production_date[:10])
        except ValueError as exc:
            raise InventoryValidationError("production_date must be an ISO date") from exc
    with get_db() as conn:
        _get_material_row(conn, material_id)
        rows = conn.execute(
            """
            SELECT * FROM material_lots
            WHERE material_id = %s
            ORDER BY COALESCE(expiry_date, use_by_date, '9999-12-31'), created_at DESC
            """,
            (material_id,),
        ).fetchall()
    lots = [
        _lot_response_from_row(row, production_date=parsed_date, near_expiry_days=near_expiry_days)
        for row in rows
    ]
    return MaterialLotListResponse(lots=lots, total=len(lots))


def list_material_movements(
    material_id: str, *, limit: int = 100
) -> list[InventoryMovementResponse]:
    """List movement rows for one material."""
    with get_db() as conn:
        _get_material_row(conn, material_id)
        rows = conn.execute(
            """
            SELECT * FROM inventory_movements
            WHERE item_type = 'material' AND item_id = %s
            ORDER BY occurred_at DESC, created_at DESC
            LIMIT %s
            """,
            (material_id, limit),
        ).fetchall()
    return [_movement_response_from_row(row) for row in rows]


def list_inventory_movements(
    *,
    item_type: str | None = None,
    item_id: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    order_id: str | None = None,
    movement_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[InventoryMovementResponse], int]:
    """List immutable movement rows for admin traceability views."""
    where: list[str] = []
    params: list[object] = []
    if item_type:
        where.append("item_type = %s")
        params.append(item_type)
    if item_id:
        where.append("item_id = %s")
        params.append(item_id)
    if source_type:
        where.append("source_type = %s")
        params.append(source_type)
    if source_id:
        where.append("source_id = %s")
        params.append(source_id)
    if order_id:
        where.append("order_id = %s")
        params.append(order_id)
    if movement_type:
        where.append("movement_type = %s")
        params.append(movement_type)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM inventory_movements
            {where_sql}
            ORDER BY occurred_at DESC, created_at DESC
            LIMIT %s OFFSET %s
            """,  # noqa: S608
            (*params, limit, offset),
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM inventory_movements {where_sql}",  # noqa: S608
            params,
        ).fetchone()["n"]
    return [_movement_response_from_row(row) for row in rows], int(total)


def _product_exists(conn: DbConnection, product_id: str) -> bool:
    return (
        conn.execute("SELECT 1 FROM products WHERE id = %s", (product_id,)).fetchone() is not None
    )


def _get_recipe_row(conn: DbConnection, recipe_id: str) -> dict:
    row = conn.execute("SELECT * FROM recipe_versions WHERE id = %s", (recipe_id,)).fetchone()
    if row is None:
        raise RecipeNotFoundError(f"Recipe not found: {recipe_id}")
    return row


def _component_stock_quantity(material: dict, quantity: float | Decimal, uom: str) -> Decimal:
    qty = _decimal(quantity, "component quantity")
    if uom == material["stock_uom"]:
        return qty
    if uom == material["purchase_uom"] and material["purchase_to_stock_factor"]:
        return qty * _decimal(material["purchase_to_stock_factor"], "purchase_to_stock_factor")
    raise InventoryValidationError("Recipe component unit cannot convert to material stock unit")


def _validate_recipe_component(conn: DbConnection, component: RecipeComponentRequest) -> None:
    material = _get_material_row(conn, component.material_id)
    if not bool(material["active"]):
        raise InventoryValidationError("Inactive materials cannot be added to a new recipe")
    _component_stock_quantity(material, component.quantity, component.uom)


def _component_response_from_row(row: dict) -> RecipeComponentResponse:
    return RecipeComponentResponse(
        id=row["id"],
        recipe_version_id=row["recipe_version_id"],
        material_id=row["material_id"],
        material_name=row["material_name"],
        material_active=None if row["material_active"] is None else bool(row["material_active"]),
        material_category=row["material_category"],
        quantity=float(row["quantity"]),
        uom=row["uom"],
        quantity_basis=row["quantity_basis"],
        wastage_percent=float(row["wastage_percent"]),
        required=bool(row["required"]),
        substitute_group=row["substitute_group"],
        sort_order=row["sort_order"],
        review_state=row["review_state"],
        created_at=_s(row["created_at"]),
        updated_at=_s(row["updated_at"]),
    )


def _snapshot_response_from_row(row: dict | None) -> RecipeCostSnapshotResponse | None:
    if row is None:
        return None
    return RecipeCostSnapshotResponse(
        id=row["id"],
        recipe_version_id=row["recipe_version_id"],
        currency=row["currency"],
        material_cost_cents=row["material_cost_cents"],
        packaging_cost_cents=row["packaging_cost_cents"],
        labor_cost_cents=row["labor_cost_cents"],
        overhead_cost_cents=row["overhead_cost_cents"],
        batch_cost_cents=row["batch_cost_cents"],
        expected_unit_cost_cents=row["expected_unit_cost_cents"],
        source_cost_references_json=row["source_cost_references_json"],
        missing_cost_count=row["missing_cost_count"],
        estimate_label=row["estimate_label"],
        review_state=row["review_state"],
        calculated_at=_s(row["calculated_at"]),
        created_by_admin_id=row["created_by_admin_id"],
        created_at=_s(row["created_at"]),
    )


def _recipe_components(conn: DbConnection, recipe_id: str) -> list[RecipeComponentResponse]:
    rows = conn.execute(
        """
        SELECT rc.*, m.name AS material_name, m.active AS material_active,
               m.category AS material_category
        FROM recipe_components rc
        LEFT JOIN materials m ON m.id = rc.material_id
        WHERE rc.recipe_version_id = %s
        ORDER BY rc.sort_order, rc.created_at, rc.id
        """,
        (recipe_id,),
    ).fetchall()
    return [_component_response_from_row(row) for row in rows]


def _recipe_diagnostics_for_row(
    conn: DbConnection,
    row: dict,
) -> list[RecipeDiagnosticResponse]:
    diagnostics: list[RecipeDiagnosticResponse] = []
    component_rows = conn.execute(
        """
        SELECT rc.*, m.id AS material_exists, m.active AS material_active,
               m.name AS material_name, m.stock_uom, m.purchase_uom,
               m.purchase_to_stock_factor
        FROM recipe_components rc
        LEFT JOIN materials m ON m.id = rc.material_id
        WHERE rc.recipe_version_id = %s
        ORDER BY rc.sort_order, rc.id
        """,
        (row["id"],),
    ).fetchall()
    if not component_rows:
        diagnostics.append(
            RecipeDiagnosticResponse(
                code="no_components",
                severity="blocking",
                message="Recipe has no component lines.",
                target_type="recipe",
                target_id=row["id"],
            )
        )
    for component in component_rows:
        if component["material_exists"] is None:
            diagnostics.append(
                RecipeDiagnosticResponse(
                    code="missing_material",
                    severity="blocking",
                    message="Recipe component references a missing material.",
                    target_type="recipe_component",
                    target_id=component["id"],
                )
            )
            continue
        if not bool(component["material_active"]):
            diagnostics.append(
                RecipeDiagnosticResponse(
                    code="inactive_material",
                    severity="warning",
                    message=f"Material '{component['material_name']}' is inactive.",
                    target_type="material",
                    target_id=component["material_id"],
                )
            )
        try:
            _component_stock_quantity(component, component["quantity"], component["uom"])
        except InventoryValidationError:
            diagnostics.append(
                RecipeDiagnosticResponse(
                    code="invalid_component_unit",
                    severity="blocking",
                    message="Recipe component unit cannot convert to the material stock unit.",
                    target_type="recipe_component",
                    target_id=component["id"],
                )
            )
        if float(component["wastage_percent"] or 0) > 25:
            diagnostics.append(
                RecipeDiagnosticResponse(
                    code="excessive_wastage",
                    severity="warning",
                    message="Component wastage is above the review threshold.",
                    target_type="recipe_component",
                    target_id=component["id"],
                )
            )
        latest_cost = conn.execute(
            """
            SELECT 1 FROM material_receipts
            WHERE material_id = %s
              AND review_state = 'reviewed'
              AND unit_cost_amount IS NOT NULL
            ORDER BY receipt_date DESC, created_at DESC
            LIMIT 1
            """,
            (component["material_id"],),
        ).fetchone()
        if latest_cost is None:
            diagnostics.append(
                RecipeDiagnosticResponse(
                    code="missing_material_cost",
                    severity="blocking",
                    message=f"Material '{component['material_name']}' has no reviewed unit cost.",
                    target_type="material",
                    target_id=component["material_id"],
                )
            )
    return diagnostics


def _recipe_response_from_row(conn: DbConnection, row: dict) -> RecipeVersionResponse:
    latest_snapshot = conn.execute(
        """
        SELECT * FROM recipe_cost_snapshots
        WHERE recipe_version_id = %s
        ORDER BY calculated_at DESC, created_at DESC
        LIMIT 1
        """,
        (row["id"],),
    ).fetchone()
    return RecipeVersionResponse(
        id=row["id"],
        product_id=row["product_id"],
        version_label=row["version_label"],
        status=row["status"],
        effective_date=_s(row["effective_date"]),
        output_quantity=float(row["output_quantity"]),
        output_uom=row["output_uom"],
        review_state=row["review_state"],
        accountant_reviewed=bool(row["accountant_reviewed"]),
        reviewed_by_admin_id=row["reviewed_by_admin_id"],
        reviewed_at=_s(row["reviewed_at"]),
        notes=row["notes"],
        created_by_admin_id=row["created_by_admin_id"],
        updated_by_admin_id=row["updated_by_admin_id"],
        components=_recipe_components(conn, row["id"]),
        latest_cost_snapshot=_snapshot_response_from_row(latest_snapshot),
        diagnostics=_recipe_diagnostics_for_row(conn, row),
        created_at=_s(row["created_at"]),
        updated_at=_s(row["updated_at"]),
    )


def _replace_recipe_components(
    conn: DbConnection,
    recipe_id: str,
    components: list[RecipeComponentRequest],
) -> None:
    conn.execute("DELETE FROM recipe_components WHERE recipe_version_id = %s", (recipe_id,))
    for index, component in enumerate(components):
        _validate_recipe_component(conn, component)
        conn.execute(
            """
            INSERT INTO recipe_components (
                id, recipe_version_id, material_id, quantity, uom,
                quantity_basis, wastage_percent, required, substitute_group,
                sort_order, review_state
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'valid')
            """,
            (
                _uuid(),
                recipe_id,
                component.material_id,
                component.quantity,
                component.uom,
                component.quantity_basis,
                component.wastage_percent,
                1 if component.required else 0,
                component.substitute_group,
                component.sort_order if component.sort_order is not None else index,
            ),
        )


def create_recipe_version(
    request: RecipeVersionCreateRequest,
    *,
    actor_user_id: str | None = None,
) -> RecipeVersionResponse:
    """Create a draft recipe/BOM version and optional component lines."""
    recipe_id = _uuid()
    with get_db() as conn:
        if not _product_exists(conn, request.product_id):
            raise InventoryValidationError("Product does not exist")
        try:
            conn.execute(
                """
                INSERT INTO recipe_versions (
                    id, product_id, version_label, status, effective_date,
                    output_quantity, output_uom, notes, created_by_admin_id,
                    updated_by_admin_id
                ) VALUES (%s, %s, %s, 'draft', %s, %s, %s, %s, %s, %s)
                """,
                (
                    recipe_id,
                    request.product_id,
                    request.version_label,
                    request.effective_date,
                    request.output_quantity,
                    request.output_uom,
                    request.notes,
                    actor_user_id,
                    actor_user_id,
                ),
            )
            _replace_recipe_components(conn, recipe_id, request.components)
        except IntegrityError as exc:
            raise InventoryValidationError(
                "Recipe version label must be unique per product"
            ) from exc
        return _recipe_response_from_row(conn, _get_recipe_row(conn, recipe_id))


def update_recipe_version(
    recipe_id: str,
    request: RecipeVersionUpdateRequest,
    *,
    actor_user_id: str | None = None,
) -> RecipeVersionResponse:
    """Update a recipe/BOM version. Component edits are limited to drafts."""
    updates = request.model_dump(exclude_unset=True)
    components = updates.pop("components", None)
    with get_db() as conn:
        row = _get_recipe_row(conn, recipe_id)
        if components is not None and row["status"] != "draft":
            raise InventoryValidationError("Only draft recipes can replace component lines")
        if actor_user_id is not None:
            updates["updated_by_admin_id"] = actor_user_id
        if updates:
            set_clause = ", ".join(f"{key} = %s" for key in updates)
            try:
                conn.execute(
                    f"UPDATE recipe_versions SET {set_clause} WHERE id = %s",  # noqa: S608
                    (*updates.values(), recipe_id),
                )
            except IntegrityError as exc:
                raise InventoryValidationError(
                    "Recipe version label must be unique per product"
                ) from exc
        if components is not None:
            _replace_recipe_components(conn, recipe_id, components)
        return _recipe_response_from_row(conn, _get_recipe_row(conn, recipe_id))


def list_recipe_versions(
    *,
    product_id: str | None = None,
    status: str | None = None,
) -> RecipeVersionListResponse:
    """List recipe/BOM versions."""
    where: list[str] = []
    params: list[object] = []
    if product_id:
        where.append("product_id = %s")
        params.append(product_id)
    if status:
        where.append("status = %s")
        params.append(status)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM recipe_versions {where_sql} ORDER BY product_id, effective_date DESC",  # noqa: S608
            params,
        ).fetchall()
        recipes = [_recipe_response_from_row(conn, row) for row in rows]
    return RecipeVersionListResponse(recipes=recipes, total=len(recipes))


def get_recipe_version(recipe_id: str) -> RecipeVersionResponse:
    """Return one recipe/BOM version."""
    with get_db() as conn:
        return _recipe_response_from_row(conn, _get_recipe_row(conn, recipe_id))


def activate_recipe_version(
    recipe_id: str,
    *,
    actor_user_id: str | None = None,
) -> RecipeVersionResponse:
    """Activate one recipe and archive conflicting active versions for its product."""
    with get_db() as conn:
        row = _get_recipe_row(conn, recipe_id)
        component_count = conn.execute(
            "SELECT COUNT(*) AS n FROM recipe_components WHERE recipe_version_id = %s",
            (recipe_id,),
        ).fetchone()["n"]
        if component_count == 0:
            raise InventoryValidationError("Cannot activate a recipe without components")
        conn.execute(
            """
            UPDATE recipe_versions
            SET status = 'archived', updated_by_admin_id = COALESCE(%s, updated_by_admin_id)
            WHERE product_id = %s AND id != %s AND status = 'active'
            """,
            (actor_user_id, row["product_id"], recipe_id),
        )
        conn.execute(
            """
            UPDATE recipe_versions
            SET status = 'active', updated_by_admin_id = COALESCE(%s, updated_by_admin_id)
            WHERE id = %s
            """,
            (actor_user_id, recipe_id),
        )
        return _recipe_response_from_row(conn, _get_recipe_row(conn, recipe_id))


def archive_recipe_version(
    recipe_id: str,
    *,
    actor_user_id: str | None = None,
) -> RecipeVersionResponse:
    """Archive a recipe/BOM version."""
    with get_db() as conn:
        _get_recipe_row(conn, recipe_id)
        conn.execute(
            """
            UPDATE recipe_versions
            SET status = 'archived', updated_by_admin_id = COALESCE(%s, updated_by_admin_id)
            WHERE id = %s
            """,
            (actor_user_id, recipe_id),
        )
        return _recipe_response_from_row(conn, _get_recipe_row(conn, recipe_id))


def get_active_recipe_for_product(
    product_id: str,
    *,
    as_of_date: str | None = None,
) -> RecipeVersionResponse:
    """Return active recipe for a product/date using deterministic tie-breaking."""
    as_of = as_of_date or date.today().isoformat()
    with get_db() as conn:
        if not _product_exists(conn, product_id):
            raise InventoryValidationError("Product does not exist")
        row = conn.execute(
            """
            SELECT * FROM recipe_versions
            WHERE product_id = %s
              AND status = 'active'
              AND effective_date <= %s
            ORDER BY effective_date DESC, created_at DESC, id DESC
            LIMIT 1
            """,
            (product_id, as_of),
        ).fetchone()
        if row is None:
            raise RecipeNotFoundError(f"Active recipe not found for product: {product_id}")
        return _recipe_response_from_row(conn, row)


_PACKAGING_CATEGORIES = {"packaging", "label", "labels", "box", "jar", "container"}


def create_recipe_cost_snapshot(
    recipe_id: str,
    request: RecipeCostSnapshotRequest,
    *,
    actor_user_id: str | None = None,
) -> RecipeCostSnapshotResponse:
    """Calculate and store an expected recipe cost snapshot from current material costs."""
    with get_db() as conn:
        recipe = _get_recipe_row(conn, recipe_id)
        components = conn.execute(
            """
            SELECT rc.*, m.name AS material_name, m.category AS material_category,
                   m.stock_uom, m.purchase_uom, m.purchase_to_stock_factor
            FROM recipe_components rc
            JOIN materials m ON m.id = rc.material_id
            WHERE rc.recipe_version_id = %s
            ORDER BY rc.sort_order, rc.id
            """,
            (recipe_id,),
        ).fetchall()
        if not components:
            raise InventoryValidationError("Cannot cost a recipe without components")

        material_cost_cents = 0
        packaging_cost_cents = 0
        missing_cost_count = 0
        source_refs: list[dict[str, object]] = []
        output_quantity = _decimal(recipe["output_quantity"], "output_quantity")

        for component in components:
            latest_cost = conn.execute(
                """
                SELECT id, unit_cost_amount, currency
                FROM material_receipts
                WHERE material_id = %s
                  AND review_state = 'reviewed'
                  AND unit_cost_amount IS NOT NULL
                ORDER BY receipt_date DESC, created_at DESC
                LIMIT 1
                """,
                (component["material_id"],),
            ).fetchone()
            if latest_cost is None:
                missing_cost_count += 1
                continue
            base_quantity = _decimal(component["quantity"], "component quantity")
            if component["quantity_basis"] == "per_unit":
                base_quantity *= output_quantity
            wastage_multiplier = Decimal("1") + (
                _decimal(component["wastage_percent"], "wastage_percent") / Decimal("100")
            )
            component_quantity = base_quantity * wastage_multiplier
            stock_quantity = _component_stock_quantity(
                component,
                component_quantity,
                component["uom"],
            )
            unit_cost = _decimal(latest_cost["unit_cost_amount"], "unit_cost_amount")
            component_cost = int(
                (stock_quantity * unit_cost * Decimal("100")).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
            if (component["material_category"] or "").casefold() in _PACKAGING_CATEGORIES:
                packaging_cost_cents += component_cost
            else:
                material_cost_cents += component_cost
            source_refs.append(
                {
                    "material_id": component["material_id"],
                    "receipt_id": latest_cost["id"],
                    "unit_cost_amount": latest_cost["unit_cost_amount"],
                    "stock_quantity": str(stock_quantity),
                }
            )

        batch_cost_cents = (
            material_cost_cents
            + packaging_cost_cents
            + request.labor_cost_cents
            + request.overhead_cost_cents
        )
        expected_unit_cost_cents = int(
            (Decimal(batch_cost_cents) / output_quantity).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        review_state = "incomplete" if missing_cost_count else "estimate"
        if not missing_cost_count and recipe["review_state"] in {"reviewed", "accountant_reviewed"}:
            review_state = recipe["review_state"]
        snapshot_id = _uuid()
        conn.execute(
            """
            INSERT INTO recipe_cost_snapshots (
                id, recipe_version_id, currency, material_cost_cents,
                packaging_cost_cents, labor_cost_cents, overhead_cost_cents,
                batch_cost_cents, expected_unit_cost_cents,
                source_cost_references_json, missing_cost_count, review_state,
                created_by_admin_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                snapshot_id,
                recipe_id,
                request.currency,
                material_cost_cents,
                packaging_cost_cents,
                request.labor_cost_cents,
                request.overhead_cost_cents,
                batch_cost_cents,
                expected_unit_cost_cents,
                json.dumps(source_refs, separators=(",", ":"), sort_keys=True),
                missing_cost_count,
                review_state,
                actor_user_id,
            ),
        )
        row = conn.execute(
            "SELECT * FROM recipe_cost_snapshots WHERE id = %s", (snapshot_id,)
        ).fetchone()
    snapshot = _snapshot_response_from_row(row)
    assert snapshot is not None
    return snapshot


def review_recipe_version(
    recipe_id: str,
    request: RecipeReviewRequest,
    *,
    actor_user_id: str | None = None,
) -> RecipeVersionResponse:
    """Update recipe review state and accountant-reviewed metadata."""
    with get_db() as conn:
        _get_recipe_row(conn, recipe_id)
        conn.execute(
            """
            UPDATE recipe_versions
            SET review_state = %s, accountant_reviewed = %s, reviewed_by_admin_id = %s,
                reviewed_at = %s, notes = COALESCE(%s, notes),
                updated_by_admin_id = COALESCE(%s, updated_by_admin_id)
            WHERE id = %s
            """,
            (
                request.review_state,
                1 if request.review_state == "accountant_reviewed" else 0,
                actor_user_id,
                now_utc(),
                request.review_note,
                actor_user_id,
                recipe_id,
            ),
        )
        return _recipe_response_from_row(conn, _get_recipe_row(conn, recipe_id))


def recipe_diagnostics(recipe_id: str) -> RecipeDiagnosticsListResponse:
    """Return diagnostics for one recipe/BOM version."""
    with get_db() as conn:
        row = _get_recipe_row(conn, recipe_id)
        diagnostics = _recipe_diagnostics_for_row(conn, row)
    return RecipeDiagnosticsListResponse(diagnostics=diagnostics)


def product_recipe_diagnostics(product_id: str) -> RecipeDiagnosticsListResponse:
    """Return recipe diagnostics for a product, including missing active recipe."""
    diagnostics: list[RecipeDiagnosticResponse] = []
    with get_db() as conn:
        if not _product_exists(conn, product_id):
            raise InventoryValidationError("Product does not exist")
        row = conn.execute(
            """
            SELECT * FROM recipe_versions
            WHERE product_id = %s AND status = 'active'
            ORDER BY effective_date DESC, created_at DESC, id DESC
            LIMIT 1
            """,
            (product_id,),
        ).fetchone()
        if row is None:
            diagnostics.append(
                RecipeDiagnosticResponse(
                    code="missing_active_recipe",
                    severity="warning",
                    message="Product has no active recipe/BOM version.",
                    target_type="product",
                    target_id=product_id,
                )
            )
        else:
            diagnostics.extend(_recipe_diagnostics_for_row(conn, row))
    return RecipeDiagnosticsListResponse(diagnostics=diagnostics)


def _get_batch_row(conn: DbConnection, batch_id: str) -> dict:
    row = conn.execute("SELECT * FROM production_batches WHERE id = %s", (batch_id,)).fetchone()
    if row is None:
        raise ProductionBatchNotFoundError(f"Production batch not found: {batch_id}")
    return row


def _batch_consumption_response_from_row(row: dict) -> ProductionBatchConsumptionResponse:
    return ProductionBatchConsumptionResponse(
        id=row["id"],
        production_batch_id=row["production_batch_id"],
        recipe_component_id=row["recipe_component_id"],
        material_id=row["material_id"],
        material_name=row["material_name"],
        material_lot_id=row["material_lot_id"],
        expected_quantity=None
        if row["expected_quantity"] is None
        else float(row["expected_quantity"]),
        actual_quantity=None if row["actual_quantity"] is None else float(row["actual_quantity"]),
        waste_quantity=float(row["waste_quantity"]),
        uom=row["uom"],
        unit_cost_amount=row["unit_cost_amount"],
        currency=row["currency"],
        movement_id=row["movement_id"],
        review_state=row["review_state"],
        created_at=_s(row["created_at"]),
        updated_at=_s(row["updated_at"]),
    )


def _batch_output_response_from_row(row: dict) -> ProductionBatchOutputResponse:
    return ProductionBatchOutputResponse(
        id=row["id"],
        production_batch_id=row["production_batch_id"],
        product_id=row["product_id"],
        batch_number=row["batch_number"],
        quantity=float(row["quantity"]),
        uom=row["uom"],
        unit_cost_amount=row["unit_cost_amount"],
        currency=row["currency"],
        movement_id=row["movement_id"],
        remaining_quantity_snapshot=row["remaining_quantity_snapshot"],
        valuation_review_state=row["valuation_review_state"],
        created_at=_s(row["created_at"]),
    )


def _batch_response_from_row(conn: DbConnection, row: dict) -> ProductionBatchResponse:
    consumption = [
        _batch_consumption_response_from_row(item)
        for item in conn.execute(
            """
            SELECT pbc.*, m.name AS material_name
            FROM production_batch_consumption pbc
            LEFT JOIN materials m ON m.id = pbc.material_id
            WHERE pbc.production_batch_id = %s
            ORDER BY pbc.created_at, pbc.id
            """,
            (row["id"],),
        ).fetchall()
    ]
    outputs = [
        _batch_output_response_from_row(item)
        for item in conn.execute(
            "SELECT * FROM production_batch_outputs "
            "WHERE production_batch_id = %s ORDER BY created_at",
            (row["id"],),
        ).fetchall()
    ]
    exceptions = [
        _exception_response_from_row(item)
        for item in conn.execute(
            """
            SELECT * FROM inventory_exceptions
            WHERE source_type = 'production_batch' AND source_id = %s AND status = 'open'
            ORDER BY created_at DESC
            """,
            (row["id"],),
        ).fetchall()
    ]
    return ProductionBatchResponse(
        id=row["id"],
        batch_number=row["batch_number"],
        product_id=row["product_id"],
        recipe_version_id=row["recipe_version_id"],
        planned_output_quantity=float(row["planned_output_quantity"]),
        actual_output_quantity=None
        if row["actual_output_quantity"] is None
        else float(row["actual_output_quantity"]),
        output_uom=row["output_uom"],
        status=row["status"],
        production_date=_s(row["production_date"]),
        ready_date=_s(row["ready_date"]),
        cost_snapshot_id=row["cost_snapshot_id"],
        variance_review_state=row["variance_review_state"],
        actor_user_id=row["actor_user_id"],
        notes=row["notes"],
        consumption=consumption,
        outputs=outputs,
        exceptions=exceptions,
        created_by_admin_id=row["created_by_admin_id"],
        updated_by_admin_id=row["updated_by_admin_id"],
        created_at=_s(row["created_at"]),
        updated_at=_s(row["updated_at"]),
    )


def _material_on_hand(conn: DbConnection, material_id: str) -> float:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(quantity_delta), 0) AS quantity
        FROM inventory_movements
        WHERE item_type = 'material' AND item_id = %s
        """,
        (material_id,),
    ).fetchone()
    return float(row["quantity"] or 0)


def _latest_material_cost(conn: DbConnection, material_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT unit_cost_amount
        FROM material_receipts
        WHERE material_id = %s
          AND review_state = 'reviewed'
          AND unit_cost_amount IS NOT NULL
        ORDER BY receipt_date DESC, created_at DESC
        LIMIT 1
        """,
        (material_id,),
    ).fetchone()
    return row["unit_cost_amount"] if row else None


def _line_cost_cents(quantity: float, unit_cost_amount: str | None) -> int | None:
    if unit_cost_amount is None or quantity == 0:
        return None
    return int(
        (
            abs(_decimal(quantity, "quantity"))
            * _decimal(unit_cost_amount, "unit_cost_amount")
            * Decimal("100")
        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def _unit_value_from_total(total_cost_cents: int, quantity: float) -> str:
    if quantity <= 0:
        raise InventoryValidationError("output quantity must be positive")
    return str(
        (Decimal(total_cost_cents) / Decimal("100") / _decimal(quantity, "quantity")).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
    )


def _expected_consumption_rows(
    conn: DbConnection,
    recipe_id: str,
    planned_output_quantity: float,
) -> list[tuple[str, str, float, str]]:
    recipe = _get_recipe_row(conn, recipe_id)
    scale = _decimal(planned_output_quantity, "planned_output_quantity") / _decimal(
        recipe["output_quantity"], "output_quantity"
    )
    rows = conn.execute(
        """
        SELECT rc.*, m.stock_uom, m.purchase_uom, m.purchase_to_stock_factor
        FROM recipe_components rc
        JOIN materials m ON m.id = rc.material_id
        WHERE rc.recipe_version_id = %s
        ORDER BY rc.sort_order, rc.id
        """,
        (recipe_id,),
    ).fetchall()
    expected: list[tuple[str, str, float, str]] = []
    for row in rows:
        if row["quantity_basis"] == "per_unit":
            quantity = _decimal(row["quantity"], "component quantity") * _decimal(
                planned_output_quantity, "planned_output_quantity"
            )
        else:
            quantity = _decimal(row["quantity"], "component quantity") * scale
        quantity *= Decimal("1") + (
            _decimal(row["wastage_percent"], "wastage_percent") / Decimal("100")
        )
        stock_quantity = _component_stock_quantity(row, quantity, row["uom"])
        expected.append((row["id"], row["material_id"], float(stock_quantity), row["stock_uom"]))
    return expected


def _seed_batch_expected_consumption(
    conn: DbConnection,
    batch_id: str,
    recipe_id: str,
    planned_output_quantity: float,
) -> None:
    conn.execute(
        "DELETE FROM production_batch_consumption WHERE production_batch_id = %s", (batch_id,)
    )
    for component_id, material_id, expected_quantity, stock_uom in _expected_consumption_rows(
        conn, recipe_id, planned_output_quantity
    ):
        conn.execute(
            """
            INSERT INTO production_batch_consumption (
                id, production_batch_id, recipe_component_id, material_id,
                expected_quantity, waste_quantity, uom, review_state
            ) VALUES (%s, %s, %s, %s, %s, 0, %s, 'draft')
            """,
            (_uuid(), batch_id, component_id, material_id, expected_quantity, stock_uom),
        )


def create_production_batch(
    request: ProductionBatchCreateRequest,
    *,
    actor_user_id: str | None = None,
) -> ProductionBatchResponse:
    """Create a draft production batch and generate expected material consumption."""
    with get_db() as conn:
        if not _product_exists(conn, request.product_id):
            raise InventoryValidationError("Product does not exist")
        recipe_id = request.recipe_version_id
        if recipe_id is None:
            active_recipe = conn.execute(
                """
                SELECT * FROM recipe_versions
                WHERE product_id = %s
                  AND status = 'active'
                  AND effective_date <= %s
                ORDER BY effective_date DESC, created_at DESC, id DESC
                LIMIT 1
                """,
                (request.product_id, request.production_date),
            ).fetchone()
            if active_recipe is None:
                raise RecipeNotFoundError(
                    f"Active recipe not found for product: {request.product_id}"
                )
            recipe_id = active_recipe["id"]
        recipe = _get_recipe_row(conn, recipe_id)
        if recipe["product_id"] != request.product_id:
            raise InventoryValidationError("Recipe does not belong to the selected product")
        batch_id = _uuid()
        try:
            conn.execute(
                """
                INSERT INTO production_batches (
                    id, batch_number, product_id, recipe_version_id,
                    planned_output_quantity, output_uom, production_date,
                    ready_date, actor_user_id, notes, created_by_admin_id,
                    updated_by_admin_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    batch_id,
                    request.batch_number,
                    request.product_id,
                    recipe_id,
                    request.planned_output_quantity,
                    request.output_uom,
                    request.production_date,
                    request.ready_date,
                    actor_user_id,
                    request.notes,
                    actor_user_id,
                    actor_user_id,
                ),
            )
        except IntegrityError as exc:
            raise InventoryValidationError("Batch number must be unique") from exc
        _seed_batch_expected_consumption(
            conn,
            batch_id,
            recipe_id,
            request.planned_output_quantity,
        )
        return _batch_response_from_row(conn, _get_batch_row(conn, batch_id))


def update_production_batch(
    batch_id: str,
    request: ProductionBatchUpdateRequest,
    *,
    actor_user_id: str | None = None,
) -> ProductionBatchResponse:
    """Update a draft production batch."""
    updates = request.model_dump(exclude_unset=True)
    with get_db() as conn:
        batch = _get_batch_row(conn, batch_id)
        if batch["status"] != "draft":
            raise InventoryValidationError("Only draft batches can be edited")
        if actor_user_id is not None:
            updates["updated_by_admin_id"] = actor_user_id
        if updates:
            set_clause = ", ".join(f"{key} = %s" for key in updates)
            conn.execute(
                f"UPDATE production_batches SET {set_clause} WHERE id = %s",  # noqa: S608
                (*updates.values(), batch_id),
            )
        updated = _get_batch_row(conn, batch_id)
        if "planned_output_quantity" in updates and updated["recipe_version_id"]:
            _seed_batch_expected_consumption(
                conn,
                batch_id,
                updated["recipe_version_id"],
                updated["planned_output_quantity"],
            )
        return _batch_response_from_row(conn, _get_batch_row(conn, batch_id))


def list_production_batches(
    *,
    product_id: str | None = None,
    status: str | None = None,
) -> ProductionBatchListResponse:
    where: list[str] = []
    params: list[object] = []
    if product_id:
        where.append("product_id = %s")
        params.append(product_id)
    if status:
        where.append("status = %s")
        params.append(status)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM production_batches {where_sql} "  # noqa: S608
            "ORDER BY production_date DESC, created_at DESC",
            params,
        ).fetchall()
        batches = [_batch_response_from_row(conn, row) for row in rows]
    return ProductionBatchListResponse(batches=batches, total=len(batches))


def get_production_batch(batch_id: str) -> ProductionBatchResponse:
    with get_db() as conn:
        return _batch_response_from_row(conn, _get_batch_row(conn, batch_id))


def cancel_production_batch(
    batch_id: str, *, actor_user_id: str | None = None
) -> ProductionBatchResponse:
    with get_db() as conn:
        batch = _get_batch_row(conn, batch_id)
        if batch["status"] == "produced":
            raise InventoryValidationError("Produced batches require correction movements")
        conn.execute(
            """
            UPDATE production_batches
            SET status = 'cancelled', updated_by_admin_id = COALESCE(%s, updated_by_admin_id)
            WHERE id = %s
            """,
            (actor_user_id, batch_id),
        )
        return _batch_response_from_row(conn, _get_batch_row(conn, batch_id))


def _batch_exception(
    conn: DbConnection,
    *,
    batch_id: str,
    exception_type: str,
    message: str,
    severity: str = "warning",
    target_type: str = "production_batch",
    target_id: str | None = None,
    actor_user_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO inventory_exceptions (
            id, exception_type, severity, target_type, target_id,
            source_type, source_id, message, created_by_admin_id
        ) VALUES (%s, %s, %s, %s, %s, 'production_batch', %s, %s, %s)
        """,
        (
            _uuid(),
            exception_type,
            severity,
            target_type,
            target_id or batch_id,
            batch_id,
            message,
            actor_user_id,
        ),
    )


def post_production_batch(
    batch_id: str,
    request: ProductionBatchPostRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
) -> ProductionBatchResponse:
    """Post a draft batch as produced, creating material and finished-good movements."""
    with get_db() as conn:
        batch = _get_batch_row(conn, batch_id)
        if batch["status"] != "draft":
            raise InventoryValidationError("Only draft batches can be posted")
        consumption_rows = conn.execute(
            "SELECT * FROM production_batch_consumption WHERE production_batch_id = %s",
            (batch_id,),
        ).fetchall()
        actual_by_id = {
            item.batch_consumption_id: item
            for item in request.actual_consumption
            if item.batch_consumption_id
        }
        actual_by_material = {
            item.material_id: item
            for item in request.actual_consumption
            if not item.batch_consumption_id
        }
        planned_by_material: dict[str, float] = {}
        actual_lines: list[tuple[dict, float, float, str | None]] = []
        for row in consumption_rows:
            actual = actual_by_id.get(row["id"]) or actual_by_material.get(row["material_id"])
            actual_quantity = float(
                actual.actual_quantity if actual else row["expected_quantity"] or 0
            )
            waste_quantity = float(actual.waste_quantity if actual else 0)
            lot_id = actual.material_lot_id if actual else row["material_lot_id"]
            planned_by_material[row["material_id"]] = (
                planned_by_material.get(row["material_id"], 0) + actual_quantity
            )
            actual_lines.append((row, actual_quantity, waste_quantity, lot_id))

        insufficient_materials = False
        for material_id, required_quantity in planned_by_material.items():
            if required_quantity > _material_on_hand(conn, material_id):
                insufficient_materials = True
                _batch_exception(
                    conn,
                    batch_id=batch_id,
                    exception_type="insufficient_materials",
                    severity="blocking",
                    message="Batch requires more material than currently on hand.",
                    target_type="material",
                    target_id=material_id,
                    actor_user_id=actor_user_id,
                )
        if insufficient_materials:
            conn.execute(
                """
                UPDATE production_batches
                SET variance_review_state = 'warning',
                    updated_by_admin_id = COALESCE(%s, updated_by_admin_id)
                WHERE id = %s
                """,
                (actor_user_id, batch_id),
            )
            return _batch_response_from_row(conn, _get_batch_row(conn, batch_id))

        insufficient_lots = False
        for row, actual_quantity, _waste_quantity, lot_id in actual_lines:
            if not lot_id or actual_quantity == 0:
                continue
            lot = conn.execute("SELECT * FROM material_lots WHERE id = %s", (lot_id,)).fetchone()
            if lot is None:
                raise InventoryValidationError("Selected material lot does not exist")
            if lot["material_id"] != row["material_id"]:
                raise InventoryValidationError(
                    "Selected material lot does not belong to the consumed material"
                )
            remaining = lot["remaining_quantity_snapshot"]
            if remaining is not None and actual_quantity > float(remaining):
                insufficient_lots = True
                _batch_exception(
                    conn,
                    batch_id=batch_id,
                    exception_type="insufficient_material_lot_quantity",
                    severity="blocking",
                    message=(
                        "Batch requires more material from the selected lot than remains available."
                    ),
                    target_type="material_lot",
                    target_id=lot_id,
                    actor_user_id=actor_user_id,
                )
        if insufficient_lots:
            conn.execute(
                """
                UPDATE production_batches
                SET variance_review_state = 'warning',
                    updated_by_admin_id = COALESCE(%s, updated_by_admin_id)
                WHERE id = %s
                """,
                (actor_user_id, batch_id),
            )
            return _batch_response_from_row(conn, _get_batch_row(conn, batch_id))

        exception_created = False
        total_consumed_cost_cents = 0
        missing_consumed_cost = False
        for row, actual_quantity, waste_quantity, lot_id in actual_lines:
            expected_quantity = float(row["expected_quantity"] or 0)
            if expected_quantity and actual_quantity > expected_quantity * (
                1 + (request.variance_tolerance_percent / 100)
            ):
                exception_created = True
                _batch_exception(
                    conn,
                    batch_id=batch_id,
                    exception_type="material_usage_variance",
                    message="Actual material usage exceeds expected recipe quantity tolerance.",
                    target_type="material",
                    target_id=row["material_id"],
                    actor_user_id=actor_user_id,
                )
            if lot_id:
                lot = conn.execute(
                    "SELECT * FROM material_lots WHERE id = %s", (lot_id,)
                ).fetchone()
                expiry_text = lot["use_by_date"] or lot["expiry_date"] if lot else None
                if expiry_text and expiry_text[:10] < batch["production_date"][:10]:
                    exception_created = True
                    _batch_exception(
                        conn,
                        batch_id=batch_id,
                        exception_type="expired_material_use",
                        message="Batch consumed a material lot after its expiry/use-by date.",
                        target_type="material_lot",
                        target_id=lot_id,
                        actor_user_id=actor_user_id,
                    )
            unit_cost_amount = _latest_material_cost(conn, row["material_id"])
            if unit_cost_amount is None:
                exception_created = True
                if actual_quantity > 0:
                    missing_consumed_cost = True
                _batch_exception(
                    conn,
                    batch_id=batch_id,
                    exception_type="missing_material_cost",
                    severity="blocking",
                    message="Consumed material has no reviewed unit cost.",
                    target_type="material",
                    target_id=row["material_id"],
                    actor_user_id=actor_user_id,
                )
            line_cost = _line_cost_cents(actual_quantity, unit_cost_amount)
            if line_cost is not None:
                total_consumed_cost_cents += line_cost
            movement_id = None
            if actual_quantity != 0:
                movement_id = _uuid()
                conn.execute(
                    """
                    INSERT INTO inventory_movements (
                        id, item_type, item_id, movement_type, quantity_delta, uom,
                        source_type, source_id, material_lot_id, actor_user_id,
                        actor_email, review_state, occurred_at
                    ) VALUES (%s, 'material', %s, 'production_consumption', %s, %s,
                              'production_batch', %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        movement_id,
                        row["material_id"],
                        -actual_quantity,
                        row["uom"],
                        batch_id,
                        lot_id,
                        actor_user_id,
                        actor_email,
                        "unreviewed" if exception_created else "reviewed",
                        batch["production_date"],
                    ),
                )
                if lot_id:
                    conn.execute(
                        """
                        UPDATE material_lots
                        SET remaining_quantity_snapshot = GREATEST(
                            COALESCE(remaining_quantity_snapshot, received_quantity) - %s,
                            0
                        )
                        WHERE id = %s
                        """,
                        (actual_quantity, lot_id),
                    )
            conn.execute(
                """
                UPDATE production_batch_consumption
                SET actual_quantity = %s, waste_quantity = %s, material_lot_id = %s,
                    unit_cost_amount = %s, movement_id = %s, review_state = %s
                WHERE id = %s
                """,
                (
                    actual_quantity,
                    waste_quantity,
                    lot_id,
                    unit_cost_amount,
                    movement_id,
                    "needs_review" if exception_created else "reviewed",
                    row["id"],
                ),
            )

        if float(request.actual_output_quantity) != float(batch["planned_output_quantity"]):
            exception_created = True
            _batch_exception(
                conn,
                batch_id=batch_id,
                exception_type="produced_quantity_variance",
                message="Actual produced quantity differs from planned output.",
                actor_user_id=actor_user_id,
            )

        output_unit_cost_amount = None
        if not missing_consumed_cost and total_consumed_cost_cents > 0:
            output_unit_cost_amount = _unit_value_from_total(
                total_consumed_cost_cents,
                request.actual_output_quantity,
            )

        output_movement_id = _uuid()
        conn.execute(
            """
            INSERT INTO inventory_movements (
                id, item_type, item_id, movement_type, quantity_delta, uom,
                source_type, source_id, product_id, actor_user_id, actor_email,
                review_state, occurred_at
            ) VALUES (%s, 'finished_good', %s, 'production_output', %s, %s,
                      'production_batch', %s, %s, %s, %s, %s, %s)
            """,
            (
                output_movement_id,
                batch["product_id"],
                request.actual_output_quantity,
                batch["output_uom"],
                batch_id,
                batch["product_id"],
                actor_user_id,
                actor_email,
                "estimate" if exception_created else "reviewed",
                batch["production_date"],
            ),
        )
        conn.execute(
            """
            INSERT INTO production_batch_outputs (
                id, production_batch_id, product_id, batch_number, quantity,
                uom, unit_cost_amount, movement_id, remaining_quantity_snapshot,
                valuation_review_state
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                _uuid(),
                batch_id,
                batch["product_id"],
                batch["batch_number"],
                request.actual_output_quantity,
                batch["output_uom"],
                output_unit_cost_amount,
                output_movement_id,
                request.actual_output_quantity,
                "estimate" if exception_created else "reviewed",
            ),
        )
        conn.execute(
            "UPDATE products SET stock = stock + %s WHERE id = %s",
            (request.actual_output_quantity, batch["product_id"]),
        )
        conn.execute(
            """
            UPDATE production_batches
            SET status = 'produced', actual_output_quantity = %s,
                variance_review_state = %s, actor_user_id = COALESCE(%s, actor_user_id),
                notes = COALESCE(%s, notes), updated_by_admin_id = COALESCE(%s, updated_by_admin_id)
            WHERE id = %s
            """,
            (
                request.actual_output_quantity,
                "warning" if exception_created else "reviewed",
                actor_user_id,
                request.notes,
                actor_user_id,
                batch_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO product_inventory_profiles (
                product_id, inventory_mode, stock_source, latest_batch_id,
                valuation_readiness, updated_by_admin_id
            ) VALUES (%s, 'legacy', 'mixed', %s, 'estimate_only', %s)
            ON CONFLICT (product_id) DO NOTHING
            """,
            (batch["product_id"], batch_id, actor_user_id),
        )
        conn.execute(
            """
            UPDATE product_inventory_profiles
            SET latest_batch_id = %s, stock_source = 'mixed',
                valuation_readiness = CASE
                    WHEN valuation_readiness = 'ready' THEN valuation_readiness
                    ELSE 'estimate_only'
                END,
                updated_by_admin_id = COALESCE(%s, updated_by_admin_id)
            WHERE product_id = %s
            """,
            (batch_id, actor_user_id, batch["product_id"]),
        )
        return _batch_response_from_row(conn, _get_batch_row(conn, batch_id))


def correct_production_batch(
    batch_id: str,
    request: ProductionBatchCorrectionRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
) -> InventoryMovementResponse:
    """Correct a produced batch through a new movement, never by editing posted rows."""
    with get_db() as conn:
        batch = _get_batch_row(conn, batch_id)
        if batch["status"] != "produced":
            raise InventoryValidationError("Only produced batches can be corrected")
        movement_id = _uuid()
        product_id = batch["product_id"] if request.item_type == "finished_good" else None
        conn.execute(
            """
            INSERT INTO inventory_movements (
                id, item_type, item_id, movement_type, quantity_delta, uom,
                source_type, source_id, product_id, actor_user_id, actor_email,
                reason, notes, review_state, occurred_at
            ) VALUES (
                %s, %s, %s, 'adjustment', %s, %s, 'production_batch_correction',
                %s, %s, %s, %s, %s, %s, 'reviewed', %s
            )
            """,
            (
                movement_id,
                request.item_type,
                request.item_id,
                request.quantity_delta,
                request.uom,
                batch_id,
                product_id,
                actor_user_id,
                actor_email,
                request.reason,
                request.notes,
                now_utc(),
            ),
        )
        if request.item_type == "finished_good":
            conn.execute(
                "UPDATE products SET stock = GREATEST(stock + %s, 0) WHERE id = %s",
                (request.quantity_delta, request.item_id),
            )
        row = conn.execute(
            "SELECT * FROM inventory_movements WHERE id = %s", (movement_id,)
        ).fetchone()
    return _movement_response_from_row(row)


def production_traceability(batch_id: str) -> ProductionTraceabilityResponse:
    """Return source material and finished-good movement traceability for a batch."""
    with get_db() as conn:
        batch = _batch_response_from_row(conn, _get_batch_row(conn, batch_id))
        source_movements = [
            _movement_response_from_row(row)
            for row in conn.execute(
                """
                SELECT * FROM inventory_movements
                WHERE source_type = 'production_batch'
                  AND source_id = %s
                  AND item_type = 'material'
                ORDER BY occurred_at, created_at
                """,
                (batch_id,),
            ).fetchall()
        ]
        finished_movements = [
            _movement_response_from_row(row)
            for row in conn.execute(
                """
                SELECT * FROM inventory_movements
                WHERE source_type = 'production_batch'
                  AND source_id = %s
                  AND item_type = 'finished_good'
                ORDER BY occurred_at, created_at
                """,
                (batch_id,),
            ).fetchall()
        ]
    return ProductionTraceabilityResponse(
        **batch.model_dump(),
        source_movements=source_movements,
        finished_movements=finished_movements,
        linked_order_lines=[],
    )


def _json_dumps(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _json_loads(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _settings_response_from_row(row: dict) -> InventoryValuationSettingsResponse:
    return InventoryValuationSettingsResponse(
        id=row["id"],
        ledger_mode=row["ledger_mode"],
        valuation_enabled=bool(row["valuation_enabled"]),
        valuation_method=row["valuation_method"],
        effective_date=_s(row["effective_date"]),
        cogs_date_basis=row["cogs_date_basis"],
        rounding_policy=row["rounding_policy"],
        missing_cost_behavior=row["missing_cost_behavior"],
        included_cost_components=_json_loads(row["included_cost_components_json"]),
        write_off_mapping=_json_loads(row["write_off_mapping_json"]),
        currency=row["currency"],
        settings_version=row["settings_version"],
        accountant_reviewed=bool(row["accountant_reviewed"]),
        reviewed_by_admin_id=row["reviewed_by_admin_id"],
        reviewed_by_name=row["reviewed_by_name"],
        reviewed_at=_s(row["reviewed_at"]),
        review_notes=row["review_notes"],
        created_at=_s(row["created_at"]),
        updated_at=_s(row["updated_at"]),
    )


def _ensure_inventory_settings(conn: DbConnection) -> dict:
    conn.execute(
        "INSERT INTO inventory_settings (id) VALUES ('default') ON CONFLICT (id) DO NOTHING"
    )
    return conn.execute("SELECT * FROM inventory_settings WHERE id = 'default'").fetchone()


def get_inventory_valuation_settings() -> InventoryValuationSettingsResponse:
    with get_db() as conn:
        return _settings_response_from_row(_ensure_inventory_settings(conn))


def update_inventory_valuation_settings(
    request: InventoryValuationSettingsRequest,
    *,
    actor_user_id: str | None = None,
) -> InventoryValuationSettingsResponse:
    with get_db() as conn:
        _ensure_inventory_settings(conn)
        if request.valuation_method == "fifo" and request.accountant_reviewed:
            # FIFO can be selected, but official use still requires lot discipline warnings.
            _ensure_inventory_exception(
                conn,
                exception_type="fifo_requires_lot_discipline",
                message=(
                    "FIFO valuation requires reviewed lot-layer discipline before official output."
                ),
                severity="warning",
                target_type="inventory_settings",
                target_id="default",
            )
        conn.execute(
            """
            UPDATE inventory_settings
            SET ledger_mode = %s, valuation_enabled = %s, valuation_method = %s,
                effective_date = %s, cogs_date_basis = %s, rounding_policy = %s,
                missing_cost_behavior = %s, included_cost_components_json = %s,
                write_off_mapping_json = %s, currency = %s,
                settings_version = settings_version + 1,
                accountant_reviewed = %s, reviewed_by_admin_id = %s,
                reviewed_by_name = %s, reviewed_at = CASE WHEN %s = 1 THEN %s ELSE reviewed_at END,
                review_notes = %s
            WHERE id = 'default'
            """,
            (
                request.ledger_mode,
                1 if request.valuation_enabled else 0,
                request.valuation_method,
                request.effective_date,
                request.cogs_date_basis,
                request.rounding_policy,
                request.missing_cost_behavior,
                _json_dumps(request.included_cost_components),
                _json_dumps(request.write_off_mapping),
                request.currency,
                1 if request.accountant_reviewed else 0,
                actor_user_id,
                request.reviewed_by_name,
                1 if request.accountant_reviewed else 0,
                now_utc(),
                request.review_notes,
            ),
        )
        return _settings_response_from_row(_ensure_inventory_settings(conn))


def _layer_response_from_row(row: dict) -> ValuationLayerResponse:
    return ValuationLayerResponse(
        id=row["id"],
        movement_id=row["movement_id"],
        item_type=row["item_type"],
        item_id=row["item_id"],
        quantity=float(row["quantity"]),
        unit_value_amount=row["unit_value_amount"],
        total_value_cents=row["total_value_cents"],
        currency=row["currency"],
        valuation_method=row["valuation_method"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        valuation_date=_s(row["valuation_date"]),
        review_state=row["review_state"],
        method_metadata_json=row["method_metadata_json"],
        reversal_layer_id=row["reversal_layer_id"],
        created_at=_s(row["created_at"]),
    )


def _cogs_response_from_row(row: dict) -> COGSLedgerResponse:
    return COGSLedgerResponse(
        id=row["id"],
        order_id=row["order_id"],
        order_number=row["order_number"],
        order_item_key=row["order_item_key"],
        product_id=row["product_id"],
        quantity_sold=float(row["quantity_sold"]),
        cogs_date=_s(row["cogs_date"]),
        unit_cost_amount=row["unit_cost_amount"],
        total_cost_cents=row["total_cost_cents"],
        currency=row["currency"],
        valuation_method=row["valuation_method"],
        source_movement_id=row["source_movement_id"],
        source_valuation_layer_id=row["source_valuation_layer_id"],
        source_finished_batch_id=row["source_finished_batch_id"],
        review_state=row["review_state"],
        reversal_cogs_id=row["reversal_cogs_id"],
        created_at=_s(row["created_at"]),
    )


def _weighted_average_before(
    conn: DbConnection,
    *,
    item_type: str,
    item_id: str,
    valuation_date: str | None = None,
) -> Decimal | None:
    params: list[object] = [item_type, item_id]
    date_filter = ""
    if valuation_date:
        date_filter = "AND valuation_date <= %s"
        params.append(valuation_date)
    rows = conn.execute(
        f"""
        SELECT quantity, total_value_cents
        FROM inventory_valuation_layers
        WHERE item_type = %s AND item_id = %s {date_filter}
          AND review_state != 'reversed'
        ORDER BY valuation_date, created_at, id
        """,  # noqa: S608
        params,
    ).fetchall()
    quantity = Decimal("0")
    value_cents = Decimal("0")
    for row in rows:
        qty = _decimal(row["quantity"], "quantity")
        value = Decimal(row["total_value_cents"] or 0)
        quantity += qty
        value_cents = value_cents + value if qty >= 0 else value_cents - value
    if quantity <= 0:
        return None
    return (value_cents / Decimal("100")) / quantity


def _unit_value_from_layer(row: dict | None) -> str | None:
    if row is None:
        return None
    if row["unit_value_amount"]:
        return row["unit_value_amount"]
    if row["total_value_cents"] is None or not row["quantity"]:
        return None
    return str(
        (
            Decimal(row["total_value_cents"])
            / Decimal("100")
            / abs(_decimal(row["quantity"], "quantity"))
        ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    )


def _source_layer_for_positive_movement(
    conn: DbConnection,
    movement: dict,
) -> dict | None:
    if movement["reversal_of_movement_id"]:
        return _valuation_layer_for_movement(conn, movement["reversal_of_movement_id"])
    if movement["movement_type"] not in {"return_restock", "cancellation_reversal"}:
        return None
    if not movement["order_id"] or not movement["product_id"]:
        return None
    return conn.execute(
        """
        SELECT vl.*
        FROM inventory_movements sale
        JOIN inventory_valuation_layers vl ON vl.movement_id = sale.id
        WHERE sale.order_id = %s
          AND sale.product_id = %s
          AND sale.order_item_key = %s
          AND sale.movement_type = 'sale_issue'
          AND vl.review_state != 'reversed'
        ORDER BY vl.valuation_date DESC, vl.created_at DESC, vl.id DESC
        LIMIT 1
        """,
        (movement["order_id"], movement["product_id"], movement["order_item_key"]),
    ).fetchone()


def _ensure_inventory_exception(
    conn: DbConnection,
    *,
    exception_type: str,
    message: str,
    severity: str = "blocking",
    target_type: str | None = None,
    target_id: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
) -> None:
    existing = conn.execute(
        """
        SELECT 1 FROM inventory_exceptions
        WHERE status = 'open'
          AND exception_type = %s
          AND COALESCE(target_type, '') = COALESCE(%s, '')
          AND COALESCE(target_id, '') = COALESCE(%s, '')
          AND COALESCE(source_type, '') = COALESCE(%s, '')
          AND COALESCE(source_id, '') = COALESCE(%s, '')
        """,
        (exception_type, target_type, target_id, source_type, source_id),
    ).fetchone()
    if existing:
        return
    conn.execute(
        """
        INSERT INTO inventory_exceptions (
            id, exception_type, severity, target_type, target_id,
            source_type, source_id, message
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            _uuid(),
            exception_type,
            severity,
            target_type,
            target_id,
            source_type,
            source_id,
            message,
        ),
    )


def record_opening_balance(
    request: OpeningBalanceRequest,
    *,
    actor_user_id: str | None = None,
) -> ValuationLayerResponse | None:
    """Record a reviewed or draft opening balance movement and optional valuation layer."""
    unit_value = _decimal_amount(request.unit_value_amount)
    with get_db() as conn:
        settings = _ensure_inventory_settings(conn)
        movement_id = _uuid()
        review_state = "reviewed" if request.reviewed else "unreviewed"
        conn.execute(
            """
            INSERT INTO inventory_movements (
                id, item_type, item_id, movement_type, quantity_delta, uom,
                source_type, source_id, actor_user_id, notes, review_state
            ) VALUES (
                %s, %s, %s, 'opening_balance', %s, %s, 'opening_balance_review',
                %s, %s, %s, %s
            )
            """,
            (
                movement_id,
                request.item_type,
                request.item_id,
                request.quantity,
                request.uom,
                movement_id,
                actor_user_id,
                request.notes,
                review_state,
            ),
        )
        if request.item_type == "finished_good":
            conn.execute(
                """
                INSERT INTO product_inventory_profiles (
                    product_id, inventory_mode, stock_source, opening_balance_state,
                    valuation_readiness, updated_by_admin_id
                ) VALUES (%s, 'fallback', 'mixed', %s, 'estimate_only', %s)
                ON CONFLICT (product_id) DO NOTHING
                """,
                (request.item_id, "reviewed" if request.reviewed else "unreviewed", actor_user_id),
            )
            conn.execute(
                """
                UPDATE product_inventory_profiles
                SET opening_balance_state = %s,
                    updated_by_admin_id = COALESCE(%s, updated_by_admin_id)
                WHERE product_id = %s
                """,
                ("reviewed" if request.reviewed else "unreviewed", actor_user_id, request.item_id),
            )
        if not request.reviewed or request.quantity == 0:
            return None
        total_value = request.total_value_cents
        if total_value is None and unit_value is not None:
            total_value = int(
                (
                    _decimal(request.quantity, "quantity")
                    * _decimal(unit_value, "unit_value_amount")
                    * Decimal("100")
                ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
        if total_value is None:
            _ensure_inventory_exception(
                conn,
                exception_type="missing_opening_balance_value",
                message="Reviewed opening balance is missing value.",
                target_type=request.item_type,
                target_id=request.item_id,
                source_type="inventory_movement",
                source_id=movement_id,
            )
            return None
        if unit_value is None:
            unit_value = str(
                (
                    Decimal(total_value) / Decimal("100") / _decimal(request.quantity, "quantity")
                ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            )
        layer_id = _uuid()
        conn.execute(
            """
            INSERT INTO inventory_valuation_layers (
                id, movement_id, item_type, item_id, quantity, unit_value_amount,
                total_value_cents, currency, valuation_method, source_type,
                source_id, valuation_date, review_state
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, 'opening_balance_review',
                %s, CURRENT_DATE, %s
            )
            """,
            (
                layer_id,
                movement_id,
                request.item_type,
                request.item_id,
                request.quantity,
                unit_value,
                total_value,
                settings["currency"],
                settings["valuation_method"],
                movement_id,
                "official"
                if settings["valuation_enabled"] and settings["accountant_reviewed"]
                else "reviewed",
            ),
        )
        return _layer_response_from_row(
            conn.execute(
                "SELECT * FROM inventory_valuation_layers WHERE id = %s", (layer_id,)
            ).fetchone()
        )


def generate_valuation_layers() -> ValuationLayerListResponse:
    """Create weighted-average valuation layers for unvalued inventory movements."""
    created: list[ValuationLayerResponse] = []
    with get_db() as conn:
        settings = _ensure_inventory_settings(conn)
        official = bool(settings["valuation_enabled"] and settings["accountant_reviewed"])
        rows = conn.execute(
            """
            SELECT im.*
            FROM inventory_movements im
            LEFT JOIN inventory_valuation_layers vl ON vl.movement_id = im.id
            WHERE vl.id IS NULL
            ORDER BY im.occurred_at, im.created_at, im.id
            """
        ).fetchall()
        for movement in rows:
            quantity = float(movement["quantity_delta"])
            if quantity == 0:
                continue
            unit_value: str | None = None
            total_value_cents: int | None = None
            if movement["movement_type"] == "receipt":
                receipt = conn.execute(
                    "SELECT unit_cost_amount, total_cost_cents "
                    "FROM material_receipts WHERE id = %s",
                    (movement["source_id"],),
                ).fetchone()
                if receipt and receipt["unit_cost_amount"]:
                    unit_value = receipt["unit_cost_amount"]
                    total_value_cents = int(
                        (
                            abs(_decimal(quantity, "quantity"))
                            * _decimal(unit_value, "unit_value_amount")
                            * Decimal("100")
                        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                    )
                elif receipt and receipt["total_cost_cents"] is not None:
                    total_value_cents = receipt["total_cost_cents"]
            elif quantity > 0 and movement["movement_type"] == "production_output":
                output = conn.execute(
                    "SELECT unit_cost_amount FROM production_batch_outputs WHERE movement_id = %s",
                    (movement["id"],),
                ).fetchone()
                if output and output["unit_cost_amount"]:
                    unit_value = output["unit_cost_amount"]
            elif quantity > 0:
                source_layer = _source_layer_for_positive_movement(conn, movement)
                unit_value = _unit_value_from_layer(source_layer)
                if unit_value is None:
                    avg = _weighted_average_before(
                        conn,
                        item_type=movement["item_type"],
                        item_id=movement["item_id"],
                        valuation_date=movement["occurred_at"],
                    )
                    if avg is not None:
                        unit_value = str(avg.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
            elif quantity < 0:
                avg = _weighted_average_before(
                    conn,
                    item_type=movement["item_type"],
                    item_id=movement["item_id"],
                    valuation_date=movement["occurred_at"],
                )
                if avg is not None:
                    unit_value = str(avg.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
            if unit_value is None and total_value_cents is None:
                _ensure_inventory_exception(
                    conn,
                    exception_type="missing_source_cost",
                    message="Inventory movement is missing a source cost for valuation.",
                    target_type=movement["item_type"],
                    target_id=movement["item_id"],
                    source_type="inventory_movement",
                    source_id=movement["id"],
                )
                continue
            if total_value_cents is None and unit_value is not None:
                total_value_cents = int(
                    (
                        abs(_decimal(quantity, "quantity"))
                        * _decimal(unit_value, "unit_value_amount")
                        * Decimal("100")
                    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                )
            if unit_value is None and total_value_cents is not None:
                unit_value = str(
                    (
                        Decimal(total_value_cents)
                        / Decimal("100")
                        / abs(_decimal(quantity, "quantity"))
                    ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                )
            layer_id = _uuid()
            conn.execute(
                """
                INSERT INTO inventory_valuation_layers (
                    id, movement_id, item_type, item_id, quantity, unit_value_amount,
                    total_value_cents, currency, valuation_method, source_type,
                    source_id, valuation_date, review_state
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    layer_id,
                    movement["id"],
                    movement["item_type"],
                    movement["item_id"],
                    quantity,
                    unit_value,
                    total_value_cents,
                    settings["currency"],
                    settings["valuation_method"],
                    movement["source_type"],
                    movement["source_id"],
                    movement["occurred_at"],
                    "official" if official else "estimate",
                ),
            )
            created.append(
                _layer_response_from_row(
                    conn.execute(
                        "SELECT * FROM inventory_valuation_layers WHERE id = %s", (layer_id,)
                    ).fetchone()
                )
            )
    return ValuationLayerListResponse(layers=created, total=len(created))


def list_valuation_layers(
    item_type: str | None = None, item_id: str | None = None
) -> ValuationLayerListResponse:
    where: list[str] = []
    params: list[object] = []
    if item_type:
        where.append("item_type = %s")
        params.append(item_type)
    if item_id:
        where.append("item_id = %s")
        params.append(item_id)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM inventory_valuation_layers {where_sql} "  # noqa: S608
            "ORDER BY valuation_date, created_at",
            params,
        ).fetchall()
    layers = [_layer_response_from_row(row) for row in rows]
    return ValuationLayerListResponse(layers=layers, total=len(layers))


def _cogs_date_from_order(row: dict, basis: str) -> str:
    if basis == "payment_date" and row["paid_at"]:
        return _s(row["paid_at"])
    if basis == "shipment_date" and row["status"] in {
        "shipped",
        "delivered",
        "return_in_transit",
        "returned",
    }:
        return _s(row["updated_at"])
    if basis == "delivery_date" and row["status"] in {"delivered", "return_in_transit", "returned"}:
        return _s(row["updated_at"])
    if basis == "period_close":
        return _s(row["updated_at"]) or _s(row["created_at"])
    return _s(row["created_at"])


def _sale_movement_for_order_item(
    conn: DbConnection, *, order_id: str, product_id: str
) -> dict | None:
    return conn.execute(
        """
        SELECT *
        FROM inventory_movements
        WHERE order_id = %s
          AND product_id = %s
          AND order_item_key = %s
          AND movement_type = 'sale_issue'
        ORDER BY occurred_at DESC, created_at DESC, id DESC
        LIMIT 1
        """,
        (order_id, product_id, f"{order_id}:{product_id}"),
    ).fetchone()


def _valuation_layer_for_movement(conn: DbConnection, movement_id: str | None) -> dict | None:
    if movement_id is None:
        return None
    return conn.execute(
        """
        SELECT *
        FROM inventory_valuation_layers
        WHERE movement_id = %s
        ORDER BY valuation_date DESC, created_at DESC, id DESC
        LIMIT 1
        """,
        (movement_id,),
    ).fetchone()


def _latest_finished_batch_id(conn: DbConnection, product_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT latest_batch_id
        FROM product_inventory_profiles
        WHERE product_id = %s
        """,
        (product_id,),
    ).fetchone()
    return row["latest_batch_id"] if row and row["latest_batch_id"] else None


def generate_cogs_rows() -> COGSLedgerListResponse:
    """Generate COGS rows for order items that do not already have one."""
    created: list[COGSLedgerResponse] = []
    with get_db() as conn:
        settings = _ensure_inventory_settings(conn)
        official = bool(settings["valuation_enabled"] and settings["accountant_reviewed"])
        rows = conn.execute(
            """
            SELECT oi.order_id, oi.product_id, oi.quantity, o.order_number,
                   o.status, o.created_at, o.updated_at, o.paid_at
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            LEFT JOIN cogs_ledger c ON c.order_id = oi.order_id AND c.product_id = oi.product_id
            WHERE c.id IS NULL
            ORDER BY o.created_at, oi.order_id, oi.product_id
            """
        ).fetchall()
        for row in rows:
            source_movement = _sale_movement_for_order_item(
                conn, order_id=row["order_id"], product_id=row["product_id"]
            )
            source_layer = _valuation_layer_for_movement(
                conn, source_movement["id"] if source_movement else None
            )
            unit_value_text = _unit_value_from_layer(source_layer)
            if unit_value_text is None:
                avg = _weighted_average_before(
                    conn,
                    item_type="finished_good",
                    item_id=row["product_id"],
                    valuation_date=_s(row["created_at"]),
                )
                unit_value_text = (
                    None
                    if avg is None
                    else str(avg.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
                )
            if unit_value_text is None:
                _ensure_inventory_exception(
                    conn,
                    exception_type="missing_cogs_cost",
                    message="Order item has no finished-goods cost for COGS.",
                    target_type="product",
                    target_id=row["product_id"],
                    source_type="order",
                    source_id=row["order_id"],
                )
                continue
            unit_value = _decimal(unit_value_text, "unit_value_amount").quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_UP
            )
            total_cost = int(
                (_decimal(row["quantity"], "quantity") * unit_value * Decimal("100")).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
            cogs_date = _cogs_date_from_order(row, settings["cogs_date_basis"])
            cogs_id = _uuid()
            conn.execute(
                """
                INSERT INTO cogs_ledger (
                    id, order_id, order_number, order_item_key, product_id,
                    quantity_sold, cogs_date, unit_cost_amount, total_cost_cents,
                    currency, valuation_method, source_movement_id,
                    source_valuation_layer_id, source_finished_batch_id, review_state
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    cogs_id,
                    row["order_id"],
                    row["order_number"],
                    f"{row['order_id']}:{row['product_id']}",
                    row["product_id"],
                    row["quantity"],
                    cogs_date,
                    str(unit_value),
                    total_cost,
                    settings["currency"],
                    settings["valuation_method"],
                    source_movement["id"] if source_movement else None,
                    source_layer["id"] if source_layer else None,
                    _latest_finished_batch_id(conn, row["product_id"]),
                    "official" if official else "estimate",
                ),
            )
            created.append(
                _cogs_response_from_row(
                    conn.execute("SELECT * FROM cogs_ledger WHERE id = %s", (cogs_id,)).fetchone()
                )
            )

        return_rows = conn.execute(
            """
            SELECT im.id AS movement_id, im.order_id, im.product_id, im.quantity_delta,
                   im.occurred_at, c.id AS original_cogs_id, c.order_number,
                   c.order_item_key, c.unit_cost_amount, c.quantity_sold,
                   c.total_cost_cents, c.valuation_method
            FROM inventory_movements im
            JOIN cogs_ledger c
              ON c.order_id = im.order_id
             AND c.product_id = im.product_id
             AND c.review_state != 'reversed'
            LEFT JOIN cogs_ledger reversal
              ON reversal.reversal_cogs_id = c.id
             AND reversal.source_movement_id = im.id
            WHERE im.movement_type IN ('return_restock', 'cancellation_reversal')
              AND im.quantity_delta > 0
              AND COALESCE(im.metadata_json, '') NOT LIKE '%%write_off_pending%%'
              AND reversal.id IS NULL
            ORDER BY im.occurred_at, im.created_at, im.id
            """
        ).fetchall()
        for row in return_rows:
            unit_value = _decimal(row["unit_cost_amount"] or "0", "unit_cost_amount")
            if unit_value == 0 and float(row["quantity_sold"] or 0) > 0:
                unit_value = (
                    Decimal(row["total_cost_cents"])
                    / Decimal("100")
                    / _decimal(row["quantity_sold"], "quantity_sold")
                ).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            total_cost = int(
                (
                    _decimal(row["quantity_delta"], "quantity_delta") * unit_value * Decimal("100")
                ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
            source_layer = _valuation_layer_for_movement(conn, row["movement_id"])
            cogs_id = _uuid()
            conn.execute(
                """
                INSERT INTO cogs_ledger (
                    id, order_id, order_number, order_item_key, product_id,
                    quantity_sold, cogs_date, unit_cost_amount, total_cost_cents,
                    currency, valuation_method, source_movement_id,
                    source_valuation_layer_id, source_finished_batch_id,
                    review_state, reversal_cogs_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'reversed', %s)
                """,
                (
                    cogs_id,
                    row["order_id"],
                    row["order_number"],
                    row["order_item_key"],
                    row["product_id"],
                    row["quantity_delta"],
                    _s(row["occurred_at"]),
                    str(unit_value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
                    total_cost,
                    settings["currency"],
                    row["valuation_method"],
                    row["movement_id"],
                    source_layer["id"] if source_layer else None,
                    _latest_finished_batch_id(conn, row["product_id"]),
                    row["original_cogs_id"],
                ),
            )
            created.append(
                _cogs_response_from_row(
                    conn.execute("SELECT * FROM cogs_ledger WHERE id = %s", (cogs_id,)).fetchone()
                )
            )
    return COGSLedgerListResponse(rows=created, total=len(created))


def list_cogs_rows(
    product_id: str | None = None, order_id: str | None = None
) -> COGSLedgerListResponse:
    where: list[str] = []
    params: list[object] = []
    if product_id:
        where.append("product_id = %s")
        params.append(product_id)
    if order_id:
        where.append("order_id = %s")
        params.append(order_id)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM cogs_ledger {where_sql} ORDER BY cogs_date, created_at",  # noqa: S608
            params,
        ).fetchall()
    cogs = [_cogs_response_from_row(row) for row in rows]
    return COGSLedgerListResponse(rows=cogs, total=len(cogs))


def inventory_close_preview(period_start: str, period_end: str) -> InventoryClosePreviewResponse:
    with get_db() as conn:
        settings = _ensure_inventory_settings(conn)
        exception_count = conn.execute(
            "SELECT COUNT(*) AS n FROM inventory_exceptions WHERE status = 'open'"
        ).fetchone()["n"]
        rows = conn.execute(
            """
            SELECT im.movement_type, vl.quantity, vl.total_value_cents
            FROM inventory_valuation_layers vl
            LEFT JOIN inventory_movements im ON im.id = vl.movement_id
            WHERE vl.valuation_date BETWEEN %s AND %s
            """,
            (period_start, period_end),
        ).fetchall()
    totals = {
        "opening_value_cents": 0,
        "receipts_value_cents": 0,
        "production_consumption_value_cents": 0,
        "finished_output_value_cents": 0,
        "sales_cogs_value_cents": 0,
        "returns_value_cents": 0,
        "adjustments_value_cents": 0,
        "ending_value_cents": 0,
    }
    for row in rows:
        value = int(row["total_value_cents"] or 0)
        movement_type = row["movement_type"]
        if movement_type == "opening_balance":
            totals["opening_value_cents"] += value
        elif movement_type == "receipt":
            totals["receipts_value_cents"] += value
        elif movement_type == "production_consumption":
            totals["production_consumption_value_cents"] += value
        elif movement_type == "production_output":
            totals["finished_output_value_cents"] += value
        elif movement_type == "sale_issue":
            totals["sales_cogs_value_cents"] += value
        elif movement_type in {"return_restock", "return_write_off"}:
            totals["returns_value_cents"] += value
        elif movement_type in {"adjustment", "spoilage", "write_off", "stock_count_correction"}:
            totals["adjustments_value_cents"] += value
        if float(row["quantity"] or 0) >= 0:
            totals["ending_value_cents"] += value
        else:
            totals["ending_value_cents"] -= value
    official = bool(
        settings["valuation_enabled"] and settings["accountant_reviewed"] and exception_count == 0
    )
    return InventoryClosePreviewResponse(
        period_start=period_start,
        period_end=period_end,
        currency=settings["currency"],
        valuation_method=settings["valuation_method"],
        official=official,
        exception_count=exception_count,
        policy_snapshot={
            "settings_version": settings["settings_version"],
            "valuation_method": settings["valuation_method"],
            "cogs_date_basis": settings["cogs_date_basis"],
            "accountant_reviewed": bool(settings["accountant_reviewed"]),
        },
        **totals,
    )


def valuation_exceptions(
    target_type: str | None = None,
    target_id: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    order_id: str | None = None,
) -> list[dict[str, object]]:
    """Refresh and return valuation readiness exceptions."""
    with get_db() as conn:
        settings = _ensure_inventory_settings(conn)
        if not bool(settings["accountant_reviewed"]):
            _ensure_inventory_exception(
                conn,
                exception_type="unreviewed_inventory_settings",
                message="Inventory valuation settings are not accountant-reviewed.",
                target_type="inventory_settings",
                target_id="default",
            )
        for row in conn.execute(
            "SELECT product_id, opening_balance_state FROM product_inventory_profiles"
        ).fetchall():
            if row["opening_balance_state"] != "reviewed":
                _ensure_inventory_exception(
                    conn,
                    exception_type="unreviewed_opening_balance",
                    message="Product opening balance has not been reviewed.",
                    target_type="product",
                    target_id=row["product_id"],
                )
        for row in conn.execute(
            """
            SELECT item_type, item_id, SUM(quantity_delta) AS quantity
            FROM inventory_movements
            GROUP BY item_type, item_id
            HAVING SUM(quantity_delta) < 0
            """
        ).fetchall():
            _ensure_inventory_exception(
                conn,
                exception_type="negative_on_hand",
                message="Inventory ledger has negative on-hand quantity.",
                target_type=row["item_type"],
                target_id=row["item_id"],
            )
        for row in conn.execute(
            """
            SELECT p.id
            FROM products p
            LEFT JOIN recipe_versions rv ON rv.product_id = p.id AND rv.status = 'active'
            WHERE p.is_active = 1 AND rv.id IS NULL
            """
        ).fetchall():
            _ensure_inventory_exception(
                conn,
                exception_type="missing_active_recipe",
                message="Active product has no active recipe/BOM for valuation readiness.",
                severity="warning",
                target_type="product",
                target_id=row["id"],
            )
        where = ["status = 'open'"]
        params: list[object] = []
        if target_type:
            where.append("target_type = %s")
            params.append(target_type)
        if target_id:
            where.append("target_id = %s")
            params.append(target_id)
        if source_type:
            where.append("source_type = %s")
            params.append(source_type)
        if source_id:
            where.append("source_id = %s")
            params.append(source_id)
        if order_id:
            where.append("source_type = 'order'")
            where.append("source_id = %s")
            params.append(order_id)
        where_sql = " AND ".join(where)
        exceptions = [
            _exception_response_from_row(row)
            for row in conn.execute(
                f"SELECT * FROM inventory_exceptions WHERE {where_sql} ORDER BY created_at DESC",  # noqa: S608
                params,
            ).fetchall()
        ]
    return exceptions
