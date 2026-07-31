"""Unit tests for the thin Econt Delivery API client."""

import httpx
import pytest

from app.models.econt import EcontCustomerInfo, EcontOrderItem, EcontOrderPayload
from app.services.econt_delivery_client import (
    EcontAuthError,
    EcontCircuitOpenError,
    EcontConfigError,
    EcontDeliveryClient,
    EcontTransientError,
    EcontUnexpectedResponseError,
    EcontValidationError,
)
from app.utils.circuit_breaker import CircuitBreaker


class FakeHttpClient:
    def __init__(self, *, response: httpx.Response | None = None, exc: Exception | None = None):
        self.response = response
        self.exc = exc
        self.calls: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json, headers):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.exc:
            raise self.exc
        return self.response


def _factory(fake: FakeHttpClient):
    def make_client(**kwargs):
        fake.timeout = kwargs.get("timeout")
        return fake

    return make_client


def _breaker(threshold: int = 3) -> CircuitBreaker:
    return CircuitBreaker(
        name="test_econt",
        failure_threshold=threshold,
        failure_window=30.0,
        recovery_timeout=60.0,
    )


def _client(fake: FakeHttpClient, breaker: CircuitBreaker | None = None) -> EcontDeliveryClient:
    return EcontDeliveryClient(
        base_url="https://delivery-demo.econt.com/services/",
        private_key="private-key",
        shop_id="shop-1",
        breaker=breaker or _breaker(),
        client_factory=_factory(fake),
    )


def _order() -> EcontOrderPayload:
    return EcontOrderPayload(
        order_number="ORDER-1",
        order_sum=42.5,
        declared_value=42.5,
        cod=True,
        currency="EUR",
        shipment_description="Atelier Marie order",
        customer_info=EcontCustomerInfo(
            name="Mira",
            phone="+359888123456",
            email="mira@example.com",
            city_name="София",
            office_code="1127",
        ),
        items=[EcontOrderItem(name="Candle", sku="cand-1", quantity=1, total_weight=0.3)],
    )


class TestEcontDeliveryClient:
    def test_create_awb_success_posts_expected_payload_and_headers(self):
        fake = FakeHttpClient(
            response=httpx.Response(
                200,
                json={"shipmentNumber": "1234567890", "pdfURL": "https://label.test/a.pdf"},
            )
        )
        client = _client(fake)

        status = client.create_awb(_order())

        assert status.shipment_number == "1234567890"
        assert status.pdf_url == "https://label.test/a.pdf"
        call = fake.calls[0]
        assert (
            call["url"] == "https://delivery-demo.econt.com/services/OrdersService.createAWB.json"
        )
        assert call["headers"]["Authorization"] == "private-key"
        assert call["headers"]["X-ID-Shop"] == "shop-1"
        assert "X-Shop-Id" not in call["headers"]
        assert call["json"]["shopID"] == "shop-1"
        assert call["json"]["order"]["declaredValue"] == 42.5
        assert call["json"]["order"]["customerInfo"]["officeCode"] == "1127"
        assert call["json"]["order"]["items"][0]["totalWeight"] == 0.3

    def test_authorization_strips_legacy_shop_prefixed_connection_code(self):
        fake = FakeHttpClient(response=httpx.Response(200, json={"ok": True}))
        client = EcontDeliveryClient(
            base_url="https://delivery-demo.econt.com/services/",
            private_key="shop-1@connection-code",
            shop_id="shop-1",
            breaker=_breaker(),
            client_factory=_factory(fake),
        )

        client.update_order(_order())

        assert fake.calls[0]["headers"]["Authorization"] == "connection-code"

    def test_constructor_requires_config(self):
        with pytest.raises(EcontConfigError):
            EcontDeliveryClient(base_url="", private_key="private", shop_id="shop")
        with pytest.raises(EcontConfigError):
            EcontDeliveryClient(base_url="https://example.test", private_key="", shop_id="shop")
        with pytest.raises(EcontConfigError):
            EcontDeliveryClient(base_url="https://example.test", private_key="private", shop_id="")

    def test_auth_error_is_classified_without_tripping_circuit(self):
        breaker = _breaker(threshold=1)
        fake = FakeHttpClient(
            response=httpx.Response(200, json={"message": "Invalid username or password"})
        )
        client = _client(fake, breaker)

        with pytest.raises(EcontAuthError) as exc_info:
            client.update_order(_order())

        assert exc_info.value.category == "auth"
        assert breaker.get_health()["state"] == "closed"

    def test_econt_517_auth_body_is_classified_as_auth(self):
        breaker = _breaker(threshold=1)
        fake = FakeHttpClient(
            response=httpx.Response(
                517,
                json={"type": "ExAccessDenied", "message": "Invalid username or password."},
            )
        )
        client = _client(fake, breaker)

        with pytest.raises(EcontAuthError) as exc_info:
            client.update_order(_order())

        assert exc_info.value.category == "auth"
        assert breaker.get_health()["state"] == "closed"

    def test_econt_517_business_body_is_classified_as_validation(self):
        breaker = _breaker(threshold=1)
        fake = FakeHttpClient(
            response=httpx.Response(
                517,
                json={"type": "ExInvalidShipmentNum", "message": "Невалиден номер на пратка."},
            )
        )
        client = _client(fake, breaker)

        with pytest.raises(EcontValidationError) as exc_info:
            client.get_trace("__atelier_marie_connection_test__")

        assert exc_info.value.category == "validation"
        assert breaker.get_health()["state"] == "closed"

    def test_validation_error_does_not_trip_circuit(self):
        breaker = _breaker(threshold=1)
        fake = FakeHttpClient(response=httpx.Response(422, json={"message": "officeCode required"}))
        client = _client(fake, breaker)

        with pytest.raises(EcontValidationError) as exc_info:
            client.create_awb(_order())

        assert exc_info.value.category == "validation"
        assert breaker.get_health()["state"] == "closed"

    def test_timeout_is_transient_and_opens_circuit(self):
        breaker = _breaker(threshold=1)
        fake = FakeHttpClient(exc=httpx.TimeoutException("timed out"))
        client = _client(fake, breaker)

        with pytest.raises(EcontTransientError):
            client.update_order(_order())

        assert breaker.get_health()["state"] == "open"

        with pytest.raises(EcontCircuitOpenError):
            client.update_order(_order())
        assert len(fake.calls) == 1

    def test_5xx_is_transient_and_redacts_error_context(self):
        breaker = _breaker(threshold=1)
        fake = FakeHttpClient(response=httpx.Response(503, text="unavailable"))
        client = _client(fake, breaker)

        with pytest.raises(EcontTransientError) as exc_info:
            client.update_order(_order())

        assert exc_info.value.category == "transient"
        assert breaker.get_health()["state"] == "open"
        assert "private-key" not in str(exc_info.value.to_safe_dict())

    def test_malformed_json_is_unexpected_response_and_trips_circuit(self):
        breaker = _breaker(threshold=1)
        fake = FakeHttpClient(response=httpx.Response(200, content=b"not-json"))
        client = _client(fake, breaker)

        with pytest.raises(EcontUnexpectedResponseError):
            client.get_trace("1234567890")

        assert breaker.get_health()["state"] == "open"

    def test_business_error_body_is_validation_error(self):
        fake = FakeHttpClient(
            response=httpx.Response(200, json={"type": "error", "message": "bad data"})
        )
        client = _client(fake)

        with pytest.raises(EcontValidationError) as exc_info:
            client.delete_label("123")

        assert str(exc_info.value) == "bad data"

    def test_test_connection_treats_business_validation_as_successful_connectivity(self):
        fake = FakeHttpClient(response=httpx.Response(422, json={"message": "shipment not found"}))
        client = _client(fake)

        assert client.test_connection() is True

    def test_circuit_open_fails_fast_without_http_call(self):
        breaker = _breaker(threshold=1)
        breaker.record_failure()
        fake = FakeHttpClient(response=httpx.Response(200, json={"ok": True}))
        client = _client(fake, breaker)

        with pytest.raises(EcontCircuitOpenError):
            client.update_order(_order())

        assert fake.calls == []
