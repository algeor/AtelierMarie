"""Expense evidence and product-cost service tests."""

import psycopg
import pytest

from conftest import FAKE_SESSION_ID


def _seed_product_and_order(db: psycopg.Connection, app, *, product_id: str, order_id: str) -> None:
    db.execute(
        "INSERT INTO products (id, name_en, price_cents, stock) "
        "VALUES (%s, %s, 1000, 10) ON CONFLICT (id) DO NOTHING",
        (product_id, product_id.replace("-", " ").title()),
    )
    db.execute(
        """
        INSERT INTO orders (
            id, session_id, status, total_cents, customer_email, customer_name,
            payment_method, payment_status, accounting_classification_state,
            accounting_readiness_status, created_at, updated_at
        ) VALUES (%s, %s, 'confirmed', 1000, %s, 'Cost Buyer', 'card', 'paid',
                  'domestic_default', 'ready', '2026-08-10 10:00:00',
                  '2026-08-10 10:00:00')
        """,
        (order_id, FAKE_SESSION_ID, f"{order_id}@example.com"),
    )
    db.execute(
        """
        INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
        VALUES (%s, %s, %s, 1000, 1)
        """,
        (order_id, product_id, product_id.replace("-", " ").title()),
    )
    db.commit()


@pytest.mark.asyncio
async def test_expense_evidence_crud_payment_status_and_exception(admin_client, db, app):
    db.execute(
        """
        INSERT INTO expense_evidence_settings (
            id, required_document_categories_json, close_behavior
        ) VALUES ('default', '["materials"]', 'block')
        """
    )
    db.commit()

    create_resp = await admin_client.post(
        "/v1/admin/accounting/expenses",
        json={
            "supplier_name": "Wax Supplier",
            "purchase_date": "2026-08-05",
            "payment_status": "unpaid",
            "category_key": "materials",
            "net_amount_cents": 10000,
            "tax_amount_cents": 2000,
            "gross_amount_cents": 12000,
            "currency": "eur",
            "review_status": "missing_document",
        },
    )
    assert create_resp.status_code == 200
    expense = create_resp.json()
    assert expense["currency"] == "EUR"
    assert expense["review_status"] == "missing_document"

    payment_resp = await admin_client.patch(
        f"/v1/admin/accounting/expenses/{expense['id']}/payment-status",
        json={
            "payment_status": "paid",
            "payment_date": "2026-08-20",
            "reason": "Bank transfer confirmed.",
        },
    )
    assert payment_resp.status_code == 200
    assert payment_resp.json()["payment_status"] == "paid"

    update_resp = await admin_client.put(
        f"/v1/admin/accounting/expenses/{expense['id']}",
        json={
            **{
                key: payment_resp.json()[key]
                for key in (
                    "supplier_name",
                    "purchase_date",
                    "payment_status",
                    "payment_date",
                    "category_key",
                    "net_amount_cents",
                    "tax_amount_cents",
                    "gross_amount_cents",
                    "currency",
                )
            },
            "document_number": "SUP-100",
            "document_date": "2026-08-04",
            "attachment_reference": "private://expenses/sup-100.pdf",
            "review_status": "reviewed",
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["attachment_reference"] == "private://expenses/sup-100.pdf"

    list_resp = await admin_client.get("/v1/admin/accounting/expenses?review_status=reviewed")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    period_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "EUR"},
    )
    period_id = period_resp.json()["id"]
    await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/review")
    exceptions_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/exceptions?status=open"
    )
    assert "expense_document_missing" not in {
        item["exception_type"] for item in exceptions_resp.json()["items"]
    }

    actions = {row["action"] for row in db.execute("SELECT action FROM finance_audit_events")}
    assert {
        "expense_evidence.create",
        "expense_evidence.update",
        "expense_evidence.update_payment_status",
    }.issubset(actions)


@pytest.mark.asyncio
async def test_product_cost_versions_effective_lookup_and_missing_diagnostics(
    admin_client, db, app
):
    _seed_product_and_order(db, app, product_id="costed-candle", order_id="costed-order")
    _seed_product_and_order(
        db, app, product_id="missing-cost-candle", order_id="missing-cost-order"
    )

    create_resp = await admin_client.post(
        "/v1/admin/accounting/product-costs",
        json={
            "product_id": "costed-candle",
            "product_name": "Costed Candle",
            "effective_date": "2026-08-01",
            "costing_basis": "recipe_bom",
            "currency": "EUR",
            "reviewed": True,
            "accountant_reviewed": False,
            "review_status": "reviewed",
            "components": [
                {
                    "component_type": "material",
                    "description": "Wax",
                    "quantity": 0.2,
                    "unit": "kg",
                    "unit_cost_cents": 1500,
                    "total_cost_cents": 300,
                },
                {
                    "component_type": "packaging",
                    "description": "Jar",
                    "quantity": 1,
                    "unit": "piece",
                    "unit_cost_cents": 100,
                    "total_cost_cents": 100,
                },
            ],
        },
    )
    assert create_resp.status_code == 200
    cost = create_resp.json()
    assert cost["estimated_unit_cost_cents"] == 400
    assert len(cost["components"]) == 2

    update_resp = await admin_client.put(
        f"/v1/admin/accounting/product-costs/{cost['id']}",
        json={
            "product_id": "costed-candle",
            "product_name": "Costed Candle",
            "effective_date": "2026-08-01",
            "costing_basis": "manual_snapshot",
            "material_cost_cents": 350,
            "packaging_cost_cents": 100,
            "estimated_unit_cost_cents": 450,
            "currency": "EUR",
            "reviewed": True,
            "accountant_reviewed": True,
            "review_status": "accountant_reviewed",
            "components": [],
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["accountant_reviewed"] is True
    assert update_resp.json()["estimated_unit_cost_cents"] == 450

    effective_resp = await admin_client.get(
        "/v1/admin/accounting/product-costs/effective?product_id=costed-candle&effective_date=2026-08-10"
    )
    assert effective_resp.status_code == 200
    assert effective_resp.json()["id"] == cost["id"]

    period_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "EUR"},
    )
    period_id = period_resp.json()["id"]
    missing_resp = await admin_client.get(
        f"/v1/admin/accounting/product-costs/missing?period_id={period_id}"
    )
    assert missing_resp.status_code == 200
    assert {item["product_id"] for item in missing_resp.json()["items"]} == {"missing-cost-candle"}

    ledger_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/ledgers/product_costs"
    )
    assert ledger_resp.status_code == 200
    assert any(row["estimate_label"] == "accountant_reviewed" for row in ledger_resp.json()["rows"])
    assert any(row["missing_cost_warning"] is True for row in ledger_resp.json()["rows"])

    actions = {row["action"] for row in db.execute("SELECT action FROM finance_audit_events")}
    assert {"product_cost_version.create", "product_cost_version.update"}.issubset(actions)
