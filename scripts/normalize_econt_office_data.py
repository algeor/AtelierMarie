"""Normalize raw Econt office API dump into the unified delivery schema.

Reads data/econt_offices_raw.json (raw {"offices": [...]} from Econt's
NomenclaturesService.getOffices) and writes data/econt_offices.json in the
6-field schema from design.md Decision 8, with bilingual name/city fields
kept as additive extras for i18n.

Run standalone:
    .venv/bin/python scripts/normalize_econt_office_data.py

Called from scripts/fetch_courier_offices.py (M2 task 2.2) once implemented.
"""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BG_TZ = ZoneInfo("Europe/Sofia")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def _hm(ms: int | None) -> str | None:
    """Extract H:M in Sofia time from an Econt Unix-ms timestamp."""
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, BG_TZ).strftime("%H:%M")


def _day_range(from_ms: int | None, to_ms: int | None) -> str | None:
    """Format 'HH:MM-HH:MM' for a day; None if either bound missing or from==to (closed)."""
    if not from_ms or not to_ms or from_ms == to_ms:
        return None
    return f"{_hm(from_ms)}-{_hm(to_ms)}"


def _working_hours(o: dict) -> str:
    if o.get("isAPS") or o.get("isMPS"):
        return "24/7"
    weekday = _day_range(o.get("normalBusinessHoursFrom"), o.get("normalBusinessHoursTo"))
    saturday = _day_range(o.get("halfDayBusinessHoursFrom"), o.get("halfDayBusinessHoursTo"))
    if not weekday:
        return "N/A"
    if not saturday:
        return f"Пон-Пет {weekday}"
    return f"Пон-Пет {weekday}, Съб {saturday}"


def _working_hours_en(o: dict) -> str:
    if o.get("isAPS") or o.get("isMPS"):
        return "24/7"
    weekday = _day_range(o.get("normalBusinessHoursFrom"), o.get("normalBusinessHoursTo"))
    saturday = _day_range(o.get("halfDayBusinessHoursFrom"), o.get("halfDayBusinessHoursTo"))
    if not weekday:
        return "N/A"
    if not saturday:
        return f"Mon-Fri {weekday}"
    return f"Mon-Fri {weekday}, Sat {saturday}"


def _address(addr: dict) -> str:
    """Compose a clean address from Econt subfields.

    Econt's `fullAddress` has a leading space and duplicates the city name.
    Compose from quarter/street/num/other instead — matches HANDOFF gotcha #1.
    """
    parts: list[str] = []
    if q := (addr.get("quarter") or "").strip():
        parts.append(q)
    if s := (addr.get("street") or "").strip():
        parts.append(s)
    if n := (addr.get("num") or "").strip():
        parts.append(f"№{n}")
    if other := (addr.get("other") or "").strip():
        parts.append(other)
    return " ".join(parts)


def normalize_econt(raw: dict) -> list[dict]:
    """Raw {'offices': [...]} → list of unified-schema offices."""
    out = []
    for o in raw.get("offices", []):
        addr = o.get("address") or {}
        city_obj = addr.get("city") or {}
        city = city_obj.get("name")
        if not city or not o.get("name"):
            continue  # skip malformed
        out.append(
            {
                "id": f"econt-{o['id']}",
                "code": str(o.get("code")) if o.get("code") is not None else None,
                "name": o["name"],
                "name_en": o.get("nameEn"),
                "type": "apt" if (o.get("isAPS") or o.get("isMPS")) else "office",
                "city": city,
                "city_en": city_obj.get("nameEn"),
                "address": _address(addr),
                "working_hours": _working_hours(o),
                "working_hours_en": _working_hours_en(o),
            }
        )
    return out


if __name__ == "__main__":
    with open(
        DATA_DIR / "econt_offices_raw.json",
        encoding="utf-8",
    ) as f:
        raw = json.load(f)
    normalized = normalize_econt(raw)
    with open(
        DATA_DIR / "econt_offices.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(normalized)} offices")
