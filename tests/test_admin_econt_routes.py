"""Admin Econt fulfillment route tests."""

import json
import uuid

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.config import get_settings
from app.models.delivery import DeliveryInfo, DeliveryOffice
from app.models.econt import EcontShipmentStatus
from app.models.users import UserResponse
from app.services import auth_service
from app.services.econt_delivery_client import EcontTransientError
from app.services.econt_fulfillment_service import build_order_payload
from app.services.order_service import checkout


class FakeEcontClient:
    def __init__(
        self,
        *,
        fail_create: bool = False,
        trace_status: EcontShipmentStatus | None = None,
    ):
        self.fail_create = fail_create
        self.trace_status = trace_status
        self.created = 0
        self.deleted: list[str] = []
        self.traced: list[str] = []

    async def update_order(self, order):
        return {"orderID": "remote-order-1"}

    async def create_awb(self, order):
        self.created += 1
        if self.fail_create:
            raise EcontTransientError(
                "timeout",
                details={"headers": {"Authorization": "private-demo-key"}},
            )
        return EcontShipmentStatus(
            shipment_number="1234567890",
            pdf_url="https://label.test/123.pdf",
        )

    async def delete_label(self, shipment_number):
        self.deleted.append(shipment_number)
        return {"deleted": True}

    async def get_trace(self, shipment_number):
        self.traced.append(shipment_number)
        return self.trace_status or EcontShipmentStatus(
            shipment_number=shipment_number,
            status="in_transit",
        )


def _seed_econt_settings(conn) -> None:
    """Re-seed the singleton Econt settings ``default`` row.

    ``econt_settings`` is a migration-seed table (never truncated by the root
    ``_clean_tables``), but these tests mutate the singleton, so this file owns an
    explicit per-test re-seed (Decision 15). Replaces the removed SQLite
    ``app.database._seed_econt_settings`` helper — non-id columns take their DB
    defaults, exactly as the old ``INSERT OR IGNORE`` did.
    """
    conn.execute(
        "INSERT INTO econt_settings (id) VALUES ('default') ON CONFLICT (id) DO NOTHING"
    )


@pytest.fixture(autouse=True)
def _reset_econt_settings(db):
    db.execute("DELETE FROM econt_settings")
    _seed_econt_settings(db)
    db.commit()
    yield
    db.execute("DELETE FROM econt_settings")
    _seed_econt_settings(db)
    db.commit()


@pytest.fixture()
def econt_secret(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "econt_delivery_private_key", SecretStr("private-demo-key"))
    yield


def _configure_econt(db: psycopg.Connection) -> None:
    db.execute(
        """
        UPDATE econt_settings
        SET enabled = 1, shop_id = 'shop-1', sender_office_code = '1127'
        WHERE id = 'default'
        """
    )
    db.commit()


def _make_order(db: psycopg.Connection, app, *, courier="econt", confirmed=True) -> str:
    session_id = app._test_session_id
    product_id = f"route-product-{uuid.uuid4().hex[:8]}"
    db.execute(
        """
        INSERT INTO products (id, name_en, price_cents, stock, is_active)
        VALUES (?, 'Candle', 2500, 10, 1)
        """,
        (product_id,),
    )
    db.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, 1)",
        (session_id, product_id),
    )
    db.commit()
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
        conn=db,
        session_id=session_id,
        customer_email="mira@example.com",
        customer_name="Mira",
        delivery=delivery,
    )
    if confirmed:
        db.execute("UPDATE orders SET status = 'confirmed' WHERE id = ?", (order["id"],))
        db.commit()
    return order["id"]


def _seed_admin_session(db: psycopg.Connection, app, *, user_id: str = "jwt-admin") -> str:
    db.execute(
        """
        INSERT INTO users (id, google_id, email, name, is_admin)
        VALUES (?, ?, ?, 'JWT Admin', 1)
        """,
        (user_id, f"google-{user_id}", f"{user_id}@example.com"),
    )
    db.execute("UPDATE sessions SET user_id = ? WHERE id = ?", (user_id, app._test_session_id))
    db.commit()
    user = UserResponse(
        id=user_id,
        email=f"{user_id}@example.com",
        name="JWT Admin",
        avatar_url=None,
        is_admin=True,
    )
    return auth_service.create_jwt(user, app._test_session_id)


class TestAdminEcontRoutes:
    @pytest.mark.asyncio
    async def test_auth_required(self, client):
        resp = await client.get("/v1/admin/orders/order-1/econt/readiness")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_readiness_reports_missing_config(self, admin_client, db, app):
        order_id = _make_order(db, app)

        resp = await admin_client.get(f"/v1/admin/orders/{order_id}/econt/readiness")

        assert resp.status_code == 200
        body = resp.json()
        assert body["ready"] is False
        assert "settings_disabled" in body["blockers"]
        assert "settings_private_key_missing" in body["blockers"]

    @pytest.mark.asyncio
    async def test_manual_status_available_without_config_or_shipment_number(
        self, admin_client, db, app
    ):
        order_id = _make_order(db, app)

        resp = await admin_client.post(
            f"/v1/admin/orders/{order_id}/econt/manual-status",
            json={"courier_status": "failed", "notes": "Customer refused delivery."},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "manual_status_recorded"
        assert body["courier_status"] == "failed"
        row = db.execute(
            """
            SELECT courier_provider, courier_status, courier_sync_status,
                   courier_shipment_number
            FROM orders WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        assert row["courier_provider"] == "econt"
        assert row["courier_status"] == "failed"
        assert row["courier_sync_status"] == "manual_status"
        assert row["courier_shipment_number"] is None
        case = db.execute(
            "SELECT reason, source, status FROM order_returns WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        assert dict(case) == {"reason": "other", "source": "econt", "status": "requested"}

    @pytest.mark.asyncio
    async def test_create_label_success_updates_order_response(
        self, admin_client, db, app, econt_secret, monkeypatch
    ):
        _configure_econt(db)
        order_id = _make_order(db, app)
        fake = FakeEcontClient()
        monkeypatch.setattr("app.services.econt_fulfillment_service.make_client", lambda conn: fake)

        resp = await admin_client.post(f"/v1/admin/orders/{order_id}/econt/label")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "created"
        assert body["shipment_number"] == "1234567890"
        assert body["label_url"] == "https://label.test/123.pdf"

        detail = await admin_client.get(f"/v1/admin/orders/{order_id}")
        order = detail.json()
        assert order["courier_provider"] == "econt"
        assert order["courier_shipment_number"] == "1234567890"
        assert order["courier_sync_status"] == "label_created"
        assert order["tracking_number"] == "1234567890"

    @pytest.mark.asyncio
    async def test_non_econt_order_rejected(self, admin_client, db, app, econt_secret):
        _configure_econt(db)
        order_id = _make_order(db, app, courier="speedy")

        resp = await admin_client.post(f"/v1/admin/orders/{order_id}/econt/label")

        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "ECONT_NOT_READY"
        assert "order_not_econt" in body["error"]["details"]["blockers"]

    @pytest.mark.asyncio
    async def test_repair_econt_order_fields_update_payload(
        self, admin_client, db, app, econt_secret
    ):
        _configure_econt(db)
        order_id = _make_order(db, app)
        row = db.execute("SELECT delivery_details FROM orders WHERE id = ?", (order_id,)).fetchone()
        details = json.loads(row["delivery_details"])
        details.pop("office_code", None)
        details.pop("phone", None)
        db.execute(
            "UPDATE orders SET delivery_details = ? WHERE id = ?",
            (json.dumps(details), order_id),
        )
        db.commit()

        blocked = await admin_client.get(f"/v1/admin/orders/{order_id}/econt/readiness")
        assert "order_office_code_missing" in blocked.json()["blockers"]
        assert "order_recipient_phone_missing" in blocked.json()["blockers"]

        resp = await admin_client.patch(
            f"/v1/admin/orders/{order_id}/econt/repair",
            json={
                "office_code": "1127",
                "recipient_phone": "+359 888 123 456",
                "pack_count": 2,
                "shipment_description": "Custom candle shipment",
                "payment_side": "sender",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["ready"] is True
        payload = build_order_payload(db, order_id)
        assert payload.customer_info.office_code == "1127"
        assert payload.customer_info.phone == "+359888123456"
        assert payload.pack_count == 2
        assert payload.shipment_description == "Custom candle shipment"
        assert payload.payment_side == "sender"
        event = db.execute(
            "SELECT action, status, actor_user_id FROM order_courier_events"
        ).fetchone()
        assert event["action"] == "repair_order"
        assert event["status"] == "success"
        assert event["actor_user_id"] is None

    @pytest.mark.asyncio
    async def test_jwt_admin_actor_is_recorded_on_econt_action(
        self, db, app, econt_secret, monkeypatch
    ):
        _configure_econt(db)
        order_id = _make_order(db, app)
        jwt_cookie = _seed_admin_session(db, app)
        monkeypatch.setattr(
            "app.services.econt_fulfillment_service.make_client",
            lambda conn: FakeEcontClient(),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as jwt_client:
            jwt_client.cookies.set(get_settings().jwt_cookie_name, jwt_cookie)
            resp = await jwt_client.post(f"/v1/admin/orders/{order_id}/econt/label")

        assert resp.status_code == 200
        event = db.execute(
            """
            SELECT action, status, actor_user_id
            FROM order_courier_events
            WHERE action = 'create_label'
            """
        ).fetchone()
        assert event["status"] == "success"
        assert event["actor_user_id"] == "jwt-admin"

    @pytest.mark.asyncio
    async def test_courier_transient_error_is_redacted(
        self, admin_client, db, app, econt_secret, monkeypatch
    ):
        _configure_econt(db)
        order_id = _make_order(db, app)
        monkeypatch.setattr(
            "app.services.econt_fulfillment_service.make_client",
            lambda conn: FakeEcontClient(fail_create=True),
        )

        resp = await admin_client.post(f"/v1/admin/orders/{order_id}/econt/label")

        assert resp.status_code == 503
        body = resp.json()
        assert body["error"]["code"] == "ECONT_TRANSIENT"
        assert "private-demo-key" not in str(body)

    @pytest.mark.asyncio
    async def test_refresh_and_delete_label(self, admin_client, db, app, econt_secret, monkeypatch):
        _configure_econt(db)
        order_id = _make_order(db, app)
        fake = FakeEcontClient()
        monkeypatch.setattr("app.services.econt_fulfillment_service.make_client", lambda conn: fake)

        create = await admin_client.post(f"/v1/admin/orders/{order_id}/econt/label")
        assert create.status_code == 200

        trace = await admin_client.post(f"/v1/admin/orders/{order_id}/econt/trace")
        assert trace.status_code == 200
        assert trace.json()["status"] == "trace_synced"

        delete = await admin_client.delete(f"/v1/admin/orders/{order_id}/econt/label")
        assert delete.status_code == 200
        assert delete.json()["status"] == "deleted"
        row = db.execute(
            "SELECT courier_shipment_number, tracking_number FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert row["courier_shipment_number"] is None
        assert row["tracking_number"] is None

    @pytest.mark.asyncio
    async def test_econt_cod_evidence_shows_without_settlement_record(
        self, admin_client, db, app, econt_secret, monkeypatch
    ):
        _configure_econt(db)
        order_id = _make_order(db, app)
        fake = FakeEcontClient(
            trace_status=EcontShipmentStatus(
                shipment_number="1234567890",
                status="delivered",
                cd_collected_amount=25.0,
                cd_collected_time="2026-08-01 10:00:00",
                cd_paid_amount=24.0,
                cd_paid_time="2026-08-02 10:00:00",
            )
        )
        monkeypatch.setattr("app.services.econt_fulfillment_service.make_client", lambda conn: fake)
        create = await admin_client.post(f"/v1/admin/orders/{order_id}/econt/label")
        assert create.status_code == 200
        db.execute("UPDATE orders SET status = 'delivered' WHERE id = ?", (order_id,))
        db.commit()

        trace = await admin_client.post(f"/v1/admin/orders/{order_id}/econt/trace")
        detail = await admin_client.get(f"/v1/admin/orders/{order_id}")

        assert trace.status_code == 200
        body = detail.json()
        assert body["econt_cod_evidence"] == {
            "collected_amount": 25.0,
            "collected_time": "2026-08-01 10:00:00",
            "paid_amount": 24.0,
            "paid_time": "2026-08-02 10:00:00",
            "source_event_id": body["econt_cod_evidence"]["source_event_id"],
            "source_action": "refresh_trace",
            "recorded_at": body["econt_cod_evidence"]["recorded_at"],
        }
        assert body["cod_settlement"] is None
        assert body["cod_settlement_required"] is True

    @pytest.mark.asyncio
    async def test_shipped_transition_uses_existing_econt_tracking(
        self, admin_client, db, app, econt_secret, monkeypatch
    ):
        _configure_econt(db)
        order_id = _make_order(db, app)
        monkeypatch.setattr(
            "app.services.econt_fulfillment_service.make_client",
            lambda conn: FakeEcontClient(),
        )
        await admin_client.post(f"/v1/admin/orders/{order_id}/econt/label")

        resp = await admin_client.patch(
            f"/v1/admin/orders/{order_id}/status",
            json={"status": "shipped"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "shipped"
        assert body["tracking_number"] == "1234567890"
        assert body["tracking_carrier"] == "econt"

    @pytest.mark.asyncio
    async def test_create_and_ship_econt_label_updates_status_and_queues_email(
        self, admin_client, db, app, econt_secret, monkeypatch
    ):
        _configure_econt(db)
        order_id = _make_order(db, app)
        fake = FakeEcontClient()
        monkeypatch.setattr("app.services.econt_fulfillment_service.make_client", lambda conn: fake)

        resp = await admin_client.post(f"/v1/admin/orders/{order_id}/econt/ship")

        assert resp.status_code == 200
        body = resp.json()
        assert body["action"] == "create_label_and_ship"
        assert body["status"] == "shipped"
        assert body["status_updated_to"] == "shipped"
        assert body["shipment_number"] == "1234567890"
        assert fake.created == 1

        order = (await admin_client.get(f"/v1/admin/orders/{order_id}")).json()
        assert order["status"] == "shipped"
        assert order["tracking_number"] == "1234567890"
        shipped_email = db.execute(
            "SELECT status FROM order_emails WHERE order_id = ? AND event = 'shipped'",
            (order_id,),
        ).fetchone()
        assert shipped_email["status"] == "queued"

    @pytest.mark.asyncio
    async def test_create_and_ship_econt_label_failure_keeps_order_confirmed(
        self, admin_client, db, app, econt_secret, monkeypatch
    ):
        _configure_econt(db)
        order_id = _make_order(db, app)
        monkeypatch.setattr(
            "app.services.econt_fulfillment_service.make_client",
            lambda conn: FakeEcontClient(fail_create=True),
        )

        resp = await admin_client.post(f"/v1/admin/orders/{order_id}/econt/ship")

        assert resp.status_code == 503
        row = db.execute(
            "SELECT status, tracking_number, courier_sync_status FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        assert row["status"] == "confirmed"
        assert row["tracking_number"] is None
        assert row["courier_sync_status"] == "failed"
        shipped_email = db.execute(
            "SELECT 1 FROM order_emails WHERE order_id = ? AND event = 'shipped'",
            (order_id,),
        ).fetchone()
        assert shipped_email is None
