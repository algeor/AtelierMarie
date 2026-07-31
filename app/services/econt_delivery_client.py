"""Thin Econt Delivery API client.

Business mapping stays in the fulfillment service. This module owns HTTP,
headers, endpoint names, timeout, response parsing, error classification, and
circuit-breaker behavior.
"""

from collections.abc import Callable
from typing import Any, Literal

import httpx
import structlog

from app.models.econt import EcontOrderPayload, EcontShipmentStatus
from app.services.econt_redaction import redact_mapping
from app.utils.circuit_breaker import CircuitBreaker

logger = structlog.get_logger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 10.0
_ECONT_BREAKER = CircuitBreaker(
    name="econt_delivery",
    failure_threshold=3,
    failure_window=30.0,
    recovery_timeout=60.0,
)

ErrorCategory = Literal[
    "config",
    "auth",
    "validation",
    "transient",
    "circuit_open",
    "unexpected_response",
]


class EcontDeliveryError(Exception):
    """Base class for Econt client errors."""

    category: ErrorCategory = "unexpected_response"

    def __init__(
        self,
        message: str,
        *,
        endpoint: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.status_code = status_code
        self.details = redact_mapping(details or {})
        super().__init__(message)

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "message": str(self),
            "endpoint": self.endpoint,
            "status_code": self.status_code,
            "details": self.details,
        }


class EcontConfigError(EcontDeliveryError):
    category: ErrorCategory = "config"


class EcontAuthError(EcontDeliveryError):
    category: ErrorCategory = "auth"


class EcontValidationError(EcontDeliveryError):
    category: ErrorCategory = "validation"


class EcontTransientError(EcontDeliveryError):
    category: ErrorCategory = "transient"


class EcontCircuitOpenError(EcontDeliveryError):
    category: ErrorCategory = "circuit_open"


class EcontUnexpectedResponseError(EcontDeliveryError):
    category: ErrorCategory = "unexpected_response"


def get_econt_circuit_breaker() -> CircuitBreaker:
    """Expose the Econt circuit breaker for admin health diagnostics."""
    return _ECONT_BREAKER


class EcontDeliveryClient:
    """HTTP client for Econt Delivery JSON endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        private_key: str,
        shop_id: str,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        breaker: CircuitBreaker | None = None,
        client_factory: Callable[..., httpx.Client] = httpx.Client,
    ) -> None:
        if not base_url:
            raise EcontConfigError("Econt base URL is missing")
        if not private_key:
            raise EcontConfigError("Econt private key is missing")
        if not shop_id:
            raise EcontConfigError("Econt shop id is missing")
        self.base_url = base_url.rstrip("/") + "/"
        self.private_key = _connection_code(private_key, shop_id)
        self.shop_id = shop_id
        self.timeout = httpx.Timeout(timeout_seconds)
        self.breaker = breaker or _ECONT_BREAKER
        self.client_factory = client_factory

    def update_order(self, order: EcontOrderPayload) -> dict[str, Any]:
        return self._post(
            "OrdersService.updateOrder.json",
            {"order": order.model_dump(by_alias=True, exclude_none=True)},
        )

    def create_awb(self, order: EcontOrderPayload) -> EcontShipmentStatus:
        body = self._post(
            "OrdersService.createAWB.json",
            {"order": order.model_dump(by_alias=True, exclude_none=True)},
        )
        return _shipment_status_from_body(body)

    def get_trace(self, shipment_number: str) -> EcontShipmentStatus:
        if not shipment_number:
            raise EcontValidationError("shipment_number is required")
        body = self._post(
            "OrdersService.getTrace.json",
            {"shipmentNumber": shipment_number},
        )
        return _shipment_status_from_body(body)

    def delete_label(self, shipment_number: str) -> dict[str, Any]:
        if not shipment_number:
            raise EcontValidationError("shipment_number is required")
        return self._post("OrdersService.deleteLabel.json", {"shipmentNumber": shipment_number})

    def test_connection(self) -> bool:
        """Safe credential smoke test that does not create a shipment.

        A validation error for the deliberately fake shipment number still proves
        that the endpoint, auth, and shop identity were accepted well enough to
        reach Econt's business validation layer.
        """
        try:
            self.get_trace("__atelier_marie_connection_test__")
        except EcontValidationError:
            return True
        return True

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.breaker.allow_request():
            raise EcontCircuitOpenError(
                "Econt Delivery circuit breaker is open",
                endpoint=endpoint,
            )

        headers = {
            "Authorization": self.private_key,
            "Content-Type": "application/json",
            "X-ID-Shop": self.shop_id,
        }
        request_payload = {"shopID": self.shop_id, **payload}
        url = self.base_url + endpoint

        try:
            with self.client_factory(timeout=self.timeout) as client:
                response = client.post(url, json=request_payload, headers=headers)
        except httpx.TimeoutException as exc:
            self.breaker.record_failure()
            raise EcontTransientError(
                "Econt request timed out",
                endpoint=endpoint,
                details={"payload": request_payload, "headers": headers},
            ) from exc
        except httpx.TransportError as exc:
            self.breaker.record_failure()
            raise EcontTransientError(
                "Econt transport error",
                endpoint=endpoint,
                details={"payload": request_payload, "headers": headers},
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            if response.status_code >= 500:
                self.breaker.record_failure()
                raise EcontTransientError(
                    "Econt service is unavailable",
                    endpoint=endpoint,
                    status_code=response.status_code,
                    details={"body": response.text},
                ) from exc
            self.breaker.record_failure()
            raise EcontUnexpectedResponseError(
                "Econt returned malformed JSON",
                endpoint=endpoint,
                status_code=response.status_code,
                details={"body": response.text},
            ) from exc

        if response.status_code in {401, 403} or _looks_like_auth_error(body):
            raise EcontAuthError(
                _error_message(body) or "Econt authentication failed",
                endpoint=endpoint,
                status_code=response.status_code,
                details={"body": body},
            )

        if _looks_like_business_error(body):
            raise EcontValidationError(
                _error_message(body) or "Econt rejected the request",
                endpoint=endpoint,
                status_code=response.status_code,
                details={"body": body},
            )

        if response.status_code >= 500:
            self.breaker.record_failure()
            raise EcontTransientError(
                "Econt service is unavailable",
                endpoint=endpoint,
                status_code=response.status_code,
                details={"body": body},
            )

        if response.status_code >= 400 or _looks_like_business_error(body):
            raise EcontValidationError(
                _error_message(body) or "Econt rejected the request",
                endpoint=endpoint,
                status_code=response.status_code,
                details={"body": body},
            )

        self.breaker.record_success()
        return body if isinstance(body, dict) else {"data": body}


def _connection_code(private_key: str, shop_id: str) -> str:
    private_key = private_key.strip()
    legacy_prefix = f"{shop_id}@"
    if private_key.startswith(legacy_prefix):
        return private_key.removeprefix(legacy_prefix)
    return private_key


def _shipment_status_from_body(body: dict[str, Any]) -> EcontShipmentStatus:
    data = body.get("shipment") or body.get("shipmentStatus") or body.get("result") or body
    if not isinstance(data, dict):
        raise EcontUnexpectedResponseError("Econt shipment response has unexpected shape")
    return EcontShipmentStatus.model_validate(data)


def _error_message(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    for key in ("message", "error", "errorMessage", "description"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    errors = body.get("errors")
    if isinstance(errors, list) and errors:
        return str(errors[0])
    return None


def _looks_like_auth_error(body: Any) -> bool:
    message = (_error_message(body) or "").casefold()
    return (
        "invalid username or password" in message
        or "authorization" in message
        and "invalid" in message
    )


def _looks_like_business_error(body: Any) -> bool:
    if not isinstance(body, dict):
        return False
    status = str(body.get("status") or body.get("type") or "").casefold()
    if status in {"error", "validation_error", "failed"} or status.startswith("ex"):
        return True
    return any(key in body for key in ("error", "errorMessage", "errors"))
