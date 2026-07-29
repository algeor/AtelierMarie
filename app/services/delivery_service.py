"""Delivery service — courier office data lookup.

Loads static JSON office data at module import (fast, in-memory filtering
sufficient at ~600–5000 offices per courier). Missing data files log a
warning and yield empty results — per courier-offices-data spec, a missing
file must never cause a startup failure.

Records on disk carry bilingual fields (`name`/`name_en`, `city`/`city_en`,
`working_hours`/`working_hours_en`). The service resolves these to the
6-field API shape (`id`, `name`, `type`, `city`, `address`, `working_hours`)
using the caller-supplied locale, matching the pattern in
`product_service._resolve_locale_fields`. English falls back to Bulgarian
when a translation is missing.

Address is currently Cyrillic-only in the source data (Econt has no English
address field); it flows through unchanged in both locales.

Adding a new courier is a data-only change:
1. Drop `data/<name>_offices.json` in the unified shape
2. Add the name to `COURIER_FILES` and to `Courier` in `app/models/delivery.py`
"""

import json
from pathlib import Path
from typing import Literal, TypedDict

import structlog

from app.models.delivery import Courier

logger = structlog.get_logger(__name__)

Locale = Literal["en", "bg"]

# Repo-rooted; resolves via app/services/delivery_service.py → app/ → repo root
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

COURIER_FILES: dict[Courier, Path] = {
    "econt": _DATA_DIR / "econt_offices.json",
    "speedy": _DATA_DIR / "speedy_offices.json",
}


class Office(TypedDict):
    """API-shape office record — matches courier-offices-data spec exactly."""

    id: str
    name: str
    type: str  # "office" | "apt"
    city: str
    address: str
    working_hours: str


# Raw records as stored in JSON — bilingual, superset of Office.
_offices_by_courier: dict[Courier, list[dict]] = {}


def _load_courier_data(courier: Courier, path: Path) -> list[dict]:
    """Load one courier's JSON file. Missing file → empty list + warning."""
    if not path.exists():
        logger.warning(
            "courier_office_data_missing",
            courier=courier,
            path=str(path),
        )
        return []
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(
            "courier_office_data_load_failed",
            courier=courier,
            path=str(path),
            error=str(e),
        )
        return []

    if not isinstance(data, list):
        logger.error(
            "courier_office_data_invalid_shape",
            courier=courier,
            path=str(path),
            got=type(data).__name__,
        )
        return []

    logger.info("courier_office_data_loaded", courier=courier, count=len(data))
    return data


def _load_all() -> None:
    """Populate the in-memory cache from all configured courier files."""
    for courier, path in COURIER_FILES.items():
        _offices_by_courier[courier] = _load_courier_data(courier, path)


def _resolve_locale(raw: dict, locale: Locale) -> Office:
    """Project a raw bilingual record onto the API-shape Office for the given locale.

    English falls back to Bulgarian when the `_en` variant is missing — mirrors
    `product_service._resolve_locale_fields`. Bulgarian is always populated
    (the source is Econt's Bulgarian API), so BG never needs fallback.
    """
    if locale == "en":
        return Office(
            id=raw["id"],
            name=raw.get("name_en") or raw["name"],
            type=raw["type"],
            city=raw.get("city_en") or raw["city"],
            address=raw["address"],
            working_hours=raw.get("working_hours_en") or raw["working_hours"],
        )
    return Office(
        id=raw["id"],
        name=raw["name"],
        type=raw["type"],
        city=raw["city"],
        address=raw["address"],
        working_hours=raw["working_hours"],
    )


def get_offices(
    courier: Courier,
    city: str,
    *,
    office_type: str | None = None,
    locale: Locale = "bg",
) -> list[Office]:
    """Return offices for `courier` in `city`, filtered by `office_type`.

    City match is case-insensitive against both the Bulgarian city name and
    its English transliteration — so `city="Sofia"` and `city="София"` both
    return Sofia offices regardless of the caller's locale.
    """
    offices = _offices_by_courier.get(courier, [])
    if not offices:
        return []

    city_folded = city.casefold()
    matched = [
        o
        for o in offices
        if o["city"].casefold() == city_folded or (o.get("city_en") or "").casefold() == city_folded
    ]

    if office_type is not None:
        matched = [o for o in matched if o["type"] == office_type]

    return [_resolve_locale(o, locale) for o in matched]


def get_office(
    courier: Courier,
    office_id: str,
    *,
    locale: Locale = "bg",
) -> Office | None:
    """Return one courier office by id, or None when it is not in the catalogue."""
    for office in _offices_by_courier.get(courier, []):
        if office.get("id") == office_id:
            return _resolve_locale(office, locale)
    return None


def get_cities(
    courier: Courier,
    *,
    query: str | None = None,
    locale: Locale = "bg",
) -> list[str]:
    """Return distinct city names for `courier`, optionally filtered by prefix.

    Prefix match is case-insensitive against both language variants — a Latin
    query like "So" matches "София" (via `city_en=Sofia`) and returns the
    caller-locale name. Result is sorted alphabetically.
    """
    offices = _offices_by_courier.get(courier, [])
    if not offices:
        return []

    seen: set[str] = set()
    result: list[str] = []
    prefix = query.casefold() if query else None

    for o in offices:
        city_bg = o["city"]
        city_en = o.get("city_en") or city_bg
        display = city_en if locale == "en" else city_bg
        if display in seen:
            continue
        if prefix is not None and not (
            city_bg.casefold().startswith(prefix) or city_en.casefold().startswith(prefix)
        ):
            continue
        seen.add(display)
        result.append(display)

    result.sort()
    return result


def reload_data() -> None:
    """Reload office data from disk. For post-fetch-script refresh or tests."""
    _offices_by_courier.clear()
    _load_all()


# Load on import — spec requires data available "at application startup".
# Empty caches on failure (see _load_courier_data) keep the app bootable.
_load_all()
