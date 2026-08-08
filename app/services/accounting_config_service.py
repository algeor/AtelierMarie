"""Accounting & Finance Hub configuration services."""

import json
import uuid
from datetime import date, datetime
from typing import Any

from app.database import DbConnection, get_db, require_row
from app.models.accounting import (
    AccountingConfigurationResponse,
    AccountingSetupException,
    CategoryMappingRequest,
    CategoryMappingResponse,
    ExpenseEvidenceSettingsRequest,
    ExpenseEvidenceSettingsResponse,
    ExportSchemaSettingsRequest,
    ExportSchemaSettingsResponse,
    ProductCostSettingsRequest,
    ProductCostSettingsResponse,
    SellerLegalProfileRequest,
    SellerLegalProfileResponse,
    VatFiscalSettingsRequest,
    VatFiscalSettingsResponse,
)
from app.services import pricing

_SETTINGS_ID = "default"
_REDACTED = "<redacted>"


def _fmt_ts(value: object) -> str | None:
    """Render a DATE/TIMESTAMPTZ column (psycopg returns date/datetime) as a string.

    Response models declare these fields as ``str``; ``None`` passes through and an
    existing string is returned unchanged.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


_SENSITIVE_BANK_KEYS = {
    "account_number",
    "iban",
    "bic",
    "swift",
    "bank_account",
    "routing_number",
}


def _json_default(value: object) -> str:
    if isinstance(value, datetime | date):
        return _fmt_ts(value) or ""
    return str(value)


def _json_dumps(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), sort_keys=True, default=_json_default)


def _json_loads(value: str | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _redact_bank_details(value: dict[str, object] | None) -> dict[str, object] | None:
    if not value:
        return None
    redacted: dict[str, object] = {}
    for key, raw in value.items():
        if key.casefold() in _SENSITIVE_BANK_KEYS:
            redacted[key] = _REDACTED
        else:
            redacted[key] = raw
    return redacted


def _redacted_payload(payload: dict[str, object] | None) -> dict[str, object] | None:
    if payload is None:
        return None
    redacted = dict(payload)
    bank_details = redacted.get("bank_details")
    if isinstance(bank_details, dict):
        redacted["bank_details"] = _redact_bank_details(bank_details)
    return redacted


def write_finance_audit_event(
    conn: DbConnection,
    *,
    action: str,
    target_type: str,
    target_id: str | None,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
    before: dict[str, object] | None = None,
    after: dict[str, object] | None = None,
    reason: str | None = None,
) -> str:
    """Append a redacted finance audit event and return its id."""
    event_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO finance_audit_events (
            id, actor_user_id, actor_email, action, target_type, target_id,
            request_id, before_json, after_json, reason, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            event_id,
            actor_user_id,
            actor_email,
            action,
            target_type,
            target_id,
            request_id,
            _json_dumps(_redacted_payload(before)),
            _json_dumps(_redacted_payload(after)),
            reason,
            pricing.now_utc(),
        ),
    )
    return event_id


def _seller_profile_from_row(
    row: dict | None,
    *,
    include_sensitive: bool = False,
) -> SellerLegalProfileResponse | None:
    if row is None:
        return None
    bank_details = _json_loads(row["bank_details_json"], None)
    if not include_sensitive:
        bank_details = _redact_bank_details(bank_details)
    return SellerLegalProfileResponse(
        id=row["id"],
        effective_date=_fmt_ts(row["effective_date"]),
        reviewed=bool(row["reviewed"]),
        company_display_name=row["company_display_name"],
        legal_name=row["legal_name"],
        uic_eik=row["uic_eik"],
        vat_identification_number=row["vat_identification_number"],
        registered_address=_json_loads(row["registered_address_json"], None),
        contact_email=row["contact_email"],
        bank_details=bank_details,
        bank_details_configured=bool(row["bank_details_json"]),
        default_currency=row["default_currency"],
        created_by_admin_id=row["created_by_admin_id"],
        created_at=_fmt_ts(row["created_at"]),
    )


def _vat_settings_from_row(row: dict | None) -> VatFiscalSettingsResponse | None:
    if row is None:
        return None
    return VatFiscalSettingsResponse(
        id=row["id"],
        effective_date=_fmt_ts(row["effective_date"]),
        reviewed=bool(row["reviewed"]),
        vat_mode=row["vat_mode"],
        oss_mode=row["oss_mode"],
        default_domestic_vat_treatment=row["default_domestic_vat_treatment"],
        fiscal_document_mode=row["fiscal_document_mode"],
        document_rules=_json_loads(row["document_rules_json"], None),
        threshold_warnings=_json_loads(row["threshold_warnings_json"], None),
        tolerance_cents=row["tolerance_cents"],
        warning_text=row["warning_text"],
        created_by_admin_id=row["created_by_admin_id"],
        created_at=_fmt_ts(row["created_at"]),
    )


def _category_mapping_from_row(row: dict) -> CategoryMappingResponse:
    return CategoryMappingResponse(
        id=row["id"],
        mapping_key=row["mapping_key"],
        category_code=row["category_code"],
        category_label=row["category_label"],
        is_required=bool(row["is_required"]),
        reviewed=bool(row["reviewed"]),
        created_at=_fmt_ts(row["created_at"]),
        updated_at=_fmt_ts(row["updated_at"]),
    )


def _export_schema_from_row(row: dict) -> ExportSchemaSettingsResponse:
    return ExportSchemaSettingsResponse(
        id=row["id"],
        workbook_language=row["workbook_language"],
        date_format=row["date_format"],
        decimal_separator=row["decimal_separator"],
        default_period_range=row["default_period_range"],
        included_tabs=_json_loads(row["included_tabs_json"], []),
        custom_columns=_json_loads(row["custom_columns_json"], None),
        reviewed=bool(row["reviewed"]),
        updated_at=_fmt_ts(row["updated_at"]),
    )


def _expense_settings_from_row(row: dict) -> ExpenseEvidenceSettingsResponse:
    return ExpenseEvidenceSettingsResponse(
        id=row["id"],
        required_document_categories=_json_loads(row["required_document_categories_json"], []),
        allowed_payment_statuses=_json_loads(row["allowed_payment_statuses_json"], []),
        default_category_mappings=_json_loads(row["default_category_mappings_json"], {}),
        close_behavior=row["close_behavior"],
        reviewed=bool(row["reviewed"]),
        updated_at=_fmt_ts(row["updated_at"]),
    )


def _product_cost_settings_from_row(row: dict) -> ProductCostSettingsResponse:
    return ProductCostSettingsResponse(
        id=row["id"],
        enabled=bool(row["enabled"]),
        costing_basis=row["costing_basis"],
        include_labor=bool(row["include_labor"]),
        include_overhead=bool(row["include_overhead"]),
        missing_cost_policy=row["missing_cost_policy"],
        reviewed=bool(row["reviewed"]),
        estimate_label=row["estimate_label"],
        updated_at=_fmt_ts(row["updated_at"]),
    )


def _latest_row(conn: DbConnection, table: str) -> dict | None:
    return conn.execute(
        f"SELECT * FROM {table} ORDER BY effective_date DESC, id DESC LIMIT 1"  # noqa: S608
    ).fetchone()


def _ensure_export_schema_row(conn: DbConnection) -> dict:
    conn.execute(
        "INSERT INTO accounting_export_schema_settings (id) VALUES (%s) "
        "ON CONFLICT (id) DO NOTHING",
        (_SETTINGS_ID,),
    )
    return require_row(
        conn.execute(
            "SELECT * FROM accounting_export_schema_settings WHERE id = %s",
            (_SETTINGS_ID,),
        ).fetchone(),
        "accounting_export_schema_settings row missing after ensure",
    )


def _ensure_expense_settings_row(conn: DbConnection) -> dict:
    conn.execute(
        """
        INSERT INTO expense_evidence_settings (
            id, required_document_categories_json, allowed_payment_statuses_json,
            default_category_mappings_json
        ) VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """,
        (
            _SETTINGS_ID,
            _json_dumps([]),
            _json_dumps(["unpaid", "paid", "partially_paid", "reimbursed"]),
            _json_dumps({}),
        ),
    )
    return require_row(
        conn.execute(
            "SELECT * FROM expense_evidence_settings WHERE id = %s",
            (_SETTINGS_ID,),
        ).fetchone(),
        "expense_evidence_settings row missing after ensure",
    )


def _ensure_product_cost_settings_row(conn: DbConnection) -> dict:
    conn.execute(
        "INSERT INTO product_cost_settings (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
        (_SETTINGS_ID,),
    )
    return require_row(
        conn.execute(
            "SELECT * FROM product_cost_settings WHERE id = %s",
            (_SETTINGS_ID,),
        ).fetchone(),
        "product_cost_settings row missing after ensure",
    )


def setup_exceptions(
    seller_profile: SellerLegalProfileResponse | None,
    vat_settings: VatFiscalSettingsResponse | None,
) -> list[AccountingSetupException]:
    """Return blocking setup exceptions for missing/unreviewed legal settings."""
    issues: list[AccountingSetupException] = []
    if seller_profile is None:
        issues.append(
            AccountingSetupException(
                code="seller_profile_missing",
                message="Seller legal profile is missing.",
            )
        )
    elif not seller_profile.reviewed:
        issues.append(
            AccountingSetupException(
                code="seller_profile_unreviewed",
                message="Seller legal profile has not been accountant-reviewed.",
            )
        )

    if vat_settings is None:
        issues.append(
            AccountingSetupException(
                code="vat_fiscal_settings_missing",
                message="VAT/fiscal settings are missing.",
            )
        )
    elif not vat_settings.reviewed:
        issues.append(
            AccountingSetupException(
                code="vat_fiscal_settings_unreviewed",
                message="VAT/fiscal settings have not been accountant-reviewed.",
            )
        )
    return issues


def get_accounting_configuration(
    *, include_sensitive: bool = False
) -> AccountingConfigurationResponse:
    """Return the current accounting configuration snapshot."""
    with get_db() as conn:
        seller = _seller_profile_from_row(
            _latest_row(conn, "seller_legal_profile_versions"),
            include_sensitive=include_sensitive,
        )
        vat = _vat_settings_from_row(_latest_row(conn, "vat_fiscal_settings_versions"))
        category_rows = conn.execute(
            "SELECT * FROM accounting_category_mappings ORDER BY mapping_key"
        ).fetchall()
        export_schema = _export_schema_from_row(_ensure_export_schema_row(conn))
        expense_settings = _expense_settings_from_row(_ensure_expense_settings_row(conn))
        product_cost_settings = _product_cost_settings_from_row(
            _ensure_product_cost_settings_row(conn)
        )

    return AccountingConfigurationResponse(
        seller_profile=seller,
        vat_fiscal_settings=vat,
        category_mappings=[_category_mapping_from_row(row) for row in category_rows],
        export_schema=export_schema,
        expense_settings=expense_settings,
        product_cost_settings=product_cost_settings,
        setup_exceptions=setup_exceptions(seller, vat),
    )


def get_current_seller_legal_profile() -> SellerLegalProfileResponse | None:
    """Return the latest seller legal profile without sensitive bank details."""
    with get_db() as conn:
        return _seller_profile_from_row(_latest_row(conn, "seller_legal_profile_versions"))


def create_seller_legal_profile(
    body: SellerLegalProfileRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
    reason: str | None = None,
) -> SellerLegalProfileResponse:
    """Insert a new seller legal profile version and audit it."""
    payload = body.model_dump(mode="json")
    with get_db() as conn:
        inserted = conn.execute(
            """
            INSERT INTO seller_legal_profile_versions (
                effective_date, reviewed, company_display_name, legal_name, uic_eik,
                vat_identification_number, registered_address_json, contact_email,
                bank_details_json, default_currency, created_by_admin_id, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                body.effective_date,
                1 if body.reviewed else 0,
                body.company_display_name,
                body.legal_name,
                body.uic_eik,
                body.vat_identification_number,
                _json_dumps(body.registered_address),
                str(body.contact_email) if body.contact_email else None,
                _json_dumps(body.bank_details),
                body.default_currency,
                actor_user_id,
                pricing.now_utc(),
            ),
        ).fetchone()
        profile_id = int(require_row(inserted, "seller profile insert returned no row")["id"])
        row = conn.execute(
            "SELECT * FROM seller_legal_profile_versions WHERE id = %s",
            (profile_id,),
        ).fetchone()
        write_finance_audit_event(
            conn,
            action="seller_profile.create_version",
            target_type="seller_legal_profile_version",
            target_id=str(profile_id),
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            after=payload,
            reason=reason,
        )
    profile = _seller_profile_from_row(require_row(row, "seller profile row missing after insert"))
    if profile is None:
        raise RuntimeError("seller profile row missing after insert")
    return profile


def create_vat_fiscal_settings(
    body: VatFiscalSettingsRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
    reason: str | None = None,
) -> VatFiscalSettingsResponse:
    """Insert a new VAT/fiscal settings version and audit it."""
    payload = body.model_dump(mode="json")
    with get_db() as conn:
        inserted = conn.execute(
            """
            INSERT INTO vat_fiscal_settings_versions (
                effective_date, reviewed, vat_mode, oss_mode,
                default_domestic_vat_treatment, fiscal_document_mode,
                document_rules_json, threshold_warnings_json, tolerance_cents,
                warning_text, created_by_admin_id, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                body.effective_date,
                1 if body.reviewed else 0,
                body.vat_mode,
                body.oss_mode,
                body.default_domestic_vat_treatment,
                body.fiscal_document_mode,
                _json_dumps(body.document_rules),
                _json_dumps(body.threshold_warnings),
                body.tolerance_cents,
                body.warning_text,
                actor_user_id,
                pricing.now_utc(),
            ),
        ).fetchone()
        settings_id = int(require_row(inserted, "VAT settings insert returned no row")["id"])
        row = conn.execute(
            "SELECT * FROM vat_fiscal_settings_versions WHERE id = %s",
            (settings_id,),
        ).fetchone()
        write_finance_audit_event(
            conn,
            action="vat_fiscal_settings.create_version",
            target_type="vat_fiscal_settings_version",
            target_id=str(settings_id),
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            after=payload,
            reason=reason,
        )
    settings = _vat_settings_from_row(require_row(row, "VAT settings row missing after insert"))
    if settings is None:
        raise RuntimeError("VAT settings row missing after insert")
    return settings


def upsert_category_mapping(
    mapping_key: str,
    body: CategoryMappingRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> CategoryMappingResponse:
    """Create or replace one accounting category mapping."""
    key = mapping_key.strip()
    if not key:
        raise ValueError("mapping_key must not be blank")

    with get_db() as conn:
        before_row = conn.execute(
            "SELECT * FROM accounting_category_mappings WHERE mapping_key = %s",
            (key,),
        ).fetchone()
        before = dict(before_row) if before_row is not None else None
        conn.execute(
            """
            INSERT INTO accounting_category_mappings (
                mapping_key, category_code, category_label, is_required, reviewed
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT(mapping_key) DO UPDATE SET
                category_code = excluded.category_code,
                category_label = excluded.category_label,
                is_required = excluded.is_required,
                reviewed = excluded.reviewed,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                key,
                body.category_code,
                body.category_label,
                1 if body.is_required else 0,
                1 if body.reviewed else 0,
            ),
        )
        row = conn.execute(
            "SELECT * FROM accounting_category_mappings WHERE mapping_key = %s",
            (key,),
        ).fetchone()
        row = require_row(row, "category mapping row missing after upsert")
        write_finance_audit_event(
            conn,
            action="category_mapping.upsert",
            target_type="accounting_category_mapping",
            target_id=key,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(row),
        )
    return _category_mapping_from_row(row)


def update_export_schema_settings(
    body: ExportSchemaSettingsRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> ExportSchemaSettingsResponse:
    """Update export schema singleton settings."""
    with get_db() as conn:
        before_row = _ensure_export_schema_row(conn)
        before = dict(before_row)
        conn.execute(
            """
            UPDATE accounting_export_schema_settings
            SET workbook_language = %s, date_format = %s, decimal_separator = %s,
                default_period_range = %s, included_tabs_json = %s, custom_columns_json = %s,
                reviewed = %s, updated_at = %s
            WHERE id = %s
            """,
            (
                body.workbook_language,
                body.date_format,
                body.decimal_separator,
                body.default_period_range,
                _json_dumps(body.included_tabs),
                _json_dumps(body.custom_columns),
                1 if body.reviewed else 0,
                pricing.now_utc(),
                _SETTINGS_ID,
            ),
        )
        row = _ensure_export_schema_row(conn)
        write_finance_audit_event(
            conn,
            action="export_schema_settings.update",
            target_type="accounting_export_schema_settings",
            target_id=_SETTINGS_ID,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(row),
        )
    return _export_schema_from_row(row)


def update_expense_evidence_settings(
    body: ExpenseEvidenceSettingsRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> ExpenseEvidenceSettingsResponse:
    """Update expense evidence singleton settings."""
    with get_db() as conn:
        before_row = _ensure_expense_settings_row(conn)
        before = dict(before_row)
        conn.execute(
            """
            UPDATE expense_evidence_settings
            SET required_document_categories_json = %s, allowed_payment_statuses_json = %s,
                default_category_mappings_json = %s, close_behavior = %s, reviewed = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (
                _json_dumps(body.required_document_categories),
                _json_dumps(body.allowed_payment_statuses),
                _json_dumps(body.default_category_mappings),
                body.close_behavior,
                1 if body.reviewed else 0,
                pricing.now_utc(),
                _SETTINGS_ID,
            ),
        )
        row = _ensure_expense_settings_row(conn)
        write_finance_audit_event(
            conn,
            action="expense_evidence_settings.update",
            target_type="expense_evidence_settings",
            target_id=_SETTINGS_ID,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(row),
        )
    return _expense_settings_from_row(row)


def update_product_cost_settings(
    body: ProductCostSettingsRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> ProductCostSettingsResponse:
    """Update optional product-cost singleton settings."""
    with get_db() as conn:
        before_row = _ensure_product_cost_settings_row(conn)
        before = dict(before_row)
        conn.execute(
            """
            UPDATE product_cost_settings
            SET enabled = %s, costing_basis = %s, include_labor = %s, include_overhead = %s,
                missing_cost_policy = %s, reviewed = %s, estimate_label = %s, updated_at = %s
            WHERE id = %s
            """,
            (
                1 if body.enabled else 0,
                body.costing_basis,
                1 if body.include_labor else 0,
                1 if body.include_overhead else 0,
                body.missing_cost_policy,
                1 if body.reviewed else 0,
                body.estimate_label,
                pricing.now_utc(),
                _SETTINGS_ID,
            ),
        )
        row = _ensure_product_cost_settings_row(conn)
        write_finance_audit_event(
            conn,
            action="product_cost_settings.update",
            target_type="product_cost_settings",
            target_id=_SETTINGS_ID,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(row),
        )
    return _product_cost_settings_from_row(row)


def current_seller_profile_version_id(conn: DbConnection) -> int | None:
    """Return the latest reviewed seller profile version id, if configured."""
    row = conn.execute(
        """
        SELECT id FROM seller_legal_profile_versions
        WHERE reviewed = 1
        ORDER BY effective_date DESC, id DESC
        LIMIT 1
        """
    ).fetchone()
    return int(row["id"]) if row else None


def current_vat_fiscal_settings_version_id(conn: DbConnection) -> int | None:
    """Return the latest reviewed VAT/fiscal settings version id, if configured."""
    row = conn.execute(
        """
        SELECT id FROM vat_fiscal_settings_versions
        WHERE reviewed = 1
        ORDER BY effective_date DESC, id DESC
        LIMIT 1
        """
    ).fetchone()
    return int(row["id"]) if row else None
