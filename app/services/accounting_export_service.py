"""Accountant export package builder."""

from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import uuid
from typing import Any

from openpyxl import Workbook

from app.config import get_settings
from app.database import get_db
from app.models.accounting import (
    AccountantAcceptanceRequest,
    FinanceExportPackageListResponse,
    FinanceExportPackageResponse,
)
from app.services import accounting_config_service, accounting_ledger_service, pricing
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
    return json.dumps(value, indent=2, sort_keys=True)


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
        generated_at=row["generated_at"],
        accepted_by_admin_id=row["accepted_by_admin_id"],
        accepted_at=row["accepted_at"],
        accountant_name=row["accountant_name"],
        accountant_reference=row["accountant_reference"],
        acceptance_note=row["acceptance_note"],
        current_final=bool(row["current_final"]),
    )


def _get_package_row(conn: sqlite3.Connection, export_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM finance_export_packages WHERE id = ?", (export_id,)).fetchone()
    if row is None:
        raise FinancePeriodError(404, "EXPORT_PACKAGE_NOT_FOUND", "Export package not found.")
    return row


def _private_export_root() -> Path:
    db_parent = Path(get_settings().database_path).resolve().parent
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
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _headers(rows: list[dict[str, object]]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen


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
        "SELECT * FROM finance_exceptions WHERE period_id = ? ORDER BY status, severity, created_at",
        (period_id,),
    ).fetchall()
    return [{key: row[key] for key in row.keys()} for row in rows]


def _summary_rows(conn: sqlite3.Connection, period: sqlite3.Row) -> list[dict[str, object]]:
    summary = _json_loads(period["summary_totals_json"]) or calculate_summary_totals(conn, period)
    return [{"metric": key, "value": value} for key, value in summary.items()]


def _source_metadata_rows(period: sqlite3.Row, export_id: str, version: int) -> list[dict[str, object]]:
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


def _collect_sheets(conn: sqlite3.Connection, period: sqlite3.Row, export_id: str, version: int) -> dict[str, list[dict[str, object]]]:
    sheets: dict[str, list[dict[str, object]]] = {
        "summary": _summary_rows(conn, period),
        "settings_snapshot": _settings_rows(),
        "exceptions": _exception_rows(conn, period["id"]),
        "source_metadata": _source_metadata_rows(period, export_id, version),
    }
    for ledger_name in _EXPORT_LEDGER_NAMES:
        ledger = accounting_ledger_service.get_ledger(period["id"], ledger_name, limit=10000)  # type: ignore[arg-type]
        sheets[ledger_name] = ledger.rows
    return sheets


def list_export_packages(period_id: str | None = None) -> FinanceExportPackageListResponse:
    with get_db() as conn:
        if period_id:
            rows = conn.execute(
                "SELECT * FROM finance_export_packages WHERE period_id = ? ORDER BY version DESC",
                (period_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM finance_export_packages ORDER BY generated_at DESC"
            ).fetchall()
    return FinanceExportPackageListResponse(items=[_package_from_row(row) for row in rows], total=len(rows))


def generate_export_package(
    period_id: str,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> FinanceExportPackageResponse:
    export_id = str(uuid.uuid4())
    with get_db() as conn:
        period = conn.execute("SELECT * FROM finance_periods WHERE id = ?", (period_id,)).fetchone()
        if period is None:
            raise FinancePeriodError(404, "FINANCE_PERIOD_NOT_FOUND", "Finance period not found.")
        if period["status"] != "closed":
            raise FinancePeriodError(
                409,
                "PERIOD_MUST_BE_CLOSED",
                "Final export packages can only be generated for closed finance periods.",
            )
        version_row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS next_version FROM finance_export_packages WHERE period_id = ?",
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
            "summary_totals": _json_loads(period["summary_totals_json"]) or {},
            "files": files,
        }
        manifest_path.write_text(_json_dumps(manifest), encoding="utf-8")
        manifest["files"]["manifest"] = {
            "path": manifest_path.name,
            "sha256": _hash_file(manifest_path),
        }

        conn.execute(
            "UPDATE finance_export_packages SET current_final = 0 WHERE period_id = ?",
            (period_id,),
        )
        conn.execute(
            """
            INSERT INTO finance_export_packages (
                id, period_id, version, schema_version, xlsx_path, csv_dir_path,
                manifest_path, manifest_json, generated_by_admin_id, generated_at,
                current_final
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
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
            "UPDATE finance_periods SET status = 'exported', updated_by_admin_id = ?, updated_at = ? WHERE id = ?",
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
            SET accepted_by_admin_id = ?, accepted_at = ?, accountant_name = ?,
                accountant_reference = ?, acceptance_note = ?
            WHERE id = ?
            """,
            (actor_user_id, now, body.accountant_name, body.accountant_reference, body.note, export_id),
        )
        after = _get_package_row(conn, export_id)
        if bool(after["current_final"]):
            conn.execute(
                "UPDATE finance_periods SET status = 'accepted', accepted_at = ?, updated_by_admin_id = ?, updated_at = ? WHERE id = ?",
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
