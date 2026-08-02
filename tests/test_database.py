"""Tests for database layer — schema constraints and utility functions."""

import sqlite3
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta

import pytest

from app.database import cleanup_expired_sessions, init_db

# SQLite-compatible datetime format (matches middleware's _SQLITE_DT_FMT)
_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.fixture()
def db_conn(db_path: str) -> sqlite3.Connection:
    """Yield a raw connection to the test DB."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    yield conn
    conn.close()


class TestCleanupExpiredSessions:
    """Verify cleanup_expired_sessions() deletes only expired rows."""

    @pytest.fixture(autouse=True)
    def _clear_all_sessions(self, db_conn):
        """Remove all pre-existing sessions so tests start from a clean slate."""
        db_conn.execute("DELETE FROM sessions")
        db_conn.commit()
        yield

    def test_removes_expired_sessions(self, db_conn: sqlite3.Connection):
        expired_at = (datetime.now(UTC) - timedelta(days=1)).strftime(_DT_FMT)
        db_conn.execute(
            "INSERT INTO sessions (id, expires_at) VALUES (?, ?)",
            ("expired-1", expired_at),
        )
        db_conn.commit()

        count = cleanup_expired_sessions()

        assert count == 1
        row = db_conn.execute("SELECT id FROM sessions WHERE id = ?", ("expired-1",)).fetchone()
        assert row is None

    def test_keeps_active_sessions(self, db_conn: sqlite3.Connection):
        active_at = (datetime.now(UTC) + timedelta(days=1)).strftime(_DT_FMT)
        db_conn.execute(
            "INSERT INTO sessions (id, expires_at) VALUES (?, ?)",
            ("active-1", active_at),
        )
        db_conn.commit()

        count = cleanup_expired_sessions()

        assert count == 0
        row = db_conn.execute("SELECT id FROM sessions WHERE id = ?", ("active-1",)).fetchone()
        assert row is not None

    def test_mixed_expired_and_active(self, db_conn: sqlite3.Connection):
        expired_at = (datetime.now(UTC) - timedelta(hours=1)).strftime(_DT_FMT)
        active_at = (datetime.now(UTC) + timedelta(hours=1)).strftime(_DT_FMT)
        db_conn.execute(
            "INSERT INTO sessions (id, expires_at) VALUES (?, ?)",
            ("expired-a", expired_at),
        )
        db_conn.execute(
            "INSERT INTO sessions (id, expires_at) VALUES (?, ?)",
            ("active-a", active_at),
        )
        db_conn.commit()

        count = cleanup_expired_sessions()

        assert count == 1
        rows = db_conn.execute("SELECT id FROM sessions ORDER BY id").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "active-a"

    def test_returns_zero_when_no_sessions(self, db_conn: sqlite3.Connection):
        count = cleanup_expired_sessions()
        assert count == 0


class TestProductImagesSchema:
    def test_fresh_db_has_zoom_url_column(self, db_conn: sqlite3.Connection):
        columns = {row[1] for row in db_conn.execute("PRAGMA table_info(product_images)")}

        assert "zoom_url" in columns


class TestDatabaseConstraints:
    """Verify CHECK constraints enforce data integrity at the DB level."""

    def test_product_price_zero_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock)"
                " VALUES ('test', 'Test', 0, 5)"
            )

    def test_product_price_negative_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) "
                "VALUES ('test', 'Test', -100, 5)"
            )

    def test_product_negative_stock_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO products (id, name_en, price_cents, stock) "
                "VALUES ('test', 'Test', 1000, -1)"
            )

    def test_product_zero_stock_allowed(self, db_conn: sqlite3.Connection):
        db_conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock)"
            " VALUES ('test', 'Test', 1000, 0)"
        )
        db_conn.commit()
        row = db_conn.execute("SELECT stock FROM products WHERE id = 'test'").fetchone()
        assert row[0] == 0

    def test_order_invalid_status_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO orders (id, session_id, status, total_cents, customer_email) "
                "VALUES ('o1', 's1', 'invalid_status', 100, 'test@example.com')"
            )

    def test_order_valid_statuses_accepted(self, db_conn: sqlite3.Connection):
        valid_statuses = (
            "pending",
            "confirmed",
            "shipped",
            "delivered",
            "return_in_transit",
            "returned",
            "cancelled",
        )
        for i, status in enumerate(valid_statuses):
            db_conn.execute(
                "INSERT INTO orders (id, session_id, status, total_cents, customer_email) "
                "VALUES (?, 's1', ?, 100, 'test@example.com')",
                (f"order-{i}", status),
            )
        db_conn.commit()
        rows = db_conn.execute("SELECT COUNT(*) FROM orders").fetchone()
        assert rows[0] == len(valid_statuses)

    def test_order_new_payment_statuses_accepted(self, db_conn: sqlite3.Connection):
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
        for i, payment_status in enumerate(valid_payment_statuses):
            db_conn.execute(
                """
                INSERT INTO orders (
                    id, session_id, status, total_cents, customer_email,
                    payment_method, payment_status
                ) VALUES (?, 's1', 'pending', 100, 'test@example.com', 'card', ?)
                """,
                (f"payment-order-{i}", payment_status),
            )
        db_conn.commit()
        rows = db_conn.execute("SELECT COUNT(*) FROM orders").fetchone()
        assert rows[0] == len(valid_payment_statuses)

    def test_order_invalid_payment_status_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO orders (
                    id, session_id, status, total_cents, customer_email,
                    payment_method, payment_status
                ) VALUES ('bad-payment', 's1', 'pending', 100, 'test@example.com', 'card', 'bogus')
                """
            )

    def test_contact_message_invalid_status_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO contact_messages (name, email, message, locale, email_status)
                VALUES ('Mira', 'mira@example.com', 'Hello', 'en', 'unknown')
                """
            )

    def test_contact_message_oversized_name_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO contact_messages (name, email, message, locale)
                VALUES (?, 'mira@example.com', 'Hello', 'en')
                """,
                ("x" * 101,),
            )

    def test_contact_message_invalid_locale_rejected(self, db_conn: sqlite3.Connection):
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO contact_messages (name, email, message, locale)
                VALUES ('Mira', 'mira@example.com', 'Hello', 'fr')
                """
            )

    def test_cart_items_cascade_on_session_delete(self, db_conn: sqlite3.Connection):
        """Deleting a session cascades to its cart items."""
        # Insert a session and a product
        expires = (datetime.now(UTC) + timedelta(days=1)).strftime(_DT_FMT)
        db_conn.execute("INSERT INTO sessions (id, expires_at) VALUES ('s1', ?)", (expires,))
        db_conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock) "
            "VALUES ('prod-1', 'Test Product', 1000, 10)"
        )
        db_conn.execute(
            "INSERT INTO cart_items (session_id, product_id, quantity) VALUES ('s1', 'prod-1', 2)"
        )
        db_conn.commit()

        # Delete the session
        db_conn.execute("DELETE FROM sessions WHERE id = 's1'")
        db_conn.commit()

        # Cart items should be gone (CASCADE)
        row = db_conn.execute("SELECT COUNT(*) FROM cart_items WHERE session_id = 's1'").fetchone()
        assert row[0] == 0


class TestReturnRefundSettlementSchema:
    """Return/refund/accounting tables enforce the operational vocabulary."""

    @staticmethod
    def _insert_order(conn: sqlite3.Connection, order_id: str = "order-returns-1") -> str:
        conn.execute(
            """
            INSERT INTO orders (
                id, session_id, status, total_cents, customer_email,
                payment_method, payment_status
            ) VALUES (?, 'session-returns', 'shipped', 5000,
                      'returns@example.com', 'card', 'paid')
            """,
            (order_id,),
        )
        return order_id

    def test_return_case_accepts_expected_fields(self, db_conn: sqlite3.Connection):
        order_id = self._insert_order(db_conn)
        db_conn.execute(
            """
            INSERT INTO order_returns (
                id, order_id, reason, source, status, refund_amount_cents,
                courier_return_fee_cents, courier_claim_id, courier_claim_status,
                courier_claim_amount_cents, restock_decision, notes,
                created_by_admin_id
            ) VALUES ('ret-1', ?, 'damaged_by_courier', 'admin', 'return_in_transit',
                      4200, 600, 'CLM-123', 'filed', 1500, 'pending',
                      'Box crushed by courier', 'admin-1')
            """,
            (order_id,),
        )
        row = db_conn.execute(
            "SELECT reason, courier_claim_id, courier_claim_status FROM order_returns"
        ).fetchone()
        assert row == ("damaged_by_courier", "CLM-123", "filed")

    def test_return_case_invalid_reason_rejected(self, db_conn: sqlite3.Connection):
        order_id = self._insert_order(db_conn)
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO order_returns (id, order_id, reason) "
                "VALUES ('ret-bad', ?, 'exchange')",
                (order_id,),
            )

    def test_return_case_negative_courier_fee_rejected(self, db_conn: sqlite3.Connection):
        order_id = self._insert_order(db_conn)
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO order_returns (
                    id, order_id, reason, courier_return_fee_cents
                ) VALUES ('ret-fee', ?, 'not_picked_up', -1)
                """,
                (order_id,),
            )

    def test_return_event_cascades_with_return_case(self, db_conn: sqlite3.Connection):
        order_id = self._insert_order(db_conn)
        db_conn.execute(
            "INSERT INTO order_returns (id, order_id, reason) VALUES ('ret-cascade', ?, 'other')",
            (order_id,),
        )
        db_conn.execute(
            """
            INSERT INTO order_return_events (
                id, order_return_id, order_id, event_type, source, payload_json
            ) VALUES ('ret-event-1', 'ret-cascade', ?, 'created', 'admin', '{"ok":true}')
            """,
            (order_id,),
        )
        db_conn.commit()

        db_conn.execute("DELETE FROM order_returns WHERE id = 'ret-cascade'")
        db_conn.commit()

        count = db_conn.execute("SELECT COUNT(*) FROM order_return_events").fetchone()[0]
        assert count == 0

    def test_payment_refund_requires_positive_amount(self, db_conn: sqlite3.Connection):
        order_id = self._insert_order(db_conn)
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO payment_refunds (id, order_id, provider, amount_cents)
                VALUES ('refund-zero', ?, 'stripe', 0)
                """,
                (order_id,),
            )

    def test_payment_refund_idempotency_key_is_unique_per_provider(
        self, db_conn: sqlite3.Connection
    ):
        order_id = self._insert_order(db_conn)
        db_conn.execute(
            """
            INSERT INTO payment_refunds (
                id, order_id, provider, amount_cents, idempotency_key
            ) VALUES ('refund-1', ?, 'stripe', 1000, 'same-key')
            """,
            (order_id,),
        )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO payment_refunds (
                    id, order_id, provider, amount_cents, idempotency_key
                ) VALUES ('refund-2', ?, 'stripe', 1000, 'same-key')
                """,
                (order_id,),
            )

    def test_cod_settlement_flags_mismatch_and_is_one_per_order(self, db_conn: sqlite3.Connection):
        order_id = self._insert_order(db_conn)
        db_conn.execute(
            """
            INSERT INTO cod_settlements (
                id, order_id, amount_cents, settlement_date, courier_reference,
                mismatch_review
            ) VALUES ('cod-settlement-1', ?, 4800, '2026-08-01', 'ECONT-PAYOUT-1', 1)
            """,
            (order_id,),
        )
        row = db_conn.execute(
            "SELECT amount_cents, mismatch_review FROM cod_settlements WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        assert row == (4800, 1)
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO cod_settlements (id, order_id, amount_cents, settlement_date)
                VALUES ('cod-settlement-2', ?, 4800, '2026-08-02')
                """,
                (order_id,),
            )


class TestAccountingFinanceHubSchema:
    """Accounting & Finance Hub tables enforce the core evidence model."""

    def test_fresh_db_has_finance_tables_and_order_snapshot_columns(
        self, db_conn: sqlite3.Connection
    ):
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
        tables = {
            row[0] for row in db_conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert expected_tables.issubset(tables)

        order_columns = {row[1] for row in db_conn.execute("PRAGMA table_info(orders)")}
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

    def test_order_accounting_snapshot_defaults(self, db_conn: sqlite3.Connection):
        db_conn.execute(
            """
            INSERT INTO orders (id, session_id, status, total_cents, customer_email)
            VALUES ('acct-order-defaults', 'acct-session', 'pending', 1000, 'acct@example.com')
            """
        )
        row = db_conn.execute(
            """
            SELECT accounting_currency, accounting_classification_state,
                   accounting_readiness_status
            FROM orders WHERE id = 'acct-order-defaults'
            """
        ).fetchone()
        assert row == ("EUR", "unreviewed", "unreviewed")

    def test_finance_period_status_and_dates_are_constrained(self, db_conn: sqlite3.Connection):
        db_conn.execute(
            """
            INSERT INTO finance_periods (id, period_start, period_end, currency, status)
            VALUES ('period-2026-08', '2026-08-01', '2026-08-31', 'EUR', 'open')
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO finance_periods (id, period_start, period_end, status)
                VALUES ('period-bad-status', '2026-08-01', '2026-08-31', 'draft')
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO finance_periods (id, period_start, period_end)
                VALUES ('period-bad-dates', '2026-09-01', '2026-08-31')
                """
            )

    def test_accounting_document_and_credit_note_reference_shape(self, db_conn: sqlite3.Connection):
        db_conn.execute(
            """
            INSERT INTO accounting_documents (
                id, document_type, document_number, issue_date, gross_amount_cents
            ) VALUES ('doc-invoice-1', 'invoice', 'INV-1', '2026-08-03', 2400)
            """
        )
        db_conn.execute(
            """
            INSERT INTO accounting_documents (
                id, document_type, document_number, issue_date,
                gross_amount_cents, original_document_id
            ) VALUES ('doc-credit-1', 'credit_note', 'CN-1', '2026-08-04', 1200,
                      'doc-invoice-1')
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO accounting_documents (
                    id, document_type, issue_date, gross_amount_cents
                ) VALUES ('doc-bad-type', 'receiptish', '2026-08-03', 2400)
                """
            )

    def test_stripe_balance_transaction_provider_id_is_unique(self, db_conn: sqlite3.Connection):
        for row_id in ("stripe-btxn-1", "stripe-btxn-2"):
            with pytest.raises(sqlite3.IntegrityError) if row_id.endswith("2") else nullcontext():
                db_conn.execute(
                    """
                    INSERT INTO stripe_balance_transactions (
                        id, balance_transaction_id, gross_amount_cents,
                        fee_amount_cents, net_amount_cents, currency
                    ) VALUES (?, 'txn_same', 1000, 50, 950, 'EUR')
                    """,
                    (row_id,),
                )

    def test_expense_and_product_cost_constraints(self, db_conn: sqlite3.Connection):
        db_conn.execute(
            """
            INSERT INTO products (id, name_en, price_cents, stock)
            VALUES ('costed-candle', 'Costed Candle', 3000, 5)
            """
        )
        db_conn.execute(
            """
            INSERT INTO expense_evidence (
                id, supplier_name, purchase_date, payment_status, category_key,
                gross_amount_cents, tax_amount_cents, linked_product_id
            ) VALUES ('expense-1', 'Wax Supplier', '2026-08-02', 'unpaid',
                      'materials', 12000, 2000, 'costed-candle')
            """
        )
        db_conn.execute(
            """
            INSERT INTO product_cost_versions (
                id, product_id, product_name, effective_date, costing_basis,
                material_cost_cents, packaging_cost_cents, estimated_unit_cost_cents
            ) VALUES ('cost-version-1', 'costed-candle', 'Costed Candle',
                      '2026-08-01', 'recipe_bom', 400, 150, 550)
            """
        )
        db_conn.execute(
            """
            INSERT INTO product_cost_components (
                id, cost_version_id, component_type, description, quantity, unit,
                unit_cost_cents, total_cost_cents, source_expense_id
            ) VALUES ('cost-component-1', 'cost-version-1', 'material', 'Wax',
                      0.18, 'kg', 2000, 360, 'expense-1')
            """
        )

        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO expense_evidence (
                    id, supplier_name, purchase_date, payment_status, gross_amount_cents
                ) VALUES ('expense-bad-status', 'Supplier', '2026-08-02', 'waiting', 100)
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """
                INSERT INTO product_cost_versions (
                    id, product_name, effective_date, costing_basis,
                    estimated_unit_cost_cents
                ) VALUES ('cost-version-bad', 'Bad', '2026-08-01', 'fifo', 100)
                """
            )


class TestWeightGramsMigration:
    """Existing DBs missing weight_grams get the column backfilled to 300."""

    @staticmethod
    def _old_schema_products_sql() -> str:
        """The products table as it existed before weight_grams was added."""
        return """
        CREATE TABLE products (
            id          TEXT PRIMARY KEY,
            name_en     TEXT NOT NULL,
            name_bg     TEXT,
            description_en TEXT,
            description_bg TEXT,
            materials   TEXT,
            days_to_craft INTEGER,
            price_cents INTEGER NOT NULL CHECK (price_cents > 0),
            category    TEXT,
            image_url   TEXT,
            stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
            is_active   INTEGER NOT NULL DEFAULT 1,
            is_featured INTEGER NOT NULL DEFAULT 0,
            translation_stale_bg INTEGER NOT NULL DEFAULT 0,
            translation_stale_en INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """

    def test_rebuild_backfills_weight_to_300(self):
        from app.database import _migrate_products_table, _table_columns

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(self._old_schema_products_sql())
        conn.execute(
            "INSERT INTO products (id, name_en, price_cents, stock) VALUES (?, ?, ?, ?)",
            ("legacy-candle", "Legacy", 2500, 7),
        )

        _migrate_products_table(conn)

        cols = _table_columns(conn, "products")
        assert "weight_grams" in cols
        assert "safety_warnings_en" in cols
        assert "safety_warnings_bg" in cols
        assert "care_instructions_en" in cols
        assert "care_instructions_bg" in cols
        row = conn.execute(
            "SELECT stock, weight_grams, safety_warnings_en, care_instructions_en "
            "FROM products WHERE id = ?",
            ("legacy-candle",),
        ).fetchone()
        assert row["stock"] == 7  # preserved
        assert row["weight_grams"] == 300  # backfilled
        assert row["safety_warnings_en"] is None
        assert row["care_instructions_en"] is None
        conn.close()

    def test_rebuild_is_idempotent(self):
        from app.database import _migrate_products_table, _table_columns

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(self._old_schema_products_sql())
        _migrate_products_table(conn)
        # Second run is a no-op (guard: columns == set(_PRODUCT_COLUMNS))
        _migrate_products_table(conn)
        assert "weight_grams" in _table_columns(conn, "products")
        conn.close()


class TestOrderConstraintMigration:
    """Existing DBs with the old status CHECK constraints are rebuilt safely."""

    @staticmethod
    def _old_orders_schema_sql() -> str:
        return """
        CREATE TABLE orders (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
            total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
            customer_email TEXT NOT NULL,
            payment_method TEXT NOT NULL DEFAULT 'cod'
                CHECK (payment_method IN ('cod', 'card', 'bank_transfer')),
            payment_status TEXT NOT NULL DEFAULT 'cod_pending'
                CHECK (payment_status IN ('pending', 'paid', 'cod_pending', 'failed', 'refunded')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """

    def test_init_db_rebuilds_order_constraints_and_preserves_rows(self, tmp_path):
        db_file = tmp_path / "legacy-orders.db"
        conn = sqlite3.connect(db_file)
        conn.executescript(self._old_orders_schema_sql())
        conn.execute(
            """
            INSERT INTO orders (
                id, session_id, status, total_cents, customer_email,
                payment_method, payment_status
            ) VALUES ('legacy-order', 'legacy-session', 'confirmed', 1200,
                      'legacy@example.com', 'card', 'pending')
            """
        )
        conn.commit()
        conn.close()

        init_db(str(db_file))

        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        preserved = conn.execute(
            "SELECT status, payment_status FROM orders WHERE id = 'legacy-order'"
        ).fetchone()
        assert preserved["status"] == "confirmed"
        assert preserved["payment_status"] == "pending"
        conn.execute(
            "INSERT INTO orders (id, session_id, status, total_cents, customer_email) "
            "VALUES ('return-order', 'legacy-session', 'return_in_transit', 100, 'r@example.com')"
        )
        conn.execute(
            """
            INSERT INTO orders (
                id, session_id, status, total_cents, customer_email,
                payment_method, payment_status
            ) VALUES ('review-order', 'legacy-session', 'pending', 100,
                      'review@example.com', 'card', 'review_required')
            """
        )
        conn.commit()
        conn.close()


class TestFaqReturnsPolicyMigration:
    """Existing FAQ seed text is updated conservatively and only once."""

    @staticmethod
    def _faq_schema_sql() -> str:
        return """
        CREATE TABLE schema_migrations (
            name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE faq_sections (
            slug TEXT PRIMARY KEY,
            title_en TEXT NOT NULL,
            title_bg TEXT,
            icon TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE faq_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT NOT NULL REFERENCES faq_sections(slug),
            question_en TEXT NOT NULL,
            question_bg TEXT,
            answer_en TEXT NOT NULL,
            answer_bg TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_published INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """

    def _conn_with_faq_row(self, answer_en: str, answer_bg: str) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(self._faq_schema_sql())
        conn.execute(
            "INSERT INTO faq_sections (slug, title_en, title_bg, sort_order) "
            "VALUES ('shipping', 'Orders, Shipping & Returns', 'Поръчки, доставка и връщане', 3)"
        )
        conn.execute(
            """
            INSERT INTO faq_items (
                section, question_en, question_bg, answer_en, answer_bg, sort_order
            ) VALUES ('shipping', 'Do you accept returns?', 'Приемате ли връщания?', ?, ?, 0)
            """,
            (answer_en, answer_bg),
        )
        return conn

    def test_exact_old_returns_answer_is_updated_and_marked(self):
        from app.database import (
            _FAQ_RETURNS_POLICY_MARKER,
            _NEW_FAQ_RETURNS_ANSWER_BG,
            _NEW_FAQ_RETURNS_ANSWER_EN,
            _OLD_FAQ_RETURNS_ANSWER_BG,
            _OLD_FAQ_RETURNS_ANSWER_EN,
            _migrate_faq_returns_policy_reference,
        )

        conn = self._conn_with_faq_row(
            _OLD_FAQ_RETURNS_ANSWER_EN,
            _OLD_FAQ_RETURNS_ANSWER_BG,
        )

        _migrate_faq_returns_policy_reference(conn)
        _migrate_faq_returns_policy_reference(conn)

        row = conn.execute("SELECT answer_en, answer_bg FROM faq_items").fetchone()
        assert row["answer_en"] == _NEW_FAQ_RETURNS_ANSWER_EN
        assert row["answer_bg"] == _NEW_FAQ_RETURNS_ANSWER_BG
        marker = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE name = ?",
            (_FAQ_RETURNS_POLICY_MARKER,),
        ).fetchone()
        assert marker is not None
        conn.close()

    def test_owner_edited_returns_answer_is_preserved(self):
        from app.database import (
            _FAQ_RETURNS_POLICY_MARKER,
            _migrate_faq_returns_policy_reference,
        )

        conn = self._conn_with_faq_row("Owner custom answer", "Редактиран от собственика")

        _migrate_faq_returns_policy_reference(conn)

        row = conn.execute("SELECT answer_en, answer_bg FROM faq_items").fetchone()
        assert row["answer_en"] == "Owner custom answer"
        assert row["answer_bg"] == "Редактиран от собственика"
        marker = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE name = ?",
            (_FAQ_RETURNS_POLICY_MARKER,),
        ).fetchone()
        assert marker is not None
        conn.close()
