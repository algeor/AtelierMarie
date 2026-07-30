"""Fetch courier office data from Speedy and Econt APIs, normalize, and write JSON.

One-off script — run manually when the office lists need refreshing (~quarterly
per courier-offices-data spec). Reads credentials from environment variables:

    SPEEDY_USERNAME, SPEEDY_PASSWORD   # https://api.speedy.bg/v1/location/office
    ECONT_USERNAME, ECONT_PASSWORD     # https://ee.econt.com/services/Nomenclatures/...

Writes `data/speedy_offices.json` and `data/econt_offices.json` in the unified
6-field schema (id, name, type, city, address, working_hours) with bilingual
`_en` variants for i18n. Also writes `data/econt_cities.json` — Econt's full
served-places nomenclature (name/postcode/region), the source that lets
ambiguous same-named towns price live (see delivery_service.get_places).

Design:
- `CourierSource` dataclass groups per-courier fetch + normalize logic
- Per-courier try/except — one courier failing doesn't block the other
- Atomic write via `.tmp` + `os.replace` so a partial download never corrupts
  the file the running app reads
- Econt normalization reuses `scripts/normalize_econt_office_data.normalize_econt`

Usage:
    .venv/bin/python scripts/fetch_courier_offices.py
    .venv/bin/python scripts/fetch_courier_offices.py --courier speedy
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from scripts.normalize_econt_office_data import normalize_econt

logger = logging.getLogger("fetch_courier_offices")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

SPEEDY_URL = "https://api.speedy.bg/v1/location/office"
ECONT_URL = "https://ee.econt.com/services/Nomenclatures/NomenclaturesService.getOffices.json"
ECONT_CITIES_URL = "https://ee.econt.com/services/Nomenclatures/NomenclaturesService.getCities.json"

_HTTP_TIMEOUT_S = 30


class CourierFetchSettings(BaseSettings):
    """Credentials for one-off courier office fetches.

    Reads the same `SPEEDY_API_*` / `ECONT_API_*` names the app config uses
    (via validation aliases) so a single `.env` drives both. The bare
    `SPEEDY_USERNAME` / `ECONT_USERNAME` names still work for older setups.
    """

    speedy_username: str = Field(default="", validation_alias="SPEEDY_API_USERNAME")
    speedy_password: str = Field(default="", validation_alias="SPEEDY_API_PASSWORD")
    econt_username: str = Field(default="", validation_alias="ECONT_API_USERNAME")
    econt_password: str = Field(default="", validation_alias="ECONT_API_PASSWORD")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_courier_fetch_settings() -> CourierFetchSettings:
    """Return cached courier fetch settings loaded from environment/.env."""
    return CourierFetchSettings()


def _post_json(url: str, payload: dict) -> dict:
    """POST JSON to `url`, return decoded response. Raises urllib errors."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310 — trusted hosts, HTTPS only
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _fetch_speedy() -> dict:
    """Fetch full Speedy office list. Credentials from env."""
    settings = get_courier_fetch_settings()
    username = settings.speedy_username
    password = settings.speedy_password
    if not username or not password:
        raise RuntimeError(
            "SPEEDY_USERNAME and SPEEDY_PASSWORD env vars are required for Speedy fetch"
        )
    # Speedy accepts credentials in the JSON body; empty `countryId` = all countries,
    # but we constrain to Bulgaria (100) to keep the payload tight.
    payload = {
        "userName": username,
        "password": password,
        "language": "BG",
        "countryId": 100,  # Bulgaria
    }
    return _post_json(SPEEDY_URL, payload)


def _extract_city_en_candidate(name_en: str) -> str:
    """Pull the English city name out of an office's `nameEn`.

    Speedy names its offices `"<CITY> - <BRANCH>"` in English (e.g.
    "SOFIA - SOMAT", "PLOVDIV - WAREHOUSE SOUTH"), or just `"<CITY>"` for a
    town's sole office. The city is the leading segment before the first
    hyphen/comma/paren. Returns an upper-cased, whitespace-collapsed token
    (canonicalized later by majority vote in `_build_speedy_city_en_map`), or
    "" when `name_en` is absent.
    """
    if not name_en:
        return ""
    normalized = name_en.replace("–", "-").replace("—", "-")
    # Leading segment before the first branch delimiter (hyphen/comma/paren).
    head = re.split(r"[-,(]", normalized, maxsplit=1)[0]
    return " ".join(head.split()).strip().upper()


def _build_speedy_city_en_map(offices: list[dict]) -> dict[str, str]:
    """Map each Bulgarian `siteName` → its canonical English city name.

    Speedy's feed carries no English *city* field (only English office `nameEn`),
    so the English city is derived from `nameEn`. Per Bulgarian city we take the
    MOST COMMON extracted candidate: the bare city name dominates because it is
    the shared prefix of every office there, so majority vote discards one-off
    locker suffixes ("(LOCKER)"), typos ("PLODVIV"), and branch noise. Values
    are Title-cased ("Sofia", "Stara Zagora") to match the conventional English
    exonyms Speedy itself uses.
    """
    candidates_by_city: dict[str, Counter[str]] = {}
    for o in offices:
        site_name = (o.get("address") or {}).get("siteName")
        candidate = _extract_city_en_candidate(o.get("nameEn") or "")
        if not site_name or not candidate:
            continue
        candidates_by_city.setdefault(site_name, Counter())[candidate] += 1

    return {
        city: " ".join(word.capitalize() for word in counter.most_common(1)[0][0].split())
        for city, counter in candidates_by_city.items()
    }


def _normalize_speedy(raw: dict) -> list[dict]:
    """Speedy office payload → unified 6-field schema with bilingual extras.

    Verified against the live `POST /v1/location/office` feed (2026-07-31, 1284
    records). Each record carries a numeric `id` — which is what Speedy's
    `calculate.pickupOfficeId` expects — so we store it AS the `id` (stringified)
    rather than the synthetic `speedy-*` slugs the old scaffold used. The Phase A
    office-mode 400 was caused by those slugs; a numeric id fixes it at the source.

    The city lives in the nested `address.siteName`; `type` is the string
    "OFFICE" or "APS" (automated parcel station / locker). Speedy's feed has no
    English *city* field, so `city_en` is derived from the English office name
    via majority vote (see `_build_speedy_city_en_map`); this powers cross-language
    /offices and /cities search. English working-hours has no source, so
    `working_hours_en` stays null and falls back to Bulgarian at read time
    (delivery_service._resolve_locale).
    """
    offices = raw.get("offices", [])
    city_en_map = _build_speedy_city_en_map(offices)
    out: list[dict] = []
    for o in offices:
        office_id = o.get("id")
        address = o.get("address") or {}
        city = address.get("siteName")
        name = o.get("name")
        if office_id is None or not city or not name:
            continue
        # `type`: "APS" = automated parcel locker; anything else is a staffed office.
        office_type = "apt" if o.get("type") == "APS" else "office"
        working_from = o.get("workingTimeFrom")
        working_to = o.get("workingTimeTo")
        working_hours = f"{working_from}-{working_to}" if working_from and working_to else "N/A"
        out.append(
            {
                "id": str(office_id),
                "name": name,
                "name_en": o.get("nameEn"),
                "type": office_type,
                "city": city,
                "city_en": city_en_map.get(city),
                "address": address.get("localAddressString")
                or address.get("fullAddressString", ""),
                "working_hours": working_hours,
                "working_hours_en": None,
            }
        )
    return out


def _fetch_econt() -> dict:
    """Fetch full Econt office list. Credentials optional (public endpoint)."""
    return _post_econt(ECONT_URL, b"{}")


def _fetch_econt_cities() -> dict:
    """Fetch Econt's served-settlements nomenclature. Credentials optional (public).

    Despite the endpoint name, `getCities` is NOT towns-only: it is Econt's
    authoritative list of every settlement it delivers to — villages included
    (verified live 2026-07-30: Труд, Костиево, Стряма, Калековец, Радиново,
    Войводиново all present). It returns ~1510 records with postCode + region,
    of which 1425 support `to_door_courier` and 1407 `to_office_courier`
    (each record's `servingOffices` array carries the serving types). This is
    the source that lets ambiguous same-named settlements (e.g. the three
    "Садово") price live instead of degrading to the flat fallback.

    There is no larger "all places" endpoint: settlements absent here are ones
    Econt genuinely does not serve, not a gap in our data. `getStreets` gives
    street-level detail WITHIN a settlement (finer, not more settlements);
    `getOffices` is narrower still (only 214 office-hosting towns). See
    delivery_service.get_places.
    """
    return _post_econt(ECONT_CITIES_URL, b'{"countryCode":"BGR"}')


def _post_econt(url: str, body: bytes) -> dict:
    """POST raw JSON `body` to an Econt Nomenclatures endpoint with optional auth."""
    # Econt's Nomenclatures endpoints are public but rate-limit anonymous callers.
    # Basic auth is accepted if credentials are set.
    settings = get_courier_fetch_settings()
    username = settings.econt_username
    password = settings.econt_password
    req = urllib.request.Request(  # noqa: S310 — HTTPS to trusted host
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if username and password:
        import base64

        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _normalize_econt_cities(raw: dict) -> list[dict]:
    """Raw {'cities': [...]} → served-place records with postcode + region.

    Drops rows missing a name or postCode (a place with no postcode can't
    disambiguate). `region`/`region_en` may be null (54 of ~1510 lack a region).
    """
    out: list[dict] = []
    for c in raw.get("cities", []):
        name = c.get("name")
        postal_code = c.get("postCode")
        if not name or not postal_code:
            continue
        out.append(
            {
                "name": name,
                "name_en": c.get("nameEn"),
                "postal_code": postal_code,
                "region": c.get("regionName"),
                "region_en": c.get("regionNameEn"),
            }
        )
    return out


def _atomic_write_json(path: Path, records: list[dict]) -> None:
    """Write JSON via .tmp + rename so partial writes never corrupt the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


@dataclass(frozen=True)
class CourierSource:
    """Per-courier fetch + normalize wiring."""

    name: str
    output_path: Path
    fetch: Callable[[], dict]
    normalize: Callable[[dict], list[dict]]


SOURCES: list[CourierSource] = [
    CourierSource(
        name="speedy",
        output_path=DATA_DIR / "speedy_offices.json",
        fetch=_fetch_speedy,
        normalize=_normalize_speedy,
    ),
    CourierSource(
        name="econt",
        output_path=DATA_DIR / "econt_offices.json",
        fetch=_fetch_econt,
        normalize=normalize_econt,
    ),
    CourierSource(
        name="econt-cities",
        output_path=DATA_DIR / "econt_cities.json",
        fetch=_fetch_econt_cities,
        normalize=_normalize_econt_cities,
    ),
]


def refresh_courier(source: CourierSource) -> int:
    """Fetch + normalize + write one source. Returns record count on success."""
    logger.info("fetching %s", source.name)
    raw = source.fetch()
    records = source.normalize(raw)
    if not records:
        raise RuntimeError(f"{source.name} normalized to zero records")
    _atomic_write_json(source.output_path, records)
    logger.info("wrote %d %s records → %s", len(records), source.name, source.output_path)
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh courier office JSON")
    parser.add_argument(
        "--courier",
        choices=[s.name for s in SOURCES],
        help="Only refresh a single courier (default: all)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    sources = [s for s in SOURCES if not args.courier or s.name == args.courier]
    failed: list[str] = []
    for source in sources:
        try:
            refresh_courier(source)
        except (urllib.error.URLError, RuntimeError, KeyError, json.JSONDecodeError) as e:
            # Per spec: one courier failing must not block the other.
            logger.error("%s refresh failed: %s", source.name, e)
            failed.append(source.name)

    if failed:
        logger.error("failed couriers: %s", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
