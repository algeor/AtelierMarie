"""Tests for courier data refresh normalizers."""

import json
import sys

from scripts import fetch_courier_offices
from scripts.fetch_courier_offices import (
    CourierSource,
    SOURCES,
    _normalize_speedy_sites,
    _parse_speedy_sites_export,
    refresh_courier,
)
from scripts.normalize_econt_office_data import normalize_econt


def test_normalize_econt_preserves_native_office_code():
    raw = {
        "offices": [
            {
                "id": 1029,
                "code": "1127",
                "name": "София",
                "nameEn": "Sofia",
                "address": {
                    "city": {"name": "София", "nameEn": "Sofia"},
                    "street": "Резбарска",
                    "num": "11",
                },
                "normalBusinessHoursFrom": 1761980400000,
                "normalBusinessHoursTo": 1762012800000,
            }
        ]
    }

    offices = normalize_econt(raw)

    assert offices[0]["id"] == "econt-1029"
    assert offices[0]["code"] == "1127"


def test_normalize_speedy_sites_to_served_places():
    raw = {
        "sites": [
            {
                "name": "Згориград",
                "nameEn": "Zgorigrad",
                "postCode": "3042",
                "region": "Враца",
                "regionEn": "Vratsa",
            },
            {"name": "Без пощенски код"},
        ]
    }

    assert _normalize_speedy_sites(raw) == [
        {
            "name": "Згориград",
            "name_en": "Zgorigrad",
            "postal_code": "3042",
            "region": "Враца",
            "region_en": "Vratsa",
        }
    ]


def test_normalize_speedy_sites_accepts_full_raw_list():
    raw = [
        {
            "name": "ЗГОРИГРАД",
            "nameEn": "ZGORIGRAD",
            "postCode": "3042",
            "region": "ВРАЦА",
            "regionEn": "VRATSA",
        }
    ]

    assert _normalize_speedy_sites(raw) == [
        {
            "name": "Згориград",
            "name_en": "Zgorigrad",
            "postal_code": "3042",
            "region": "Враца",
            "region_en": "Vratsa",
        }
    ]


def test_parse_speedy_sites_export_accepts_csv():
    raw = "name;nameEn;postCode;region;regionEn\nРОМАН;ROMAN;3130;ВРАЦА;VRATSA\n"

    assert _parse_speedy_sites_export(raw) == {
        "sites": [
            {
                "name": "РОМАН",
                "nameEn": "ROMAN",
                "postCode": "3130",
                "region": "ВРАЦА",
                "regionEn": "VRATSA",
            }
        ]
    }


def test_refresh_sources_include_speedy_sites():
    source = next(s for s in SOURCES if s.name == "speedy-sites")

    assert source.output_path.name == "speedy_sites.json"


def test_refresh_courier_writes_speedy_status(tmp_path, monkeypatch):
    status_path = tmp_path / "courier_refresh_status.json"
    monkeypatch.setattr(fetch_courier_offices, "REFRESH_STATUS_PATH", status_path)
    source = CourierSource(
        name="speedy",
        output_path=tmp_path / "speedy_offices.json",
        fetch=lambda: {"offices": []},
        normalize=lambda _raw: [
            {
                "id": "1",
                "name": "Speedy Sofia",
                "type": "office",
                "city": "Sofia",
                "address": "Center",
                "working_hours": "09:00-18:00",
            }
        ],
    )

    assert refresh_courier(source) == 1

    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["speedy"]["status"] == "success"
    assert status["speedy"]["records"] == 1
    assert status["speedy"]["error"] is None


def test_main_isolates_speedy_refresh_failure(tmp_path, monkeypatch):
    status_path = tmp_path / "courier_refresh_status.json"
    monkeypatch.setattr(fetch_courier_offices, "REFRESH_STATUS_PATH", status_path)

    success = CourierSource(
        name="econt",
        output_path=tmp_path / "econt_offices.json",
        fetch=lambda: {"offices": []},
        normalize=lambda _raw: [
            {
                "id": "e1",
                "name": "Econt Sofia",
                "type": "office",
                "city": "Sofia",
                "address": "Center",
                "working_hours": "09:00-18:00",
            }
        ],
    )

    def fail_fetch():
        raise RuntimeError("Speedy unavailable")

    failure = CourierSource(
        name="speedy",
        output_path=tmp_path / "speedy_offices.json",
        fetch=fail_fetch,
        normalize=lambda _raw: [],
    )
    monkeypatch.setattr(fetch_courier_offices, "SOURCES", [failure, success])
    monkeypatch.setattr(sys, "argv", ["fetch_courier_offices.py"])

    assert fetch_courier_offices.main() == 1
    assert success.output_path.exists()
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["speedy"]["status"] == "failed"
    assert status["speedy"]["error"] == "Speedy unavailable"
    assert status["econt"]["status"] == "success"
