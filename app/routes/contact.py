"""Contact form endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.database import get_db
from app.models.contact import ContactRequest, ContactResponse
from app.services.contact_service import ContactRateLimitExceededError, create_contact_message

router = APIRouter()


def _client_ip(request: Request) -> str | None:
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
    try:
        with get_db() as conn:
            message_id = create_contact_message(conn, body, ip_address=_client_ip(request))
    except ContactRateLimitExceededError as exc:
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "RATE_LIMITED", "message": str(exc), "details": None}},
        )

    return ContactResponse(message_id=message_id)
