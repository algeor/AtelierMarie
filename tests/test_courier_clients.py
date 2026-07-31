"""Unit tests for the Speedy and Econt courier calculation clients.

Covers task 3.1 of shipping-pricing (Phase A): each client returns a live quote
on success (`price_source="live"`, `is_fallback=False`) and degrades to the flat
fallback (`price_source="flat"`, `is_fallback=True`) on timeout, 5xx, auth
failure, or a malformed response — never raising to the caller.

The clients import `httpx` lazily inside `calculate`, so we patch
`httpx.AsyncClient` with a fake async context-manager client.
"""

from types import SimpleNamespace

import httpx
import pytest

from app.constants import FALLBACK_SHIPPING_CENTS
from app.services import econt_client, speedy_client


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, *, content=b"", headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = ""
        self.content = content
        self.headers = headers or {}

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient as an async context manager.

    `post` either returns a canned _FakeResponse or raises the configured
    exception (to simulate a timeout / transport error). The outgoing request
    JSON is recorded on `captured` so tests can assert the payload shape.
    """

    def __init__(self, *, response=None, raises=None, captured=None):
        self._response = response
        self._raises = raises
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *args, **kwargs):
        if self._captured is not None and "json" in kwargs:
            self._captured.append(kwargs["json"])
        if self._raises is not None:
            raise self._raises
        return self._response


def _patch_httpx(monkeypatch, *, response=None, raises=None, captured=None):
    """Patch httpx.AsyncClient so both clients get the fake client.

    Pass a `captured` list to record each POST's `json=` payload.
    """

    def _factory(*args, **kwargs):
        return _FakeAsyncClient(response=response, raises=raises, captured=captured)

    monkeypatch.setattr(httpx, "AsyncClient", _factory)


# ===========================================================================
# Speedy client
# ===========================================================================


class TestSpeedyClient:
    @pytest.mark.asyncio
    async def test_happy_path_returns_live_quote(self, monkeypatch):
        """A well-formed 200 response yields a live quote in cents."""
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(
                200,
                {"calculations": [{"price": {"total": 6.5}, "deliveryDeadline": 2}]},
            ),
        )
        quote = await speedy_client.calculate(
            client_id="12345678901234",
            recipient_city="Пловдив",
            recipient_office_id="speedy-pdv-01",
            weight_grams=1400,
            username="u",
            password="p",
            quoted_at="2026-07-28 10:00:00",
        )
        assert quote.courier == "speedy"
        assert quote.cents == 650
        assert quote.estimated_delivery_days == 2
        assert quote.price_source == "live"
        assert quote.is_fallback is False
        assert quote.quoted_at == "2026-07-28 10:00:00"

    @pytest.mark.asyncio
    async def test_timeout_returns_flat_fallback(self, monkeypatch):
        _patch_httpx(monkeypatch, raises=httpx.TimeoutException("timed out"))
        quote = await speedy_client.calculate(
            client_id="12345678901234",
            recipient_city="Пловдив",
            recipient_office_id=None,
            weight_grams=800,
            username="u",
            password="p",
            quoted_at="2026-07-28 10:00:00",
        )
        assert quote.courier == "speedy"
        assert quote.cents == FALLBACK_SHIPPING_CENTS
        assert quote.price_source == "flat"
        assert quote.is_fallback is True
        assert quote.quoted_at == "2026-07-28 10:00:00"

    @pytest.mark.asyncio
    async def test_5xx_returns_flat_fallback(self, monkeypatch):
        _patch_httpx(monkeypatch, response=_FakeResponse(503, {}))
        quote = await speedy_client.calculate(
            client_id="12345678901234",
            recipient_city="Пловдив",
            recipient_office_id=None,
            weight_grams=800,
            username="u",
            password="p",
        )
        assert quote.price_source == "flat"
        assert quote.is_fallback is True

    @pytest.mark.asyncio
    async def test_auth_failure_returns_flat_fallback(self, monkeypatch):
        """A 401 (bad credentials) degrades to fallback, never raises."""
        _patch_httpx(monkeypatch, response=_FakeResponse(401, {"error": "unauthorized"}))
        quote = await speedy_client.calculate(
            client_id="12345678901234",
            recipient_city="Пловдив",
            recipient_office_id=None,
            weight_grams=800,
            username="bad",
            password="creds",
        )
        assert quote.cents == FALLBACK_SHIPPING_CENTS
        assert quote.price_source == "flat"

    @pytest.mark.asyncio
    async def test_empty_calculations_returns_fallback(self, monkeypatch):
        _patch_httpx(monkeypatch, response=_FakeResponse(200, {"calculations": []}))
        quote = await speedy_client.calculate(
            client_id="12345678901234",
            recipient_city="Пловдив",
            recipient_office_id=None,
            weight_grams=800,
            username="u",
            password="p",
        )
        assert quote.is_fallback is True

    @pytest.mark.asyncio
    async def test_missing_price_returns_fallback(self, monkeypatch):
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(200, {"calculations": [{"price": {}}]}),
        )
        quote = await speedy_client.calculate(
            client_id="12345678901234",
            recipient_city="Пловдив",
            recipient_office_id=None,
            weight_grams=800,
            username="u",
            password="p",
        )
        assert quote.is_fallback is True
        assert quote.price_source == "flat"


# ===========================================================================
# Speedy payload contract (transport-independent)
# ===========================================================================


class TestSpeedyPayloadContract:
    """Assert the assembled calculate payload directly — no mocked HTTP.

    A canned 200 response must not be able to hide a payload Speedy would
    reject (spec: payload contract). These call `build_calculate_payload`.
    """

    def test_office_mode_sends_numeric_client_id_and_pickup_office_id(self):
        from app.models.shipping import ShippingAddress  # noqa: F401 (import parity)

        payload = speedy_client.build_calculate_payload(
            client_id="12345678901234",
            recipient_city="София",
            recipient_office_id="42",
            weight_grams=800,
            username="u",
            password="p",
        )
        assert payload["sender"]["clientId"] == 12345678901234
        assert isinstance(payload["sender"]["clientId"], int)
        assert payload["recipient"]["pickupOfficeId"] == 42
        assert isinstance(payload["recipient"]["pickupOfficeId"], int)
        # An empty serviceIds list 400s live (task 0) — a concrete service is named.
        assert payload["service"]["serviceIds"] == [speedy_client._DEFAULT_SERVICE_ID]

    def test_empty_client_id_yields_null_sender_client_id(self):
        payload = speedy_client.build_calculate_payload(
            client_id="",
            recipient_city="София",
            recipient_office_id=None,
            weight_grams=800,
            username="u",
            password="p",
        )
        # Empty/non-numeric clientId must NOT reach Speedy as a slug — it is None
        # (and _sender_client_id logs speedy_sender_client_id_invalid).
        assert payload["sender"]["clientId"] is None

    def test_slug_office_id_dropped_not_sent_as_string(self):
        payload = speedy_client.build_calculate_payload(
            client_id="12345678901234",
            recipient_city="Пловдив",
            recipient_office_id="speedy-pdv-01",  # slug, not numeric
            weight_grams=800,
            username="u",
            password="p",
        )
        # A non-numeric office ref is dropped rather than sent as an invalid value.
        assert "pickupOfficeId" not in payload["recipient"]


# ===========================================================================
# Econt client
# ===========================================================================


class TestEcontClient:
    @pytest.mark.asyncio
    async def test_calculate_uses_configured_url(self, monkeypatch):
        captured: dict[str, str] = {}

        class _UrlCapturingClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, **kwargs):
                captured["url"] = url
                return _FakeResponse(200, {"label": {"totalPrice": 5.9}})

        monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: _UrlCapturingClient())
        monkeypatch.setattr(
            econt_client,
            "get_settings",
            lambda: SimpleNamespace(econt_calculate_url="http://fake-econt/calculate"),
        )

        quote = await econt_client.calculate(
            sender_name="Atelier Marie",
            sender_phone="0899869055",
            sender_address="ул. Тест 1",
            sender_city="София",
            recipient_city="Варна",
            recipient_office_id="econt-vn-02",
            weight_grams=1200,
            username="u",
            password="p",
        )

        assert quote.price_source == "live"
        assert captured["url"] == "http://fake-econt/calculate"

    @pytest.mark.asyncio
    async def test_happy_path_returns_live_quote(self, monkeypatch):
        captured: list = []
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(
                200,
                {"label": {"totalPrice": 5.9, "deliveryDays": 1}},
            ),
            captured=captured,
        )
        quote = await econt_client.calculate(
            sender_name="Atelier Marie",
            sender_phone="0899869055",
            sender_address="ул. Тест 1",
            sender_city="София",
            recipient_city="Варна",
            recipient_office_id="econt-vn-02",
            weight_grams=1200,
            username="u",
            password="p",
            quoted_at="2026-07-28 10:00:00",
        )
        assert quote.courier == "econt"
        assert quote.cents == 590
        assert quote.estimated_delivery_days == 1
        assert quote.price_source == "live"
        assert quote.is_fallback is False
        # The payload must carry the fields Econt's calculate mode requires:
        # shipmentType, sender name+phone, and a (placeholder) receiver name+phone.
        label = captured[0]["label"]
        assert captured[0]["mode"] == "calculate"
        assert label["shipmentType"] == econt_client._SHIPMENT_TYPE
        assert label["senderClient"] == {"name": "Atelier Marie", "phones": ["0899869055"]}
        assert label["receiverClient"]["name"] == econt_client._PLACEHOLDER_RECEIVER_NAME
        assert label["receiverClient"]["phones"] == [econt_client._PLACEHOLDER_RECEIVER_PHONE]

    @pytest.mark.asyncio
    async def test_shipment_type_is_pack(self):
        # Guard against a regression to a rejected token (e.g. "courier"): the
        # live API only accepts pack/document/post_pack for label.shipmentType.
        assert econt_client._SHIPMENT_TYPE == "pack"

    @pytest.mark.asyncio
    async def test_door_mode_nests_postcode_inside_city(self, monkeypatch):
        # postCode must sit INSIDE the city object — Econt uses it to
        # disambiguate same-named settlements (ExMultipleCity otherwise). An
        # address-level postCode is ignored and the call 517s (confirmed live).
        from app.models.shipping import ShippingAddress

        captured: list = []
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(200, {"label": {"totalPrice": 5.9}}),
            captured=captured,
        )
        await econt_client.calculate(
            sender_name="Atelier Marie",
            sender_phone="0899869055",
            sender_address="ул. Тест 1",
            sender_city="София",
            recipient_city="Садово",
            recipient_office_id=None,
            weight_grams=1000,
            username="u",
            password="p",
            address=ShippingAddress(
                courier="econt",
                city="Садово",
                postal_code="4122",
                street="Главна",
                building="1",
            ),
        )
        receiver_address = captured[0]["label"]["receiverAddress"]
        assert receiver_address["city"]["postCode"] == "4122"
        # No address-level postCode — Econt ignores it there.
        assert "postCode" not in receiver_address

    @pytest.mark.asyncio
    async def test_door_mode_omits_missing_address_fields(self, monkeypatch):
        # A preview address may carry only a city (+ maybe postcode). Optional
        # street/building must be omitted from the payload, not sent as null.
        from app.models.shipping import ShippingAddress

        captured: list = []
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(200, {"label": {"totalPrice": 5.9}}),
            captured=captured,
        )
        await econt_client.calculate(
            sender_name="Atelier Marie",
            sender_phone="0899869055",
            sender_address="ул. Тест 1",
            sender_city="София",
            recipient_city="Пловдив",
            recipient_office_id=None,
            weight_grams=1000,
            username="u",
            password="p",
            address=ShippingAddress(courier="econt", city="Пловдив", postal_code="4000"),
        )
        receiver_address = captured[0]["label"]["receiverAddress"]
        assert receiver_address == {"city": {"name": "Пловдив", "postCode": "4000"}}
        assert "street" not in receiver_address
        assert "num" not in receiver_address

    @pytest.mark.asyncio
    async def test_timeout_returns_flat_fallback(self, monkeypatch):
        _patch_httpx(monkeypatch, raises=httpx.TimeoutException("timed out"))
        quote = await econt_client.calculate(
            sender_name="Atelier Marie",
            sender_phone="0899869055",
            sender_address="ул. Тест 1",
            sender_city="София",
            recipient_city="Варна",
            recipient_office_id=None,
            weight_grams=900,
            username="u",
            password="p",
        )
        assert quote.courier == "econt"
        assert quote.cents == FALLBACK_SHIPPING_CENTS
        assert quote.price_source == "flat"
        assert quote.is_fallback is True

    @pytest.mark.asyncio
    async def test_5xx_returns_flat_fallback(self, monkeypatch):
        _patch_httpx(monkeypatch, response=_FakeResponse(500, {}))
        quote = await econt_client.calculate(
            sender_name="Atelier Marie",
            sender_phone="0899869055",
            sender_address="ул. Тест 1",
            sender_city="София",
            recipient_city="Варна",
            recipient_office_id=None,
            weight_grams=900,
            username="u",
            password="p",
        )
        assert quote.price_source == "flat"
        assert quote.is_fallback is True

    @pytest.mark.asyncio
    async def test_auth_failure_returns_flat_fallback(self, monkeypatch):
        _patch_httpx(monkeypatch, response=_FakeResponse(403, {"error": "forbidden"}))
        quote = await econt_client.calculate(
            sender_name="Atelier Marie",
            sender_phone="0899869055",
            sender_address="ул. Тест 1",
            sender_city="София",
            recipient_city="Варна",
            recipient_office_id=None,
            weight_grams=900,
            username="bad",
            password="creds",
        )
        assert quote.cents == FALLBACK_SHIPPING_CENTS
        assert quote.is_fallback is True

    @pytest.mark.asyncio
    async def test_missing_price_returns_fallback(self, monkeypatch):
        _patch_httpx(monkeypatch, response=_FakeResponse(200, {"label": {}}))
        quote = await econt_client.calculate(
            sender_name="Atelier Marie",
            sender_phone="0899869055",
            sender_address="ул. Тест 1",
            sender_city="София",
            recipient_city="Варна",
            recipient_office_id=None,
            weight_grams=900,
            username="u",
            password="p",
        )
        assert quote.is_fallback is True
        assert quote.price_source == "flat"


# ===========================================================================
# Speedy shipment / track / print (Sections 3-6)
#
# These are real operations, NOT the best-effort pricing path: on failure they
# raise a typed SpeedyError with the Speedy error `context`/`message` mapped in,
# never a silent fallback (design Decision 6).
# ===========================================================================


class _FakeSyncClient:
    """Sync counterpart of _FakeAsyncClient for create_shipment_sync."""

    def __init__(self, *, response=None, raises=None, captured=None):
        self._response = response
        self._raises = raises
        self._captured = captured

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, *args, **kwargs):
        if self._captured is not None and "json" in kwargs:
            self._captured.append(kwargs["json"])
        if self._raises is not None:
            raise self._raises
        return self._response


def _patch_httpx_sync(monkeypatch, *, response=None, raises=None, captured=None):
    def _factory(*args, **kwargs):
        return _FakeSyncClient(response=response, raises=raises, captured=captured)

    monkeypatch.setattr(httpx, "Client", _factory)


class TestSpeedyShipmentPayloadContract:
    """Assert the assembled /shipment payload carries the REAL recipient."""

    def test_office_mode_real_recipient_and_numeric_ids(self):
        payload = speedy_client.build_shipment_payload(
            client_id="12345678901234",
            recipient_name="Иван Петров",
            recipient_phone="0888123456",
            weight_grams=500,
            username="u",
            password="p",
            order_ref="order-1",
            recipient_office_id="42",
        )
        assert payload["sender"]["clientId"] == 12345678901234
        assert payload["recipient"]["clientName"] == "Иван Петров"
        assert payload["recipient"]["phone1"] == {"number": "0888123456"}
        assert payload["recipient"]["pickupOfficeId"] == 42
        assert payload["ref1"] == "order-1"
        # No COD → sender pays the courier service, no cod block.
        assert payload["payment"]["courierServicePayer"] == "SENDER"
        assert "cod" not in payload["service"]["additionalServices"]

    def test_door_mode_builds_address_and_cod(self):
        payload = speedy_client.build_shipment_payload(
            client_id="12345678901234",
            recipient_name="Иван Петров",
            recipient_phone="0888123456",
            weight_grams=500,
            username="u",
            password="p",
            order_ref="order-2",
            recipient_city="София",
            recipient_postcode="1000",
            recipient_street="Витоша",
            recipient_building="5",
            cod_amount_cents=2599,
        )
        addr = payload["recipient"]["address"]
        assert addr == {
            "siteName": "София",
            "postCode": "1000",
            "streetName": "Витоша",
            "streetNo": "5",
        }
        # COD → recipient pays, amount in BGN (cents / 100).
        assert payload["payment"]["courierServicePayer"] == "RECIPIENT"
        assert payload["service"]["additionalServices"]["cod"]["amount"] == 25.99


class TestSpeedyCreateShipment:
    @pytest.mark.asyncio
    async def test_happy_path_returns_shipment_id(self, monkeypatch):
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(200, {"id": 63689182611, "parcels": [{"id": 1}]}),
        )
        tracking = await speedy_client.create_shipment(
            client_id="12345678901234",
            recipient_name="Иван",
            recipient_phone="0888123456",
            weight_grams=500,
            username="u",
            password="p",
            order_ref="order-1",
            recipient_office_id="42",
        )
        assert tracking == "63689182611"

    @pytest.mark.asyncio
    async def test_http_error_maps_speedy_context(self, monkeypatch):
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(
                400, {"error": {"context": "recipient.phone", "message": "phone required"}}
            ),
        )
        with pytest.raises(speedy_client.ShipmentCreationError) as exc:
            await speedy_client.create_shipment(
                client_id="12345678901234",
                recipient_name="Иван",
                recipient_phone="",
                weight_grams=500,
                username="u",
                password="p",
                order_ref="order-1",
                recipient_office_id="42",
            )
        assert exc.value.context == "recipient.phone"
        assert "phone required" in str(exc.value)

    @pytest.mark.asyncio
    async def test_transport_error_raises_typed(self, monkeypatch):
        _patch_httpx(monkeypatch, raises=httpx.ConnectError("no route"))
        with pytest.raises(speedy_client.ShipmentCreationError):
            await speedy_client.create_shipment(
                client_id="12345678901234",
                recipient_name="Иван",
                recipient_phone="0888",
                weight_grams=500,
                username="u",
                password="p",
                order_ref="order-1",
                recipient_office_id="42",
            )

    @pytest.mark.asyncio
    async def test_missing_id_raises(self, monkeypatch):
        _patch_httpx(monkeypatch, response=_FakeResponse(200, {"parcels": []}))
        with pytest.raises(speedy_client.ShipmentCreationError):
            await speedy_client.create_shipment(
                client_id="12345678901234",
                recipient_name="Иван",
                recipient_phone="0888",
                weight_grams=500,
                username="u",
                password="p",
                order_ref="order-1",
                recipient_office_id="42",
            )

    def test_sync_happy_path_returns_id(self, monkeypatch):
        _patch_httpx_sync(monkeypatch, response=_FakeResponse(200, {"id": 999}))
        tracking = speedy_client.create_shipment_sync(
            client_id="12345678901234",
            recipient_name="Иван",
            recipient_phone="0888",
            weight_grams=500,
            username="u",
            password="p",
            order_ref="order-1",
            recipient_office_id="42",
        )
        assert tracking == "999"

    def test_sync_error_maps_typed(self, monkeypatch):
        _patch_httpx_sync(
            monkeypatch,
            response=_FakeResponse(400, {"error": {"message": "bad office"}}),
        )
        with pytest.raises(speedy_client.ShipmentCreationError):
            speedy_client.create_shipment_sync(
                client_id="12345678901234",
                recipient_name="Иван",
                recipient_phone="0888",
                weight_grams=500,
                username="u",
                password="p",
                order_ref="order-1",
                recipient_office_id="42",
            )


class TestSpeedyTrack:
    @pytest.mark.parametrize(
        "description,expected",
        [
            ("Пратката е доставена", "delivered"),
            ("Delivered to recipient", "delivered"),
            ("Товар за разнос", "out_for_delivery"),
            ("Пратката е върната", "returned"),
            ("Delivery unsuccessful", "failed"),
            ("Приета в сортиращ център", "in_transit"),
            (None, "in_transit"),
        ],
    )
    def test_normalize_status(self, description, expected):
        assert speedy_client.normalize_track_status(description) == expected

    @pytest.mark.asyncio
    async def test_happy_path_maps_last_operation(self, monkeypatch):
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(
                200,
                {"parcels": [{"operations": [{"description": "Пратката е доставена"}]}]},
            ),
        )
        status = await speedy_client.track_shipment(
            tracking_number="123", username="u", password="p"
        )
        assert status == "delivered"

    @pytest.mark.asyncio
    async def test_no_operations_is_in_transit(self, monkeypatch):
        _patch_httpx(monkeypatch, response=_FakeResponse(200, {"parcels": [{"operations": []}]}))
        status = await speedy_client.track_shipment(
            tracking_number="123", username="u", password="p"
        )
        assert status == "in_transit"

    @pytest.mark.asyncio
    async def test_http_error_raises_tracking_error(self, monkeypatch):
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(404, {"error": {"message": "unknown parcel"}}),
        )
        with pytest.raises(speedy_client.TrackingError):
            await speedy_client.track_shipment(tracking_number="x", username="u", password="p")

    @pytest.mark.asyncio
    async def test_transport_error_raises_tracking_error(self, monkeypatch):
        _patch_httpx(monkeypatch, raises=httpx.TimeoutException("t"))
        with pytest.raises(speedy_client.TrackingError):
            await speedy_client.track_shipment(tracking_number="x", username="u", password="p")


class TestSpeedyPrintLabel:
    @pytest.mark.asyncio
    async def test_happy_path_returns_pdf_bytes(self, monkeypatch):
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(
                200, {}, content=b"%PDF-1.4 ...", headers={"content-type": "application/pdf"}
            ),
        )
        pdf = await speedy_client.print_label(tracking_number="123", username="u", password="p")
        assert pdf.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_non_pdf_body_raises(self, monkeypatch):
        # A JSON error body with a 200 must not be handed back as a "PDF".
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(
                200,
                {"error": {"message": "no label"}},
                headers={"content-type": "application/json"},
            ),
        )
        with pytest.raises(speedy_client.LabelPrintError):
            await speedy_client.print_label(tracking_number="123", username="u", password="p")

    @pytest.mark.asyncio
    async def test_http_error_raises_label_error(self, monkeypatch):
        _patch_httpx(
            monkeypatch,
            response=_FakeResponse(400, {"error": {"message": "bad size"}}),
        )
        with pytest.raises(speedy_client.LabelPrintError):
            await speedy_client.print_label(tracking_number="123", username="u", password="p")
