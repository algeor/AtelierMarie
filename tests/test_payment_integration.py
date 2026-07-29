"""Tests for payment integration: checkout service, update_status, mark_bank_transfer_paid,
payment_service handlers, webhook route, 24h auto-cancel, and order_cancelled email template.
"""

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.database import init_db
from app.email.renderer import render_template
from app.models.delivery import DeliveryInfo, DeliveryOffice
from app.services.order_service import (
    PaymentAlreadyPaidError as BankTransferAlreadyPaidError,
)
from app.services.order_service import (
    WrongPaymentMethodError as InvalidPaymentMethodError,
)
from app.services.order_service import (
    checkout,
    mark_bank_transfer_paid,
    update_status,
)
from app.services.order_service import (
    get_order_admin as get_order,
)
from app.services.payment_service import (
    handle_payment_succeeded,
    handle_session_expired,
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
