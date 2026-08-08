"""Public legal identity API models."""

from pydantic import BaseModel


class LegalIdentityResponse(BaseModel):
    """Legal identity values shown on public policy and product pages."""

    trading_name: str
    legal_name: str | None = None
    country: str
    geographic_address: str | None = None
    contact_email: str
    registration_number: str | None = None
    vat_number: str | None = None
    responsible_party_name: str
    responsible_party_address: str | None = None
    responsible_party_email: str
