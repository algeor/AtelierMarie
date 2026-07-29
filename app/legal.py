"""Public legal identity values used in backend-rendered customer messages."""

from __future__ import annotations

from typing import Literal

Locale = Literal["en", "bg"]
PolicyKey = Literal["terms", "privacy", "cookies", "contact"]

LEGAL_IDENTITY = {
    "trading_name": "Atelier Marie",
    "legal_name": "TODO: legal entity name",
    "country": "Bulgaria",
    "geographic_address": "TODO: geographic business address",
    "contact_email": "contacts@theateliermarie.com",
    "registration_number": "TODO: registration number",
    "vat_number": "TODO: VAT number or not VAT registered",
}

_POLICY_PATHS: dict[PolicyKey, str] = {
    "terms": "/terms",
    "privacy": "/privacy",
    "cookies": "/cookies",
    "contact": "/contact",
}


def localized_policy_url(frontend_url: str, locale: str, policy: PolicyKey) -> str:
    """Return an absolute localized storefront URL for a public policy page."""
    safe_locale = locale if locale in {"en", "bg"} else "en"
    return f"{frontend_url.rstrip('/')}/{safe_locale}{_POLICY_PATHS[policy]}"
