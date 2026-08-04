"""Tests for database layer — schema constraints and utility functions."""

from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest

from app.database import IntegrityError, cleanup_expired_sessions, get_db


@pytest.fixture(autouse=True)
def _pool(app):
    """Ensure the psycopg pool is initialized (app fixture opens it)."""
    return app


class TestCleanupExpiredSessions:
    """Verify cleanup_expired_sessions() deletes only expired rows."""

    @pytest.fixture(autouse=True)
    def _clear_all_sessions(self):
        """Remove all pre-existing sessions so tests start from a clean slate."""
        with get_db() as conn:
            conn.execute("DELETE FROM sessions")
        yield

    def test_removes_expired_sessions(self):
        expired_at = datetime.now(UTC) - timedelta(days=1)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO sessions (id, expires_at) VALUES (%s, %s)",
                ("expired-1", expired_at),
            )

        count = cleanup_expired_sessions()

        assert count == 1
        with get_db() as conn:
            row = conn.execute("SELECT id FROM sessions WHERE id = %s", ("expired-1",)).fetchone()
        assert row is None

    def test_keeps_active_sessions(self):
        active_at = datetime.now(UTC) + timedelta(days=1)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO sessions (id, expires_at) VALUES (%s, %s)",
                ("active-1", active_at),
            )

        count = cleanup_expired_sessions()

        assert count == 0
        with get_db() as conn:
            row = conn.execute("SELECT id FROM sessions WHERE id = %s", ("active-1",)).fetchone()
        assert row is not None

    def test_mixed_expired_and_active(self):
        expired_at = datetime.now(UTC) - timedelta(hours=1)
        active_at = datetime.now(UTC) + timedelta(hours=1)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO sessions (id, expires_at) VALUES (%s, %s)",
                ("expired-a", expired_at),
            )
            conn.execute(
                "INSERT INTO sessions (id, expires_at) VALUES (%s, %s)",
                ("active-a", active_at),
            )

        count = cleanup_expired_sessions()

        assert count == 1
        with get_db() as conn:
            rows = conn.execute("SELECT id FROM sessions ORDER BY id").fetchall()
        assert len(rows) == 1
        assert rows[0]["id"] == "active-a"

    def test_returns_zero_when_no_sessions(self):
        count = cleanup_expired_sessions()
        assert count == 0


class TestProductImagesSchema:
    def test_fresh_db_has_zoom_url_column(self):
        with get_db() as conn:
            rows = conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'product_images'"
            ).fetchall()
        columns = {row["column_name"] for row in rows}
        assert "zoom_url" in columns


class TestDatabaseConstraints:
    """Verify CHECK constraints enforce data integrity at the DB level."""

    def test_product_price_zero_rejected(self):
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock)"
                " VALUES ('test', 'Test', 0, 5)"
            )

    def test_product_price_negative_rejected(self):
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) "
                "VALUES ('test', 'Test', -100, 5)"
            )

    def test_product_negative_stock_rejected(self):
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) "
                "VALUES ('test', 'Test', 1000, -1)"
            )

    def test_product_zero_stock_allowed(self):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock)"
                " VALUES ('test', 'Test', 1000, 0)"
            )
            row = conn.execute("SELECT stock FROM products WHERE id = 'test'").fetchone()
        assert row["stock"] == 0

    def test_order_invalid_status_rejected(self):
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO orders (id, session_id, status, total_cents, customer_email) "
                "VALUES ('o1', 's1', 'invalid_status', 100, 'test@example.com')"
            )

    def test_order_valid_statuses_accepted(self):
        valid_statuses = (
            "pending",
            "confirmed",
            "shipped",
            "delivered",
            "return_in_transit",
            "returned",
            "cancelled",
        )
        with get_db() as conn:
            for i, status in enumerate(valid_statuses):
                conn.execute(
                    "INSERT INTO orders (id, session_id, status, total_cents, customer_email) "
                    "VALUES (%s, 's1', %s, 100, 'test@example.com')",
                    (f"order-{i}", status),
                )
            rows = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()
        assert rows["n"] == len(valid_statuses)

    def test_order_new_payment_statuses_accepted(self):
        valid_payment_statuses = (
            "pending",
            "paid",
            "cod_pending",
            "failed",
            "review_required",
            "refund_pending",
            "partially_refunded",
            "refunded",
            "dispute_open",
            "dispute_won",
            "dispute_lost",
        )
        with get_db() as conn:
            for i, payment_status in enumerate(valid_payment_statuses):
                conn.execute(
                    """
                    INSERT INTO orders (
                        id, session_id, status, total_cents, customer_email,
                        payment_method, payment_status
                    ) VALUES (%s, 's1', 'pending', 100, 'test@example.com', 'card', %s)
                    """,
                    (f"payment-order-{i}", payment_status),
                )
            rows = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()
        assert rows["n"] == len(valid_payment_statuses)

    def test_order_invalid_payment_status_rejected(self):
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO orders (
                    id, session_id, status, total_cents, customer_email,
                    payment_method, payment_status
                ) VALUES ('bad-payment', 's1', 'pending', 100, 'test@example.com', 'card', 'bogus')
                """
            )

    def test_contact_message_invalid_status_rejected(self):
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO contact_messages (name, email, message, locale, email_status)
                VALUES ('Mira', 'mira@example.com', 'Hello', 'en', 'unknown')
                """
            )

    def test_contact_message_oversized_name_rejected(self):
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO contact_messages (name, email, message, locale)
                VALUES (%s, 'mira@example.com', 'Hello', 'en')
                """,
                ("x" * 101,),
            )

    def test_contact_message_invalid_locale_rejected(self):
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO contact_messages (name, email, message, locale)
                VALUES ('Mira', 'mira@example.com', 'Hello', 'fr')
                """
            )

    def test_cart_items_cascade_on_session_delete(self):
        """Deleting a session cascades to its cart items."""
        expires = datetime.now(UTC) + timedelta(days=1)
        with get_db() as conn:
            conn.execute("INSERT INTO sessions (id, expires_at) VALUES ('s1', %s)", (expires,))
            conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) "
                "VALUES ('prod-1', 'Test Product', 1000, 10)"
            )
            conn.execute(
                "INSERT INTO cart_items (session_id, product_id, quantity) "
                "VALUES ('s1', 'prod-1', 2)"
            )
            # Delete the session
            conn.execute("DELETE FROM sessions WHERE id = 's1'")
            # Cart items should be gone (CASCADE)
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM cart_items WHERE session_id = 's1'"
            ).fetchone()
        assert row["n"] == 0


class TestReturnRefundSettlementSchema:
    """Return/refund/accounting tables enforce the operational vocabulary."""

    @staticmethod
    def _insert_order(conn, order_id: str = "order-returns-1") -> str:
        conn.execute(
            """
            INSERT INTO orders (
                id, session_id, status, total_cents, customer_email,
                payment_method, payment_status
            ) VALUES (%s, 'session-returns', 'shipped', 5000,
                      'returns@example.com', 'card', 'paid')
            """,
            (order_id,),
        )
        return order_id

    def test_return_case_accepts_expected_fields(self):
        with get_db() as conn:
            order_id = self._insert_order(conn)
            conn.execute(
                """
                INSERT INTO order_returns (
                    id, order_id, reason, source, status, refund_amount_cents,
                    courier_return_fee_cents, courier_claim_id, courier_claim_status,
                    courier_claim_amount_cents, restock_decision, notes,
                    created_by_admin_id
                ) VALUES ('ret-1', %s, 'damaged_by_courier', 'admin', 'return_in_transit',
                          4200, 600, 'CLM-123', 'filed', 1500, 'pending',
                          'Box crushed by courier', 'admin-1')
                """,
                (order_id,),
            )
            row = conn.execute(
                "SELECT reason, courier_claim_id, courier_claim_status FROM order_returns"
            ).fetchone()
        assert row["reason"] == "damaged_by_courier"
        assert row["courier_claim_id"] == "CLM-123"
        assert row["courier_claim_status"] == "filed"

    def test_return_case_invalid_reason_rejected(self):
        with get_db() as conn:
            order_id = self._insert_order(conn)
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                "INSERT INTO order_returns (id, order_id, reason) "
                "VALUES ('ret-bad', %s, 'exchange')",
                (order_id,),
            )

    def test_return_case_negative_courier_fee_rejected(self):
        with get_db() as conn:
            order_id = self._insert_order(conn)
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO order_returns (
                    id, order_id, reason, courier_return_fee_cents
                ) VALUES ('ret-fee', %s, 'not_picked_up', -1)
                """,
                (order_id,),
            )

    def test_return_event_cascades_with_return_case(self):
        with get_db() as conn:
            order_id = self._insert_order(conn)
            conn.execute(
                "INSERT INTO order_returns (id, order_id, reason) "
                "VALUES ('ret-cascade', %s, 'other')",
                (order_id,),
            )
            conn.execute(
                """
                INSERT INTO order_return_events (
                    id, order_return_id, order_id, event_type, source, payload_json
                ) VALUES ('ret-event-1', 'ret-cascade', %s, 'created', 'admin', '{"ok":true}')
                """,
                (order_id,),
            )
            conn.execute("DELETE FROM order_returns WHERE id = 'ret-cascade'")
            row = conn.execute("SELECT COUNT(*) AS n FROM order_return_events").fetchone()
        assert row["n"] == 0

    def test_payment_refund_requires_positive_amount(self):
        with get_db() as conn:
            order_id = self._insert_order(conn)
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO payment_refunds (id, order_id, provider, amount_cents)
                VALUES ('refund-zero', %s, 'stripe', 0)
                """,
                (order_id,),
            )

    def test_payment_refund_idempotency_key_is_unique_per_provider(self):
        with get_db() as conn:
            order_id = self._insert_order(conn)
            conn.execute(
                """
                INSERT INTO payment_refunds (
                    id, order_id, provider, amount_cents, idempotency_key
                ) VALUES ('refund-1', %s, 'stripe', 1000, 'same-key')
                """,
                (order_id,),
            )
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO payment_refunds (
                    id, order_id, provider, amount_cents, idempotency_key
                ) VALUES ('refund-2', %s, 'stripe', 1000, 'same-key')
                """,
                (order_id,),
            )

    def test_cod_settlement_flags_mismatch_and_is_one_per_order(self):
        with get_db() as conn:
            order_id = self._insert_order(conn)
            conn.execute(
                """
                INSERT INTO cod_settlements (
                    id, order_id, amount_cents, settlement_date, courier_reference,
                    mismatch_review
                ) VALUES ('cod-settlement-1', %s, 4800, '2026-08-01', 'ECONT-PAYOUT-1', 1)
                """,
                (order_id,),
            )
            row = conn.execute(
                "SELECT amount_cents, mismatch_review FROM cod_settlements WHERE order_id = %s",
                (order_id,),
            ).fetchone()
        assert row["amount_cents"] == 4800
        assert row["mismatch_review"] == 1
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO cod_settlements (id, order_id, amount_cents, settlement_date)
                VALUES ('cod-settlement-2', %s, 4800, '2026-08-02')
                """,
                (order_id,),
            )


class TestAccountingFinanceHubSchema:
    """Accounting & Finance Hub tables enforce the core evidence model."""

    def test_fresh_db_has_finance_tables_and_order_snapshot_columns(self):
        expected_tables = {
            "finance_periods",
            "finance_audit_events",
            "seller_legal_profile_versions",
            "vat_fiscal_settings_versions",
            "accounting_category_mappings",
            "accounting_export_schema_settings",
            "expense_evidence_settings",
            "product_cost_settings",
            "accounting_documents",
            "stripe_balance_transactions",
            "finance_export_packages",
            "expense_evidence",
            "product_cost_versions",
            "product_cost_components",
            "finance_exceptions",
        }
        with get_db() as conn:
            table_rows = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ).fetchall()
            tables = {row["table_name"] for row in table_rows}
            assert expected_tables.issubset(tables)

            col_rows = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'orders'"
            ).fetchall()
        order_columns = {row["column_name"] for row in col_rows}
        assert {
            "invoice_profile_json",
            "accounting_currency",
            "seller_legal_profile_version_id",
            "vat_fiscal_settings_version_id",
            "accounting_classification_state",
            "accounting_snapshot_json",
            "accounting_readiness_status",
            "finance_period_id",
        }.issubset(order_columns)

    def test_order_accounting_snapshot_defaults(self):
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO orders (id, session_id, status, total_cents, customer_email)
                VALUES ('acct-order-defaults', 'acct-session', 'pending', 1000, 'acct@example.com')
                """
            )
            row = conn.execute(
                """
                SELECT accounting_currency, accounting_classification_state,
                       accounting_readiness_status
                FROM orders WHERE id = 'acct-order-defaults'
                """
            ).fetchone()
        assert row["accounting_currency"] == "EUR"
        assert row["accounting_classification_state"] == "unreviewed"
        assert row["accounting_readiness_status"] == "unreviewed"

    def test_finance_period_status_and_dates_are_constrained(self):
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO finance_periods (id, period_start, period_end, currency, status)
                VALUES ('period-2026-08', '2026-08-01', '2026-08-31', 'EUR', 'open')
                """
            )
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO finance_periods (id, period_start, period_end, status)
                VALUES ('period-bad-status', '2026-08-01', '2026-08-31', 'draft')
                """
            )
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO finance_periods (id, period_start, period_end)
                VALUES ('period-bad-dates', '2026-09-01', '2026-08-31')
                """
            )

    def test_accounting_document_and_credit_note_reference_shape(self):
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO accounting_documents (
                    id, document_type, document_number, issue_date, gross_amount_cents
                ) VALUES ('doc-invoice-1', 'invoice', 'INV-1', '2026-08-03', 2400)
                """
            )
            conn.execute(
                """
                INSERT INTO accounting_documents (
                    id, document_type, document_number, issue_date,
                    gross_amount_cents, original_document_id
                ) VALUES ('doc-credit-1', 'credit_note', 'CN-1', '2026-08-04', 1200,
                          'doc-invoice-1')
                """
            )
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO accounting_documents (
                    id, document_type, issue_date, gross_amount_cents
                ) VALUES ('doc-bad-type', 'receiptish', '2026-08-03', 2400)
                """
            )

    def test_stripe_balance_transaction_provider_id_is_unique(self):
        for row_id in ("stripe-btxn-1", "stripe-btxn-2"):
            ctx = pytest.raises(IntegrityError) if row_id.endswith("2") else nullcontext()
            with ctx, get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO stripe_balance_transactions (
                        id, balance_transaction_id, gross_amount_cents,
                        fee_amount_cents, net_amount_cents, currency
                    ) VALUES (%s, 'txn_same', 1000, 50, 950, 'EUR')
                    """,
                    (row_id,),
                )

    def test_expense_and_product_cost_constraints(self):
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO products (id, name_en, price_cents, stock)
                VALUES ('costed-candle', 'Costed Candle', 3000, 5)
                """
            )
            conn.execute(
                """
                INSERT INTO expense_evidence (
                    id, supplier_name, purchase_date, payment_status, category_key,
                    gross_amount_cents, tax_amount_cents, linked_product_id
                ) VALUES ('expense-1', 'Wax Supplier', '2026-08-02', 'unpaid',
                          'materials', 12000, 2000, 'costed-candle')
                """
            )
            conn.execute(
                """
                INSERT INTO product_cost_versions (
                    id, product_id, product_name, effective_date, costing_basis,
                    material_cost_cents, packaging_cost_cents, estimated_unit_cost_cents
                ) VALUES ('cost-version-1', 'costed-candle', 'Costed Candle',
                          '2026-08-01', 'recipe_bom', 400, 150, 550)
                """
            )
            conn.execute(
                """
                INSERT INTO product_cost_components (
                    id, cost_version_id, component_type, description, quantity, unit,
                    unit_cost_cents, total_cost_cents, source_expense_id
                ) VALUES ('cost-component-1', 'cost-version-1', 'material', 'Wax',
                          0.18, 'kg', 2000, 360, 'expense-1')
                """
            )

        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO expense_evidence (
                    id, supplier_name, purchase_date, payment_status, gross_amount_cents
                ) VALUES ('expense-bad-status', 'Supplier', '2026-08-02', 'waiting', 100)
                """
            )
        with pytest.raises(IntegrityError), get_db() as conn:
            conn.execute(
                """
                INSERT INTO product_cost_versions (
                    id, product_name, effective_date, costing_basis,
                    estimated_unit_cost_cents
                ) VALUES ('cost-version-bad', 'Bad', '2026-08-01', 'fifo', 100)
                """
            )
