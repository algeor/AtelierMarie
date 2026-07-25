"""Fetch courier office data from Speedy and Econt APIs, normalize, and write JSON.

One-off script — run manually when the office lists need refreshing (~quarterly
per courier-offices-data spec). Reads credentials from environment variables:

    SPEEDY_USERNAME, SPEEDY_PASSWORD   # https://api.speedy.bg/v1/location/office
    ECONT_USERNAME, ECONT_PASSWORD     # https://ee.econt.com/services/Nomenclatures/...

Writes `data/speedy_offices.json` and `data/econt_offices.json` in the unified
6-field schema (id, name, type, city, address, working_hours) with bilingual
`_en` variants for i18n.

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
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

from scripts.normalize_econt_office_data import normalize_econt

logger = logging.getLogger("fetch_courier_offices")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

SPEEDY_URL = "https://api.speedy.bg/v1/location/office"
ECONT_URL = "https://ee.econt.com/services/Nomenclatures/NomenclaturesService.getOffices.json"

_HTTP_TIMEOUT_S = 30


class CourierFetchSettings(BaseSettings):
    """Credentials for one-off courier office fetches."""

    speedy_username: str = ""
    speedy_password: str = ""
    econt_username: str = ""
    econt_password: str = ""

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


def _normalize_speedy(raw: dict) -> list[dict]:
    """Speedy office payload → unified 6-field schema with bilingual extras.

    NOTE: This is a scaffold. Speedy's exact response schema needs verification
    once credentials are available (see design.md Open Questions). Fields below
    are the documented shape from their public docs; adjust when real data arrives.
    """
    out: list[dict] = []
    for o in raw.get("offices", []):
        site = o.get("site") or {}
        city = site.get("name") or site.get("nameBg")
        name = o.get("name") or o.get("nameBg")
        if not city or not name:
            continue
        # Speedy exposes `type`: 1 = office, 2 = APS (locker). Fall back to office.
        office_type = "apt" if o.get("type") == 2 else "office"
        out.append(
            {
                "id": f"speedy-{o.get('id')}",
                "name": name,
                "name_en": o.get("nameEn"),
                "type": office_type,
                "city": city,
                "city_en": site.get("nameEn"),
                "address": (o.get("address") or {}).get("localAddressString")
                or o.get("addressString", ""),
                "working_hours": o.get("workingTime", "N/A"),
                "working_hours_en": o.get("workingTimeEn"),
            }
        )
    return out


def _fetch_econt() -> dict:
    """Fetch full Econt office list. Credentials optional (public endpoint)."""
    # Econt's Nomenclatures endpoint is public but rate-limits anonymous callers.
    # Basic auth is accepted if credentials are set.
    settings = get_courier_fetch_settings()
    username = settings.econt_username
    password = settings.econt_password
    req = urllib.request.Request(  # noqa: S310 — HTTPS to trusted host
        ECONT_URL,
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if username and password:
        import base64

        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


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
]


def refresh_courier(source: CourierSource) -> int:
    """Fetch + normalize + write one courier. Returns record count on success."""
    logger.info("fetching %s offices", source.name)
    raw = source.fetch()
    records = source.normalize(raw)
    if not records:
        raise RuntimeError(f"{source.name} normalized to zero records")
    _atomic_write_json(source.output_path, records)
    logger.info("wrote %d %s offices → %s", len(records), source.name, source.output_path)
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
