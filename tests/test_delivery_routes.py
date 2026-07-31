"""Integration tests for `/v1/delivery/*` endpoints.

Covers task 4.2 of shipping-courier-integration: offices by city, cities
search, empty results, invalid courier param, office_type filtering,
and cross-language matching for both endpoints.

Uses the module-scoped app/client from conftest.py (FakeSessionMiddleware).
"""

import pytest


class TestListOffices:
    """`GET /v1/delivery/offices` — covers courier-offices-data spec scenarios."""

    @pytest.mark.asyncio
    async def test_econt_offices_in_sofia(self, client):
        resp = await client.get("/v1/delivery/offices?courier=econt&city=София")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # 6-field API-shape contract
        expected_keys = {"id", "name", "type", "city", "address", "working_hours"}
        for office in data:
            assert set(office.keys()) == expected_keys
            assert office["city"].casefold() == "софия".casefold()

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


class TestGetPlaces:
    """`delivery_service.get_places` — served-place lookup with postcode/region."""

    def test_speedy_uses_full_site_nomenclature(self):
        from app.services import delivery_service

        assert len(delivery_service.get_places("speedy")) > 5000

    def test_ambiguous_name_yields_distinct_places(self):
        from app.services import delivery_service

        places = delivery_service.get_places("econt", query="Садово")
        sadovo = [p for p in places if p["name"] == "Садово"]
        # Три различни "Садово" — distinguished by region + postcode.
        assert len(sadovo) == 3
        regions = {p["region"] for p in sadovo}
        postcodes = {p["postal_code"] for p in sadovo}
        assert regions == {"Пловдив", "Благоевград", "Бургас"}
        assert postcodes == {"4122", "2922", "8463"}

    def test_prefix_match_bg(self):
        from app.services import delivery_service

        places = delivery_service.get_places("econt", query="Айтос")
        assert any(p["name"] == "Айтос" and p["postal_code"] == "8500" for p in places)

    def test_middle_word_match_bg(self):
        from app.services import delivery_service

        places = delivery_service.get_places("econt", query="Пазар")
        assert any(p["name"] == "Нови Пазар" and p["postal_code"] == "9900" for p in places)

    def test_region_match_keeps_exact_city_first(self):
        from app.services import delivery_service

        places = delivery_service.get_places("econt", query="Плевен")
        assert places[0] == {"name": "Плевен", "region": "Плевен", "postal_code": "5800"}
        assert any(p["name"] == "Белене" and p["region"] == "Плевен" for p in places)

    def test_postcode_match(self):
        from app.services import delivery_service

        places = delivery_service.get_places("econt", query="5972")
        assert places == [{"name": "Искър", "region": "Плевен", "postal_code": "5972"}]

    def test_same_name_same_region_postcodes_not_collapsed(self):
        from app.services import delivery_service

        places = delivery_service.get_places("econt", query="Искър")
        iskyr_pleven = [p for p in places if p["name"] == "Искър" and p["region"] == "Плевен"]
        assert {p["postal_code"] for p in iskyr_pleven} == {"5868", "5972"}

    def test_query_tokens_can_match_region_and_postcode(self):
        from app.services import delivery_service

        places = delivery_service.get_places("econt", query="Плевен 5972")
        assert places == [{"name": "Искър", "region": "Плевен", "postal_code": "5972"}]

    def test_prefix_match_en_localizes(self):
        from app.services import delivery_service

        places = delivery_service.get_places("econt", query="Sado", locale="en")
        sadovo = [p for p in places if p["name"] == "Sadovo"]
        assert len(sadovo) == 3
        assert all(p["region"] in {"Plovdiv", "Blagoevgrad", "Burgas"} for p in sadovo)

    def test_no_prefix_returns_sorted(self):
        from app.services import delivery_service

        places = delivery_service.get_places("econt")
        assert len(places) > 1000
        names = [p["name"] for p in places]
        assert names == sorted(names)

    def test_speedy_uses_shared_places(self):
        from app.services import delivery_service

        places = delivery_service.get_places("speedy", query="Соф")
        assert any(p["name"] == "София" and p["postal_code"] == "1000" for p in places)

    def test_speedy_prefix_match_en_localizes(self):
        from app.services import delivery_service

        places = delivery_service.get_places("speedy", query="Sof", locale="en")
        assert any(p["name"] == "Sofia" and p["postal_code"] == "1000" for p in places)

    def test_speedy_postcode_match_uses_shared_places(self):
        from app.services import delivery_service

        places = delivery_service.get_places("speedy", query="5972")
        assert places == [{"name": "Искър", "region": "Плевен", "postal_code": "5972"}]

    def test_zgorigrad_supplement_available_for_both_couriers(self):
        from app.services import delivery_service

        expected = {"name": "Згориград", "region": "Враца", "postal_code": "3042"}
        assert delivery_service.get_places("econt", query="Згор") == [expected]
        assert delivery_service.get_places("speedy", query="Згор") == [expected]

    def test_zgorigrad_english_lookup_localizes_and_translates_to_bg(self):
        from app.services import delivery_service

        expected = {"name": "Zgorigrad", "region": "Vratsa", "postal_code": "3042"}
        assert delivery_service.get_places("econt", query="Zgori", locale="en") == [expected]
        assert delivery_service.get_places("speedy", query="Zgori", locale="en") == [expected]
        assert delivery_service.resolve_city_bg("econt", "Zgorigrad") == "Згориград"
        assert delivery_service.resolve_city_bg("speedy", "Zgorigrad") == "Згориград"

    def test_roman_supplement_available_for_speedy(self):
        from app.services import delivery_service

        places = delivery_service.get_places("speedy", query="Roman", locale="en")
        assert places[0] == {"name": "Roman", "region": "Vratsa", "postal_code": "3130"}
        assert delivery_service.resolve_city_bg("speedy", "Roman") == "Роман"

    def test_speedy_full_sites_include_other_office_towns_with_postcodes(self):
        from app.services import delivery_service

        places = delivery_service.get_places("speedy", query="Batak", locale="en")
        assert {p["postal_code"] for p in places if p["name"] == "Batak"} == {"4580", "5228"}


class TestListPlaces:
    """`GET /v1/delivery/places` — served-place endpoint."""

    @pytest.mark.asyncio
    async def test_ambiguous_town_returns_multiple_rows(self, client):
        resp = await client.get("/v1/delivery/places?courier=econt&q=Садово")
        assert resp.status_code == 200
        data = resp.json()
        sadovo = [p for p in data if p["name"] == "Садово"]
        assert len(sadovo) == 3
        for p in sadovo:
            assert set(p.keys()) == {"name", "region", "postal_code"}
        assert {p["postal_code"] for p in sadovo} == {"4122", "2922", "8463"}

    @pytest.mark.asyncio
    async def test_locale_en(self, client):
        resp = await client.get("/v1/delivery/places?courier=econt&q=Sado&locale=en")
        assert resp.status_code == 200
        data = resp.json()
        assert any(p["name"] == "Sadovo" and p["region"] == "Plovdiv" for p in data)

    @pytest.mark.asyncio
    async def test_speedy_returns_shared_places(self, client):
        resp = await client.get("/v1/delivery/places?courier=speedy&q=Со")
        assert resp.status_code == 200
        assert any(p["name"] == "София" and p["postal_code"] == "1000" for p in resp.json())

    @pytest.mark.asyncio
    async def test_place_search_matches_postcode(self, client):
        resp = await client.get("/v1/delivery/places?courier=econt&q=5972")
        assert resp.status_code == 200
        assert resp.json() == [{"name": "Искър", "region": "Плевен", "postal_code": "5972"}]

    @pytest.mark.asyncio
    async def test_zgorigrad_place_search(self, client):
        resp = await client.get("/v1/delivery/places?courier=econt&q=Zgori&locale=en")
        assert resp.status_code == 200
        assert resp.json() == [{"name": "Zgorigrad", "region": "Vratsa", "postal_code": "3042"}]

    @pytest.mark.asyncio
    async def test_roman_place_search_for_speedy(self, client):
        resp = await client.get("/v1/delivery/places?courier=speedy&q=Roman&locale=en")
        assert resp.status_code == 200
        assert resp.json()[0] == {"name": "Roman", "region": "Vratsa", "postal_code": "3130"}

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self, client):
        resp = await client.get("/v1/delivery/places?courier=econt&q=xyz123")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_invalid_courier_rejected(self, client):
        resp = await client.get("/v1/delivery/places?courier=dhl")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_courier_rejected(self, client):
        resp = await client.get("/v1/delivery/places")
        assert resp.status_code == 422


class TestDeliverySettings:
    """Admin-managed delivery availability switches."""

    @pytest.mark.asyncio
    async def test_public_settings_default_enabled(self, client):
        resp = await client.get("/v1/delivery/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["speedy_office_enabled"] is True
        assert data["speedy_door_enabled"] is True
        assert data["econt_office_enabled"] is True
        assert data["econt_door_enabled"] is True
        assert data["cod_enabled"] is True
        assert data["card_enabled"] is True
        assert data["bank_transfer_enabled"] is True
        assert data["updated_at"]

    @pytest.mark.asyncio
    async def test_admin_update_persists_to_public_settings(self, admin_client, client):
        payload = {
            "speedy_office_enabled": False,
            "speedy_door_enabled": True,
            "econt_office_enabled": True,
            "econt_door_enabled": False,
            "cod_enabled": True,
            "card_enabled": False,
            "bank_transfer_enabled": True,
        }
        update = await admin_client.put("/v1/admin/delivery-settings", json=payload)
        assert update.status_code == 200
        assert update.json()["speedy_office_enabled"] is False
        assert update.json()["econt_door_enabled"] is False
        assert update.json()["card_enabled"] is False

        public = await client.get("/v1/delivery/settings")
        assert public.status_code == 200
        assert public.json()["speedy_office_enabled"] is False
        assert public.json()["econt_door_enabled"] is False
        assert public.json()["card_enabled"] is False

    @pytest.mark.asyncio
    async def test_disabled_office_discovery_returns_empty(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/delivery-settings",
            json={
                "speedy_office_enabled": False,
                "speedy_door_enabled": True,
                "econt_office_enabled": True,
                "econt_door_enabled": True,
            },
        )

        offices = await client.get("/v1/delivery/offices?courier=speedy&city=София")
        cities = await client.get("/v1/delivery/cities?courier=speedy&q=Со")
        assert offices.status_code == 200
        assert cities.status_code == 200
        assert offices.json() == []
        assert cities.json() == []

    @pytest.mark.asyncio
    async def test_disabled_door_discovery_returns_empty(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/delivery-settings",
            json={
                "speedy_office_enabled": True,
                "speedy_door_enabled": True,
                "econt_office_enabled": True,
                "econt_door_enabled": False,
            },
        )

        resp = await client.get("/v1/delivery/places?courier=econt&q=Соф")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_disabled_method_rejected_for_shipping_quote(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/delivery-settings",
            json={
                "speedy_office_enabled": True,
                "speedy_door_enabled": True,
                "econt_office_enabled": True,
                "econt_door_enabled": False,
            },
        )

        resp = await client.post(
            "/v1/delivery/calculate",
            json={
                "method": "door",
                "city": "София",
                "office_id": None,
                "address": {
                    "courier": "econt",
                    "city": "София",
                    "postal_code": "1000",
                    "street": "Витоша",
                },
                "items_total_cents": 1200,
                "couriers": ["econt"],
            },
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "DELIVERY_METHOD_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_disabled_method_rejected_for_checkout(self, admin_client, client):
        await admin_client.put(
            "/v1/admin/delivery-settings",
            json={
                "speedy_office_enabled": True,
                "speedy_door_enabled": False,
                "econt_office_enabled": True,
                "econt_door_enabled": True,
            },
        )

        resp = await client.post(
            "/v1/orders",
            json={
                "customer_email": "buyer@example.com",
                "customer_name": "Test Buyer",
                "delivery": {
                    "method": "door",
                    "door": {
                        "courier": "speedy",
                        "city": "София",
                        "postal_code": "1000",
                        "street": "Витоша",
                        "phone": "+359888123456",
                    },
                },
            },
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "DELIVERY_METHOD_UNAVAILABLE"
