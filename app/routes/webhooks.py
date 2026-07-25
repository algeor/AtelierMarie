"""Public webhook endpoints (signature-authenticated, not admin).

`POST /v1/webhooks/zeptomail` consumes ZeptoMail bounce/complaint events. The
path is registered in `session_skip_paths` so the session middleware issues no
cookie on this machine-to-machine call.
"""

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.services.webhook_service import (
    WebhookVerificationError,
    handle_webhook_event,
    verify_signature,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

# Reject absurdly large bodies before reading/verifying (defense-in-depth).
_MAX_BODY_BYTES = 64 * 1024


@router.post(
    "/zeptomail",
    summary="ZeptoMail bounce/complaint webhook",
    description="Consumes hard_bounce / soft_bounce / fbl_complaint events. "
    "Authenticated by the ZeptoMail producer-signature HMAC over the raw body.",
)
async def zeptomail_webhook(request: Request) -> JSONResponse:
    settings = get_settings()

    # Raw bytes BEFORE JSON parsing — the HMAC is over the raw body.
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
