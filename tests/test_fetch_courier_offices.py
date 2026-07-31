"""Tests for courier data refresh normalizers."""

from scripts.fetch_courier_offices import (
    SOURCES,
    _normalize_speedy_sites,
    _parse_speedy_sites_export,
)


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
