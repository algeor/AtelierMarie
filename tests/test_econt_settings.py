"""Tests for Econt settings backend, admin routes, and redaction helpers."""

import pytest
from pydantic import SecretStr

from app.config import get_settings
from app.database import _seed_econt_settings
from app.services.econt_delivery_client import EcontAuthError
from app.services.econt_redaction import redact_mapping, redact_secret


@pytest.fixture(autouse=True)
def _reset_econt_settings(db):
    db.execute("DELETE FROM econt_settings")
    _seed_econt_settings(db)
    db.commit()
    yield
    db.execute("DELETE FROM econt_settings")
    _seed_econt_settings(db)
    db.commit()


class TestEcontSettingsRoutes:
    @pytest.mark.asyncio
    async def test_admin_auth_required(self, client):
        resp = await client.get("/v1/admin/econt/settings")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_settings_returns_secret_state_without_secret_value(
        self, admin_client, monkeypatch
    ):
        settings = get_settings()
        monkeypatch.setattr(settings, "econt_delivery_private_key", SecretStr("private-demo-key"))
        monkeypatch.setattr(settings, "econt_delivery_shop_id", "shop-env-1")

        resp = await admin_client.get("/v1/admin/econt/settings")

        assert resp.status_code == 200
        body = resp.json()
        assert body["environment"] == "demo"
        assert body["base_url"] == "https://delivery-demo.econt.com/services/"
        assert body["office_locator_url"] == "https://delivery-demo.econt.com/customer_info.php"
        assert body["office_locator_origins"] == ["https://delivery-demo.econt.com"]
        assert body["secret_state"]["private_key_configured"] is True
        assert body["secret_state"]["shop_id_configured"] is True
        assert "private-demo-key" not in str(body)

    @pytest.mark.asyncio
    async def test_patch_settings_persists_non_secret_fields(self, admin_client):
        resp = await admin_client.patch(
            "/v1/admin/econt/settings",
            json={
                "enabled": True,
                "environment": "production",
                "shop_id": "shop-db-9",
                "sender_office_code": "1127",
                "default_pack_count": 2,
                "shipment_description": "Atelier Marie candles",
                "office_locator_enabled": True,
                "auto_confirm_on_label": True,
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True
        assert body["environment"] == "production"
        assert body["base_url"] == "https://delivery.econt.com/services/"
        assert body["shop_id"] == "shop-db-9"
        assert body["sender_office_code"] == "1127"
        assert body["default_pack_count"] == 2
        assert body["shipment_description"] == "Atelier Marie candles"
        assert body["office_locator_enabled"] is True
        assert body["auto_confirm_on_label"] is True

        get_resp = await admin_client.get("/v1/admin/econt/settings")
        assert get_resp.json()["shop_id"] == "shop-db-9"

    @pytest.mark.asyncio
    async def test_patch_rejects_unknown_or_invalid_fields(self, admin_client):
        resp = await admin_client.patch(
            "/v1/admin/econt/settings",
            json={"private_key": "must-not-be-accepted"},
        )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_rejects_stored_credential_source(self, admin_client):
        resp = await admin_client.patch(
            "/v1/admin/econt/settings",
            json={"credential_source": "stored"},
        )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_connection_reports_missing_configuration(self, admin_client):
        resp = await admin_client.post("/v1/admin/econt/test-connection")

        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "missing_configuration"
        assert "private_key_missing" in body["details"]["blockers"]
        assert "shop_id_missing" in body["details"]["blockers"]

        settings_resp = await admin_client.get("/v1/admin/econt/settings")
        assert settings_resp.json()["last_health_status"] == "missing_configuration"

    @pytest.mark.asyncio
    async def test_connection_success_with_env_secret_and_required_settings(
        self, admin_client, monkeypatch
    ):
        calls = {}

        class FakeConnectionClient:
            def __init__(self, *, base_url, private_key, shop_id):
                calls["base_url"] = base_url
                calls["private_key"] = private_key
                calls["shop_id"] = shop_id

            def test_connection(self):
                calls["tested"] = True
                return True

        monkeypatch.setattr(
            "app.services.econt_settings_service.EcontDeliveryClient",
            FakeConnectionClient,
        )
        settings = get_settings()
        monkeypatch.setattr(settings, "econt_delivery_private_key", SecretStr("private-demo-key"))

        patch_resp = await admin_client.patch(
            "/v1/admin/econt/settings",
            json={
                "enabled": True,
                "shop_id": "shop-db-9",
                "sender_office_code": "1127",
            },
        )
        assert patch_resp.status_code == 200

        resp = await admin_client.post("/v1/admin/econt/test-connection")

        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "success"
        assert body["details"] == {"blockers": []}
        assert calls == {
            "base_url": "https://delivery-demo.econt.com/services/",
            "private_key": "private-demo-key",
            "shop_id": "shop-db-9",
            "tested": True,
        }
        assert "private-demo-key" not in str(body)

    @pytest.mark.asyncio
    async def test_connection_maps_econt_auth_failure(self, admin_client, monkeypatch):
        class FakeConnectionClient:
            def __init__(self, *, base_url, private_key, shop_id):
                pass

            def test_connection(self):
                raise EcontAuthError(
                    "invalid private key",
                    status_code=403,
                    details={"headers": {"Authorization": "private-demo-key"}},
                )

        monkeypatch.setattr(
            "app.services.econt_settings_service.EcontDeliveryClient",
            FakeConnectionClient,
        )
        settings = get_settings()
        monkeypatch.setattr(settings, "econt_delivery_private_key", SecretStr("private-demo-key"))

        patch_resp = await admin_client.patch(
            "/v1/admin/econt/settings",
            json={
                "enabled": True,
                "shop_id": "shop-db-9",
                "sender_office_code": "1127",
            },
        )
        assert patch_resp.status_code == 200

        resp = await admin_client.post("/v1/admin/econt/test-connection")

        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "authentication_failed"
        assert body["details"]["error"]["status_code"] == 403
        assert "private-demo-key" not in str(body)

        settings_resp = await admin_client.get("/v1/admin/econt/settings")
        assert settings_resp.json()["last_health_status"] == "authentication_failed"

    @pytest.mark.asyncio
    async def test_econt_health_endpoint_exposes_circuit_breaker(self, admin_client):
        resp = await admin_client.get("/v1/admin/health/econt")

        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "econt_delivery"
        assert body["state"] in {"closed", "open", "half_open"}


class TestEcontRedaction:
    def test_redact_secret_masks_configured_values(self):
        assert redact_secret("private-demo-key") == "<redacted>"
        assert redact_secret("") is None

    def test_redact_mapping_preserves_shape_and_removes_secret_keys(self):
        payload = {
            "headers": {"Authorization": "private-demo-key"},
            "customerInfo": {"name": "Mira", "phone": "+359888123456"},
            "nested": [{"privateKey": "abc"}],
        }

        redacted = redact_mapping(payload)

        assert redacted == {
            "headers": {"Authorization": "<redacted>"},
            "customerInfo": {"name": "Mira", "phone": "+359888123456"},
            "nested": [{"privateKey": "<redacted>"}],
        }
