"""Accounting document registry tests."""

import json
import sqlite3

import pytest


def _seed_settings(
    db: sqlite3.Connection, *, document_rules: dict[str, object] | None = None
) -> tuple[int, int]:
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
            effective_date, reviewed, vat_mode, fiscal_document_mode, document_rules_json
        ) VALUES ('2026-08-01', 1, 'registered', 'external_reference', ?)
        """,
        (json.dumps(document_rules or {}),),
    )
    vat_id = int(db.execute("SELECT last_insert_rowid()").fetchone()[0])
    db.commit()
    return seller_id, vat_id


def _seed_order(
    db: sqlite3.Connection,
    app,
    *,
    order_id: str = "doc-order",
    seller_id: int,
    vat_id: int,
) -> None:
    db.execute(
        "INSERT OR IGNORE INTO products (id, name_en, price_cents, stock) "
        "VALUES ('doc-candle', 'Doc Candle', 1000, 10)"
    )
    db.execute(
        """
        INSERT INTO orders (
            id, session_id, status, total_cents, customer_email, customer_name,
            payment_method, payment_status, seller_legal_profile_version_id,
            vat_fiscal_settings_version_id, accounting_classification_state,
            accounting_readiness_status, created_at, updated_at
        ) VALUES (?, ?, 'confirmed', 1000, 'doc@example.com', 'Doc Buyer',
                  'card', 'paid', ?, ?, 'domestic_default', 'ready',
                  '2026-08-10 10:00:00', '2026-08-10 10:00:00')
        """,
        (order_id, app._test_session_id, seller_id, vat_id),
    )
    db.execute(
        """
        INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
        VALUES (?, 'doc-candle', 'Doc Candle', 1000, 1)
        """,
        (order_id,),
    )
    db.execute(
        """
        INSERT INTO payments (id, order_id, provider, amount_cents, provider_status)
        VALUES ('doc-payment', ?, 'stripe', 1000, 'paid')
        """,
        (order_id,),
    )
    db.commit()


@pytest.mark.asyncio
async def test_accounting_document_crud_credit_note_validation_and_audit(admin_client, db, app):
    seller_id, vat_id = _seed_settings(db)
    _seed_order(db, app, seller_id=seller_id, vat_id=vat_id)
    db.execute(
        """
        INSERT INTO payment_refunds (
            id, order_id, payment_id, provider, provider_refund_id, amount_cents, status
        ) VALUES ('doc-refund', 'doc-order', 'doc-payment', 'stripe', 're_doc', 300,
                  'succeeded')
        """
    )
    db.commit()

    invoice_resp = await admin_client.post(
        "/v1/admin/accounting/documents",
        json={
            "document_type": "invoice",
            "source_system": "accountant",
            "document_number": "INV-100",
            "issue_date": "2026-08-10",
            "order_id": "doc-order",
            "currency": "eur",
            "net_amount_cents": 800,
            "tax_amount_cents": 200,
            "gross_amount_cents": 1000,
            "vat_summary": {"standard": 200},
            "status": "recorded",
        },
    )
    assert invoice_resp.status_code == 200
    invoice = invoice_resp.json()
    assert invoice["document_number"] == "INV-100"
    assert invoice["currency"] == "EUR"

    bad_credit_resp = await admin_client.post(
        "/v1/admin/accounting/documents",
        json={
            "document_type": "credit_note",
            "source_system": "accountant",
            "document_number": "CN-BAD",
            "issue_date": "2026-08-11",
            "order_id": "doc-order",
            "refund_id": "doc-refund",
            "gross_amount_cents": 300,
        },
    )
    assert bad_credit_resp.status_code == 422
    assert bad_credit_resp.json()["error"]["code"] == "CREDIT_NOTE_ORIGINAL_REQUIRED"

    credit_resp = await admin_client.post(
        "/v1/admin/accounting/documents",
        json={
            "document_type": "credit_note",
            "source_system": "accountant",
            "document_number": "CN-100",
            "issue_date": "2026-08-11",
            "order_id": "doc-order",
            "refund_id": "doc-refund",
            "original_document_id": invoice["id"],
            "gross_amount_cents": 300,
        },
    )
    assert credit_resp.status_code == 200
    assert credit_resp.json()["original_document_id"] == invoice["id"]

    update_resp = await admin_client.put(
        f"/v1/admin/accounting/documents/{invoice['id']}",
        json={
            **{
                key: invoice[key]
                for key in (
                    "document_type",
                    "source_system",
                    "issue_date",
                    "order_id",
                    "currency",
                    "net_amount_cents",
                    "tax_amount_cents",
                    "gross_amount_cents",
                    "status",
                )
            },
            "document_number": "INV-100-UPDATED",
            "vat_summary": invoice["vat_summary"],
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["document_number"] == "INV-100-UPDATED"

    list_resp = await admin_client.get("/v1/admin/accounting/orders/doc-order/documents")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 2

    actions = [
        row["action"]
        for row in db.execute(
            "SELECT action FROM finance_audit_events ORDER BY created_at"
        ).fetchall()
    ]
    assert actions.count("accounting_document.create") == 2
    assert "accounting_document.update" in actions


@pytest.mark.asyncio
async def test_document_reference_clears_missing_document_exception(admin_client, db, app):
    seller_id, vat_id = _seed_settings(db, document_rules={"card": "invoice_reference"})
    _seed_order(db, app, order_id="doc-required-order", seller_id=seller_id, vat_id=vat_id)

    period_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "EUR"},
    )
    period_id = period_resp.json()["id"]
    await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/review")
    missing_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/exceptions?status=open"
    )
    assert "missing_document_reference" in {
        item["exception_type"] for item in missing_resp.json()["items"]
    }

    create_resp = await admin_client.post(
        "/v1/admin/accounting/documents",
        json={
            "document_type": "invoice",
            "source_system": "accountant",
            "document_number": "INV-CLEAR",
            "issue_date": "2026-08-10",
            "order_id": "doc-required-order",
            "gross_amount_cents": 1000,
        },
    )
    assert create_resp.status_code == 200

    refreshed_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/exceptions?status=open"
    )
    assert "missing_document_reference" not in {
        item["exception_type"] for item in refreshed_resp.json()["items"]
    }
