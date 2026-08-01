"""Tests for Econt fulfillment service mapping, persistence, and audit behavior."""

import json
import sqlite3
import uuid

import pytest
from pydantic import SecretStr

from app.config import get_settings
from app.database import init_db
from app.models.delivery import DeliveryInfo, DeliveryOffice
from app.models.econt import EcontShipmentStatus, EcontTraceEvent
from app.services import return_service
from app.services.econt_delivery_client import EcontTransientError
from app.services.econt_fulfillment_service import (
    EcontFulfillmentValidationError,
    build_order_payload,
    create_label,
    create_label_and_mark_shipped,
    delete_label,
    record_manual_status,
    refresh_trace,
    repair_order_fields,
    sync_order,
    validate_label_readiness,
)
from app.services.order_service import checkout


class FakeEcontClient:
    def __init__(self):
        self.updated_orders = []
        self.created_orders = []
        self.deleted_shipments = []
        self.traced_shipments = []
        self.next_update_response = {"orderID": "remote-order-1"}
        self.next_shipment = EcontShipmentStatus(
            shipment_number="1234567890",
            pdf_url="https://label.test/123.pdf",
        )
        self.next_trace = EcontShipmentStatus(
            shipment_number="1234567890",
            status="delivered",
        )
        self.raise_on_create = None

    async def update_order(self, order):
        self.updated_orders.append(order)
        return self.next_update_response

    async def create_awb(self, order):
        self.created_orders.append(order)
        if self.raise_on_create:
            raise self.raise_on_create
        return self.next_shipment

    async def delete_label(self, shipment_number):
        self.deleted_shipments.append(shipment_number)
        return {"deleted": True}

    async def get_trace(self, shipment_number):
        self.traced_shipments.append(shipment_number)
        return self.next_trace


@pytest.fixture()
def conn(tmp_path):
    path = str(tmp_path / "econt-fulfillment.db")
    init_db(path)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    yield db
    db.close()


@pytest.fixture()
def econt_secret(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "econt_delivery_private_key", SecretStr("private-demo-key"))
    yield


def _configure_econt(
    conn: sqlite3.Connection,
    *,
    auto_confirm_on_label: bool = False,
    auto_delivered_on_trace: bool = False,
) -> None:
    conn.execute(
        """
        UPDATE econt_settings
        SET enabled = 1, shop_id = 'shop-1', sender_office_code = '1127',
            default_pack_count = 2, shipment_description = 'Atelier Marie candles',
            auto_confirm_on_label = ?, auto_delivered_on_trace = ?
        WHERE id = 'default'
        """,
        (1 if auto_confirm_on_label else 0, 1 if auto_delivered_on_trace else 0),
    )
    conn.commit()


def _seed_admin(conn: sqlite3.Connection, user_id: str = "admin-1") -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO users (id, google_id, email, name, is_admin)
        VALUES (?, ?, ?, 'Admin', 1)
        """,
        (user_id, f"google-{user_id}", f"{user_id}@example.com"),
    )
    conn.commit()


def _make_order(conn: sqlite3.Connection, *, courier="econt", payment_method="cod") -> str:
    session_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO sessions (id, expires_at) VALUES (?, datetime('now', '+1 day'))",
        (session_id,),
    )
    conn.execute(
        """
        INSERT INTO products (id, name_en, price_cents, stock, weight_grams, is_active)
        VALUES ('weighted-candle', 'Weighted Candle', 2500, 10, 500, 1)
        """
    )
    conn.execute(
        """
        INSERT INTO cart_items (session_id, product_id, quantity)
        VALUES (?, 'weighted-candle', 2)
        """,
        (session_id,),
    )
    conn.commit()
    delivery = DeliveryInfo(
        method="office",
        office=DeliveryOffice(
            courier=courier,
            office_id="econt-1029" if courier == "econt" else "2",
            office_name="София",
            office_type="office",
            city="София",
            phone="+359888123456",
        ),
    )
    order = checkout(
        conn=conn,
        session_id=session_id,
        customer_email="mira@example.com",
        customer_name="Mira",
        delivery=delivery,
        payment_method=payment_method,
    )
    conn.execute("UPDATE orders SET status = 'confirmed' WHERE id = ?", (order["id"],))
    conn.commit()
    return order["id"]


class TestEcontPayloadMapping:
    def test_builds_office_cod_payload_with_weights(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn)

        payload = build_order_payload(conn, order_id)
        data = payload.model_dump(by_alias=True, exclude_none=True)

        assert data["orderNumber"] == order_id
        assert data["cod"] is True
        assert data["currency"] == "EUR"
        assert data["orderSum"] == 50.0
        assert "declaredValue" not in data
        assert data["shipmentDescription"] == "Atelier Marie candles"
        assert data["packCount"] == 2
        assert data["customerInfo"]["name"] == "Mira"
        assert data["customerInfo"]["officeCode"] == "1127"
        assert data["senderInfo"]["officeCode"] == "1127"
        assert data["items"][0]["totalWeight"] == 1.0

    def test_declared_value_uses_configured_courier_currency_amount(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn)
        conn.execute(
            """
            UPDATE econt_settings
            SET declared_value_enabled = 1, courier_currency = 'BGN',
                currency_conversion_rate = 1.95583
            WHERE id = 'default'
            """
        )
        conn.commit()

        payload = build_order_payload(conn, order_id)
        data = payload.model_dump(by_alias=True, exclude_none=True)

        assert data["currency"] == "BGN"
        assert data["orderSum"] == 97.79
        assert data["declaredValue"] == 97.79

    def test_non_cod_maps_cod_false(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn, payment_method="bank_transfer")

        payload = build_order_payload(conn, order_id)

        assert payload.cod is False

    def test_builds_return_and_reject_instruction_payload_fields(self, conn, econt_secret):
        _configure_econt(conn)
        conn.execute(
            """
            UPDATE econt_settings
            SET return_parcel_destination = 'sender', days_until_return = 5,
                return_parcel_payment_side = 'sender', reject_action = 'return_to_sender',
                reject_payment_side = 'receiver', reject_return_payment_side = 'sender'
            WHERE id = 'default'
            """
        )
        conn.commit()
        order_id = _make_order(conn)

        payload = build_order_payload(conn, order_id)
        data = payload.model_dump(by_alias=True, exclude_none=True)

        assert data["returnParcelDestination"] == "sender"
        assert data["daysUntilReturn"] == 5
        assert data["returnParcelPaymentSide"] == "sender"
        assert data["executeIfNotTaken"] == "return_to_sender"
        assert data["rejectAction"] == "return_to_sender"
        assert data["rejectPaymentSide"] == "receiver"
        assert data["rejectReturnPaymentSide"] == "sender"


class TestEcontReadiness:
    def test_readiness_lists_settings_and_order_blockers(self, conn):
        order_id = _make_order(conn)
        conn.execute("UPDATE orders SET status = 'pending' WHERE id = ?", (order_id,))

        readiness = validate_label_readiness(conn, order_id)

        assert readiness["ready"] is False
        assert "settings_disabled" in readiness["blockers"]
        assert "settings_private_key_missing" in readiness["blockers"]
        assert "order_status_not_supported" in readiness["blockers"]

    @pytest.mark.asyncio
    async def test_speedy_order_is_rejected_before_econt_call(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn, courier="speedy")

        with pytest.raises(EcontFulfillmentValidationError) as exc_info:
            await create_label(conn, order_id, client=FakeEcontClient())

        assert "order_not_econt" in exc_info.value.blockers

    @pytest.mark.asyncio
    async def test_missing_econt_office_code_blocks_label_before_courier_call(
        self, conn, econt_secret
    ):
        _configure_econt(conn)
        order_id = _make_order(conn)
        row = conn.execute("SELECT delivery_details FROM orders WHERE id = ?", (order_id,)).fetchone()
        details = json.loads(row["delivery_details"])
        details.pop("office_code", None)
        conn.execute(
            "UPDATE orders SET delivery_details = ? WHERE id = ?",
            (json.dumps(details), order_id),
        )
        conn.commit()
        client = FakeEcontClient()

        readiness = validate_label_readiness(conn, order_id)
        with pytest.raises(EcontFulfillmentValidationError) as exc_info:
            await create_label(conn, order_id, client=client)

        assert "order_office_code_missing" in readiness["blockers"]
        assert "order_office_code_missing" in exc_info.value.blockers
        assert client.created_orders == []


class TestEcontActions:
    @pytest.mark.asyncio
    async def test_sync_order_persists_remote_id_and_event(self, conn, econt_secret):
        _configure_econt(conn)
        _seed_admin(conn)
        order_id = _make_order(conn)
        client = FakeEcontClient()

        result = await sync_order(conn, order_id, client=client, actor_user_id="admin-1")

        assert result == {"status": "synced", "courier_order_id": "remote-order-1"}
        row = conn.execute(
            "SELECT courier_order_id, courier_sync_status FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert row["courier_order_id"] == "remote-order-1"
        assert row["courier_sync_status"] == "synced"
        event = conn.execute(
            "SELECT action, status, actor_user_id FROM order_courier_events"
        ).fetchone()
        assert event["action"] == "sync_order"
        assert event["status"] == "success"
        assert event["actor_user_id"] == "admin-1"

    def test_repair_order_fields_records_audit_event(self, conn, econt_secret):
        _configure_econt(conn)
        _seed_admin(conn)
        order_id = _make_order(conn)

        result = repair_order_fields(
            conn,
            order_id,
            office_code="1127",
            pack_count=3,
            actor_user_id="admin-1",
        )

        assert result["courier_sync_status"] == "repaired"
        event = conn.execute(
            """
            SELECT action, status, request_json, response_json, actor_user_id
            FROM order_courier_events
            """
        ).fetchone()
        assert event["action"] == "repair_order"
        assert event["status"] == "success"
        assert event["actor_user_id"] == "admin-1"
        assert json.loads(event["request_json"])["pack_count"] == 3
        assert json.loads(event["response_json"])["courier_sync_status"] == "repaired"

    @pytest.mark.asyncio
    async def test_create_label_persists_metadata_tracking_and_event(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn)
        client = FakeEcontClient()

        result = await create_label(conn, order_id, client=client)

        assert result["status"] == "created"
        assert result["shipment_number"] == "1234567890"
        row = conn.execute(
            """
            SELECT courier_provider, courier_shipment_number, courier_label_url,
                   courier_sync_status, tracking_number, tracking_carrier, tracking_url
            FROM orders WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        assert row["courier_provider"] == "econt"
        assert row["courier_shipment_number"] == "1234567890"
        assert row["courier_label_url"] == "https://label.test/123.pdf"
        assert row["courier_sync_status"] == "label_created"
        assert row["tracking_number"] == "1234567890"
        assert row["tracking_carrier"] == "econt"
        assert row["tracking_url"].endswith("/1234567890")
        event = conn.execute(
            "SELECT action, status, response_json FROM order_courier_events"
        ).fetchone()
        assert event["action"] == "create_label"
        assert event["status"] == "success"
        assert json.loads(event["response_json"])["shipmentNumber"] == "1234567890"

    @pytest.mark.asyncio
    async def test_create_label_rejects_pending_order_even_when_auto_confirm_setting_enabled(
        self, conn, econt_secret
    ):
        _configure_econt(conn, auto_confirm_on_label=True)
        order_id = _make_order(conn)
        conn.execute("UPDATE orders SET status = 'pending' WHERE id = ?", (order_id,))
        conn.commit()
        client = FakeEcontClient()

        readiness = validate_label_readiness(conn, order_id)
        with pytest.raises(EcontFulfillmentValidationError) as exc_info:
            await create_label(conn, order_id, client=client)

        assert readiness["ready"] is False
        assert "order_status_not_supported" in readiness["blockers"]
        assert "order_status_not_supported" in exc_info.value.blockers
        row = conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        assert row["status"] == "pending"
        assert client.created_orders == []

    @pytest.mark.asyncio
    async def test_create_label_is_idempotent_when_shipment_exists(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn)
        conn.execute(
            """
            UPDATE orders
            SET courier_shipment_number = 'existing', courier_label_url = 'https://label'
            WHERE id = ?
            """,
            (order_id,),
        )
        client = FakeEcontClient()

        result = await create_label(conn, order_id, client=client)

        assert result == {
            "status": "existing",
            "shipment_number": "existing",
            "label_url": "https://label",
            "tracking_url": "https://www.econt.com/services/track-shipment/existing",
        }
        assert client.created_orders == []
        event = conn.execute("SELECT action, status FROM order_courier_events").fetchone()
        assert event["action"] == "create_label"
        assert event["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_create_label_and_mark_shipped_moves_confirmed_order(self, conn, econt_secret):
        _configure_econt(conn)
        _seed_admin(conn)
        order_id = _make_order(conn)
        client = FakeEcontClient()

        result = await create_label_and_mark_shipped(
            conn,
            order_id,
            client=client,
            actor_user_id="admin-1",
        )

        assert result["status"] == "shipped"
        assert result["status_updated_to"] == "shipped"
        assert result["shipment_number"] == "1234567890"
        row = conn.execute(
            "SELECT status, tracking_number, tracking_carrier FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert row["status"] == "shipped"
        assert row["tracking_number"] == "1234567890"
        assert row["tracking_carrier"] == "econt"
        actions = [
            r["action"]
            for r in conn.execute(
                "SELECT action FROM order_courier_events ORDER BY id"
            ).fetchall()
        ]
        assert actions == ["create_label", "mark_shipped"]

    @pytest.mark.asyncio
    async def test_create_label_and_mark_shipped_failure_keeps_order_confirmed(
        self, conn, econt_secret
    ):
        _configure_econt(conn)
        order_id = _make_order(conn)
        client = FakeEcontClient()
        client.raise_on_create = EcontTransientError("timeout")

        with pytest.raises(EcontTransientError):
            await create_label_and_mark_shipped(conn, order_id, client=client)

        row = conn.execute(
            "SELECT status, tracking_number, courier_sync_status FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert row["status"] == "confirmed"
        assert row["tracking_number"] is None
        assert row["courier_sync_status"] == "failed"

    @pytest.mark.asyncio
    async def test_failed_create_label_persists_redacted_error(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn)
        client = FakeEcontClient()
        client.raise_on_create = EcontTransientError(
            "timeout",
            details={"headers": {"Authorization": "private-demo-key"}},
        )

        with pytest.raises(EcontTransientError):
            await create_label(conn, order_id, client=client)

        row = conn.execute(
            "SELECT courier_sync_status, courier_last_error FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert row["courier_sync_status"] == "failed"
        assert "private-demo-key" not in row["courier_last_error"]
        assert "<redacted>" in row["courier_last_error"]
        event = conn.execute("SELECT status, error_json FROM order_courier_events").fetchone()
        assert event["status"] == "failed"
        assert "private-demo-key" not in event["error_json"]

    @pytest.mark.asyncio
    async def test_refresh_trace_persists_trace_sync_event(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn)
        conn.execute(
            """
            UPDATE orders
            SET courier_shipment_number = '1234567890', tracking_number = '1234567890'
            WHERE id = ?
            """,
            (order_id,),
        )
        client = FakeEcontClient()

        result = await refresh_trace(conn, order_id, client=client)

        assert result["status"] == "trace_synced"
        row = conn.execute(
            "SELECT courier_sync_status FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert row["courier_sync_status"] == "trace_synced"
        event = conn.execute("SELECT action, status FROM order_courier_events").fetchone()
        assert event["action"] == "refresh_trace"
        assert event["status"] == "success"

    @pytest.mark.asyncio
    async def test_refresh_trace_does_not_auto_mark_shipped_order_delivered_when_enabled(
        self, conn, econt_secret
    ):
        _configure_econt(conn, auto_delivered_on_trace=True)
        order_id = _make_order(conn)
        conn.execute(
            """
            UPDATE orders
            SET status = 'shipped', courier_shipment_number = '1234567890',
                tracking_number = '1234567890', tracking_carrier = 'econt'
            WHERE id = ?
            """,
            (order_id,),
        )
        conn.commit()
        client = FakeEcontClient()

        result = await refresh_trace(conn, order_id, client=client)

        assert result["status"] == "trace_synced"
        row = conn.execute(
            "SELECT status, payment_status FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert row["status"] == "shipped"
        assert row["payment_status"] == "cod_pending"
        event = conn.execute(
            "SELECT status FROM order_courier_events WHERE action = 'refresh_trace'"
        ).fetchone()
        assert event["status"] == "success"
        auto_event = conn.execute(
            "SELECT 1 FROM order_courier_events WHERE action = 'auto_delivered_on_trace'"
        ).fetchone()
        assert auto_event is None

    @pytest.mark.asyncio
    async def test_refresh_trace_normalizes_returning_status_and_preserves_metadata(
        self, conn, econt_secret
    ):
        _configure_econt(conn)
        order_id = _make_order(conn)
        conn.execute(
            """
            UPDATE orders
            SET status = 'shipped', courier_shipment_number = '1234567890',
                tracking_number = '1234567890', tracking_carrier = 'econt'
            WHERE id = ?
            """,
            (order_id,),
        )
        stock_before = conn.execute(
            "SELECT stock FROM products WHERE id = 'weighted-candle'"
        ).fetchone()[0]
        conn.commit()
        client = FakeEcontClient()
        client.next_trace = EcontShipmentStatus(
            shipment_number="1234567890",
            short_delivery_status_en="Is returning to sender",
            return_shipment_url="https://econt.test/return/123",
            previous_shipment_number="1111111111",
            next_shipments=[{"shipmentNumber": "2222222222"}],
            last_processed_instruction="return_to_sender",
            cd_collected_amount=25.0,
            cd_collected_time="2026-08-01 10:00:00",
            cd_paid_amount=24.0,
            cd_paid_time="2026-08-02 10:00:00",
            events=[EcontTraceEvent(type="is_returning_to_sender")],
        )

        result = await refresh_trace(conn, order_id, client=client)

        assert result["courier_status"] == "return_in_transit"
        order = conn.execute(
            "SELECT status, payment_status, courier_status FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert order["status"] == "shipped"
        assert order["payment_status"] == "cod_pending"
        assert order["courier_status"] == "return_in_transit"
        assert conn.execute(
            "SELECT stock FROM products WHERE id = 'weighted-candle'"
        ).fetchone()[0] == stock_before
        case = conn.execute(
            "SELECT reason, source, status FROM order_returns WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        assert dict(case) == {"reason": "not_picked_up", "source": "econt", "status": "requested"}
        event = conn.execute(
            "SELECT response_json FROM order_courier_events WHERE action = 'refresh_trace'"
        ).fetchone()
        assert "returnShipmentURL" in event["response_json"]
        assert "cdCollectedAmount" in event["response_json"]
        assert "cdPaidAmount" in event["response_json"]

    @pytest.mark.asyncio
    async def test_refresh_trace_normalizes_failed_delivery_event(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn)
        conn.execute(
            """
            UPDATE orders
            SET status = 'shipped', courier_shipment_number = '1234567890',
                tracking_number = '1234567890', tracking_carrier = 'econt'
            WHERE id = ?
            """,
            (order_id,),
        )
        conn.commit()
        client = FakeEcontClient()
        client.next_trace = EcontShipmentStatus(
            shipment_number="1234567890",
            events=[EcontTraceEvent(type="failed_delivery")],
        )

        result = await refresh_trace(conn, order_id, client=client)

        assert result["courier_status"] == "failed"
        case = conn.execute(
            "SELECT reason, source, status FROM order_returns WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        assert dict(case) == {"reason": "other", "source": "econt", "status": "requested"}

    @pytest.mark.asyncio
    async def test_refresh_trace_does_not_advance_existing_return_case(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn)
        conn.execute(
            """
            UPDATE orders
            SET status = 'shipped', courier_shipment_number = '1234567890',
                tracking_number = '1234567890', tracking_carrier = 'econt'
            WHERE id = ?
            """,
            (order_id,),
        )
        existing_case = return_service.create_return_case(
            conn,
            order_id=order_id,
            reason="not_picked_up",
            source="admin",
            status="return_in_transit",
        )
        conn.commit()
        client = FakeEcontClient()
        client.next_trace = EcontShipmentStatus(
            shipment_number="1234567890",
            short_delivery_status_en="Returned to sender",
            events=[EcontTraceEvent(type="returned_to_sender")],
        )

        result = await refresh_trace(conn, order_id, client=client)

        assert result["courier_status"] == "returned"
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

    def test_manual_status_records_evidence_without_credentials_or_shipment(self, conn):
        order_id = _make_order(conn)

        result = record_manual_status(
            conn,
            order_id,
            courier_status="returned",
            notes="Courier portal shows returned to sender.",
            actor_user_id="admin-1",
        )

        assert result["status"] == "manual_status_recorded"
        assert result["courier_status"] == "returned"
        order = conn.execute(
            """
            SELECT status, courier_provider, courier_status, courier_sync_status,
                   courier_shipment_number, tracking_number
            FROM orders WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        assert order["status"] == "confirmed"
        assert order["courier_provider"] == "econt"
        assert order["courier_status"] == "returned"
        assert order["courier_sync_status"] == "manual_status"
        assert order["courier_shipment_number"] is None
        assert order["tracking_number"] is None
        case = conn.execute(
            "SELECT reason, source, status FROM order_returns WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        assert dict(case) == {"reason": "not_picked_up", "source": "econt", "status": "requested"}
        event = conn.execute(
            "SELECT action, request_json, actor_user_id FROM order_courier_events"
        ).fetchone()
        assert event["action"] == "manual_status"
        assert (
            json.loads(event["request_json"])["notes"]
            == "Courier portal shows returned to sender."
        )
        assert event["actor_user_id"] == "admin-1"

    @pytest.mark.asyncio
    async def test_delete_label_blocks_shipped_orders(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn)
        conn.execute(
            """
            UPDATE orders
            SET status = 'shipped', courier_shipment_number = '1234567890'
            WHERE id = ?
            """,
            (order_id,),
        )

        with pytest.raises(EcontFulfillmentValidationError):
            await delete_label(conn, order_id, client=FakeEcontClient())

    @pytest.mark.asyncio
    async def test_delete_label_clears_metadata_after_courier_success(self, conn, econt_secret):
        _configure_econt(conn)
        order_id = _make_order(conn)
        conn.execute(
            """
            UPDATE orders
            SET courier_provider = 'econt', courier_order_id = 'remote-order-1',
                courier_shipment_number = '1234567890', courier_label_url = 'https://label',
                courier_label_created_at = '2026-07-01 10:00:00',
                courier_last_error = '{"category":"transient"}',
                tracking_number = '1234567890', tracking_carrier = 'econt', tracking_url = 'https://track'
            WHERE id = ?
            """,
            (order_id,),
        )
        client = FakeEcontClient()

        result = await delete_label(conn, order_id, client=client)

        assert result == {"status": "deleted"}
        assert client.deleted_shipments == ["1234567890"]
        row = conn.execute(
            """
            SELECT courier_provider, courier_order_id, courier_shipment_number,
                   courier_label_url, courier_label_created_at, courier_last_error,
                   courier_last_synced_at, tracking_number, tracking_carrier,
                   tracking_url, courier_sync_status
            FROM orders WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        assert row["courier_provider"] == "econt"
        assert row["courier_order_id"] == "remote-order-1"
        assert row["courier_shipment_number"] is None
        assert row["courier_label_url"] is None
        assert row["courier_label_created_at"] is None
        assert row["courier_last_error"] is None
        assert row["courier_last_synced_at"] is not None
        assert row["tracking_number"] is None
        assert row["tracking_carrier"] is None
        assert row["tracking_url"] is None
        assert row["courier_sync_status"] == "label_deleted"
