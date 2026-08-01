"""Accounting export package builder tests."""

from pathlib import Path
import sqlite3

from openpyxl import load_workbook
import pytest


def _seed_reviewed_settings(db: sqlite3.Connection) -> tuple[int, int]:
    db.execute(
        """
        INSERT INTO seller_legal_profile_versions (
            effective_date, reviewed, legal_name, default_currency
        ) VALUES ('2026-08-01', 1, 'Atelier Marie OOD', 'EUR')
        """
    )
    seller_id = int(db.execute("SELECT last_insert_rowid()").fetchone()[0])
    db.execute(
        """
        INSERT INTO vat_fiscal_settings_versions (
            effective_date, reviewed, vat_mode, fiscal_document_mode
        ) VALUES ('2026-08-01', 1, 'registered', 'external_reference')
        """
    )
    vat_id = int(db.execute("SELECT last_insert_rowid()").fetchone()[0])
    db.commit()
    return seller_id, vat_id


def _seed_paid_order(db: sqlite3.Connection, app, *, seller_id: int, vat_id: int) -> None:
    db.execute(
        "INSERT OR IGNORE INTO products (id, name_en, price_cents, stock) VALUES ('export-candle', 'Export Candle', 1000, 10)"
    )
    db.execute(
        """
        INSERT INTO orders (
            id, session_id, status, total_cents, customer_email, customer_name,
            payment_method, payment_status, seller_legal_profile_version_id,
            vat_fiscal_settings_version_id, accounting_classification_state,
            accounting_readiness_status, created_at, updated_at
        ) VALUES ('export-order', ?, 'confirmed', 1000, 'export@example.com',
                  'Export Buyer', 'card', 'paid', ?, ?, 'domestic_default', 'ready',
                  '2026-08-10 10:00:00', '2026-08-10 10:00:00')
        """,
        (app._test_session_id, seller_id, vat_id),
    )
    db.execute(
        """
        INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
        VALUES ('export-order', 'export-candle', 'Export Candle', 1000, 1)
        """
    )
    db.execute(
        """
        INSERT INTO payments (id, order_id, provider, amount_cents, provider_status)
        VALUES ('export-payment', 'export-order', 'stripe', 1000, 'paid')
        """
    )
    db.execute(
        """
        INSERT INTO expense_evidence (
            id, supplier_name, document_number, purchase_date, payment_status,
            category_key, gross_amount_cents, tax_amount_cents, review_status
        ) VALUES ('export-expense', 'Wax Supplier', 'SUP-EXP', '2026-08-05',
                  'paid', 'materials', 12000, 2000, 'reviewed')
        """
    )
    db.commit()


async def _closed_period(admin_client) -> str:
    period_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "EUR"},
    )
    period_id = period_resp.json()["id"]
    await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/review")
    close_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/close")
    assert close_resp.status_code == 200
    return period_id


@pytest.mark.asyncio
async def test_export_package_generation_manifest_download_accept_and_versioning(admin_client, db, app):
    seller_id, vat_id = _seed_reviewed_settings(db)
    _seed_paid_order(db, app, seller_id=seller_id, vat_id=vat_id)

    open_period_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-07-01", "period_end": "2026-07-31", "currency": "EUR"},
    )
    open_export_resp = await admin_client.post(
        f"/v1/admin/accounting/periods/{open_period_resp.json()['id']}/exports"
    )
    assert open_export_resp.status_code == 409
    assert open_export_resp.json()["error"]["code"] == "PERIOD_MUST_BE_CLOSED"

    period_id = await _closed_period(admin_client)
    export_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/exports")
    assert export_resp.status_code == 200
    package = export_resp.json()
    assert package["version"] == 1
    assert package["current_final"] is True
    xlsx_path = Path(package["xlsx_path"])
    manifest_path = Path(package["manifest_path"])
    assert xlsx_path.exists()
    assert manifest_path.exists()
    assert "private-exports" in str(xlsx_path)
    manifest = package["manifest"]
    assert manifest["schema_version"] == "accounting-finance-hub.v1"
    assert manifest["row_counts"]["sales"] >= 1
    assert "summary.csv" in manifest["files"]["csv_components"]
    assert manifest["files"]["xlsx"]["sha256"]

    workbook = load_workbook(xlsx_path, read_only=True)
    assert {"summary", "sales", "expenses", "product_costs", "settings_snapshot"}.issubset(
        set(workbook.sheetnames)
    )
    workbook.close()

    download_resp = await admin_client.get(
        f"/v1/admin/accounting/exports/{package['id']}/download?file=manifest"
    )
    assert download_resp.status_code == 200
    assert download_resp.headers["cache-control"] == "no-store, no-cache"

    accept_resp = await admin_client.post(
        f"/v1/admin/accounting/exports/{package['id']}/accept",
        json={
            "accountant_name": "Accountant Demo",
            "accountant_reference": "AUG-OK",
            "note": "Accepted for booking.",
        },
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["accepted_at"] is not None
    assert accept_resp.json()["accountant_reference"] == "AUG-OK"
    period_after_accept = await admin_client.get(f"/v1/admin/accounting/periods/{period_id}")
    assert period_after_accept.json()["status"] == "accepted"

    reopen_resp = await admin_client.post(
        f"/v1/admin/accounting/periods/{period_id}/reopen",
        json={"reason": "Late correction."},
    )
    assert reopen_resp.status_code == 200
    close_again_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/close")
    assert close_again_resp.status_code == 200
    export_v2_resp = await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/exports")
    assert export_v2_resp.status_code == 200
    assert export_v2_resp.json()["version"] == 2
    assert export_v2_resp.json()["xlsx_path"] != package["xlsx_path"]
    assert xlsx_path.exists()

    list_resp = await admin_client.get(f"/v1/admin/accounting/exports?period_id={period_id}")
    assert [item["version"] for item in list_resp.json()["items"]] == [2, 1]
    assert [item["current_final"] for item in list_resp.json()["items"]] == [True, False]

    actions = {row["action"] for row in db.execute("SELECT action FROM finance_audit_events")}
    assert "finance_export_package.generate" in actions
    assert "finance_export_package.accept" in actions
