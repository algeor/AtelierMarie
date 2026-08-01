"""Public webhook endpoints (signature-authenticated, not admin).

`POST /v1/webhooks/zeptomail` consumes ZeptoMail bounce/complaint events.
`POST /v1/webhooks/stripe` consumes Stripe payment events.
Both paths are registered in `session_skip_paths` so no session cookie is issued.
"""

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import get_db
from app.responses import error_response
from app.services.payment_service import (
    StripeWebhookVerificationError,
    _now_str,
    construct_stripe_webhook_event,
    handle_charge_refunded,
    handle_dispute_event,
    handle_payment_failed,
    handle_payment_succeeded,
    handle_refund_updated,
    handle_session_expired,
)
from app.services.webhook_service import (
    WebhookVerificationError,
    handle_webhook_event,
    verify_signature,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

_MAX_BODY_BYTES = 64 * 1024


def _stripe_value(obj: object, key: str) -> object | None:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _stripe_str(obj: object, key: str) -> str | None:
    value = _stripe_value(obj, key)
    return value if isinstance(value, str) and value else None


def _stripe_int(obj: object, key: str) -> int | None:
    value = _stripe_value(obj, key)
    return value if isinstance(value, int) else None


def _stripe_bool(obj: object, key: str) -> bool | None:
    value = _stripe_value(obj, key)
    return value if isinstance(value, bool) else None


def _stripe_metadata_str(obj: object, key: str) -> str | None:
    metadata = _stripe_value(obj, "metadata")
    if isinstance(metadata, dict):
        value = metadata.get(key)
    else:
        getter = getattr(metadata, "get", None)
        value = getter(key) if callable(getter) else None
    return value if isinstance(value, str) and value else None


@router.post(
    "/zeptomail",
    summary="ZeptoMail bounce/complaint webhook",
    description="Consumes hard_bounce / soft_bounce / fbl_complaint events. "
    "Authenticated by the ZeptoMail producer-signature HMAC over the raw body.",
)
async def zeptomail_webhook(request: Request) -> JSONResponse:
    settings = get_settings()

    raw_body = await request.body()
    if len(raw_body) > _MAX_BODY_BYTES:
        return error_response(413, "PAYLOAD_TOO_LARGE", "Body too large")

    try:
        verify_signature(
            raw_body,
            request.headers.get("producer-signature"),
            settings.zeptomail_webhook_auth_key.get_secret_value(),
        )
    except WebhookVerificationError as exc:
        logger.warning("webhook_signature_rejected", reason=str(exc))
        return error_response(401, "INVALID_SIGNATURE", "Signature rejected")

    import json

    try:
        payload = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError):
        return error_response(400, "INVALID_PAYLOAD", "Malformed JSON")

    result = handle_webhook_event(payload if isinstance(payload, dict) else {})
    return JSONResponse(status_code=200, content=result)


@router.post(
    "/stripe",
    summary="Stripe payment webhook",
    description="Consumes allowlisted Stripe payment events. "
    "Authenticated by Stripe-Signature header. Returns 200 for all valid requests "
    "(including unknown event types); 400 only on bad signature.",
)
async def stripe_webhook(request: Request) -> JSONResponse:
    settings = get_settings()

    raw_body = await request.body()
    if len(raw_body) > _MAX_BODY_BYTES:
        return error_response(413, "PAYLOAD_TOO_LARGE", "Body too large")

    sig_header = request.headers.get("stripe-signature", "")
    webhook_secret = settings.stripe_webhook_secret

    try:
        event = construct_stripe_webhook_event(
            raw_body,
            sig_header,
            webhook_secret,
            settings.stripe_secret_key,
        )
    except StripeWebhookVerificationError as exc:
        logger.warning("stripe_webhook_signature_rejected", error=str(exc))
        return error_response(400, "INVALID_SIGNATURE", "Stripe signature rejected")

    now = _now_str()
    event_id = event.id
    event_type = event.type
    event_obj = event.data.object
    event_created = _stripe_int(event, "created")
    livemode = _stripe_bool(event, "livemode")

    with get_db() as conn:
        if event_type == "checkout.session.completed":
            order_id = (
                _stripe_str(event_obj, "client_reference_id")
                or _stripe_metadata_str(event_obj, "order_id")
                or ""
            )
            payment_intent_id = _stripe_str(event_obj, "payment_intent")
            stripe_session_id = _stripe_str(event_obj, "id")
            handle_payment_succeeded(
                conn,
                event_id,
                order_id,
                payment_intent_id,
                now,
                stripe_session_id,
                settings.admin_notification_email,
            )
        elif event_type == "checkout.session.expired":
            order_id = (
                _stripe_str(event_obj, "client_reference_id")
                or _stripe_metadata_str(event_obj, "order_id")
                or ""
            )
            stripe_session_id = _stripe_str(event_obj, "id") or ""
            handle_session_expired(conn, event_id, order_id, stripe_session_id, now)
        elif event_type == "payment_intent.payment_failed":
            last_error = _stripe_value(event_obj, "last_payment_error")
            error_code = _stripe_str(last_error, "code") or _stripe_str(last_error, "decline_code")
            handle_payment_failed(
                conn,
                event_id,
                _stripe_metadata_str(event_obj, "order_id"),
                _stripe_str(event_obj, "id"),
                now,
                error_code=error_code,
                event_created=event_created,
                livemode=livemode,
            )
        elif event_type == "charge.refunded":
            handle_charge_refunded(
                conn,
                event_id,
                _stripe_metadata_str(event_obj, "order_id"),
                _stripe_str(event_obj, "id"),
                _stripe_str(event_obj, "payment_intent"),
                now,
                amount_refunded=_stripe_int(event_obj, "amount_refunded"),
                event_created=event_created,
                livemode=livemode,
            )
        elif event_type in {"refund.updated", "charge.refund.updated"}:
            handle_refund_updated(
                conn,
                event_id,
                event_type,
                _stripe_str(event_obj, "id"),
                _stripe_str(event_obj, "payment_intent"),
                now,
                amount_cents=_stripe_int(event_obj, "amount"),
                status=_stripe_str(event_obj, "status"),
                failure_reason=_stripe_str(event_obj, "failure_reason"),
                event_created=event_created,
                livemode=livemode,
            )
        elif event_type in {
            "charge.dispute.created",
            "charge.dispute.updated",
            "charge.dispute.closed",
        }:
            evidence_details = _stripe_value(event_obj, "evidence_details")
            handle_dispute_event(
                conn,
                event_id,
                event_type,
                _stripe_metadata_str(event_obj, "order_id"),
                _stripe_str(event_obj, "payment_intent"),
                _stripe_str(event_obj, "id"),
                _stripe_str(event_obj, "status"),
                now,
                amount_cents=_stripe_int(event_obj, "amount"),
                evidence_due_by=_stripe_int(evidence_details, "due_by"),
                event_created=event_created,
                livemode=livemode,
            )
        else:
            logger.info("stripe_webhook_ignored", event_type=event_type, event_id=event_id)

    return JSONResponse(status_code=200, content={"status": "ok"})
