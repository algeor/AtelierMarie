"""Stripe payout reconciliation import and review tests."""

import psycopg
import pytest

from conftest import FAKE_SESSION_ID


def _seed_reviewed_settings(db: psycopg.Connection) -> tuple[int, int]:
    seller_id = int(
        db.execute(
            """
            INSERT INTO seller_legal_profile_versions (
                effective_date, reviewed, legal_name, default_currency
            ) VALUES ('2026-08-01', 1, 'Atelier Marie OOD', 'EUR')
            RETURNING id
            """
        ).fetchone()["id"]
    )
    vat_id = int(
        db.execute(
            """
            INSERT INTO vat_fiscal_settings_versions (
                effective_date, reviewed, vat_mode, fiscal_document_mode, tolerance_cents
            ) VALUES ('2026-08-01', 1, 'registered', 'external_reference', 1)
            RETURNING id
            """
        ).fetchone()["id"]
    )
    db.commit()
    return seller_id, vat_id


def _seed_paid_card_order(
    db: psycopg.Connection,
    app,
    *,
    order_id: str,
    payment_id: str,
    payment_intent_id: str,
    amount_cents: int,
    seller_id: int,
    vat_id: int,
) -> None:
    db.execute(
        "INSERT INTO products (id, name_en, price_cents, stock) "
        "VALUES ('stripe-candle', 'Stripe Candle', 1000, 10) ON CONFLICT (id) DO NOTHING"
    )
    db.execute(
        """
        INSERT INTO orders (
            id, session_id, status, total_cents, customer_email, customer_name,
            payment_method, payment_status, stripe_payment_intent_id,
            seller_legal_profile_version_id, vat_fiscal_settings_version_id,
            accounting_classification_state, accounting_readiness_status,
            created_at, updated_at
        ) VALUES (%s, %s, 'confirmed', %s, %s, 'Stripe Buyer', 'card', 'paid', %s, %s, %s,
                  'domestic_default', 'ready', '2026-08-10 10:00:00',
                  '2026-08-10 10:00:00')
        """,
        (
            order_id,
            FAKE_SESSION_ID,
            amount_cents,
            f"{order_id}@example.com",
            payment_intent_id,
            seller_id,
            vat_id,
        ),
    )
    db.execute(
        """
        INSERT INTO order_items (
            order_id, product_id, product_name, price_cents,
            quantity, allocated_quantity, backordered_quantity
        )
        VALUES (%s, 'stripe-candle', 'Stripe Candle', %s, 1, 1, 0)
        """,
        (order_id, amount_cents),
    )
    db.execute(
        """
        INSERT INTO payments (
            id, order_id, provider, amount_cents, currency, stripe_payment_intent_id,
            provider_status, created_at, updated_at
        ) VALUES (%s, %s, 'stripe', %s, 'EUR', %s, 'paid', '2026-08-10 10:01:00',
                  '2026-08-10 10:01:00')
        """,
        (payment_id, order_id, amount_cents, payment_intent_id),
    )
    db.commit()


@pytest.mark.asyncio
async def test_stripe_manual_csv_import_matches_and_flags_exceptions(admin_client, db, app):
    seller_id, vat_id = _seed_reviewed_settings(db)
    _seed_paid_card_order(
        db,
        app,
        order_id="stripe-match-order",
        payment_id="payment-match",
        payment_intent_id="pi_match",
        amount_cents=1000,
        seller_id=seller_id,
        vat_id=vat_id,
    )
    _seed_paid_card_order(
        db,
        app,
        order_id="stripe-mismatch-order",
        payment_id="payment-mismatch",
        payment_intent_id="pi_mismatch",
        amount_cents=1000,
        seller_id=seller_id,
        vat_id=vat_id,
    )
    db.execute(
        """
        INSERT INTO payment_refunds (
            id, order_id, payment_id, provider, provider_refund_id, amount_cents,
            status, created_at, confirmed_at
        ) VALUES ('refund-match', 'stripe-match-order', 'payment-match', 'stripe',
                  're_match', 300, 'succeeded', '2026-08-11 10:00:00',
                  '2026-08-11 11:00:00')
        """
    )
    db.commit()

    csv_content = "\n".join(
        [
            "balance_transaction_id,provider_created_at,gross_amount_cents,fee_amount_cents,net_amount_cents,currency,payment_intent_id,provider_refund_id,dispute_id,payout_id,payout_status",
            "txn_match,2026-08-10 10:02:00,1000,50,950,EUR,pi_match,,,po_1,paid",
            "txn_mismatch,2026-08-10 10:03:00,1200,50,1150,EUR,pi_mismatch,,,po_1,paid",
            "txn_refund,2026-08-11 11:01:00,-300,0,-300,EUR,,re_match,,po_1,paid",
            "txn_unmatched,2026-08-12 10:00:00,500,25,475,EUR,,,,po_1,paid",
            "txn_duplicate,2026-08-12 10:01:00,700,35,665,EUR,,,,po_1,paid",
            "txn_duplicate,2026-08-12 10:02:00,700,35,665,EUR,,,,po_1,paid",
            "txn_dispute,2026-08-13 10:00:00,-100,0,-100,EUR,,,dp_1,po_1,paid",
            "txn_payout_failed,2026-08-14 10:00:00,0,0,0,EUR,,,,po_failed,failed",
        ]
    )
    import_resp = await admin_client.post(
        "/v1/admin/accounting/stripe/manual-import",
        files={"file": ("stripe.csv", csv_content, "text/csv")},
    )
    assert import_resp.status_code == 200
    body = import_resp.json()
    assert body["imported"] == 7
    assert body["duplicate_provider_ids"] == 1
    assert body["matched"] == 2
    assert body["mismatched"] == 1
    assert body["unmatched"] == 3
    assert body["errors"] == []

    status_resp = await admin_client.get("/v1/admin/accounting/stripe/import-status")
    assert status_resp.status_code == 200
    status = status_resp.json()
    assert status["total_rows"] == 7
    assert status["matched"] == 2
    assert status["mismatched"] == 1
    assert status["duplicate"] == 1

    review_resp = await admin_client.post(
        "/v1/admin/accounting/stripe/matches/txn_unmatched/review",
        json={"match_status": "ignored", "reason": "Provider test row ignored."},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["match_status"] == "ignored"

    period_resp = await admin_client.post(
        "/v1/admin/accounting/periods",
        json={"period_start": "2026-08-01", "period_end": "2026-08-31", "currency": "EUR"},
    )
    period_id = period_resp.json()["id"]
    await admin_client.post(f"/v1/admin/accounting/periods/{period_id}/review")
    exceptions_resp = await admin_client.get(
        f"/v1/admin/accounting/periods/{period_id}/exceptions?status=open"
    )
    exception_types = {item["exception_type"] for item in exceptions_resp.json()["items"]}
    assert {
        "stripe_payout_mismatch",
        "stripe_payout_duplicate",
        "stripe_payout_unmatched",
    }.issubset(exception_types)

    audit_actions = {
        row["action"] for row in db.execute("SELECT action FROM finance_audit_events").fetchall()
    }
    assert "stripe_balance_transactions.import" in audit_actions
    assert "stripe_balance_transaction.review_match" in audit_actions
