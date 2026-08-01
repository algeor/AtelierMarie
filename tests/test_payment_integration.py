"""Tests for payment integration: checkout service, update_status, mark_bank_transfer_paid,
payment_service handlers, webhook route, 24h auto-cancel, and order_cancelled email template.
"""

import sqlite3
import threading
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
    StripeRefundActionError,
    create_checkout_session,
    create_checkout_session_async,
    create_retry_session,
    create_stripe_refund_async,
    handle_charge_refunded,
    handle_dispute_event,
    handle_payment_failed,
    handle_refund_updated,
    handle_payment_succeeded,
    handle_session_expired,
)
from app.services.payment_settings_service import (
    PaymentSettingsValidationError,
    get_payment_settings,
    stripe_config_health,
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
        assert updated["paid_at"] is not None
        assert updated["collected_at"] is not None

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

    def test_rejects_non_pending_bank_transfer(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="bank_transfer")
        conn.execute("UPDATE orders SET payment_status = 'failed' WHERE id = ?", (order["id"],))
        conn.commit()

        with pytest.raises(ManualPaymentActionError) as exc:
            mark_bank_transfer_paid(conn, order["id"])

        assert exc.value.code == "INVALID_PAYMENT_STATE"
        assert get_order(conn, order["id"])["payment_status"] == "failed"

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

    def test_mark_refunded_rejects_unpaid_payment(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")

        with pytest.raises(ManualPaymentActionError) as exc:
            apply_manual_payment_action(conn, order["id"], "mark_refunded", "Manual refund")

        assert exc.value.code == "INVALID_PAYMENT_STATE"
        assert get_order(conn, order["id"])["payment_status"] == "pending"

    def test_refunded_payment_cannot_be_marked_paid_again(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        conn.execute("UPDATE orders SET payment_status = 'refunded' WHERE id = ?", (order["id"],))
        conn.commit()

        with pytest.raises(ManualPaymentActionError) as exc:
            apply_manual_payment_action(conn, order["id"], "mark_paid", "Undo refund")

        assert exc.value.code == "INVALID_PAYMENT_STATE"
        assert get_order(conn, order["id"])["payment_status"] == "refunded"

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
        assert updated["payment_status"] == "review_required"
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
    def test_sets_review_required(self, conn, delivery):
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
        assert updated["payment_status"] == "review_required"
        event = conn.execute(
            "SELECT provider_status FROM payment_events WHERE stripe_event_id = ?",
            ("evt_exp_001",),
        ).fetchone()
        assert event["provider_status"] == "review_required"

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
# 10.5c Stripe refund creation
# ---------------------------------------------------------------------------


class TestStripeRefundCreation:
    def _paid_card_order(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        conn.execute(
            """
            UPDATE orders
            SET payment_status = 'paid', paid_at = ?, stripe_payment_intent_id = 'pi_refund'
            WHERE id = ?
            """,
            (datetime.now(UTC).strftime(_DT_FMT), order["id"]),
        )
        conn.execute(
            """
            UPDATE payments
            SET stripe_payment_intent_id = 'pi_refund', provider_status = 'paid'
            WHERE order_id = ? AND provider = 'stripe'
            """,
            (order["id"],),
        )
        conn.commit()
        return get_order(conn, order["id"])

    def _fake_stripe(self, monkeypatch, *, calls: list[dict], fail: bool = False):
        import sys
        import types

        class FakeRefund:
            id = "re_created"
            status = "pending"

        class FakeRefundAPI:
            @staticmethod
            def create(**kwargs):
                calls.append(kwargs)
                if fail:
                    raise RuntimeError("stripe unavailable")
                return FakeRefund()

        fake_stripe = types.ModuleType("stripe")
        fake_stripe.api_key = None
        fake_stripe.Refund = FakeRefundAPI
        monkeypatch.setitem(sys.modules, "stripe", fake_stripe)

    async def test_full_refund_creates_pending_record_and_marks_order_pending(
        self, conn, delivery, monkeypatch
    ):
        order = self._paid_card_order(conn, delivery)
        calls: list[dict] = []
        self._fake_stripe(monkeypatch, calls=calls)

        refund = await create_stripe_refund_async(
            conn,
            order_id=order["id"],
            amount_cents=None,
            reason="Customer return",
            idempotency_key="refund-full-1",
            admin_id="admin-1",
            stripe_secret_key="sk_test_refund",
        )

        assert refund["amount_cents"] == order["total_cents"]
        assert refund["status"] == "pending"
        assert refund["provider_refund_id"] == "re_created"
        assert calls[0]["payment_intent"] == "pi_refund"
        assert calls[0]["amount"] == order["total_cents"]
        assert calls[0]["idempotency_key"] == "refund-full-1"
        assert get_order(conn, order["id"])["payment_status"] == "refund_pending"

    async def test_partial_refund_uses_requested_amount(self, conn, delivery, monkeypatch):
        order = self._paid_card_order(conn, delivery)
        calls: list[dict] = []
        self._fake_stripe(monkeypatch, calls=calls)

        refund = await create_stripe_refund_async(
            conn,
            order_id=order["id"],
            amount_cents=50,
            reason="Partial goodwill refund",
            idempotency_key="refund-partial-1",
            stripe_secret_key="sk_test_refund",
        )

        assert refund["amount_cents"] == 50
        assert calls[0]["amount"] == 50

    async def test_duplicate_idempotency_key_returns_existing_without_stripe_call(
        self, conn, delivery, monkeypatch
    ):
        order = self._paid_card_order(conn, delivery)
        calls: list[dict] = []
        self._fake_stripe(monkeypatch, calls=calls)

        first = await create_stripe_refund_async(
            conn,
            order_id=order["id"],
            amount_cents=50,
            reason=None,
            idempotency_key="refund-dupe-1",
            stripe_secret_key="sk_test_refund",
        )
        second = await create_stripe_refund_async(
            conn,
            order_id=order["id"],
            amount_cents=75,
            reason=None,
            idempotency_key="refund-dupe-1",
            stripe_secret_key="sk_test_refund",
        )

        assert second["id"] == first["id"]
        assert second["amount_cents"] == 50
        assert len(calls) == 1

    async def test_over_refund_rejected_before_stripe_call(self, conn, delivery, monkeypatch):
        order = self._paid_card_order(conn, delivery)
        calls: list[dict] = []
        self._fake_stripe(monkeypatch, calls=calls)
        conn.execute(
            """
            INSERT INTO payment_refunds (id, order_id, provider, amount_cents, status)
            VALUES ('existing-refund', ?, 'stripe', ?, 'pending')
            """,
            (order["id"], order["total_cents"] - 10),
        )
        conn.commit()

        with pytest.raises(StripeRefundActionError) as exc_info:
            await create_stripe_refund_async(
                conn,
                order_id=order["id"],
                amount_cents=11,
                reason=None,
                idempotency_key="refund-too-much",
                stripe_secret_key="sk_test_refund",
            )

        assert exc_info.value.code == "REFUND_AMOUNT_EXCEEDS_PAID"
        assert calls == []

    async def test_failed_stripe_creation_records_failed_refund_and_review_state(
        self, conn, delivery, monkeypatch
    ):
        order = self._paid_card_order(conn, delivery)
        calls: list[dict] = []
        self._fake_stripe(monkeypatch, calls=calls, fail=True)

        with pytest.raises(StripeRefundActionError) as exc_info:
            await create_stripe_refund_async(
                conn,
                order_id=order["id"],
                amount_cents=50,
                reason=None,
                idempotency_key="refund-fails-1",
                stripe_secret_key="sk_test_refund",
            )

        assert exc_info.value.code == "STRIPE_REFUND_FAILED"
        refund = conn.execute(
            "SELECT status, failure_reason FROM payment_refunds WHERE order_id = ?",
            (order["id"],),
        ).fetchone()
        assert refund["status"] == "failed"
        assert "stripe unavailable" in refund["failure_reason"]
        assert get_order(conn, order["id"])["payment_status"] == "review_required"

    def test_refund_succeeded_webhook_marks_full_refund_confirmed(self, conn, delivery):
        order = self._paid_card_order(conn, delivery)
        payment_id = conn.execute(
            "SELECT id FROM payments WHERE order_id = ? AND provider = 'stripe'",
            (order["id"],),
        ).fetchone()["id"]
        conn.execute(
            """
            INSERT INTO payment_refunds (
                id, order_id, payment_id, provider, provider_refund_id, amount_cents, status
            ) VALUES ('refund-full', ?, ?, 'stripe', 're_full', ?, 'pending')
            """,
            (order["id"], payment_id, order["total_cents"]),
        )
        conn.execute(
            "UPDATE orders SET payment_status = 'refund_pending' WHERE id = ?",
            (order["id"],),
        )
        conn.commit()

        handle_refund_updated(
            conn,
            "evt_refund_full",
            "refund.updated",
            "re_full",
            "pi_refund",
            datetime.now(UTC).strftime(_DT_FMT),
            amount_cents=order["total_cents"],
            status="succeeded",
        )

        assert get_order(conn, order["id"])["payment_status"] == "refunded"
        refund = conn.execute(
            "SELECT status, confirmed_at FROM payment_refunds WHERE id = 'refund-full'"
        ).fetchone()
        assert refund["status"] == "succeeded"
        assert refund["confirmed_at"] is not None

    def test_refund_succeeded_webhook_marks_partial_refund(self, conn, delivery):
        order = self._paid_card_order(conn, delivery)
        payment_id = conn.execute(
            "SELECT id FROM payments WHERE order_id = ? AND provider = 'stripe'",
            (order["id"],),
        ).fetchone()["id"]
        conn.execute(
            """
            INSERT INTO payment_refunds (
                id, order_id, payment_id, provider, provider_refund_id, amount_cents, status
            ) VALUES ('refund-partial', ?, ?, 'stripe', 're_partial', 50, 'pending')
            """,
            (order["id"], payment_id),
        )
        conn.execute(
            "UPDATE orders SET payment_status = 'refund_pending' WHERE id = ?",
            (order["id"],),
        )
        conn.commit()

        handle_refund_updated(
            conn,
            "evt_refund_partial",
            "charge.refund.updated",
            "re_partial",
            "pi_refund",
            datetime.now(UTC).strftime(_DT_FMT),
            amount_cents=50,
            status="succeeded",
        )

        assert get_order(conn, order["id"])["payment_status"] == "partially_refunded"

    def test_refund_failed_webhook_records_failure_and_review_state(self, conn, delivery):
        order = self._paid_card_order(conn, delivery)
        payment_id = conn.execute(
            "SELECT id FROM payments WHERE order_id = ? AND provider = 'stripe'",
            (order["id"],),
        ).fetchone()["id"]
        conn.execute(
            """
            INSERT INTO payment_refunds (
                id, order_id, payment_id, provider, provider_refund_id, amount_cents, status
            ) VALUES ('refund-failed', ?, ?, 'stripe', 're_failed', 50, 'pending')
            """,
            (order["id"], payment_id),
        )
        conn.execute(
            "UPDATE orders SET payment_status = 'refund_pending' WHERE id = ?",
            (order["id"],),
        )
        conn.commit()

        handle_refund_updated(
            conn,
            "evt_refund_failed",
            "refund.updated",
            "re_failed",
            "pi_refund",
            datetime.now(UTC).strftime(_DT_FMT),
            amount_cents=50,
            status="failed",
            failure_reason="expired_or_canceled_card",
        )

        assert get_order(conn, order["id"])["payment_status"] == "review_required"
        refund = conn.execute(
            "SELECT status, failure_reason FROM payment_refunds WHERE id = 'refund-failed'"
        ).fetchone()
        assert refund["status"] == "failed"
        assert refund["failure_reason"] == "expired_or_canceled_card"

    def test_dispute_events_update_payment_status_and_record_details(self, conn, delivery):
        order = self._paid_card_order(conn, delivery)
        now = datetime.now(UTC).strftime(_DT_FMT)

        handle_dispute_event(
            conn,
            "evt_dispute_open",
            "charge.dispute.created",
            None,
            "pi_refund",
            "dp_1",
            "needs_response",
            now,
            amount_cents=100,
            evidence_due_by=123456,
        )

        assert get_order(conn, order["id"])["payment_status"] == "dispute_open"
        event = conn.execute(
            "SELECT provider_status, details FROM payment_events WHERE stripe_event_id = ?",
            ("evt_dispute_open",),
        ).fetchone()
        assert event["provider_status"] == "dispute_open"
        assert '"dispute_id":"dp_1"' in event["details"]

        handle_dispute_event(
            conn,
            "evt_dispute_won",
            "charge.dispute.closed",
            order["id"],
            "pi_refund",
            "dp_1",
            "won",
            now,
        )
        assert get_order(conn, order["id"])["payment_status"] == "dispute_won"

        handle_dispute_event(
            conn,
            "evt_dispute_lost",
            "charge.dispute.closed",
            order["id"],
            "pi_refund",
            "dp_1",
            "lost",
            now,
        )
        assert get_order(conn, order["id"])["payment_status"] == "dispute_lost"


# ---------------------------------------------------------------------------
# 10.5d security and retry edge cases
# ---------------------------------------------------------------------------


class TestPaymentSecurityEdges:
    def test_payment_settings_defaults_are_inserted(self, conn):
        settings = get_payment_settings(conn)

        assert settings == {
            "card_payments_enabled": False,
            "pay_on_delivery_enabled": True,
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
        assert [row["setting_key"] for row in rows] == ["pay_on_delivery_max_cents"]
        assert {row["admin_email"] for row in rows} == {"owner@example.com"}
        assert {row["request_id"] for row in rows} == {"req-settings"}

    def test_card_health_requires_stripe_return_urls(self):
        settings = Settings(
            stripe_secret_key="sk_test_ready",
            stripe_webhook_secret="whsec_ready",
            stripe_success_url="",
            stripe_cancel_url="",
        )

        health = stripe_config_health(settings)

        assert health["ready_for_card_payments"] is False
        assert "STRIPE_SUCCESS_URL is missing" in health["problems"]
        assert "STRIPE_CANCEL_URL is missing" in health["problems"]

    def test_card_enable_rejects_missing_return_urls(self):
        settings = Settings(
            stripe_secret_key="sk_test_ready",
            stripe_webhook_secret="whsec_ready",
            stripe_success_url="",
            stripe_cancel_url="",
        )

        with pytest.raises(PaymentSettingsValidationError, match="STRIPE_SUCCESS_URL"):
            validate_payment_settings_update(
                {
                    "card_payments_enabled": True,
                    "pay_on_delivery_enabled": True,
                    "pay_on_delivery_max_cents": 5000,
                },
                settings,
            )

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

    async def test_async_stripe_checkout_offloads_provider_call_and_persists(self, conn, delivery):
        import sys
        import types

        order = _do_checkout(conn, delivery, payment_method="card")
        caller_thread_id = threading.get_ident()
        provider_thread_ids: list[int] = []

        class FakeSession:
            id = "cs_async"
            url = "https://checkout.example/async-session"
            status = "open"
            payment_intent = None

        class FakeCheckoutSession:
            @staticmethod
            def create(**_kwargs):
                provider_thread_ids.append(threading.get_ident())
                return FakeSession()

        fake_stripe = types.ModuleType("stripe")
        fake_stripe.api_key = None
        fake_stripe.checkout = types.SimpleNamespace(Session=FakeCheckoutSession)

        with patch.dict(sys.modules, {"stripe": fake_stripe}):
            url = await create_checkout_session_async(
                conn,
                order,
                "https://shop.example/success",
                "https://shop.example/cancel",
                "sk_test_async",
            )

        assert url == "https://checkout.example/async-session"
        assert provider_thread_ids and provider_thread_ids[0] != caller_thread_id
        row = conn.execute(
            "SELECT stripe_checkout_session_id FROM orders WHERE id = ?",
            (order["id"],),
        ).fetchone()
        assert row["stripe_checkout_session_id"] == "cs_async"

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

    def test_retry_session_marks_failed_order_pending_and_reuses_url(self, conn, delivery):
        import sys
        import types

        order = _do_checkout(conn, delivery, payment_method="card")
        conn.execute("UPDATE orders SET payment_status = 'failed' WHERE id = ?", (order["id"],))
        conn.commit()
        calls: list[dict] = []

        class FakeSession:
            id = "cs_retry_new"
            url = "https://checkout.example/retry-new"
            status = "open"
            payment_intent = None

        class FakeCheckoutSession:
            @staticmethod
            def create(**kwargs):
                calls.append(kwargs)
                return FakeSession()

        fake_stripe = types.ModuleType("stripe")
        fake_stripe.api_key = None
        fake_stripe.checkout = types.SimpleNamespace(Session=FakeCheckoutSession)

        with patch.dict(sys.modules, {"stripe": fake_stripe}):
            first_url = create_retry_session(
                conn,
                order["id"],
                order["payment_return_token"],
                "https://shop.example/success",
                "https://shop.example/cancel",
                "sk_test_retry",
            )
            second_url = create_retry_session(
                conn,
                order["id"],
                order["payment_return_token"],
                "https://shop.example/success",
                "https://shop.example/cancel",
                "sk_test_retry",
            )

        assert first_url == "https://checkout.example/retry-new"
        assert second_url == "https://checkout.example/retry-new"
        assert len(calls) == 1
        assert get_order(conn, order["id"])["payment_status"] == "pending"

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
# 10.7 abandoned card payment cleanup — pending/failed cards move to review
# ---------------------------------------------------------------------------


class TestAbandonedCardPaymentReview:
    def _run(self, conn):
        from app.main import _cancel_abandoned_card_orders

        with patch("app.main.get_db") as m:
            m.return_value.__enter__ = lambda s: conn
            m.return_value.__exit__ = MagicMock(return_value=False)
            return _cancel_abandoned_card_orders()

    def test_marks_old_card_pending_order_for_review_and_keeps_stock_reserved(
        self, conn, delivery
    ):
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
        assert updated["status"] == "pending"
        assert updated["payment_status"] == "review_required"
        assert conn.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()[0] == stock_after_order
        assert updated["reserved_until"] is not None

    def test_expired_card_reservation_writes_payment_event_and_expires_stripe(self, conn, delivery):
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
        assert updated["status"] == "pending"
        assert updated["payment_status"] == "review_required"
        assert conn.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()[0] == stock_after_order
        assert updated["reserved_until"] is not None
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
        assert event["provider_status"] == "review_required"
        assert event["processing_status"] == "requires_review"
        assert "stripe_expired" in event["details"]
        assert "requires_admin_callback" in event["details"]
        assert "review_expires_at" in event["details"]

    def test_expired_unconfirmed_review_order_is_cancelled_and_releases_stock_without_refund(
        self, conn, delivery
    ):
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
        assert conn.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()[0] == 3
        expired_at = (datetime.now(UTC) - timedelta(minutes=1)).strftime(_DT_FMT)
        conn.execute(
            """
            UPDATE orders
            SET payment_status = 'review_required', reserved_until = ?,
                stripe_checkout_session_id = 'cs_abandoned'
            WHERE id = ?
            """,
            (expired_at, order["id"]),
        )
        conn.execute(
            """
            UPDATE payments
            SET provider_status = 'review_required', stripe_checkout_session_id = 'cs_abandoned'
            WHERE order_id = ? AND provider = 'stripe'
            """,
            (order["id"],),
        )
        conn.commit()

        count = self._run(conn)

        assert count == 1
        updated = get_order(conn, order["id"])
        assert updated["status"] == "cancelled"
        assert updated["payment_status"] == "failed"
        assert updated["reserved_until"] is None
        assert conn.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()[0] == 5
        assert conn.execute(
            "SELECT COUNT(*) FROM payment_refunds WHERE order_id = ?",
            (order["id"],),
        ).fetchone()[0] == 0
        payment = conn.execute(
            "SELECT provider_status FROM payments WHERE order_id = ? AND provider = 'stripe'",
            (order["id"],),
        ).fetchone()
        assert payment["provider_status"] == "failed"
        event = conn.execute(
            """
            SELECT event_type, provider_status, processing_status, details
            FROM payment_events
            WHERE order_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (order["id"],),
        ).fetchone()
        assert event["event_type"] == "reservation_closed"
        assert event["provider_status"] == "failed"
        assert event["processing_status"] == "processed"
        assert '"stock_released":true' in event["details"]
        assert '"refund_created":false' in event["details"]

    def test_admin_records_abandoned_card_callback_outcome(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        conn.execute(
            "UPDATE orders SET payment_status = 'review_required' WHERE id = ?",
            (order["id"],),
        )

        updated = apply_manual_payment_action(
            conn,
            order["id"],
            "record_callback",
            "Left voicemail, try again tomorrow",
            callback_outcome="needs_follow_up",
            admin_id="admin-1",
            admin_email="owner@example.com",
        )

        assert updated["payment_method"] == "card"
        assert updated["payment_status"] == "review_required"
        event = conn.execute(
            "SELECT event_type, provider_status, admin_email, details "
            "FROM payment_events WHERE order_id = ? ORDER BY created_at DESC LIMIT 1",
            (order["id"],),
        ).fetchone()
        assert event["event_type"] == "manual_record_callback"
        assert event["provider_status"] == "review_required"
        assert event["admin_email"] == "owner@example.com"
        assert '"callback_outcome":"needs_follow_up"' in event["details"]

    def test_admin_converts_confirmed_abandoned_card_order_to_cod(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        conn.execute(
            """
            UPDATE orders
            SET payment_status = 'review_required', stripe_checkout_session_id = 'cs_abandoned'
            WHERE id = ?
            """,
            (order["id"],),
        )
        stripe_payment = conn.execute(
            "SELECT id FROM payments WHERE order_id = ? AND provider = 'stripe'",
            (order["id"],),
        ).fetchone()
        conn.execute(
            """
            UPDATE payments
            SET stripe_checkout_session_id = 'cs_abandoned', provider_status = 'review_required'
            WHERE id = ?
            """,
            (stripe_payment["id"],),
        )

        updated = apply_manual_payment_action(
            conn,
            order["id"],
            "convert_to_cod",
            "Customer confirmed by phone",
            callback_outcome="confirmed",
            admin_id="admin-1",
            admin_email="owner@example.com",
        )

        assert updated["payment_method"] == "cod"
        assert updated["payment_status"] == "cod_pending"
        assert updated["reserved_until"] is None
        provider_rows = conn.execute(
            "SELECT provider, provider_status FROM payments WHERE order_id = ? ORDER BY provider",
            (order["id"],),
        ).fetchall()
        assert [(row["provider"], row["provider_status"]) for row in provider_rows] == [
            ("cod", "cod_pending"),
            ("stripe", "review_required"),
        ]
        event = conn.execute(
            "SELECT event_type, provider, provider_status, details "
            "FROM payment_events WHERE order_id = ? ORDER BY created_at DESC LIMIT 1",
            (order["id"],),
        ).fetchone()
        assert event["event_type"] == "manual_convert_to_cod"
        assert event["provider"] == "cod"
        assert event["provider_status"] == "cod_pending"
        assert f'"original_card_payment_id":"{stripe_payment["id"]}"' in event["details"]
        assert '"original_stripe_checkout_session_id":"cs_abandoned"' in event["details"]

    def test_cancel_unconfirmed_abandoned_card_order_restores_stock_without_refund(
        self, conn, delivery
    ):
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
        assert conn.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()[0] == 3
        conn.execute(
            "UPDATE orders SET payment_status = 'review_required' WHERE id = ?",
            (order["id"],),
        )

        updated = apply_manual_payment_action(
            conn,
            order["id"],
            "cancel",
            "Customer did not confirm abandoned card payment",
        )

        assert updated["status"] == "cancelled"
        assert updated["payment_status"] == "failed"
        assert conn.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()[0] == 5
        assert conn.execute(
            "SELECT COUNT(*) FROM payment_refunds WHERE order_id = ?",
            (order["id"],),
        ).fetchone()[0] == 0

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

    def test_marks_old_card_failed_order_for_review(self, conn, delivery):
        order = _do_checkout(conn, delivery, payment_method="card")
        old_time = (datetime.now(UTC) - timedelta(hours=25)).strftime(_DT_FMT)
        conn.execute(
            "UPDATE orders SET created_at = ?, payment_status = 'failed' WHERE id = ?",
            (old_time, order["id"]),
        )
        conn.commit()
        self._run(conn)
        updated = get_order(conn, order["id"])
        assert updated["status"] == "pending"
        assert updated["payment_status"] == "review_required"


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
