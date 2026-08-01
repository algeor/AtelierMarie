"""Admin Speedy route tests."""

import json
import sqlite3
import uuid

import pytest
from pydantic import SecretStr

from app.config import get_settings
from app.models.delivery import DeliveryInfo, DeliveryOffice
from app.services import speedy_client
from app.services.order_service import checkout


@pytest.fixture(autouse=True)
def speedy_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "speedy_api_username", "speedy-user")
    monkeypatch.setattr(settings, "speedy_api_password", SecretStr("speedy-secret"))
    monkeypatch.setattr(settings, "speedy_client_id", "123456")


def _make_speedy_order(
    db: sqlite3.Connection,
    app,
    *,
    status: str = "confirmed",
    tracking_number: str | None = None,
    courier: str = "speedy",
) -> str:
    product_id = f"speedy-route-{uuid.uuid4().hex[:8]}"
    db.execute(
        """
        INSERT INTO products (id, name_en, price_cents, stock, weight_grams, is_active)
        VALUES (?, 'Route Candle', 2500, 10, 500, 1)
        """,
        (product_id,),
    )
    db.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, 1)",
        (app._test_session_id, product_id),
    )
    db.commit()
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
        conn=db,
        session_id=app._test_session_id,
        customer_email="speedy-route@example.com",
        customer_name="Speedy Route Buyer",
        delivery=delivery,
        payment_method="cod",
    )
    db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order["id"]))
    if tracking_number:
        db.execute(
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
    db.commit()
    return order["id"]


class TestAdminSpeedyRoutes:
    @pytest.mark.asyncio
    async def test_auth_required(self, client):
        resp = await client.get("/v1/admin/speedy/health")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_overview_returns_health_queues_metrics_and_events(
        self, admin_client, db, app, monkeypatch
    ):
        ready_id = _make_speedy_order(db, app, status="confirmed")
        shipped_id = _make_speedy_order(
            db,
            app,
            status="shipped",
            tracking_number="63689182611",
        )

        async def fake_client_id(**_kwargs):
            return "123456"

        monkeypatch.setattr(speedy_client, "get_own_client_id", fake_client_id)

        resp = await admin_client.get("/v1/admin/speedy")

        assert resp.status_code == 200
        body = resp.json()
        assert body["health"]["status"] == "healthy"
        assert [order["order_id"] for order in body["queues"]["ready_to_ship"]] == [ready_id]
        assert [order["order_id"] for order in body["queues"]["shipped"]] == [shipped_id]
        assert body["metrics"]["recent_successes"] == 0
        assert "speedy-secret" not in json.dumps(body)

    @pytest.mark.asyncio
    async def test_ship_label_track_search_info_cancel_and_pickup_actions(
        self, admin_client, db, app, monkeypatch
    ):
        ready_id = _make_speedy_order(db, app, status="confirmed")

        async def fake_create_shipment(**_kwargs):
            return "63689182611"

        async def fake_print_label(**_kwargs):
            return b"%PDF-route"

        async def fake_track_shipment(**_kwargs):
            return "in_transit"

        async def fake_search(reference, **_kwargs):
            assert reference == ready_id
            return ["63689182611"]

        async def fake_info(shipment_ids, **_kwargs):
            assert shipment_ids == ["63689182611"]
            return [{"id": "63689182611", "status": "accepted"}]

        async def fake_cancel(shipment_id, **_kwargs):
            assert shipment_id == "63689182611"
            return {"cancelled": True}

        async def fake_terms(**_kwargs):
            return ["2026-08-02T14:00:00+03:00"]

        async def fake_pickup(**_kwargs):
            return [{"id": "pickup-1"}]

        monkeypatch.setattr(speedy_client, "create_shipment", fake_create_shipment)
        monkeypatch.setattr("app.routes.admin.print_label", fake_print_label)
        monkeypatch.setattr("app.routes.admin.track_shipment", fake_track_shipment)
        monkeypatch.setattr(speedy_client, "find_parcels_by_reference", fake_search)
        monkeypatch.setattr(speedy_client, "get_shipment_info", fake_info)
        monkeypatch.setattr(speedy_client, "cancel_shipment", fake_cancel)
        monkeypatch.setattr(speedy_client, "pickup_terms", fake_terms)
        monkeypatch.setattr(speedy_client, "request_pickup", fake_pickup)

        ship_resp = await admin_client.post(f"/v1/admin/speedy/orders/{ready_id}/ship")
        assert ship_resp.status_code == 200
        assert ship_resp.json()["shipment_number"] == "63689182611"

        label_resp = await admin_client.get(f"/v1/admin/speedy/orders/{ready_id}/label")
        assert label_resp.status_code == 200
        assert label_resp.headers["content-type"] == "application/pdf"

        track_resp = await admin_client.post(f"/v1/admin/speedy/orders/{ready_id}/track")
        assert track_resp.status_code == 200
        assert track_resp.json()["courier_status"] == "in_transit"

        search_resp = await admin_client.post(
            "/v1/admin/speedy/shipments/search",
            json={"reference": ready_id, "include_returns": True},
        )
        assert search_resp.status_code == 200
        assert search_resp.json()["barcodes"] == ["63689182611"]

        info_resp = await admin_client.post(
            "/v1/admin/speedy/shipments/info",
            json={"shipment_ids": ["63689182611"]},
        )
        assert info_resp.status_code == 200
        assert info_resp.json()["shipments"] == [{"id": "63689182611", "status": "accepted"}]

        terms_resp = await admin_client.post(
            "/v1/admin/speedy/pickup/terms",
            json={"shipment_ids": ["63689182611"]},
        )
        assert terms_resp.status_code == 200
        assert terms_resp.json()["cutoffs"] == ["2026-08-02T14:00:00+03:00"]

        pickup_resp = await admin_client.post(
            "/v1/admin/speedy/pickup",
            json={
                "shipment_ids": ["63689182611"],
                "pickup_datetime": "2026-08-02T14:00:00+03:00",
                "visit_end_time": "17:00",
                "contact_name": "Mira",
                "phone": "+359888123456",
            },
        )
        assert pickup_resp.status_code == 200
        assert pickup_resp.json()["orders"] == [{"id": "pickup-1"}]

        cancel_resp = await admin_client.post(
            f"/v1/admin/speedy/orders/{ready_id}/cancel-shipment",
            json={"comment": "cancel route test"},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

        events_resp = await admin_client.get("/v1/admin/speedy/events")
        assert events_resp.status_code == 200
        actions = {event["action"] for event in events_resp.json()}
        assert {
            "create_waybill",
            "print_label",
            "refresh_tracking",
            "shipment_search",
            "shipment_info",
            "pickup_terms",
            "request_pickup",
            "cancel_shipment",
        }.issubset(actions)

    @pytest.mark.asyncio
    async def test_speedy_error_envelope_and_event_are_redacted(
        self, admin_client, db, app, monkeypatch
    ):
        order_id = _make_speedy_order(
            db,
            app,
            status="shipped",
            tracking_number="63689182611",
        )

        async def fail_cancel(*_args, **_kwargs):
            raise speedy_client.SpeedyValidationError(
                "already picked up",
                context="shipment.cancel",
                endpoint="shipment/cancel",
                details={"password": "speedy-secret"},
            )

        monkeypatch.setattr(speedy_client, "cancel_shipment", fail_cancel)

        resp = await admin_client.post(
            f"/v1/admin/speedy/orders/{order_id}/cancel-shipment",
            json={"comment": "cancel route test"},
        )

        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "SPEEDY_VALIDATION"
        serialized = json.dumps(body)
        assert "speedy-secret" not in serialized
        assert body["error"]["details"]["details"]["password"] == "<redacted>"

        order = db.execute(
            """
            SELECT tracking_number, courier_status, courier_sync_status
            FROM orders WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
        assert order["tracking_number"] == "63689182611"
        assert order["courier_status"] is None
        assert order["courier_sync_status"] == "waybill_created"

        event = db.execute(
            "SELECT error_json FROM order_courier_events WHERE action = 'cancel_shipment'"
        ).fetchone()
        assert event is not None
        assert "speedy-secret" not in event["error_json"]
