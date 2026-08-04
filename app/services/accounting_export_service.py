"""Accountant export package builder."""

from __future__ import annotations

import csv
import json
import sqlite3
import uuid
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path

from openpyxl import Workbook

from app.database import get_db
from app.models.accounting import (
    AccountantAcceptanceRequest,
    FinanceExportPackageListResponse,
    FinanceExportPackageResponse,
)
from app.services import accounting_config_service, accounting_ledger_service, pricing
from app.services.accounting_config_service import _fmt_ts
from app.services.finance_period_service import FinancePeriodError, calculate_summary_totals

_SCHEMA_VERSION = "accounting-finance-hub.v1"
_EXPORT_LEDGER_NAMES = [
    "sales",
    "payments",
    "stripe_payouts",
    "cod_settlements",
    "refunds",
    "courier_claims",
    "return_reasons",
    "inventory_adjustments",
    "inventory_movements",
    "documents",
    "expenses",
    "product_costs",
]


def _json_loads(value: str | None) -> dict[str, object] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _json_dumps(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=_fmt_ts)


def _package_from_row(row: sqlite3.Row) -> FinanceExportPackageResponse:
    return FinanceExportPackageResponse(
        id=row["id"],
        period_id=row["period_id"],
        version=row["version"],
        schema_version=row["schema_version"],
        xlsx_path=row["xlsx_path"],
        csv_dir_path=row["csv_dir_path"],
        manifest_path=row["manifest_path"],
        manifest=_json_loads(row["manifest_json"]),
        generated_by_admin_id=row["generated_by_admin_id"],
        generated_at=_fmt_ts(row["generated_at"]),
        accepted_by_admin_id=row["accepted_by_admin_id"],
        accepted_at=_fmt_ts(row["accepted_at"]),
        accountant_name=row["accountant_name"],
        accountant_reference=row["accountant_reference"],
        acceptance_note=row["acceptance_note"],
        current_final=bool(row["current_final"]),
    )


def _get_package_row(conn: sqlite3.Connection, export_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM finance_export_packages WHERE id = %s", (export_id,)
    ).fetchone()
    if row is None:
        raise FinancePeriodError(404, "EXPORT_PACKAGE_NOT_FOUND", "Export package not found.")
    return row


def _private_export_root() -> Path:
    db_parent = Path("./data/exports").resolve()
    db_parent.mkdir(parents=True, exist_ok=True)
    return db_parent / "private-exports" / "accounting"


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cell(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return _fmt_ts(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=_fmt_ts)


def _headers(rows: list[dict[str, object]]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen


def _sheet_totals(rows: list[dict[str, object]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in rows:
        for key, value in row.items():
            if key.endswith("_cents") and isinstance(value, int):
                totals[key] = totals.get(key, 0) + value
    return totals


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    headers = _headers(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([_cell(row.get(header)) for header in headers])


def _write_workbook(path: Path, sheets: dict[str, list[dict[str, object]]]) -> None:
    workbook = Workbook()
    default = workbook.active
    workbook.remove(default)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name[:31])
        headers = _headers(rows)
        sheet.append(headers)
        for row in rows:
            sheet.append([_cell(row.get(header)) for header in headers])
    workbook.save(path)


def _settings_rows() -> list[dict[str, object]]:
    config = accounting_config_service.get_accounting_configuration()
    payload = config.model_dump(mode="json")
    return [{"section": key, "payload_json": value} for key, value in payload.items()]


def _exception_rows(conn: sqlite3.Connection, period_id: str) -> list[dict[str, object]]:
    rows = conn.execute(
        "SELECT * FROM finance_exceptions WHERE period_id = %s "
        "ORDER BY status, severity, created_at",
        (period_id,),
    ).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]


def _summary_rows(conn: sqlite3.Connection, period: sqlite3.Row) -> list[dict[str, object]]:
    summary = _json_loads(period["summary_totals_json"]) or calculate_summary_totals(conn, period)
    return [{"metric": key, "value": value} for key, value in summary.items()]


def _source_metadata_rows(
    period: sqlite3.Row, export_id: str, version: int
) -> list[dict[str, object]]:
    return [
        {
            "export_id": export_id,
            "period_id": period["id"],
            "period_start": period["period_start"],
            "period_end": period["period_end"],
            "currency": period["currency"],
            "period_status": period["status"],
            "version": version,
            "schema_version": _SCHEMA_VERSION,
            "generated_at": pricing.now_utc(),
        }
    ]


def _inventory_settings(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM inventory_settings WHERE id = 'default'").fetchone()


def _inventory_label(settings: sqlite3.Row | None) -> str:
    if settings and settings["valuation_enabled"] and settings["accountant_reviewed"]:
        return "official"
    return "estimate_only"


def _material_on_hand_rows(
    conn: sqlite3.Connection, period: sqlite3.Row
) -> list[dict[str, object]]:
    settings = _inventory_settings(conn)
    rows = conn.execute(
        """
        SELECT m.id AS material_id, m.sku, m.name, m.category, m.stock_uom AS uom,
               m.active, m.evidence_required,
               COALESCE((
                   SELECT SUM(im.quantity_delta)
                   FROM inventory_movements im
                   WHERE im.item_type = 'material'
                     AND im.item_id = m.id
                     AND (im.occurred_at)::date <= %s
               ), 0) AS on_hand_quantity,
               COALESCE((
                   SELECT SUM(CASE WHEN vl.quantity >= 0
                                   THEN vl.total_value_cents ELSE -vl.total_value_cents END)
                   FROM inventory_valuation_layers vl
                   WHERE vl.item_type = 'material'
                     AND vl.item_id = m.id
                     AND (vl.valuation_date)::date <= %s
                     AND vl.review_state != 'reversed'
               ), 0) AS on_hand_value_cents,
               (SELECT COUNT(*) FROM inventory_exceptions ie
                WHERE ie.status = 'open' AND ie.target_type = 'material' AND ie.target_id = m.id)
                   AS open_exception_count
        FROM materials m
        ORDER BY m.category, m.name, m.id
        """,
        (period["period_end"], period["period_end"]),
    ).fetchall()
    label = _inventory_label(settings)
    return [
        {
            **{key: row[key] for key in row.keys()},
            "currency": period["currency"],
            "valuation_method": settings["valuation_method"] if settings else None,
            "export_label": label,
        }
        for row in rows
    ]


def _finished_goods_on_hand_rows(
    conn: sqlite3.Connection, period: sqlite3.Row
) -> list[dict[str, object]]:
    settings = _inventory_settings(conn)
    rows = conn.execute(
        """
        SELECT p.id AS product_id, p.name_en AS product_name,
               COALESCE(pip.inventory_mode, 'legacy') AS inventory_mode,
               COALESCE(pip.stock_source, 'product_stock') AS stock_source,
               p.stock AS display_stock,
               COALESCE((
                   SELECT SUM(im.quantity_delta)
                   FROM inventory_movements im
                   WHERE im.item_type = 'finished_good'
                     AND im.item_id = p.id
                     AND (im.occurred_at)::date <= %s
               ), 0) AS ledger_on_hand_quantity,
               COALESCE((
                   SELECT SUM(CASE WHEN vl.quantity >= 0
                                   THEN vl.total_value_cents ELSE -vl.total_value_cents END)
                   FROM inventory_valuation_layers vl
                   WHERE vl.item_type = 'finished_good'
                     AND vl.item_id = p.id
                     AND (vl.valuation_date)::date <= %s
                     AND vl.review_state != 'reversed'
               ), 0) AS on_hand_value_cents,
               pip.opening_balance_state, pip.valuation_readiness,
               (SELECT COUNT(*) FROM inventory_exceptions ie
                WHERE ie.status = 'open' AND ie.target_type = 'product' AND ie.target_id = p.id)
                   AS open_exception_count
        FROM products p
        LEFT JOIN product_inventory_profiles pip ON pip.product_id = p.id
        WHERE pip.product_id IS NOT NULL
           OR EXISTS (
               SELECT 1 FROM inventory_movements im
               WHERE im.item_type = 'finished_good' AND im.item_id = p.id
           )
        ORDER BY p.name_en, p.id
        """,
        (period["period_end"], period["period_end"]),
    ).fetchall()
    label = _inventory_label(settings)
    return [
        {
            **{key: row[key] for key in row.keys()},
            "uom": "unit",
            "currency": period["currency"],
            "valuation_method": settings["valuation_method"] if settings else None,
            "export_label": label,
        }
        for row in rows
    ]


def _inventory_valuation_rows(
    conn: sqlite3.Connection, period: sqlite3.Row
) -> list[dict[str, object]]:
    settings = _inventory_settings(conn)
    rows = conn.execute(
        """
        SELECT vl.id AS valuation_layer_id, vl.movement_id, vl.item_type, vl.item_id,
               COALESCE(m.name, p.name_en, vl.item_id) AS item_name,
               im.movement_type, vl.quantity, vl.unit_value_amount,
               vl.total_value_cents, vl.currency, vl.valuation_method,
               vl.source_type, vl.source_id, vl.valuation_date, vl.review_state,
               vl.reversal_layer_id
        FROM inventory_valuation_layers vl
        LEFT JOIN inventory_movements im ON im.id = vl.movement_id
        LEFT JOIN materials m ON vl.item_type = 'material' AND m.id = vl.item_id
        LEFT JOIN products p ON vl.item_type = 'finished_good' AND p.id = vl.item_id
        WHERE (vl.valuation_date)::date BETWEEN %s AND %s
        ORDER BY vl.valuation_date, vl.created_at, vl.id
        """,
        (period["period_start"], period["period_end"]),
    ).fetchall()
    label = _inventory_label(settings)
    return [{**{key: row[key] for key in row.keys()}, "export_label": label} for row in rows]


def _cogs_rows(conn: sqlite3.Connection, period: sqlite3.Row) -> list[dict[str, object]]:
    settings = _inventory_settings(conn)
    rows = conn.execute(
        """
        SELECT c.id AS cogs_id, c.order_id, c.order_number, c.order_item_key,
               c.product_id, p.name_en AS product_name, c.quantity_sold,
               c.cogs_date, c.unit_cost_amount, c.total_cost_cents, c.currency,
               c.valuation_method, c.source_movement_id, c.source_valuation_layer_id,
               c.source_finished_batch_id, c.review_state, c.reversal_cogs_id
        FROM cogs_ledger c
        LEFT JOIN products p ON p.id = c.product_id
        WHERE (c.cogs_date)::date BETWEEN %s AND %s
        ORDER BY c.cogs_date, c.created_at, c.id
        """,
        (period["period_start"], period["period_end"]),
    ).fetchall()
    label = _inventory_label(settings)
    return [{**{key: row[key] for key in row.keys()}, "export_label": label} for row in rows]


def _inventory_writeoff_rows(
    conn: sqlite3.Connection, period: sqlite3.Row
) -> list[dict[str, object]]:
    settings = _inventory_settings(conn)
    rows = conn.execute(
        """
        SELECT im.id AS movement_id, im.item_type, im.item_id,
               COALESCE(m.name, p.name_en, im.item_id) AS item_name,
               im.movement_type, im.quantity_delta, im.uom, im.source_type,
               im.source_id, im.order_id, im.order_item_key, im.reason,
               im.notes, im.review_state, im.occurred_at,
               vl.id AS valuation_layer_id, vl.total_value_cents,
               vl.review_state AS valuation_review_state
        FROM inventory_movements im
        LEFT JOIN inventory_valuation_layers vl ON vl.movement_id = im.id
        LEFT JOIN materials m ON im.item_type = 'material' AND m.id = im.item_id
        LEFT JOIN products p ON im.item_type = 'finished_good' AND p.id = im.item_id
        WHERE (im.occurred_at)::date BETWEEN %s AND %s
          AND im.movement_type IN (
              'return_write_off', 'write_off', 'spoilage',
              'stock_count_correction', 'adjustment'
          )
        ORDER BY im.occurred_at, im.created_at, im.id
        """,
        (period["period_start"], period["period_end"]),
    ).fetchall()
    label = _inventory_label(settings)
    return [
        {
            **{key: row[key] for key in row.keys()},
            "currency": period["currency"],
            "valuation_method": settings["valuation_method"] if settings else None,
            "export_label": label,
        }
        for row in rows
    ]


def _collect_sheets(
    conn: sqlite3.Connection, period: sqlite3.Row, export_id: str, version: int
) -> dict[str, list[dict[str, object]]]:
    sheets: dict[str, list[dict[str, object]]] = {
        "summary": _summary_rows(conn, period),
        "settings_snapshot": _settings_rows(),
        "exceptions": _exception_rows(conn, period["id"]),
        "source_metadata": _source_metadata_rows(period, export_id, version),
    }
    for ledger_name in _EXPORT_LEDGER_NAMES:
        ledger = accounting_ledger_service.get_ledger(period["id"], ledger_name, limit=10000)  # type: ignore[arg-type]
        sheets[ledger_name] = ledger.rows
    sheets["material_on_hand"] = _material_on_hand_rows(conn, period)
    sheets["finished_goods_on_hand"] = _finished_goods_on_hand_rows(conn, period)
    sheets["inventory_valuation"] = _inventory_valuation_rows(conn, period)
    sheets["cogs"] = _cogs_rows(conn, period)
    sheets["inventory_writeoffs"] = _inventory_writeoff_rows(conn, period)
    return sheets


def list_export_packages(period_id: str | None = None) -> FinanceExportPackageListResponse:
    with get_db() as conn:
        if period_id:
            rows = conn.execute(
                "SELECT * FROM finance_export_packages WHERE period_id = %s ORDER BY version DESC",
                (period_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM finance_export_packages ORDER BY generated_at DESC"
            ).fetchall()
    return FinanceExportPackageListResponse(
        items=[_package_from_row(row) for row in rows], total=len(rows)
    )


def generate_export_package(
    period_id: str,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinanceExportPackageResponse:
    export_id = str(uuid.uuid4())
    with get_db() as conn:
        period = conn.execute(
            "SELECT * FROM finance_periods WHERE id = %s", (period_id,)
        ).fetchone()
        if period is None:
            raise FinancePeriodError(404, "FINANCE_PERIOD_NOT_FOUND", "Finance period not found.")
        if period["status"] != "closed":
            raise FinancePeriodError(
                409,
                "PERIOD_MUST_BE_CLOSED",
                "Final export packages can only be generated for closed finance periods.",
            )
        version_row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS next_version FROM finance_export_packages "
            "WHERE period_id = %s",
            (period_id,),
        ).fetchone()
        version = int(version_row["next_version"])
        package_dir = _private_export_root() / period_id / f"v{version}"
        csv_dir = package_dir / "csv"
        csv_dir.mkdir(parents=True, exist_ok=True)
        xlsx_path = package_dir / f"accounting-export-{period_id}-v{version}.xlsx"
        manifest_path = package_dir / "manifest.json"

        sheets = _collect_sheets(conn, period, export_id, version)
        _write_workbook(xlsx_path, sheets)
        components: dict[str, dict[str, object]] = {}
        for sheet_name, rows in sheets.items():
            csv_path = csv_dir / f"{sheet_name}.csv"
            _write_csv(csv_path, rows)
            components[csv_path.name] = {
                "sheet": sheet_name,
                "row_count": len(rows),
                "totals": _sheet_totals(rows),
                "sha256": _hash_file(csv_path),
            }
        files = {
            "xlsx": {"path": xlsx_path.name, "sha256": _hash_file(xlsx_path)},
            "csv_components": components,
        }
        manifest = {
            "export_id": export_id,
            "period_id": period_id,
            "period_start": period["period_start"],
            "period_end": period["period_end"],
            "currency": period["currency"],
            "schema_version": _SCHEMA_VERSION,
            "generated_at": pricing.now_utc(),
            "generated_by_admin_id": actor_user_id,
            "filters": {"period_id": period_id},
            "row_counts": {name: len(rows) for name, rows in sheets.items()},
            "sheet_totals": {name: _sheet_totals(rows) for name, rows in sheets.items()},
            "summary_totals": _json_loads(period["summary_totals_json"]) or {},
            "files": files,
        }
        manifest_path.write_text(_json_dumps(manifest), encoding="utf-8")
        manifest["files"]["manifest"] = {
            "path": manifest_path.name,
            "sha256": _hash_file(manifest_path),
        }

        conn.execute(
            "UPDATE finance_export_packages SET current_final = 0 WHERE period_id = %s",
            (period_id,),
        )
        conn.execute(
            """
            INSERT INTO finance_export_packages (
                id, period_id, version, schema_version, xlsx_path, csv_dir_path,
                manifest_path, manifest_json, generated_by_admin_id, generated_at,
                current_final
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            """,
            (
                export_id,
                period_id,
                version,
                _SCHEMA_VERSION,
                str(xlsx_path),
                str(csv_dir),
                str(manifest_path),
                _json_dumps(manifest),
                actor_user_id,
                pricing.now_utc(),
            ),
        )
        conn.execute(
            "UPDATE finance_periods SET status = 'exported', updated_by_admin_id = %s, "
            "updated_at = %s WHERE id = %s",
            (actor_user_id, pricing.now_utc(), period_id),
        )
        row = _get_package_row(conn, export_id)
        accounting_config_service.write_finance_audit_event(
            conn,
            action="finance_export_package.generate",
            target_type="finance_export_package",
            target_id=export_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            after=_package_from_row(row).model_dump(mode="json"),
        )
        return _package_from_row(row)


def accept_export_package(
    export_id: str,
    body: AccountantAcceptanceRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinanceExportPackageResponse:
    now = pricing.now_utc()
    with get_db() as conn:
        before = _get_package_row(conn, export_id)
        conn.execute(
            """
            UPDATE finance_export_packages
            SET accepted_by_admin_id = %s, accepted_at = %s, accountant_name = %s,
                accountant_reference = %s, acceptance_note = %s
            WHERE id = %s
            """,
            (
                actor_user_id,
                now,
                body.accountant_name,
                body.accountant_reference,
                body.note,
                export_id,
            ),
        )
        after = _get_package_row(conn, export_id)
        if bool(after["current_final"]):
            conn.execute(
                "UPDATE finance_periods SET status = 'accepted', accepted_at = %s, "
                "updated_by_admin_id = %s, updated_at = %s WHERE id = %s",
                (now, actor_user_id, now, after["period_id"]),
            )
        accounting_config_service.write_finance_audit_event(
            conn,
            action="finance_export_package.accept",
            target_type="finance_export_package",
            target_id=export_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=_package_from_row(before).model_dump(mode="json"),
            after=_package_from_row(after).model_dump(mode="json"),
            reason=body.note,
        )
        return _package_from_row(after)


def resolve_download_path(export_id: str, file: str) -> Path:
    """Resolve a package file by export id and logical file name."""
    with get_db() as conn:
        row = _get_package_row(conn, export_id)
    if file == "xlsx":
        path = Path(row["xlsx_path"])
    elif file == "manifest":
        path = Path(row["manifest_path"])
    else:
        csv_root = Path(row["csv_dir_path"]).resolve()
        path = (csv_root / Path(file).name).resolve()
        try:
            path.relative_to(csv_root)
        except ValueError as exc:
            raise FinancePeriodError(403, "EXPORT_FILE_FORBIDDEN", "Invalid export file.") from exc
    if not path.exists() or not path.is_file():
        raise FinancePeriodError(404, "EXPORT_FILE_NOT_FOUND", "Export file not found.")
    return path
