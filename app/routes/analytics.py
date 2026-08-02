"""Public first-party analytics ingestion endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.database import get_db
from app.dependencies.session import require_session
from app.models.analytics import (
    AnalyticsConsentRequest,
    AnalyticsConsentResponse,
    AnalyticsEventRequest,
    AnalyticsIngestionRequest,
    AnalyticsIngestionResponse,
)
from app.responses import error_response
from app.services import analytics_service

router = APIRouter()


def _parse_payload(payload: dict[str, Any]) -> AnalyticsIngestionRequest:
    """Accept either a direct event body, {event}, or {events}."""
    if "event_type" in payload:
        return AnalyticsIngestionRequest(event=AnalyticsEventRequest.model_validate(payload))
    return AnalyticsIngestionRequest.model_validate(payload)


@router.post(
    "/consent",
    response_model=AnalyticsConsentResponse,
    summary="Record first-party analytics consent",
    description="Persist the current analytics consent choice for the active session.",
)
async def record_analytics_consent(
    body: AnalyticsConsentRequest,
    session_id: Annotated[str, Depends(require_session)],
) -> AnalyticsConsentResponse | JSONResponse:
    """Persist the server-side consent record used by analytics ingestion."""
    try:
        await run_in_threadpool(
            analytics_service.record_consent,
            session_id=session_id,
            analytics=body.analytics,
            consent_version=body.consent_version,
            locale=body.locale,
        )
    except analytics_service.AnalyticsValidationError as exc:
        return error_response(422, "VALIDATION_ERROR", str(exc))
    return AnalyticsConsentResponse(
        analytics=body.analytics,
        consent_version=body.consent_version,
    )


@router.post(
    "/events",
    response_model=AnalyticsIngestionResponse,
    status_code=202,
    summary="Ingest first-party analytics events",
    description="Accept one consented storefront event or a bounded batch for the current session.",
)
async def ingest_analytics_events(
    request: Request,
    session_id: Annotated[str, Depends(require_session)],
) -> AnalyticsIngestionResponse | JSONResponse:
    """Validate and persist consented analytics events."""
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            await run_in_threadpool(analytics_service.mark_validation_failure)
            return error_response(422, "VALIDATION_ERROR", "Analytics payload must be an object")
        body = _parse_payload(payload)
    except (ValueError, ValidationError) as exc:
        await run_in_threadpool(analytics_service.mark_validation_failure)
        return error_response(422, "VALIDATION_ERROR", str(exc))

    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,)).fetchone()
        user_id = row["user_id"] if row else None

    try:
        consent_verified = await run_in_threadpool(
            analytics_service.has_current_analytics_consent,
            session_id,
        )
        result = await run_in_threadpool(
            analytics_service.ingest_events,
            body.event_list(),
            session_id=session_id,
            user_id=user_id,
            consent_verified=consent_verified,
        )
    except analytics_service.AnalyticsValidationError as exc:
        return error_response(422, "VALIDATION_ERROR", str(exc))

    return AnalyticsIngestionResponse(**result)
