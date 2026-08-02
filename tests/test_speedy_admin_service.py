"""Tests for the Speedy admin service orchestration layer."""

import json
import sqlite3
import uuid

import pytest
from pydantic import SecretStr

from app.config import get_settings
from app.database import init_db
from app.models.delivery import DeliveryInfo, DeliveryOffice
from app.services import return_service, speedy_admin_service, speedy_client
from app.services.order_service import checkout


@pytest.fixture()
def conn(tmp_path):
    db_path = str(tmp_path / "speedy-admin-service.db")
    init_db(db_path)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    yield db
    db.close()


@pytest.fixture(autouse=True)
def speedy_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "speedy_api_username", "speedy-user")
    monkeypatch.setattr(settings, "speedy_api_password", SecretStr("speedy-secret"))
    monkeypatch.setattr(settings, "speedy_client_id", "123456")


def _make_order(
    conn: sqlite3.Connection,
    *,
    courier: str = "speedy",
    status: str = "confirmed",
    tracking_number: str | None = None,
) -> str:
    session_id = uuid.uuid4().hex
    product_id = f"speedy-admin-{uuid.uuid4().hex[:8]}"
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
            office_name="Sofia Center",
            office_type="office",
            city="Sofia",
            phone="+359888123456",
        ),
    )
    order = checkout(
        conn=conn,
        session_id=session_id,
        customer_email="speedy@example.com",
        customer_name="Speedy Buyer",
        delivery=delivery,
        payment_method="cod",
    )
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order["id"]))
    if tracking_number:
        conn.execute(
            """
            UPDATE orders
            SET tracking_number = ?, tracking_carrier = 'speedy',
                tracking_url = ?, courier_provider = 'speedy',
                courier_shipment_number = ?, courier_sync_status = 'waybill_created'
            WHERE id = ?
            """,
            (
                tracking_number,
                f"https://www.speedy.bg/en/track-shipment?shipmentNumber={tracking_number}",
                tracking_number,
                order["id"],
            ),
        )
    conn.commit()
    return order["id"]


class TestSpeedyAdminHealthAndQueues:
    @pytest.mark.asyncio
    async def test_health_blocks_missing_configuration_without_calling_speedy(
        self, conn, monkeypatch
    ):
        settings = get_settings()
        monkeypatch.setattr(settings, "speedy_api_username", "")
        monkeypatch.setattr(settings, "speedy_api_password", SecretStr(""))
        monkeypatch.setattr(settings, "speedy_client_id", "")

        async def fail_if_called(**_kwargs):
            raise AssertionError("missing config must not call Speedy")

        monkeypatch.setattr(speedy_client, "get_own_client_id", fail_if_called)

        health = await speedy_admin_service.get_health(conn)

        assert health["status"] == "blocked"
        assert health["ok"] is False
        assert set(health["blockers"]) == {
            "username_missing",
            "password_missing",
            "client_id_missing",
        }

    @pytest.mark.asyncio
    async def test_health_uses_client_service_and_persists_safe_success(self, conn, monkeypatch):
        async def fake_client_id(**kwargs):
            assert kwargs["username"] == "speedy-user"
            assert kwargs["password"] == "speedy-secret"
            return "123456"

        monkeypatch.setattr(speedy_client, "get_own_client_id", fake_client_id)

        health = await speedy_admin_service.get_health(conn)

        assert health["status"] == "healthy"
        assert health["verified_client_id"] == "123456"
        stored = conn.execute(
            "SELECT value FROM site_settings WHERE key = 'speedy_admin_health'"
        ).fetchone()
        assert stored is not None
        assert "speedy-secret" not in stored["value"]

    def test_queues_include_ready_and_shipped_speedy_orders_only(self, conn):
        ready_id = _make_order(conn, status="confirmed")
        shipped_id = _make_order(conn, status="shipped", tracking_number="63689182611")
        _make_order(conn, courier="econt", status="confirmed")

        queues = speedy_admin_service.get_queues(conn)

        assert [order["order_id"] for order in queues["ready_to_ship"]] == [ready_id]
        assert [order["order_id"] for order in queues["shipped"]] == [shipped_id]


class TestSpeedyAdminActions:
    @pytest.mark.asyncio
    async def test_create_waybill_uses_existing_ship_transition_and_records_event(
        self, conn, monkeypatch
    ):
        order_id = _make_order(conn, status="confirmed")

        async def fake_create_shipment(**kwargs):
            assert kwargs["username"] == "speedy-user"
            assert kwargs["password"] == "speedy-secret"
            return "63689182611"

        monkeypatch.setattr(speedy_client, "create_shipment", fake_create_shipment)

        result = await speedy_admin_service.create_or_reuse_waybill(
            conn,
            order_id,
            actor_user_id="admin-1",
        )

        assert result["status"] == "created"
        assert result["shipment_number"] == "63689182611"
        row = conn.execute(
            """
            SELECT status, tracking_number, tracking_carrier, courier_provider,
                   courier_shipment_number, courier_sync_status
            FROM orders WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        assert dict(row) == {
            "status": "shipped",
            "tracking_number": "63689182611",
            "tracking_carrier": "speedy",
            "courier_provider": "speedy",
            "courier_shipment_number": "63689182611",
            "courier_sync_status": "waybill_created",
        }
        event = conn.execute(
            "SELECT action, status, actor_user_id, request_json FROM order_courier_events"
        ).fetchone()
        assert event["action"] == "create_waybill"
        assert event["status"] == "success"
        assert event["actor_user_id"] == "admin-1"
        assert "speedy-secret" not in event["request_json"]

    @pytest.mark.asyncio
    async def test_print_and_track_record_events_without_credentials(self, conn):
        order_id = _make_order(conn, status="shipped", tracking_number="63689182611")

        async def fake_print_label(**kwargs):
            assert kwargs["tracking_number"] == "63689182611"
            assert kwargs["password"] == "speedy-secret"
            return b"%PDF-test"

        async def fake_track_shipment(**kwargs):
            assert kwargs["tracking_number"] == "63689182611"
            return "in_transit"

        shipment_number, pdf = await speedy_admin_service.print_order_label(
            conn,
            order_id,
            print_label_func=fake_print_label,
        )
        tracking = await speedy_admin_service.refresh_tracking(
            conn,
            order_id,
            track_shipment_func=fake_track_shipment,
        )

        assert shipment_number == "63689182611"
        assert pdf == b"%PDF-test"
        assert tracking["courier_status"] == "in_transit"
        events = conn.execute(
            "SELECT action, request_json, response_json FROM order_courier_events ORDER BY id"
        ).fetchall()
        assert [event["action"] for event in events] == ["print_label", "refresh_tracking"]
        serialized = json.dumps([dict(event) for event in events])
        assert "speedy-secret" not in serialized
        assert "password" not in serialized.casefold()

    @pytest.mark.asyncio
    async def test_cancel_marks_shipment_cancelled_without_cancelling_order(
        self, conn, monkeypatch
    ):
        order_id = _make_order(conn, status="shipped", tracking_number="63689182611")

        async def fake_cancel(shipment_id, **kwargs):
            assert shipment_id == "63689182611"
            assert kwargs["comment"] == "admin cancelled"
            return {"cancelled": True, "shipment_id": shipment_id}

        monkeypatch.setattr(speedy_client, "cancel_shipment", fake_cancel)

        result = await speedy_admin_service.cancel_order_shipment(
            conn,
            order_id,
            comment="admin cancelled",
        )

        assert result["status"] == "cancelled"
        row = conn.execute(
            """
            SELECT status, tracking_number, courier_status, courier_sync_status
            FROM orders WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        assert row["status"] == "shipped"
        assert row["tracking_number"] == "63689182611"
        assert row["courier_status"] == "cancelled"
        assert row["courier_sync_status"] == "shipment_cancelled"

    @pytest.mark.asyncio
    async def test_cancel_rejection_preserves_tracking_and_redacts_error(self, conn, monkeypatch):
        order_id = _make_order(conn, status="shipped", tracking_number="63689182611")

        async def fail_cancel(*_args, **_kwargs):
            raise speedy_client.SpeedyValidationError(
                "already picked up",
                endpoint="shipment/cancel",
                details={"password": "speedy-secret", "body": {"password": "speedy-secret"}},
            )

        monkeypatch.setattr(speedy_client, "cancel_shipment", fail_cancel)

        with pytest.raises(speedy_client.SpeedyValidationError):
            await speedy_admin_service.cancel_order_shipment(conn, order_id)

        row = conn.execute(
            "SELECT tracking_number, courier_status, courier_sync_status FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert row["tracking_number"] == "63689182611"
        assert row["courier_status"] is None
        assert row["courier_sync_status"] == "waybill_created"
        event = conn.execute(
            "SELECT status, error_json FROM order_courier_events WHERE action = 'cancel_shipment'"
        ).fetchone()
        assert event["status"] == "failed"
        assert "speedy-secret" not in event["error_json"]
        assert json.loads(event["error_json"])["details"]["password"] == "<redacted>"

    @pytest.mark.asyncio
    async def test_pickup_terms_and_request_validate_shipments_and_record_events(
        self, conn, monkeypatch
    ):
        _make_order(conn, status="shipped", tracking_number="63689182611")

        async def fake_terms(**kwargs):
            assert kwargs["client_id"] == "123456"
            return ["2026-08-02T14:00:00+03:00"]

        async def fake_pickup(**kwargs):
            assert kwargs["shipment_ids"] == ["63689182611"]
            assert kwargs["contact_name"] == "Mira"
            return [{"id": "pickup-1", "shipmentIds": ["63689182611"]}]

        monkeypatch.setattr(speedy_client, "pickup_terms", fake_terms)
        monkeypatch.setattr(speedy_client, "request_pickup", fake_pickup)

        with pytest.raises(speedy_admin_service.SpeedyAdminValidationError):
            await speedy_admin_service.pickup_terms_for_shipments(conn, [])

        terms = await speedy_admin_service.pickup_terms_for_shipments(conn, ["63689182611"])
        pickup = await speedy_admin_service.request_pickup(
            conn,
            shipment_ids=["63689182611"],
            pickup_datetime="2026-08-02T14:00:00+03:00",
            visit_end_time="17:00",
            contact_name="Mira",
            phone="+359888123456",
        )

        assert terms["cutoffs"] == ["2026-08-02T14:00:00+03:00"]
        assert pickup["orders"] == [{"id": "pickup-1", "shipmentIds": ["63689182611"]}]
        actions = [
            row["action"]
            for row in conn.execute(
                "SELECT action FROM order_courier_events ORDER BY id"
            ).fetchall()
        ]
        assert actions == ["pickup_terms", "request_pickup"]

    @pytest.mark.asyncio
    async def test_returned_tracking_creates_single_speedy_return_review_signal(self, conn):
        order_id = _make_order(conn, status="shipped", tracking_number="63689182611")

        async def fake_track_shipment(**_kwargs):
            return "returned"

        await speedy_admin_service.refresh_tracking(
            conn,
            order_id,
            track_shipment_func=fake_track_shipment,
        )
        await speedy_admin_service.refresh_tracking(
            conn,
            order_id,
            track_shipment_func=fake_track_shipment,
        )

        cases = conn.execute(
            "SELECT reason, source, status FROM order_returns WHERE order_id = ?",
            (order_id,),
        ).fetchall()
        assert [dict(case) for case in cases] == [
            {"reason": "not_picked_up", "source": "speedy", "status": "requested"}
        ]

    @pytest.mark.asyncio
    async def test_tracking_event_stores_raw_details_when_available(self, conn):
        order_id = _make_order(conn, status="shipped", tracking_number="63689182611")
        tracking_details = {
            "parcels": [
                {
                    "id": "63689182611",
                    "operations": [{"description": "Returned to sender", "operationCode": 42}],
                }
            ]
        }

        async def fake_track_shipment(**_kwargs):
            return {"courier_status": "returned", "tracking_details": tracking_details}

        await speedy_admin_service.refresh_tracking(
            conn,
            order_id,
            track_shipment_func=fake_track_shipment,
        )

        event = conn.execute(
            "SELECT response_json FROM order_courier_events WHERE action = 'refresh_tracking'"
        ).fetchone()
        response = json.loads(event["response_json"])
        assert response["courier_status"] == "returned"
        assert response["tracking_details"] == tracking_details

    @pytest.mark.asyncio
    async def test_failed_tracking_signal_does_not_mutate_business_state(self, conn):
        order_id = _make_order(conn, status="shipped", tracking_number="63689182611")
        before = conn.execute(
            """
            SELECT o.status, o.payment_status, oi.product_id, p.stock
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN products p ON p.id = oi.product_id
            WHERE o.id = ?
            """,
            (order_id,),
        ).fetchone()

        async def fake_track_shipment(**_kwargs):
            return "failed"

        await speedy_admin_service.refresh_tracking(
            conn,
            order_id,
            track_shipment_func=fake_track_shipment,
        )

        after = conn.execute(
            """
            SELECT o.status, o.payment_status, o.courier_status, p.stock
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN products p ON p.id = oi.product_id
            WHERE o.id = ?
            """,
            (order_id,),
        ).fetchone()
        assert after["status"] == before["status"]
        assert after["payment_status"] == before["payment_status"]
        assert after["stock"] == before["stock"]
        assert after["courier_status"] == "failed"
        case = conn.execute(
            "SELECT reason, source, status FROM order_returns WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        assert dict(case) == {"reason": "other", "source": "speedy", "status": "requested"}

    @pytest.mark.asyncio
    async def test_returned_tracking_does_not_advance_existing_return_case(self, conn):
        order_id = _make_order(conn, status="shipped", tracking_number="63689182611")
        existing_case = return_service.create_return_case(
            conn,
            order_id=order_id,
            reason="not_picked_up",
            source="admin",
            status="return_in_transit",
        )

        async def fake_track_shipment(**_kwargs):
            return "returned"

        await speedy_admin_service.refresh_tracking(
            conn,
            order_id,
            track_shipment_func=fake_track_shipment,
        )

        cases = conn.execute(
            """
            SELECT id, status, received_at, inspected_at, closed_at
            FROM order_returns WHERE order_id = ?
            """,
            (order_id,),
        ).fetchall()
        assert len(cases) == 1
        case = cases[0]
        assert case["id"] == existing_case["id"]
        assert case["status"] == "return_in_transit"
        assert case["received_at"] is None
        assert case["inspected_at"] is None
        assert case["closed_at"] is None
