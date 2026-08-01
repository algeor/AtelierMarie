"""Accounting & Finance Hub configuration service and admin route tests."""

import json

import pytest

from app.services import accounting_config_service


@pytest.mark.asyncio
async def test_accounting_config_requires_admin(client):
    resp = await client.get("/v1/admin/accounting/config")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_accounting_config_reports_missing_setup(admin_client):
    resp = await admin_client.get("/v1/admin/accounting/config")

    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-store, no-cache"
    body = resp.json()
    assert {item["code"] for item in body["setup_exceptions"]} == {
        "seller_profile_missing",
        "vat_fiscal_settings_missing",
    }
    assert body["product_cost_settings"]["enabled"] is False


@pytest.mark.asyncio
async def test_seller_and_vat_settings_are_versioned_redacted_and_audited(
    admin_client, db
):
    seller_resp = await admin_client.post(
        "/v1/admin/accounting/config/seller-profile",
        json={
            "effective_date": "2026-08-01",
            "reviewed": True,
            "company_display_name": "Atelier Marie",
            "legal_name": "Atelier Marie OOD",
            "uic_eik": "123456789",
            "vat_identification_number": "BG123456789",
            "registered_address": {"country": "BG", "city": "Sofia"},
            "contact_email": "accounting@example.com",
            "bank_details": {"iban": "BG00SECRET", "bank_name": "Demo Bank"},
            "default_currency": "eur",
        },
    )
    assert seller_resp.status_code == 200
    seller = seller_resp.json()
    assert seller["reviewed"] is True
    assert seller["default_currency"] == "EUR"
    assert seller["bank_details"] == {"iban": "<redacted>", "bank_name": "Demo Bank"}
    assert seller["bank_details_configured"] is True

    vat_resp = await admin_client.post(
        "/v1/admin/accounting/config/vat-fiscal",
        json={
            "effective_date": "2026-08-01",
            "reviewed": True,
            "vat_mode": "registered",
            "oss_mode": "not_registered",
            "default_domestic_vat_treatment": "standard",
            "fiscal_document_mode": "external_reference",
            "document_rules": {"cod": "fiscal_receipt_reference"},
            "threshold_warnings": {"distance_sales_eur": 10000},
            "tolerance_cents": 2,
            "warning_text": "Reviewed by accountant.",
        },
    )
    assert vat_resp.status_code == 200
    assert vat_resp.json()["vat_mode"] == "registered"

    config_resp = await admin_client.get("/v1/admin/accounting/config")
    assert config_resp.json()["setup_exceptions"] == []

    audit_rows = db.execute(
        "SELECT action, after_json FROM finance_audit_events ORDER BY created_at"
    ).fetchall()
    assert [row["action"] for row in audit_rows] == [
        "seller_profile.create_version",
        "vat_fiscal_settings.create_version",
    ]
    seller_after = json.loads(audit_rows[0]["after_json"])
    assert seller_after["bank_details"]["iban"] == "<redacted>"
    assert "BG00SECRET" not in audit_rows[0]["after_json"]


@pytest.mark.asyncio
async def test_mapping_and_singleton_settings_update_with_audit(admin_client, db):
    mapping_resp = await admin_client.put(
        "/v1/admin/accounting/config/category-mappings/material_purchases",
        json={
            "category_code": "601",
            "category_label": "Material purchases",
            "is_required": True,
            "reviewed": True,
        },
    )
    assert mapping_resp.status_code == 200
    assert mapping_resp.json()["mapping_key"] == "material_purchases"

    export_resp = await admin_client.put(
        "/v1/admin/accounting/config/export-schema",
        json={
            "workbook_language": "bg",
            "date_format": "dd.mm.yyyy",
            "decimal_separator": ",",
            "default_period_range": "monthly",
            "included_tabs": ["summary", "expenses", "product_cost_estimates"],
            "custom_columns": {"expenses": {"supplier_name": "Supplier"}},
            "reviewed": True,
        },
    )
    assert export_resp.status_code == 200
    assert export_resp.json()["workbook_language"] == "bg"

    expense_resp = await admin_client.put(
        "/v1/admin/accounting/config/expense-settings",
        json={
            "required_document_categories": ["materials", "packaging"],
            "allowed_payment_statuses": ["unpaid", "paid"],
            "default_category_mappings": {"materials": "material_purchases"},
            "close_behavior": "block",
            "reviewed": True,
        },
    )
    assert expense_resp.status_code == 200
    assert expense_resp.json()["close_behavior"] == "block"

    product_cost_resp = await admin_client.put(
        "/v1/admin/accounting/config/product-cost-settings",
        json={
            "enabled": True,
            "costing_basis": "recipe_bom",
            "include_labor": True,
            "include_overhead": False,
            "missing_cost_policy": "warning",
            "reviewed": False,
            "estimate_label": "management_estimate",
        },
    )
    assert product_cost_resp.status_code == 200
    assert product_cost_resp.json()["enabled"] is True

    actions = {
        row["action"]
        for row in db.execute("SELECT action FROM finance_audit_events").fetchall()
    }
    assert {
        "category_mapping.upsert",
        "export_schema_settings.update",
        "expense_evidence_settings.update",
        "product_cost_settings.update",
    }.issubset(actions)

    config = (await admin_client.get("/v1/admin/accounting/config")).json()
    assert config["category_mappings"][0]["category_label"] == "Material purchases"
    assert config["export_schema"]["included_tabs"] == [
        "summary",
        "expenses",
        "product_cost_estimates",
    ]
    assert config["expense_settings"]["required_document_categories"] == [
        "materials",
        "packaging",
    ]
    assert config["product_cost_settings"]["costing_basis"] == "recipe_bom"


def test_current_reviewed_version_helpers(db):
    seller = accounting_config_service.create_seller_legal_profile(
        accounting_config_service.SellerLegalProfileRequest(
            effective_date="2026-08-01",
            reviewed=True,
            legal_name="Atelier Marie OOD",
        )
    )
    vat = accounting_config_service.create_vat_fiscal_settings(
        accounting_config_service.VatFiscalSettingsRequest(
            effective_date="2026-08-01",
            reviewed=True,
            vat_mode="registered",
        )
    )

    assert accounting_config_service.current_seller_profile_version_id(db) == seller.id
    assert accounting_config_service.current_vat_fiscal_settings_version_id(db) == vat.id
