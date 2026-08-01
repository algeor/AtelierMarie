"""Stripe balance transaction import and payout reconciliation service."""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import io
import json
import sqlite3
import uuid
from typing import Any

from app.config import get_settings
from app.database import get_db
from app.models.accounting import (
    StripeBalanceImportResponse,
    StripePayoutImportStatusResponse,
    StripePayoutMatchReviewRequest,
)
from app.services import accounting_config_service, pricing
from app.services.finance_period_service import FinancePeriodError


def _json_dumps(value: object | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _json_loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _first(row: dict[str, Any], *keys: str) -> Any:
    normalized = {str(key).strip().casefold(): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(key.casefold())
        if value not in {None, ""}:
            return value
    return None


def _text(row: dict[str, Any], *keys: str) -> str | None:
    value = _first(row, *keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date_text(row: dict[str, Any], *keys: str) -> str | None:
    value = _text(row, *keys)
    if value is None:
        return None
    return value[:19].replace("T", " ")


def _amount_cents(row: dict[str, Any], *keys: str, required: bool = False) -> int | None:
    value = _first(row, *keys)
    if value in {None, ""}:
        if required:
            raise ValueError(f"Missing amount column: one of {', '.join(keys)}")
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip().replace(",", "")
    try:
        if "." in text:
            return int((Decimal(text) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return int(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid amount '{value}'") from exc


def _normalize_import_row(row: dict[str, Any]) -> dict[str, Any]:
    balance_transaction_id = _text(row, "balance_transaction_id", "id", "Balance Transaction ID")
    if not balance_transaction_id:
        raise ValueError("Missing balance_transaction_id")
    gross = _amount_cents(row, "gross_amount_cents", "gross", "amount", required=True)
    fee = _amount_cents(row, "fee_amount_cents", "fee") or 0
    net = _amount_cents(row, "net_amount_cents", "net")
    if net is None:
        net = int(gross or 0) - fee
    currency = (_text(row, "currency") or "EUR").upper()
    return {
        "id": str(uuid.uuid4()),
        "balance_transaction_id": balance_transaction_id,
        "reporting_category": _text(row, "reporting_category", "reporting category"),
        "transaction_type": _text(row, "transaction_type", "type"),
        "provider_created_at": _date_text(row, "provider_created_at", "created", "created_at"),
        "available_on": _date_text(row, "available_on", "available", "available_on_date"),
        "gross_amount_cents": gross,
        "fee_amount_cents": fee,
        "net_amount_cents": net,
        "currency": currency,
        "payment_intent_id": _text(row, "payment_intent_id", "payment_intent"),
        "charge_id": _text(row, "charge_id", "charge"),
        "provider_refund_id": _text(row, "provider_refund_id", "refund_id", "refund"),
        "dispute_id": _text(row, "dispute_id", "dispute"),
        "payout_id": _text(row, "payout_id", "payout"),
        "payout_effective_at": _date_text(row, "payout_effective_at", "payout_effective_date"),
        "payout_arrival_at": _date_text(row, "payout_arrival_at", "payout_arrival_date"),
        "payout_status": _text(row, "payout_status"),
        "trace_id": _text(row, "trace_id", "trace"),
        "raw_row_json": _json_dumps(row),
    }


def _tolerance_cents(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT tolerance_cents FROM vat_fiscal_settings_versions ORDER BY effective_date DESC, id DESC LIMIT 1"
    ).fetchone()
    return int(row["tolerance_cents"] or 0) if row else 1


def _matching_local_amount(conn: sqlite3.Connection, row: sqlite3.Row) -> int | None:
    if row["payment_intent_id"]:
        payment = conn.execute(
            """
            SELECT amount_cents FROM payments
            WHERE provider = 'stripe' AND stripe_payment_intent_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (row["payment_intent_id"],),
        ).fetchone()
        if payment:
            return int(payment["amount_cents"])
    if row["provider_refund_id"]:
        refund = conn.execute(
            """
            SELECT amount_cents FROM payment_refunds
            WHERE provider = 'stripe' AND provider_refund_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (row["provider_refund_id"],),
        ).fetchone()
        if refund:
            return -int(refund["amount_cents"])
    return None


def _reconcile_row(conn: sqlite3.Connection, row_id: str) -> str:
    row = conn.execute("SELECT * FROM stripe_balance_transactions WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        return "unmatched"
    if row["match_status"] in {"duplicate", "ignored"}:
        return row["match_status"]
    local_amount = _matching_local_amount(conn, row)
    if local_amount is None:
        match_status = "unmatched"
    else:
        match_status = (
            "matched"
            if abs(int(row["gross_amount_cents"]) - local_amount) <= _tolerance_cents(conn)
            else "mismatch"
        )
    conn.execute(
        """
        UPDATE stripe_balance_transactions
        SET match_status = ?, status = ?
        WHERE id = ?
        """,
        (match_status, "matched" if match_status == "matched" else "unmatched", row_id),
    )
    return match_status


def import_balance_rows(
    rows: list[dict[str, Any]],
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> StripeBalanceImportResponse:
    """Import normalized or CSV-derived Stripe balance transaction rows."""
    result = StripeBalanceImportResponse()
    seen_provider_ids: set[str] = set()
    changed_row_ids: list[str] = []
    with get_db() as conn:
        for index, raw in enumerate(rows, start=1):
            try:
                item = _normalize_import_row(raw)
            except ValueError as exc:
                result.errors.append(f"row {index}: {exc}")
                continue
            if item["balance_transaction_id"] in seen_provider_ids:
                result.duplicate_provider_ids += 1
                conn.execute(
                    """
                    UPDATE stripe_balance_transactions
                    SET match_status = 'duplicate', status = 'duplicate'
                    WHERE balance_transaction_id = ?
                    """,
                    (item["balance_transaction_id"],),
                )
                continue
            seen_provider_ids.add(str(item["balance_transaction_id"]))
            existing = conn.execute(
                """
                SELECT id FROM stripe_balance_transactions
                WHERE balance_transaction_id = ?
                """,
                (item["balance_transaction_id"],),
            ).fetchone()
            if existing:
                row_id = existing["id"]
                conn.execute(
                    """
                    UPDATE stripe_balance_transactions
                    SET reporting_category = ?, transaction_type = ?, provider_created_at = ?,
                        available_on = ?, gross_amount_cents = ?, fee_amount_cents = ?,
                        net_amount_cents = ?, currency = ?, payment_intent_id = ?, charge_id = ?,
                        provider_refund_id = ?, dispute_id = ?, payout_id = ?,
                        payout_effective_at = ?, payout_arrival_at = ?, payout_status = ?,
                        trace_id = ?, raw_row_json = ?, imported_at = ?
                    WHERE id = ?
                    """,
                    (
                        item["reporting_category"],
                        item["transaction_type"],
                        item["provider_created_at"],
                        item["available_on"],
                        item["gross_amount_cents"],
                        item["fee_amount_cents"],
                        item["net_amount_cents"],
                        item["currency"],
                        item["payment_intent_id"],
                        item["charge_id"],
                        item["provider_refund_id"],
                        item["dispute_id"],
                        item["payout_id"],
                        item["payout_effective_at"],
                        item["payout_arrival_at"],
                        item["payout_status"],
                        item["trace_id"],
                        item["raw_row_json"],
                        pricing.now_utc(),
                        row_id,
                    ),
                )
                result.updated += 1
            else:
                row_id = item["id"]
                conn.execute(
                    """
                    INSERT INTO stripe_balance_transactions (
                        id, balance_transaction_id, reporting_category, transaction_type,
                        provider_created_at, available_on, gross_amount_cents,
                        fee_amount_cents, net_amount_cents, currency, payment_intent_id,
                        charge_id, provider_refund_id, dispute_id, payout_id,
                        payout_effective_at, payout_arrival_at, payout_status, trace_id,
                        raw_row_json, imported_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row_id,
                        item["balance_transaction_id"],
                        item["reporting_category"],
                        item["transaction_type"],
                        item["provider_created_at"],
                        item["available_on"],
                        item["gross_amount_cents"],
                        item["fee_amount_cents"],
                        item["net_amount_cents"],
                        item["currency"],
                        item["payment_intent_id"],
                        item["charge_id"],
                        item["provider_refund_id"],
                        item["dispute_id"],
                        item["payout_id"],
                        item["payout_effective_at"],
                        item["payout_arrival_at"],
                        item["payout_status"],
                        item["trace_id"],
                        item["raw_row_json"],
                        pricing.now_utc(),
                    ),
                )
                result.imported += 1
            changed_row_ids.append(str(row_id))

        for row_id in changed_row_ids:
            status = _reconcile_row(conn, row_id)
            if status == "matched":
                result.matched += 1
            elif status == "mismatch":
                result.mismatched += 1
            elif status == "ignored":
                result.ignored += 1
            elif status == "unmatched":
                result.unmatched += 1

        accounting_config_service.write_finance_audit_event(
            conn,
            action="stripe_balance_transactions.import",
            target_type="stripe_balance_transactions",
            target_id=None,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            after=result.model_dump(mode="json"),
        )
    return result


def import_balance_csv(
    content: bytes,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> StripeBalanceImportResponse:
    """Import Stripe balance transactions from CSV bytes."""
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise FinancePeriodError(422, "INVALID_STRIPE_CSV", "CSV must include a header row.")
    return import_balance_rows(
        list(reader),
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        request_id=request_id,
    )


def sync_from_stripe(
    *,
    limit: int = 100,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> StripeBalanceImportResponse:
    """Sync Stripe balance transactions via the Stripe SDK when configured."""
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise FinancePeriodError(422, "STRIPE_NOT_CONFIGURED", "Stripe secret key is not configured.")
    try:
        import stripe  # type: ignore[import-not-found]
    except ImportError as exc:
        raise FinancePeriodError(503, "STRIPE_SDK_UNAVAILABLE", "Stripe SDK is unavailable.") from exc
    stripe.api_key = settings.stripe_secret_key
    try:
        provider_rows = stripe.BalanceTransaction.list(limit=limit)
    except Exception as exc:  # pragma: no cover - provider-specific exception hierarchy.
        raise FinancePeriodError(502, "STRIPE_SYNC_FAILED", str(exc)) from exc

    rows: list[dict[str, Any]] = []
    for item in getattr(provider_rows, "data", provider_rows):
        getter = item.get if isinstance(item, dict) else lambda key, default=None: getattr(item, key, default)
        source = getter("source")
        rows.append(
            {
                "balance_transaction_id": getter("id"),
                "reporting_category": getter("reporting_category"),
                "transaction_type": getter("type"),
                "provider_created_at": getter("created"),
                "available_on": getter("available_on"),
                "gross_amount_cents": getter("amount"),
                "fee_amount_cents": getter("fee") or 0,
                "net_amount_cents": getter("net"),
                "currency": str(getter("currency") or "EUR").upper(),
                "payment_intent_id": getattr(source, "payment_intent", None) if source else None,
                "charge_id": getattr(source, "id", None) if source else None,
                "provider_refund_id": getattr(source, "refund", None) if source else None,
                "payout_id": getter("payout"),
                "raw": dict(item) if isinstance(item, dict) else str(item),
            }
        )
    return import_balance_rows(
        rows,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        request_id=request_id,
    )


def import_status() -> StripePayoutImportStatusResponse:
    """Return aggregate Stripe import/reconciliation status."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total_rows,
                   SUM(CASE WHEN match_status = 'matched' THEN 1 ELSE 0 END) AS matched,
                   SUM(CASE WHEN match_status = 'unmatched' THEN 1 ELSE 0 END) AS unmatched,
                   SUM(CASE WHEN match_status = 'mismatch' THEN 1 ELSE 0 END) AS mismatched,
                   SUM(CASE WHEN match_status = 'duplicate' THEN 1 ELSE 0 END) AS duplicate,
                   SUM(CASE WHEN match_status = 'ignored' THEN 1 ELSE 0 END) AS ignored,
                   MAX(imported_at) AS latest_imported_at
            FROM stripe_balance_transactions
            """
        ).fetchone()
    return StripePayoutImportStatusResponse(
        total_rows=int(row["total_rows"] or 0),
        matched=int(row["matched"] or 0),
        unmatched=int(row["unmatched"] or 0),
        mismatched=int(row["mismatched"] or 0),
        duplicate=int(row["duplicate"] or 0),
        ignored=int(row["ignored"] or 0),
        latest_imported_at=row["latest_imported_at"],
    )


def review_match(
    balance_transaction_id: str,
    body: StripePayoutMatchReviewRequest,
    *,
    actor_user_id: str | None = None,
    actor_email: str | None = None,
    request_id: str | None = None,
) -> dict[str, object]:
    """Manually set the match status for a Stripe balance transaction."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM stripe_balance_transactions
            WHERE balance_transaction_id = ? OR id = ?
            """,
            (balance_transaction_id, balance_transaction_id),
        ).fetchone()
        if row is None:
            raise FinancePeriodError(
                404,
                "STRIPE_BALANCE_TRANSACTION_NOT_FOUND",
                "Stripe balance transaction not found.",
            )
        before = dict(row)
        raw = _json_loads(row["raw_row_json"], {})
        if not isinstance(raw, dict):
            raw = {"raw": raw}
        raw["manual_review"] = {
            "match_status": body.match_status,
            "reason": body.reason,
            "reviewed_by_admin_id": actor_user_id,
            "reviewed_at": pricing.now_utc(),
        }
        conn.execute(
            """
            UPDATE stripe_balance_transactions
            SET match_status = ?, status = ?, raw_row_json = ?
            WHERE id = ?
            """,
            (
                body.match_status,
                body.match_status
                if body.match_status in {"matched", "duplicate", "ignored"}
                else "unmatched",
                _json_dumps(raw),
                row["id"],
            ),
        )
        updated = conn.execute(
            "SELECT * FROM stripe_balance_transactions WHERE id = ?", (row["id"],)
        ).fetchone()
        accounting_config_service.write_finance_audit_event(
            conn,
            action="stripe_balance_transaction.review_match",
            target_type="stripe_balance_transaction",
            target_id=row["id"],
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            request_id=request_id,
            before=before,
            after=dict(updated),
            reason=body.reason,
        )
        return {key: updated[key] for key in updated.keys()}
