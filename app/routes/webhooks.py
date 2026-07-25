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
from app.services.payment_service import _now_str, handle_payment_succeeded, handle_session_expired
from app.services.webhook_service import (
    WebhookVerificationError,
    handle_webhook_event,
    verify_signature,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

_MAX_BODY_BYTES = 64 * 1024


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
        return JSONResponse(
            status_code=413,
            content={"error": {"code": "PAYLOAD_TOO_LARGE", "message": "Body too large"}},
        )

    try:
        verify_signature(
            raw_body,
            request.headers.get("producer-signature"),
            settings.zeptomail_webhook_auth_key.get_secret_value(),
        )
    except WebhookVerificationError as exc:
        logger.warning("webhook_signature_rejected", reason=str(exc))
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "INVALID_SIGNATURE", "message": "Signature rejected"}},
        )

    import json

    try:
        payload = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError):
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "INVALID_PAYLOAD", "message": "Malformed JSON"}},
        )

    result = handle_webhook_event(payload if isinstance(payload, dict) else {})
    return JSONResponse(status_code=200, content=result)


@router.post(
    "/stripe",
    summary="Stripe payment webhook",
    description="Consumes checkout.session.completed and checkout.session.expired events. "
    "Authenticated by Stripe-Signature header. Returns 200 for all valid requests "
    "(including unknown event types); 400 only on bad signature.",
)
async def stripe_webhook(request: Request) -> JSONResponse:
    settings = get_settings()

    raw_body = await request.body()
    if len(raw_body) > _MAX_BODY_BYTES:
        return JSONResponse(status_code=200, content={"status": "ignored"})

    sig_header = request.headers.get("stripe-signature", "")
    webhook_secret = settings.stripe_webhook_secret

    try:
        import stripe  # local import — isolates the Stripe dependency

        stripe.api_key = settings.stripe_secret_key
        event = stripe.Webhook.construct_event(raw_body, sig_header, webhook_secret)
    except Exception as exc:
        logger.warning("stripe_webhook_signature_rejected", error=str(exc))
        return JSONResponse(
            status_code=400,
            content={"error": {
                "code": "INVALID_SIGNATURE", "message": "Stripe signature rejected",
            }},
        )

    now = _now_str()
    event_id = event["id"]
    event_type = event["type"]
    session_obj = event.get("data", {}).get("object", {})
    order_id = session_obj.get("client_reference_id") or ""

    with get_db() as conn:
        if event_type == "checkout.session.completed":
            payment_intent_id = session_obj.get("payment_intent")
            handle_payment_succeeded(conn, event_id, order_id, payment_intent_id, now)
        elif event_type == "checkout.session.expired":
            handle_session_expired(conn, event_id, order_id, now)
        else:
            logger.info("stripe_webhook_ignored", event_type=event_type, event_id=event_id)

    return JSONResponse(status_code=200, content={"status": "ok"})

