"""Public legal identity values used across storefront and customer messages."""

from __future__ import annotations

from typing import Any, Literal

Locale = Literal["en", "bg"]
PolicyKey = Literal["terms", "privacy", "cookies", "contact"]

LEGAL_IDENTITY: dict[str, str | None] = {
    "trading_name": "Atelier Marie",
    "legal_name": None,
    "country": "Bulgaria",
    "geographic_address": None,
    "contact_email": "contacts@theateliermarie.com",
    "registration_number": None,
    "vat_number": None,
}


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _address_value(address: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        value = _string_or_none(address.get(key))
        if value:
            return value
    return None


def format_registered_address(address: dict[str, object] | None) -> str | None:
    """Format the admin-managed address object for public legal copy."""
    if not address:
        return None

    formatted = _address_value(address, "formatted", "formatted_address")
    if formatted:
        return formatted

    line_1 = _address_value(address, "line1", "line_1", "address_line1", "address_line_1", "street")
    line_2 = _address_value(address, "line2", "line_2", "address_line2", "address_line_2")
    city = _address_value(address, "city", "locality")
    postal_code = _address_value(address, "postal_code", "postcode", "zip")
    country = _address_value(address, "country", "country_code")

    city_line = " ".join(part for part in [postal_code, city] if part)
    parts = [part for part in [line_1, line_2, city_line, country] if part]
    return ", ".join(parts) or None


def _profile_value(profile: Any, key: str) -> object:
    if profile is None:
        return None
    if isinstance(profile, dict):
        return profile.get(key)
    return getattr(profile, key, None)


def legal_identity_from_seller_profile(profile: Any) -> dict[str, str | None]:
    """Return public legal identity values from the latest seller profile."""
    registered_address = _profile_value(profile, "registered_address")
    address = format_registered_address(
        registered_address if isinstance(registered_address, dict) else None
    )
    country = None
    if isinstance(registered_address, dict):
        country = _address_value(registered_address, "country", "country_code")

    identity = {
        "trading_name": _string_or_none(_profile_value(profile, "company_display_name"))
        or LEGAL_IDENTITY["trading_name"],
        "legal_name": _string_or_none(_profile_value(profile, "legal_name")),
        "country": country or LEGAL_IDENTITY["country"],
        "geographic_address": address,
        "contact_email": _string_or_none(_profile_value(profile, "contact_email"))
        or LEGAL_IDENTITY["contact_email"],
        "registration_number": _string_or_none(_profile_value(profile, "uic_eik")),
        "vat_number": _string_or_none(_profile_value(profile, "vat_identification_number")),
    }
    identity["responsible_party_name"] = identity["trading_name"]
    identity["responsible_party_address"] = identity["geographic_address"]
    identity["responsible_party_email"] = identity["contact_email"]
    return identity


def get_public_legal_identity() -> dict[str, str | None]:
    """Load the latest admin-managed public legal identity with static fallback."""
    from app.services import accounting_config_service

    return legal_identity_from_seller_profile(
        accounting_config_service.get_current_seller_legal_profile()
    )


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
