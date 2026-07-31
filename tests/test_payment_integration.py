"""Tests for payment integration: checkout service, update_status, mark_bank_transfer_paid,
payment_service handlers, webhook route, 24h auto-cancel, and order_cancelled email template.
"""

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.database import init_db
from app.email.renderer import render_template
from app.models.delivery import DeliveryInfo, DeliveryOffice
from app.services.order_service import (
    ManualPaymentActionError,
    apply_manual_payment_action,
    checkout,
    mark_bank_transfer_paid,
    update_status,
)
from app.services.order_service import (
    PaymentAlreadyPaidError as BankTransferAlreadyPaidError,
)
from app.services.order_service import (
    WrongPaymentMethodError as InvalidPaymentMethodError,
)
from app.services.order_service import (
    get_order_admin as get_order,
)
from app.services.payment_service import (
    InvalidRetryStateError,
    InvalidRetryTokenError,
    create_checkout_session,
    create_retry_session,
    handle_charge_refunded,
    handle_payment_failed,
    handle_payment_succeeded,
    handle_session_expired,
)
from app.services.payment_settings_service import (
    PaymentSettingsValidationError,
    get_payment_settings,
    update_payment_settings,
    validate_payment_settings_update,
)

_DT_FMT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


@pytest.fixture()
def delivery() -> DeliveryInfo:
    return DeliveryInfo(
        method="office",
        office=DeliveryOffice(
            courier="econt",
            office_id="econt-1029",
            office_name="София",
            office_type="office",
            city="София",
            phone="+359888000000",
        ),
    )


def _seed_product(conn: sqlite3.Connection, stock: int = 5) -> str:
    pid = f"test-product-{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active)"
        " VALUES (?, 'Test', 100, ?, 1)",
        (pid, stock),
    )
    conn.commit()
    return pid


def _add_cart(conn: sqlite3.Connection, session_id: str, product_id: str, qty: int = 1):
    conn.execute("INSERT OR IGNORE INTO sessions (id) VALUES (?)", (session_id,))
    conn.execute(
        "INSERT OR REPLACE INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)",
        (session_id, product_id, qty),
    )
    conn.commit()


def _do_checkout(conn, delivery, payment_method="cod", session_id=None):
    sid = session_id or uuid.uuid4().hex
    pid = _seed_product(conn)
    _add_cart(conn, sid, pid)
    return checkout(
        conn,
        session_id=sid,
        customer_email="test@example.com",
        customer_name=None,
        delivery=delivery,
        notes=None,
        payment_method=payment_method,
    )


# ---------------------------------------------------------------------------
# 10.1 checkout() — payment fields per method
# ---------------------------------------------------------------------------


class TestCheckoutPaymentFields:
    def test_order_number_uses_public_format(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="cod")

        assert order["order_number"].startswith("AM-")
        assert len(order["order_number"]) == 9
        assert set(order["order_number"][3:]).issubset(set("0123456789ABCDEFGHJKMNPQRSTVWXYZ"))

    def test_order_number_generation_retries_collision(self, conn, delivery):
        from app.services import order_service

        order = _do_checkout(conn, delivery, payment_method="cod")
        conn.execute("UPDATE orders SET order_number = 'AM-000000' WHERE id = ?", (order["id"],))
        conn.commit()

        with patch(
            "app.services.order_service.secrets.choice",
            side_effect=list("000000111111"),
        ):
            assert order_service._generate_order_number(conn) == "AM-111111"

    def test_cod_sets_cod_pending(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="cod")
        assert order["payment_method"] == "cod"
        assert order["payment_status"] == "cod_pending"

    def test_card_sets_pending(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        assert order["payment_method"] == "card"
        assert order["payment_status"] == "pending"

    def test_bank_transfer_sets_pending(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="bank_transfer")
        assert order["payment_method"] == "bank_transfer"
        assert order["payment_status"] == "pending"

    def test_cod_queues_placed_email(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="cod")
        row = conn.execute(
            "SELECT event FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order["id"],),
        ).fetchone()
        assert row is not None

    def test_card_queues_payment_pending_email(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        row = conn.execute(
            "SELECT event FROM order_emails WHERE order_id = ? AND event = 'payment_pending'",
            (order["id"],),
        ).fetchone()
        assert row is not None
        # Must NOT queue placed
        placed = conn.execute(
            "SELECT event FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order["id"],),
        ).fetchone()
        assert placed is None

    def test_bank_transfer_queues_payment_pending_email(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="bank_transfer")
        row = conn.execute(
            "SELECT event FROM order_emails WHERE order_id = ? AND event = 'payment_pending'",
            (order["id"],),
        ).fetchone()
        assert row is not None


# ---------------------------------------------------------------------------
# 10.2 update_status() — COD auto-pays on delivery
# ---------------------------------------------------------------------------


class TestUpdateStatusPayment:
    def test_cod_delivered_sets_paid(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="cod")
        update_status(conn, order["id"], "confirmed")
        update_status(conn, order["id"], "shipped", tracking_number="123", tracking_carrier="econt")
        update_status(conn, order["id"], "delivered")
        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "paid"

    def test_non_cod_delivered_does_not_change_payment_status(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="bank_transfer")
        # Manually mark paid so it's in a realistic state
        conn.execute("UPDATE orders SET payment_status = 'paid' WHERE id = ?", (order["id"],))
        conn.commit()
        update_status(conn, order["id"], "confirmed")
        update_status(conn, order["id"], "shipped", tracking_number="123", tracking_carrier="econt")
        update_status(conn, order["id"], "delivered")
        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "paid"  # unchanged by deliver

    def test_cancellation_does_not_change_payment_status(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="cod")
        update_status(conn, order["id"], "cancelled")
        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "cod_pending"


# ---------------------------------------------------------------------------
# 10.3 mark_bank_transfer_paid()
# ---------------------------------------------------------------------------


class TestMarkBankTransferPaid:
    def test_sets_paid_and_queues_placed_email(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="bank_transfer")
        mark_bank_transfer_paid(conn, order["id"])
        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "paid"
        row = conn.execute(
            "SELECT event FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order["id"],),
        ).fetchone()
        assert row is not None

    def test_409_on_double_mark(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="bank_transfer")
        mark_bank_transfer_paid(conn, order["id"])
        with pytest.raises(BankTransferAlreadyPaidError):
            mark_bank_transfer_paid(conn, order["id"])

    def test_422_on_wrong_payment_method(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="cod")
        with pytest.raises(InvalidPaymentMethodError):
            mark_bank_transfer_paid(conn, order["id"])


# ---------------------------------------------------------------------------
# 10.3b manual payment actions — current vocabulary
# ---------------------------------------------------------------------------


class TestManualPaymentActions:
    def test_note_required(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="cod")
        with pytest.raises(ManualPaymentActionError):
            apply_manual_payment_action(conn, order["id"], "mark_collected", "   ")

    def test_mark_cod_collected_maps_to_paid_and_writes_event(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="cod")

        updated = apply_manual_payment_action(
            conn,
            order["id"],
            "mark_collected",
            "Collected by courier",
            admin_id="admin-1",
            admin_email="owner@example.com",
            request_id="req-1",
        )

        assert updated["payment_status"] == "paid"
        assert updated["paid_at"] is not None
        assert updated["collected_at"] is not None
        event = conn.execute(
            "SELECT event_type, admin_note, admin_email FROM payment_events WHERE order_id = ?",
            (order["id"],),
        ).fetchone()
        assert event["event_type"] == "manual_mark_collected"
        assert event["admin_note"] == "Collected by courier"
        assert event["admin_email"] == "owner@example.com"

    def test_mark_refunded_uses_current_refunded_status(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        conn.execute("UPDATE orders SET payment_status = 'paid' WHERE id = ?", (order["id"],))
        conn.commit()

        updated = apply_manual_payment_action(conn, order["id"], "mark_refunded", "Manual refund")

        assert updated["payment_status"] == "refunded"
        event = conn.execute(
            "SELECT provider_status FROM payment_events WHERE order_id = ?",
            (order["id"],),
        ).fetchone()
        assert event["provider_status"] == "refunded"

    def test_cancel_unpaid_card_restores_stock_and_marks_failed(self, conn, delivery):
        pid = _seed_product(conn, stock=5)
        sid = uuid.uuid4().hex
        _add_cart(conn, sid, pid, qty=2)
        order = checkout(
            conn,
            session_id=sid,
            customer_email="x@example.com",
            customer_name=None,
            delivery=delivery,
            notes=None,
            payment_method="card",
        )
        stock_after_order = conn.execute(
            "SELECT stock FROM products WHERE id = ?", (pid,)
        ).fetchone()[0]

        updated = apply_manual_payment_action(conn, order["id"], "cancel", "Customer request")

        assert updated["status"] == "cancelled"
        assert updated["payment_status"] == "failed"
        assert (
            conn.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()[0]
            == stock_after_order + 2
        )
        event = conn.execute(
            "SELECT event_type, provider_status FROM payment_events WHERE order_id = ?",
            (order["id"],),
        ).fetchone()
        assert event["event_type"] == "manual_cancel"
        assert event["provider_status"] == "failed"


# ---------------------------------------------------------------------------
# 10.4 handle_payment_succeeded()
# ---------------------------------------------------------------------------


class TestHandlePaymentSucceeded:
    def test_sets_paid_and_stores_intent_id(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        now = datetime.now(UTC).strftime(_DT_FMT)
        result = handle_payment_succeeded(conn, "evt_001", order["id"], "pi_abc", now)
        assert result is True
        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "paid"
        assert updated["stripe_payment_intent_id"] == "pi_abc"

    def test_queues_placed_email_on_success(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        now = datetime.now(UTC).strftime(_DT_FMT)
        handle_payment_succeeded(conn, "evt_002", order["id"], "pi_def", now)
        row = conn.execute(
            "SELECT event FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order["id"],),
        ).fetchone()
        assert row is not None

    def test_idempotent_on_duplicate_event_id(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        now = datetime.now(UTC).strftime(_DT_FMT)
        handle_payment_succeeded(conn, "evt_003", order["id"], "pi_ghi", now)
        result2 = handle_payment_succeeded(conn, "evt_003", order["id"], "pi_ghi", now)
        assert result2 is False
        # Only one placed email queued
        count = conn.execute(
            "SELECT COUNT(*) FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order["id"],),
        ).fetchone()[0]
        assert count == 1
        event_count = conn.execute(
            "SELECT COUNT(*) FROM payment_events WHERE stripe_event_id = 'evt_003'"
        ).fetchone()[0]
        assert event_count == 1

    def test_ignores_cancelled_order(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        conn.execute(
            "UPDATE orders SET status = 'cancelled', stripe_checkout_session_id = 'cs_current' "
            "WHERE id = ?",
            (order["id"],),
        )
        conn.commit()
        now = datetime.now(UTC).strftime(_DT_FMT)

        handle_payment_succeeded(
            conn, "evt_cancelled", order["id"], "pi_cancelled", now, "cs_current"
        )

        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "pending"
        count = conn.execute(
            "SELECT COUNT(*) FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order["id"],),
        ).fetchone()[0]
        assert count == 0

    def test_ignores_non_card_order(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="cod")
        now = datetime.now(UTC).strftime(_DT_FMT)

        handle_payment_succeeded(conn, "evt_cod", order["id"], "pi_cod", now, "cs_cod")

        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "cod_pending"
        count = conn.execute(
            "SELECT COUNT(*) FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order["id"],),
        ).fetchone()[0]
        assert count == 1  # the original COD placed email only

    def test_ignores_mismatched_session_id(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        conn.execute(
            "UPDATE orders SET stripe_checkout_session_id = 'cs_current' WHERE id = ?",
            (order["id"],),
        )
        conn.commit()
        now = datetime.now(UTC).strftime(_DT_FMT)

        handle_payment_succeeded(conn, "evt_stale", order["id"], "pi_stale", now, "cs_old")

        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "pending"
        count = conn.execute(
            "SELECT COUNT(*) FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order["id"],),
        ).fetchone()[0]
        assert count == 0

    def test_late_success_after_reservation_expired_requires_review(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        expired_at = (datetime.now(UTC) - timedelta(minutes=1)).strftime(_DT_FMT)
        conn.execute(
            "UPDATE orders SET reserved_until = ?, stripe_checkout_session_id = 'cs_current' "
            "WHERE id = ?",
            (expired_at, order["id"]),
        )
        conn.commit()
        now = datetime.now(UTC).strftime(_DT_FMT)

        handle_payment_succeeded(
            conn,
            "evt_expired_success",
            order["id"],
            "pi_late",
            now,
            "cs_current",
            "owner@example.com",
        )

        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "failed"
        count = conn.execute(
            "SELECT COUNT(*) FROM order_emails WHERE order_id = ? AND event = 'placed'",
            (order["id"],),
        ).fetchone()[0]
        assert count == 0
        event = conn.execute(
            "SELECT processing_status, details FROM payment_events WHERE stripe_event_id = ?",
            ("evt_expired_success",),
        ).fetchone()
        assert event["processing_status"] == "requires_review"
        assert "reservation_expired" in event["details"]
        assert "requires_admin_review" in event["details"]
        alert = conn.execute(
            "SELECT alert_type, order_id, source, details FROM admin_alerts WHERE order_id = ?",
            (order["id"],),
        ).fetchone()
        assert alert["alert_type"] == "payment_requires_review"
        assert alert["source"] == "stripe"
        assert "pi_late" in alert["details"]
        admin_email = conn.execute(
            "SELECT event, recipient FROM order_emails "
            "WHERE order_id = ? AND event = 'admin_payment_review_required'",
            (order["id"],),
        ).fetchone()
        assert admin_email["recipient"] == "owner@example.com"


# ---------------------------------------------------------------------------
# 10.5 handle_session_expired()
# ---------------------------------------------------------------------------


class TestHandleSessionExpired:
    def test_sets_failed(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        # Simulate the session id Stripe would have stored after create_checkout_session.
        conn.execute(
            "UPDATE orders SET stripe_checkout_session_id = 'cs_test_abc' WHERE id = ?",
            (order["id"],),
        )
        conn.commit()
        now = datetime.now(UTC).strftime(_DT_FMT)
        result = handle_session_expired(conn, "evt_exp_001", order["id"], "cs_test_abc", now)
        assert result is True
        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "failed"

    def test_idempotent_on_duplicate(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        conn.execute(
            "UPDATE orders SET stripe_checkout_session_id = 'cs_test_dup' WHERE id = ?",
            (order["id"],),
        )
        conn.commit()
        now = datetime.now(UTC).strftime(_DT_FMT)
        handle_session_expired(conn, "evt_exp_002", order["id"], "cs_test_dup", now)
        result2 = handle_session_expired(conn, "evt_exp_002", order["id"], "cs_test_dup", now)
        assert result2 is False

    def test_ignores_stale_session_id(self, conn, delivery):
        """Late-arriving expired event for an old session must not flip a paid order to failed."""
        order = _do_checkout(conn, delivery, payment_method="card")
        # Simulate: customer retried and paid with cs_test_new; cs_test_old expired late.
        conn.execute(
            "UPDATE orders SET stripe_checkout_session_id = 'cs_test_new',"
            " payment_status = 'paid' WHERE id = ?",
            (order["id"],),
        )
        conn.commit()
        now = datetime.now(UTC).strftime(_DT_FMT)
        handle_session_expired(conn, "evt_exp_stale", order["id"], "cs_test_old", now)
        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "paid"


# ---------------------------------------------------------------------------
# 10.5b additional allowlisted Stripe events
# ---------------------------------------------------------------------------


class TestAdditionalStripeEvents:
    def test_payment_failed_records_audit_without_failing_order(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        now = datetime.now(UTC).strftime(_DT_FMT)

        result = handle_payment_failed(
            conn,
            "evt_pi_failed",
            order["id"],
            "pi_failed",
            now,
            error_code="card_declined",
            event_created=123,
            livemode=False,
        )

        assert result is True
        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "pending"
        event = conn.execute(
            """
            SELECT event_type, provider_status, processing_status, details
            FROM payment_events
            WHERE stripe_event_id = 'evt_pi_failed'
            """
        ).fetchone()
        assert event["event_type"] == "payment_intent.payment_failed"
        assert event["provider_status"] == "failed"
        assert event["processing_status"] == "processed"
        assert "card_declined" in event["details"]

    def test_payment_failed_duplicate_is_idempotent(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        now = datetime.now(UTC).strftime(_DT_FMT)
        handle_payment_failed(conn, "evt_pi_dup", order["id"], "pi_dup", now)

        result = handle_payment_failed(conn, "evt_pi_dup", order["id"], "pi_dup", now)

        assert result is False
        count = conn.execute(
            "SELECT COUNT(*) FROM payment_events WHERE stripe_event_id = 'evt_pi_dup'"
        ).fetchone()[0]
        assert count == 1

    def test_charge_refunded_is_audit_only(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        conn.execute(
            "UPDATE orders SET payment_status = 'paid', stripe_payment_intent_id = 'pi_refund' "
            "WHERE id = ?",
            (order["id"],),
        )
        conn.execute(
            "UPDATE payments SET stripe_payment_intent_id = 'pi_refund' WHERE order_id = ?",
            (order["id"],),
        )
        conn.commit()
        now = datetime.now(UTC).strftime(_DT_FMT)

        result = handle_charge_refunded(
            conn,
            "evt_charge_refunded",
            None,
            "ch_refund",
            "pi_refund",
            now,
            amount_refunded=100,
        )

        assert result is True
        updated = get_order(conn, order["id"])
        assert updated["payment_status"] == "paid"
        event = conn.execute(
            """
            SELECT order_id, event_type, provider_status, processing_status, details
            FROM payment_events
            WHERE stripe_event_id = 'evt_charge_refunded'
            """
        ).fetchone()
        assert event["order_id"] == order["id"]
        assert event["event_type"] == "charge.refunded"
        assert event["provider_status"] == "refunded"
        assert event["processing_status"] == "processed"
        assert "audit_only" in event["details"]


# ---------------------------------------------------------------------------
# 10.5c security and retry edge cases
# ---------------------------------------------------------------------------


class TestPaymentSecurityEdges:
    def test_payment_settings_defaults_are_inserted(self, conn):
        settings = get_payment_settings(conn)

        assert settings == {
            "card_payments_enabled": False,
            "pay_on_delivery_enabled": False,
            "pay_on_delivery_max_cents": 5000,
        }
        count = conn.execute(
            "SELECT COUNT(*) FROM site_settings "
            "WHERE key IN ('card_payments_enabled', 'pay_on_delivery_enabled', "
            "'pay_on_delivery_max_cents')"
        ).fetchone()[0]
        assert count == 3

    def test_payment_settings_update_writes_audit_events(self, conn):
        updated = update_payment_settings(
            conn,
            {
                "card_payments_enabled": False,
                "pay_on_delivery_enabled": True,
                "pay_on_delivery_max_cents": 2500,
            },
            Settings(),
            admin_id="admin-1",
            admin_email="owner@example.com",
            request_id="req-settings",
        )

        assert updated["pay_on_delivery_enabled"] is True
        assert updated["pay_on_delivery_max_cents"] == 2500
        rows = conn.execute(
            """
            SELECT setting_key, old_value, new_value, admin_email, request_id
            FROM site_setting_events
            ORDER BY setting_key
            """
        ).fetchall()
        assert [row["setting_key"] for row in rows] == [
            "pay_on_delivery_enabled",
            "pay_on_delivery_max_cents",
        ]
        assert {row["admin_email"] for row in rows} == {"owner@example.com"}
        assert {row["request_id"] for row in rows} == {"req-settings"}

    def test_stripe_checkout_uses_database_total_not_client_amount(self, conn, delivery):
        import sys
        import types

        order = _do_checkout(conn, delivery, payment_method="card")
        captured: dict = {}

        class FakeSession:
            id = "cs_amount"
            url = "https://checkout.example/session"
            status = "open"
            payment_intent = None

        class FakeCheckoutSession:
            @staticmethod
            def create(**kwargs):
                captured.update(kwargs)
                return FakeSession()

        fake_stripe = types.ModuleType("stripe")
        fake_stripe.api_key = None
        fake_stripe.checkout = types.SimpleNamespace(Session=FakeCheckoutSession)

        with patch.dict(sys.modules, {"stripe": fake_stripe}):
            create_checkout_session(
                conn,
                order,
                "https://shop.example/success?token={payment_return_token}",
                "https://shop.example/cancel?token={payment_return_token}",
                "sk_test_amount",
            )

        unit_amount = captured["line_items"][0]["price_data"]["unit_amount"]
        assert unit_amount == order["total_cents"]

    def test_retry_rejects_wrong_return_token(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")

        with pytest.raises(InvalidRetryTokenError):
            create_retry_session(
                conn,
                order["id"],
                "wrong-token",
                "https://shop.example/success",
                "https://shop.example/cancel",
                "sk_test_retry",
            )

    def test_retry_rejects_expired_reservation(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        expired_at = (datetime.now(UTC) - timedelta(minutes=1)).strftime(_DT_FMT)
        conn.execute("UPDATE orders SET reserved_until = ? WHERE id = ?", (expired_at, order["id"]))
        conn.commit()

        with pytest.raises(InvalidRetryStateError):
            create_retry_session(
                conn,
                order["id"],
                order["payment_return_token"],
                "https://shop.example/success",
                "https://shop.example/cancel",
                "sk_test_retry",
            )

    def test_production_rejects_stripe_test_key_for_card_enable(self):
        settings = Settings(
            environment="production",
            jwt_secret="a-real-production-secret-key",
            admin_api_key="a-long-enough-production-api-key-here",
            stripe_secret_key="sk_test_not_live",
            stripe_webhook_secret="whsec_test",
            stripe_publishable_key="pk_test_123",
        )

        with pytest.raises(PaymentSettingsValidationError, match="live Stripe secret key"):
            validate_payment_settings_update(
                {
                    "card_payments_enabled": True,
                    "pay_on_delivery_enabled": True,
                    "pay_on_delivery_max_cents": 5000,
                },
                settings,
            )


# ---------------------------------------------------------------------------
# 10.6 POST /v1/webhooks/stripe — route level
# ---------------------------------------------------------------------------


@pytest.fixture()
def stripe_app(tmp_path):
    from app.config import get_settings
    from app.database import init_db

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    get_settings.cache_clear()
    import os

    os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test"  # pragma: allowlist secret
    os.environ["DATABASE_PATH"] = db_path

    from app.main import create_app

    app = create_app()
    yield app

    get_settings.cache_clear()
    os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
    os.environ.pop("DATABASE_PATH", None)


class TestStripeWebhookRoute:
    @pytest.mark.anyio
    async def test_invalid_signature_returns_400(self, stripe_app):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=stripe_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/v1/webhooks/stripe",
                content=b'{"type":"checkout.session.completed"}',
                headers={"stripe-signature": "bad_sig", "content-type": "application/json"},
            )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_oversized_body_returns_413(self, stripe_app):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=stripe_app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/v1/webhooks/stripe",
                content=b"{" + (b" " * (64 * 1024)) + b"}",
                headers={"stripe-signature": "bad_sig", "content-type": "application/json"},
            )
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

    @pytest.mark.anyio
    async def test_unknown_event_type_returns_200(self, stripe_app):
        import json
        import sys
        import types

        body = json.dumps(
            {
                "id": "evt_unknown",
                "type": "some.unknown.event",
                "data": {"object": {}},
            }
        ).encode()

        mock_event = MagicMock()
        mock_event.id = "evt_unknown"
        mock_event.type = "some.unknown.event"
        mock_event.data.object = MagicMock()

        fake_stripe = types.ModuleType("stripe")
        fake_stripe.api_key = None
        fake_stripe.Webhook = MagicMock()
        fake_stripe.Webhook.construct_event = MagicMock(return_value=mock_event)

        with patch.dict(sys.modules, {"stripe": fake_stripe}):
            from httpx import ASGITransport, AsyncClient

            async with AsyncClient(
                transport=ASGITransport(app=stripe_app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/v1/webhooks/stripe",
                    content=body,
                    headers={"stripe-signature": "t=1,v1=abc", "content-type": "application/json"},
                )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 10.7 24h auto-cancel — card pending/failed orders
# ---------------------------------------------------------------------------


class TestAutoCancel:
    def _run(self, conn):
        from app.main import _cancel_abandoned_card_orders

        with patch("app.main.get_db") as m:
            m.return_value.__enter__ = lambda s: conn
            m.return_value.__exit__ = MagicMock(return_value=False)
            _cancel_abandoned_card_orders()

    def test_cancels_old_card_pending_order_and_restores_stock(self, conn, delivery):
        pid = _seed_product(conn, stock=5)
        sid = uuid.uuid4().hex
        _add_cart(conn, sid, pid, qty=2)
        order = checkout(
            conn,
            session_id=sid,
            customer_email="x@x.com",
            customer_name=None,
            delivery=delivery,
            notes=None,
            payment_method="card",
        )
        stock_after_order = conn.execute(
            "SELECT stock FROM products WHERE id = ?", (pid,)
        ).fetchone()[0]
        old_time = (datetime.now(UTC) - timedelta(hours=25)).strftime(_DT_FMT)
        conn.execute("UPDATE orders SET created_at = ? WHERE id = ?", (old_time, order["id"]))
        conn.commit()
        self._run(conn)
        updated = get_order(conn, order["id"])
        assert updated["status"] == "cancelled"
        assert (
            conn.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()[0]
            == stock_after_order + 2
        )

    def test_expired_card_reservation_writes_payment_event_and_expires_stripe(
        self, conn, delivery
    ):
        from app.config import Settings
        from app.main import _cancel_abandoned_card_orders

        pid = _seed_product(conn, stock=5)
        sid = uuid.uuid4().hex
        _add_cart(conn, sid, pid, qty=2)
        order = checkout(
            conn,
            session_id=sid,
            customer_email="x@x.com",
            customer_name=None,
            delivery=delivery,
            notes=None,
            payment_method="card",
        )
        stock_after_order = conn.execute(
            "SELECT stock FROM products WHERE id = ?", (pid,)
        ).fetchone()[0]
        expired_at = (datetime.now(UTC) - timedelta(minutes=1)).strftime(_DT_FMT)
        conn.execute(
            "UPDATE orders SET reserved_until = ?, stripe_checkout_session_id = 'cs_expired' "
            "WHERE id = ?",
            (expired_at, order["id"]),
        )
        conn.commit()

        with (
            patch("app.main.get_db") as db_mock,
            patch("app.main.get_settings") as settings_mock,
            patch(
                "app.services.payment_service.expire_checkout_session", return_value=True
            ) as expire,
        ):
            db_mock.return_value.__enter__ = lambda s: conn
            db_mock.return_value.__exit__ = MagicMock(return_value=False)
            settings_mock.return_value = Settings(stripe_secret_key="sk_test_cleanup")
            count = _cancel_abandoned_card_orders()

        assert count == 1
        expire.assert_called_once_with("cs_expired", "sk_test_cleanup")
        updated = get_order(conn, order["id"])
        assert updated["status"] == "cancelled"
        assert updated["payment_status"] == "failed"
        assert (
            conn.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()[0]
            == stock_after_order + 2
        )
        event = conn.execute(
            """
            SELECT event_type, source, provider_status, processing_status, details
            FROM payment_events
            WHERE order_id = ?
            """,
            (order["id"],),
        ).fetchone()
        assert event["event_type"] == "reservation_expired"
        assert event["source"] == "system"
        assert event["provider_status"] == "failed"
        assert event["processing_status"] == "processed"
        assert "stripe_expired" in event["details"]

    def test_does_not_cancel_cod_orders(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="cod")
        old_time = (datetime.now(UTC) - timedelta(hours=25)).strftime(_DT_FMT)
        conn.execute("UPDATE orders SET created_at = ? WHERE id = ?", (old_time, order["id"]))
        conn.commit()
        self._run(conn)
        assert get_order(conn, order["id"])["status"] == "pending"

    def test_does_not_cancel_bank_transfer_orders(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="bank_transfer")
        old_time = (datetime.now(UTC) - timedelta(hours=25)).strftime(_DT_FMT)
        conn.execute("UPDATE orders SET created_at = ? WHERE id = ?", (old_time, order["id"]))
        conn.commit()
        self._run(conn)
        assert get_order(conn, order["id"])["status"] == "pending"

    def test_cancels_old_card_failed_order(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        old_time = (datetime.now(UTC) - timedelta(hours=25)).strftime(_DT_FMT)
        conn.execute(
            "UPDATE orders SET created_at = ?, payment_status = 'failed' WHERE id = ?",
            (old_time, order["id"]),
        )
        conn.commit()
        self._run(conn)
        assert get_order(conn, order["id"])["status"] == "cancelled"


# ---------------------------------------------------------------------------
# 10.8 order_cancelled email template — refund language guard
# ---------------------------------------------------------------------------


class TestOrderCancelledTemplate:
    def _render(self, payment_method: str, payment_status: str) -> str:
        context = {
            "order_id_short": "abc12345",
            "customer_name": "Alice",
            "total_display": "€32.00",
            "payment_method": payment_method,
            "payment_status": payment_status,
        }
        _, body = render_template("cancelled", "en", context)
        return body

    def test_refund_language_present_for_paid_card(self):
        body = self._render("card", "paid")
        assert "refund" in body.lower()

    def test_refund_language_absent_for_cod(self):
        body = self._render("cod", "cod_pending")
        assert "refund" not in body.lower()

    def test_refund_language_absent_for_unpaid_card(self):
        body = self._render("card", "pending")
        assert "refund" not in body.lower()

    def test_refund_language_absent_for_failed_card(self):
        body = self._render("card", "failed")
        assert "refund" not in body.lower()
