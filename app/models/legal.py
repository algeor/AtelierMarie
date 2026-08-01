"""Public legal identity API models."""

from pydantic import BaseModel


class LegalIdentityResponse(BaseModel):
    """Legal identity values shown on public policy and product pages."""

    trading_name: str
    legal_name: str
    country: str
    geographic_address: str
    contact_email: str
    registration_number: str
    vat_number: str
    responsible_party_name: str
    responsible_party_address: str
    responsible_party_email: str
