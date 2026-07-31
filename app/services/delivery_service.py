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
import re
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

# Served-place nomenclature (name + postcode + region) for door delivery.
# Offices are office-hosting towns only; places are the settlement/postcode rows
# needed to build to-door courier payloads. Speedy has its own `/location/site`
# source, but older worktrees may not have refreshed it yet, so Speedy falls
# back to Econt's settlement file plus the manual supplement below.
ECONT_PLACES_FILE = _DATA_DIR / "econt_cities.json"
SPEEDY_PLACES_FILE = _DATA_DIR / "speedy_sites.json"
SERVED_PLACES_SUPPLEMENT_FILE = _DATA_DIR / "served_places_supplement.json"

PLACES_FILES: dict[Courier, tuple[Path, ...]] = {
    "econt": (ECONT_PLACES_FILE,),
    "speedy": (SPEEDY_PLACES_FILE,),
}

PLACES_FALLBACK_FILES: dict[Courier, tuple[Path, ...]] = {
    "speedy": (ECONT_PLACES_FILE,),
}


class Office(TypedDict):
    """API-shape office record — matches courier-offices-data spec exactly."""

    id: str
    name: str
    type: str  # "office" | "apt"
    city: str
    address: str
    working_hours: str


class CityPlace(TypedDict):
    """API-shape served-place record — a name + region + postcode triple.

    Region distinguishes same-named towns (e.g. the three "Садово"); postcode
    is the disambiguator Econt's pricing API needs (see `get_places`).
    """

    name: str
    region: str | None
    postal_code: str | None


# Raw records as stored in JSON — bilingual, superset of Office.
_offices_by_courier: dict[Courier, list[dict]] = {}

# Raw served-place records (bilingual name + region, postcode) keyed by courier.
_places_by_courier: dict[Courier, list[dict]] = {}

# Per-courier map from any city spelling (English transliteration OR Bulgarian,
# both casefolded) to the Bulgarian city name. Econt's pricing API only accepts
# Cyrillic city names, so a checkout coming in with locale=en sends a Latin city
# (e.g. "Sadovo") that must be resolved back to "Садово" before pricing. Built
# from the same office data the /offices and /cities endpoints already expose.
_city_bg_by_courier: dict[Courier, dict[str, str]] = {}

# Cross-courier Bulgarian city spelling -> English display/alias. Speedy's live
# office feed does not include English city names, but the frontend/API contract
# still supports Latin city lookup (e.g. "Sofia"). Seed this from courier data
# that does have translations, then use it as an in-memory fallback.
_city_en_by_bg: dict[str, str] = {}


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


def _load_optional_courier_data(courier: Courier, path: Path) -> list[dict]:
    """Load optional data if present; missing optional files are expected."""
    if not path.exists():
        logger.info("courier_optional_data_missing", courier=courier, path=str(path))
        return []
    return _load_courier_data(courier, path)


def _load_supplemental_places(courier: Courier) -> list[dict]:
    """Load manually verified served places not present in courier feeds."""
    records = _load_optional_courier_data(courier, SERVED_PLACES_SUPPLEMENT_FILE)
    out: list[dict] = []
    for record in records:
        if not record.get("name") or not record.get("postal_code"):
            continue
        couriers = record.get("couriers")
        if isinstance(couriers, list) and courier not in couriers:
            continue
        out.append(record)
    return out


def _load_place_data(courier: Courier) -> list[dict]:
    """Load served places for a courier, with fallback and supplement records."""
    records: list[dict] = []
    for path in PLACES_FILES.get(courier, ()):  # primary courier-specific places
        if path == SPEEDY_PLACES_FILE:
            records.extend(_load_optional_courier_data(courier, path))
        else:
            records.extend(_load_courier_data(courier, path))

    if not records:
        for path in PLACES_FALLBACK_FILES.get(courier, ()):  # compatibility path
            records.extend(_load_courier_data(courier, path))

    records.extend(_load_supplemental_places(courier))
    records.extend(_office_city_place_backfills(courier, records))
    return records


def _office_city_place_backfills(courier: Courier, known_places: list[dict]) -> list[dict]:
    """Backfill office-hosting towns missing from served-place feeds.

    This is mainly a compatibility bridge while Speedy's `/location/site` file is
    absent: if Speedy has an office/locker in a town, the town should at least be
    selectable for door delivery. Rows without a known postcode remain editable
    in the frontend; manually verified postcodes live in the supplement file.
    """
    known_names = {
        folded
        for place in known_places
        for folded in (_fold_search(place.get("name")), _fold_search(place.get("name_en")))
        if folded
    }
    out: list[dict] = []
    for office in _offices_by_courier.get(courier, []):
        city = office.get("city")
        if not city:
            continue
        display_city = _humanize_place_name(city)
        city_en = office.get("city_en")
        if _fold_search(display_city) in known_names or _fold_search(city_en) in known_names:
            continue
        known_names.add(_fold_search(display_city))
        if city_en:
            known_names.add(_fold_search(city_en))
        out.append(
            {
                "name": display_city,
                "name_en": city_en,
                "postal_code": office.get("postal_code"),
                "region": office.get("region"),
                "region_en": office.get("region_en"),
                "source": "office-city-backfill",
            }
        )
    return out


def _humanize_place_name(value: str) -> str:
    """Normalize all-uppercase courier city labels for customer display."""
    return value.title() if value.isupper() else value


def _add_city_bg_entries(
    mapping: dict[str, str], records: list[dict], *, bg_key: str, en_key: str
) -> None:
    """Merge casefolded (BG and EN) name spellings → Bulgarian name into `mapping`.

    Works for both offices (`city`/`city_en`) and served places (`name`/`name_en`).
    """
    for r in records:
        name_bg = r.get(bg_key)
        if not name_bg:
            continue
        mapping[name_bg.casefold()] = name_bg
        name_en = r.get(en_key) or _city_en_by_bg.get(name_bg.casefold())
        if name_en:
            mapping[name_en.casefold()] = name_bg


def _add_city_en_entries(records: list[dict], *, bg_key: str, en_key: str) -> None:
    """Seed fallback English city aliases from records that carry translations."""
    for r in records:
        name_bg = r.get(bg_key)
        name_en = r.get(en_key)
        if name_bg and name_en:
            _city_en_by_bg.setdefault(name_bg.casefold(), name_en)


def _city_en(raw: dict) -> str:
    """Return English city display/alias, falling back to cross-courier data."""
    city_bg = raw["city"]
    return raw.get("city_en") or _city_en_by_bg.get(city_bg.casefold()) or city_bg


def _load_all() -> None:
    """Populate the in-memory caches from all configured courier files.

    The city→Bulgarian map is fed by BOTH offices and served places: places
    cover every delivery town (offices only office-hosting ones), so merging
    them widens the Latin→Cyrillic resolution `resolve_city_bg` relies on.
    """
    for courier, path in COURIER_FILES.items():
        offices = _load_courier_data(courier, path)
        _offices_by_courier[courier] = offices

    for courier in COURIER_FILES:
        _places_by_courier[courier] = _load_place_data(courier)

    _city_en_by_bg.clear()
    for records in _offices_by_courier.values():
        _add_city_en_entries(records, bg_key="city", en_key="city_en")
    for records in _places_by_courier.values():
        _add_city_en_entries(records, bg_key="name", en_key="name_en")

    for courier in COURIER_FILES:
        mapping: dict[str, str] = {}
        _add_city_bg_entries(
            mapping, _offices_by_courier.get(courier, []), bg_key="city", en_key="city_en"
        )
        _add_city_bg_entries(
            mapping, _places_by_courier.get(courier, []), bg_key="name", en_key="name_en"
        )
        _city_bg_by_courier[courier] = mapping


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
            city=_city_en(raw),
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
        if o["city"].casefold() == city_folded or _city_en(o).casefold() == city_folded
    ]

    if office_type is not None:
        matched = [o for o in matched if o["type"] == office_type]

    return [_resolve_locale(o, locale) for o in matched]


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
        city_en = _city_en(o)
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


def get_places(
    courier: Courier,
    *,
    query: str | None = None,
    locale: Locale = "bg",
) -> list[CityPlace]:
    """Return served places (name + region + postcode) for `courier`.

    A place is a specific delivery destination: same-named towns appear as
    distinct rows distinguished by region + postcode (e.g. three "Садово").
    Search is case-insensitive across Bulgarian/English name, region, and
    postcode. Exact name/postcode hits are ranked first, followed by name
    prefixes and broader token/contains matches. Dedupe includes postcode so
    genuinely distinct same-name/same-region places survive. Sorted by match
    quality, then name/region/postcode for stable ordering. Couriers without a
    places file return [].
    """
    places = _places_by_courier.get(courier, [])
    if not places:
        return []

    seen: set[tuple[str, str | None, str | None]] = set()
    result: list[tuple[int, CityPlace]] = []
    folded_query = _fold_search(query)
    query_tokens = _search_tokens(folded_query)

    for p in places:
        name_bg = p["name"]
        name_en = p.get("name_en") or name_bg
        display = name_en if locale == "en" else name_bg
        region = (p.get("region_en") if locale == "en" else p.get("region")) or None
        postal_code = p.get("postal_code")
        key = (display, region, postal_code)
        if key in seen:
            continue

        match_score = _place_match_score(p, folded_query, query_tokens)
        if match_score is None:
            continue
        seen.add(key)
        result.append(
            (
                match_score,
                CityPlace(name=display, region=region, postal_code=postal_code),
            )
        )

    result.sort(
        key=lambda item: (
            item[0],
            item[1]["name"],
            item[1]["region"] or "",
            item[1]["postal_code"] or "",
        )
    )
    return [place for _, place in result]


def _fold_search(value: str | None) -> str:
    """Casefold + whitespace-collapse one search string."""
    return " ".join((value or "").casefold().split())


def _search_tokens(value: str) -> list[str]:
    """Split a folded query into useful name/region/postcode tokens."""
    if not value:
        return []
    return [token for token in re.split(r"[^\w]+", value) if token]


def _place_search_fields(place: dict) -> tuple[str, str, list[str]]:
    """Return folded name fields and all searchable place fields."""
    name_bg = _fold_search(place.get("name"))
    name_en = _fold_search(place.get("name_en"))
    fields = [
        name_bg,
        name_en,
        _fold_search(place.get("region")),
        _fold_search(place.get("region_en")),
        _fold_search(place.get("postal_code")),
    ]
    return name_bg, name_en, [field for field in fields if field]


def _place_match_score(
    place: dict,
    folded_query: str,
    query_tokens: list[str],
) -> int | None:
    """Rank a place for the current query, or None when it does not match."""
    if not folded_query:
        return 0

    name_bg, name_en, fields = _place_search_fields(place)
    postal_code = _fold_search(place.get("postal_code"))
    name_fields = [name for name in (name_bg, name_en) if name]

    if folded_query in (*name_fields, postal_code):
        return 0
    if any(name.startswith(folded_query) for name in name_fields):
        return 1
    if len(query_tokens) == 1 and any(
        token and any(part.startswith(token) for part in re.split(r"\s+", name))
        for token in query_tokens
        for name in name_fields
    ):
        return 2
    if any(folded_query in field for field in fields):
        return 3
    if query_tokens and all(any(token in field for field in fields) for token in query_tokens):
        return 4
    return None


def resolve_city_bg(courier: Courier, city: str) -> str:
    """Return the Bulgarian spelling of `city` for `courier`'s pricing API.

    Econt's calculate endpoint only accepts Cyrillic city names; a checkout
    made with locale=en sends a Latin transliteration (e.g. "Sadovo"). Maps
    either spelling to the Bulgarian name using the courier's office data.
    Unknown cities pass through unchanged — the caller's live-pricing attempt
    then either succeeds (city already Cyrillic / recognized by the courier) or
    degrades to the flat fallback, which is the correct behavior for a city we
    have no office data for.
    """
    return _city_bg_by_courier.get(courier, {}).get(city.casefold(), city)


def reload_data() -> None:
    """Reload office + places data from disk. For post-fetch-script refresh or tests."""
    _offices_by_courier.clear()
    _places_by_courier.clear()
    _city_bg_by_courier.clear()
    _city_en_by_bg.clear()
    _load_all()


# Load on import — spec requires data available "at application startup".
# Empty caches on failure (see _load_courier_data) keep the app bootable.
_load_all()
