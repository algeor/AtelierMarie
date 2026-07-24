"""Contact form endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.database import get_db
from app.models.contact import ContactRequest, ContactResponse
from app.services.contact_service import ContactRateLimitExceededError, create_contact_message

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or None
    return request.client.host if request.client else None


@router.post(
    "",
    response_model=ContactResponse,
    status_code=201,
    summary="Submit contact message",
    description="Persist a public contact message and queue the owner email notification.",
)
def submit_contact(request: Request, body: ContactRequest) -> ContactResponse | JSONResponse:
    """Accept a contact form submission."""
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_CONTENT_TYPE",
                    "message": "Content-Type must be application/json",
                }
            },
        )

    try:
        with get_db() as conn:
            message_id = create_contact_message(conn, body, ip_address=_client_ip(request))
    except ContactRateLimitExceededError as exc:
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "RATE_LIMITED", "message": str(exc), "details": None}},
        )

    return ContactResponse(message_id=message_id)
