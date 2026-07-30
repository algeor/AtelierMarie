"""Integration tests for `/v1/delivery/*` endpoints.

Covers task 4.2 of shipping-courier-integration: offices by city, cities
search, empty results, invalid courier param, office_type filtering,
and cross-language matching for both endpoints.

Uses the module-scoped app/client from conftest.py (FakeSessionMiddleware).
"""

import pytest

from app.config import get_settings
from app.services import delivery_service


class TestDeliveryConfig:
    @pytest.mark.asyncio
    async def test_public_config_defaults_to_demo_locator_for_demo_environment(
        self, client, db, monkeypatch
    ):
        settings = get_settings()
        monkeypatch.setattr(settings, "econt_office_locator_url", "")
        monkeypatch.setattr(settings, "econt_office_locator_origins", [])
        db.execute("UPDATE econt_settings SET office_locator_enabled = 1 WHERE id = 'default'")
        db.commit()

        resp = await client.get("/v1/delivery/config")

        assert resp.status_code == 200
        body = resp.json()
        assert body == {
            "econt": {
                "office_locator_enabled": True,
                "office_locator_url": "https://delivery-demo.econt.com/customer_info.php",
                "office_locator_origins": ["https://delivery-demo.econt.com"],
            }
        }
        assert "private" not in str(body).lower()

    @pytest.mark.asyncio
    async def test_public_config_defaults_to_production_locator_for_production_environment(
        self, client, db, monkeypatch
    ):
        settings = get_settings()
        monkeypatch.setattr(settings, "econt_office_locator_url", "")
        monkeypatch.setattr(settings, "econt_office_locator_origins", [])
        db.execute(
            """
            UPDATE econt_settings
            SET office_locator_enabled = 1, environment = 'production'
            WHERE id = 'default'
            """
        )
        db.commit()

        resp = await client.get("/v1/delivery/config")

        assert resp.status_code == 200
        assert resp.json()["econt"] == {
            "office_locator_enabled": True,
            "office_locator_url": "https://delivery.econt.com/customer_info.php",
            "office_locator_origins": ["https://delivery.econt.com"],
        }

    @pytest.mark.asyncio
    async def test_public_config_allows_explicit_locator_override(self, client, db, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(
            settings,
            "econt_office_locator_url",
            "https://custom-locator.example/customer_info.php",
        )
        monkeypatch.setattr(
            settings, "econt_office_locator_origins", ["https://custom-locator.example"]
        )
        db.execute("UPDATE econt_settings SET office_locator_enabled = 1 WHERE id = 'default'")
        db.commit()

        resp = await client.get("/v1/delivery/config")

        assert resp.status_code == 200
        assert resp.json()["econt"] == {
            "office_locator_enabled": True,
            "office_locator_url": "https://custom-locator.example/customer_info.php",
            "office_locator_origins": ["https://custom-locator.example"],
        }


class TestListOffices:
    """`GET /v1/delivery/offices` — covers courier-offices-data spec scenarios."""

    @pytest.mark.asyncio
    async def test_econt_offices_in_sofia(self, client):
        resp = await client.get("/v1/delivery/offices?courier=econt&city=София")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Public API-shape contract includes the Econt-native code needed for AWB creation.
        expected_keys = {"id", "code", "name", "type", "city", "address", "working_hours"}
        for office in data:
            assert set(office.keys()) == expected_keys
            assert office["code"]
            assert office["city"].casefold() == "софия".casefold()

    @pytest.mark.asyncio
    async def test_legacy_econt_office_without_code_still_serializes(self, client, monkeypatch):
        monkeypatch.setitem(
            delivery_service._offices_by_courier,
            "econt",
            [
                {
                    "id": "econt-legacy",
                    "name": "София Legacy",
                    "name_en": "Sofia Legacy",
                    "type": "office",
                    "city": "София",
                    "city_en": "Sofia",
                    "address": "ул. Тест 1",
                    "working_hours": "Пон-Пет 09:00-18:00",
                    "working_hours_en": "Mon-Fri 09:00-18:00",
                }
            ],
        )
        resp = await client.get("/v1/delivery/offices?courier=econt&city=София")
        assert resp.status_code == 200
        assert resp.json()[0]["code"] is None

    @pytest.mark.asyncio
    async def test_speedy_offices_in_sofia(self, client):
        resp = await client.get("/v1/delivery/offices?courier=speedy&city=София")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert all(o["city"].casefold() == "софия".casefold() for o in data)

    @pytest.mark.asyncio
    async def test_cross_language_city_match(self, client):
        """`city=Sofia` (EN) should return the same offices as `city=София` (BG)."""
        resp_en = await client.get("/v1/delivery/offices?courier=speedy&city=Sofia")
        resp_bg = await client.get("/v1/delivery/offices?courier=speedy&city=София")
        assert resp_en.status_code == 200
        assert resp_bg.status_code == 200
        assert len(resp_en.json()) == len(resp_bg.json())

    @pytest.mark.asyncio
    async def test_locker_filter(self, client):
        """`type=apt` returns only automated parcel terminals."""
        resp = await client.get("/v1/delivery/offices?courier=speedy&city=София&type=apt")
        assert resp.status_code == 200
        data = resp.json()
        assert all(o["type"] == "apt" for o in data)

    @pytest.mark.asyncio
    async def test_staffed_office_filter(self, client):
        resp = await client.get("/v1/delivery/offices?courier=speedy&city=София&type=office")
        assert resp.status_code == 200
        data = resp.json()
        assert all(o["type"] == "office" for o in data)

    @pytest.mark.asyncio
    async def test_unknown_city_returns_empty(self, client):
        resp = await client.get("/v1/delivery/offices?courier=speedy&city=НесъществуващоСело")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_invalid_courier_rejected(self, client):
        resp = await client.get("/v1/delivery/offices?courier=dhl&city=София")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_office_type_rejected(self, client):
        resp = await client.get("/v1/delivery/offices?courier=speedy&city=София&type=warehouse")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_courier_rejected(self, client):
        resp = await client.get("/v1/delivery/offices?city=София")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_city_rejected(self, client):
        resp = await client.get("/v1/delivery/offices?courier=speedy")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_locale_en_returns_english_names(self, client):
        resp = await client.get("/v1/delivery/offices?courier=speedy&city=Sofia&locale=en")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        # English city name should come back on the record
        assert data[0]["city"] == "Sofia"


class TestListCities:
    """`GET /v1/delivery/cities` — courier-offices-data spec scenarios."""

    @pytest.mark.asyncio
    async def test_list_all_speedy_cities(self, client):
        resp = await client.get("/v1/delivery/cities?courier=speedy")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Sorted alphabetically per delivery_service contract
        assert data == sorted(data)

    @pytest.mark.asyncio
    async def test_prefix_search_bg(self, client):
        resp = await client.get("/v1/delivery/cities?courier=speedy&q=Со")
        assert resp.status_code == 200
        data = resp.json()
        # Every returned city starts with "Со" (case-insensitive) in BG or EN form
        for city in data:
            assert city.casefold().startswith("со") or "so" in city.casefold()

    @pytest.mark.asyncio
    async def test_prefix_search_en(self, client):
        resp = await client.get("/v1/delivery/cities?courier=speedy&q=So")
        assert resp.status_code == 200
        data = resp.json()
        # Should include София via the city_en=Sofia match
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_no_prefix_match_returns_empty(self, client):
        resp = await client.get("/v1/delivery/cities?courier=speedy&q=xyz123")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_invalid_courier_rejected(self, client):
        resp = await client.get("/v1/delivery/cities?courier=dhl")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_courier_rejected(self, client):
        resp = await client.get("/v1/delivery/cities")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_locale_en_returns_english_cities(self, client):
        resp = await client.get("/v1/delivery/cities?courier=speedy&locale=en")
        assert resp.status_code == 200
        data = resp.json()
        assert "Sofia" in data
