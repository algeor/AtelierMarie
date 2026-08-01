"""Tests for async courier status polling and leases."""

import inspect
import json
import sqlite3
import uuid

import pytest
from pydantic import SecretStr

from app.config import get_settings
from app.database import init_db
from app.models.delivery import DeliveryInfo, DeliveryOffice
from app.models.econt import EcontShipmentStatus, EcontTraceEvent
from app.services import courier_polling_service
from app.services.order_service import checkout
from app.services.speedy_client import SpeedyTransientError


def test_courier_polling_code_does_not_use_thread_offload():
    from app.main import courier_status_polling_loop

    assert "to_thread" not in inspect.getsource(courier_polling_service)
    assert "to_thread" not in inspect.getsource(courier_status_polling_loop)


class FakeEcontClient:
    def __init__(self, status: EcontShipmentStatus):
        self.status = status
        self.traced: list[str] = []

    async def get_trace(self, shipment_number: str) -> EcontShipmentStatus:
        self.traced.append(shipment_number)
        return self.status


@pytest.fixture()
def conn(tmp_path):
    db_path = str(tmp_path / "courier-polling.db")
    init_db(db_path)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    yield db
    db.close()


@pytest.fixture(autouse=True)
def courier_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "speedy_api_username", "speedy-user")
    monkeypatch.setattr(settings, "speedy_api_password", SecretStr("speedy-secret"))
    monkeypatch.setattr(settings, "speedy_client_id", "123456")
    monkeypatch.setattr(settings, "courier_polling_enabled", True)
    monkeypatch.setattr(settings, "courier_polling_speedy_enabled", True)
    monkeypatch.setattr(settings, "courier_polling_econt_enabled", True)
    monkeypatch.setattr(settings, "courier_polling_interval_seconds", 60)
    monkeypatch.setattr(settings, "courier_polling_batch_size", 10)
    monkeypatch.setattr(settings, "courier_polling_lease_seconds", 30)
    monkeypatch.setattr(settings, "courier_polling_max_backoff_seconds", 600)


def _make_order(
    conn: sqlite3.Connection,
    *,
    courier: str = "speedy",
    status: str = "shipped",
    tracking_number: str | None = "63689182611",
) -> str:
    session_id = uuid.uuid4().hex
    product_id = f"poll-product-{uuid.uuid4().hex[:8]}"
    conn.execute(
        "INSERT INTO sessions (id, expires_at) VALUES (?, datetime('now', '+1 day'))",
        (session_id,),
    )
    conn.execute(
        """
        INSERT INTO products (id, name_en, price_cents, stock, weight_grams, is_active)
        VALUES (?, 'Courier Candle', 2500, 10, 500, 1)
        """,
        (product_id,),
    )
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, 1)",
        (session_id, product_id),
    )
    conn.commit()
    delivery = DeliveryInfo(
        method="office",
        office=DeliveryOffice(
            courier=courier,
            office_id="2" if courier == "speedy" else "econt-1029",
            office_code="1127" if courier == "econt" else None,
            office_name="Sofia Center",
            office_type="office",
            city="Sofia",
            phone="+359888123456",
        ),
    )
    order = checkout(
        conn=conn,
        session_id=session_id,
        customer_email="poll@example.com",
        customer_name="Polling Buyer",
        delivery=delivery,
        payment_method="cod",
    )
    conn.execute(
        """
        UPDATE orders
        SET status = ?, tracking_number = ?, tracking_carrier = ?,
            courier_provider = ?, courier_shipment_number = ?
        WHERE id = ?
        """,
        (status, tracking_number, courier, courier, tracking_number, order["id"]),
    )
    conn.commit()
    return order["id"]


def test_acquire_due_orders_respects_batch_and_existing_lease(conn):
    first_id = _make_order(conn, tracking_number="111")
    second_id = _make_order(conn, tracking_number="222")
    conn.execute(
        """
        UPDATE orders
        SET courier_poll_lease_token = 'busy',
            courier_poll_lease_expires_at = datetime('now', '+5 minutes')
        WHERE id = ?
        """,
        (second_id,),
    )

    rows = courier_polling_service.acquire_due_orders(
        conn,
        batch_size=1,
        lease_seconds=30,
        providers={"speedy"},
    )

    assert [row["id"] for row in rows] == [first_id]
    leased = conn.execute(
        "SELECT courier_poll_lease_token FROM orders WHERE id = ?",
        (first_id,),
    ).fetchone()
    assert leased["courier_poll_lease_token"]


@pytest.mark.asyncio
async def test_poll_due_shipments_success_stores_speedy_evidence_and_schedules_next(conn):
    order_id = _make_order(conn, tracking_number="63689182611")
    tracking_details = {"parcels": [{"operations": [{"description": "Returned to sender"}]}]}

    async def fake_track(**_kwargs):
        return {"courier_status": "returned", "tracking_details": tracking_details}

    result = await courier_polling_service.poll_due_shipments(
        conn,
        providers={"speedy"},
        speedy_track_func=fake_track,
    )

    assert result == {"acquired": 1, "succeeded": 1, "failed": 0, "skipped": 0}
    order = conn.execute(
        """
        SELECT courier_status, courier_poll_attempts, courier_next_poll_at,
               courier_poll_lease_token
        FROM orders WHERE id = ?
        """,
        (order_id,),
    ).fetchone()
    assert order["courier_status"] == "returned"
    assert order["courier_poll_attempts"] == 0
    assert order["courier_next_poll_at"] is not None
    assert order["courier_poll_lease_token"] is None
    event = conn.execute(
        "SELECT response_json FROM order_courier_events WHERE order_id = ?",
        (order_id,),
    ).fetchone()
    assert json.loads(event["response_json"])["tracking_details"] == tracking_details
    case = conn.execute(
        "SELECT reason, source, status FROM order_returns WHERE order_id = ?",
        (order_id,),
    ).fetchone()
    assert dict(case) == {"reason": "not_picked_up", "source": "speedy", "status": "requested"}


@pytest.mark.asyncio
async def test_poll_due_shipments_supports_econt_trace_path(conn):
    order_id = _make_order(conn, courier="econt", tracking_number="1234567890")
    client = FakeEcontClient(
        EcontShipmentStatus(
            shipment_number="1234567890",
            short_delivery_status_en="Returned to sender",
            events=[EcontTraceEvent(type="returned_to_sender")],
        )
    )

    result = await courier_polling_service.poll_due_shipments(
        conn,
        providers={"econt"},
        econt_client=client,
    )

    assert result["succeeded"] == 1
    assert client.traced == ["1234567890"]
    order = conn.execute(
        "SELECT courier_status, courier_poll_attempts FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    assert order["courier_status"] == "returned"
    assert order["courier_poll_attempts"] == 0


@pytest.mark.asyncio
async def test_failed_poll_records_backoff_and_safe_error(conn):
    order_id = _make_order(conn, tracking_number="63689182611")

    async def fail_track(**_kwargs):
        raise SpeedyTransientError(
            "timeout",
            endpoint="track",
            details={"password": "speedy-secret"},
        )

    result = await courier_polling_service.poll_due_shipments(
        conn,
        providers={"speedy"},
        speedy_track_func=fail_track,
    )

    assert result["failed"] == 1
    row = conn.execute(
        """
        SELECT courier_sync_status, courier_last_error, courier_poll_attempts,
               courier_next_poll_at, courier_poll_lease_token
        FROM orders WHERE id = ?
        """,
        (order_id,),
    ).fetchone()
    assert row["courier_sync_status"] == "poll_failed"
    assert row["courier_poll_attempts"] == 1
    assert row["courier_next_poll_at"] is not None
    assert row["courier_poll_lease_token"] is None
    assert "speedy-secret" not in row["courier_last_error"]


@pytest.mark.asyncio
async def test_manual_refresh_uses_same_async_provider_path(conn):
    order_id = _make_order(conn, tracking_number="63689182611")

    async def fake_track(**_kwargs):
        return {"courier_status": "delivered", "tracking_details": {"ok": True}}

    result = await courier_polling_service.refresh_order_now(
        conn,
        order_id,
        provider="speedy",
        speedy_track_func=fake_track,
    )

    assert result["courier_status"] == "delivered"
    row = conn.execute(
        "SELECT courier_status, courier_last_polled_at FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    assert row["courier_status"] == "delivered"
    assert row["courier_last_polled_at"] is not None
