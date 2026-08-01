"""Service and audit-sync tests for admin-managed Cookie Policy content."""

import sqlite3

import pytest

from app.database import get_db, init_db
from app.services import cookies_service
from app.services.cookies_service import CookiesNotFoundError, CookiesValidationError


@pytest.fixture()
def cookies_db(tmp_path) -> str:
    path = str(tmp_path / "cookies.db")
    init_db(path)
    return path


def test_seed_matches_existing_cookie_copy_and_public_locale(cookies_db):
    en = cookies_service.get_public_cookies("en")
    assert en["title"] == "Cookie Policy"
    assert {item["name"] for item in en["cookies"]} >= {
        "session_id",
        "atelier_auth",
        "NEXT_LOCALE",
        "atelier_cookie_consent",
    }

    bg = cookies_service.get_public_cookies("bg")
    assert bg["title"] == "Политика за бисквитки"
    assert bg["headers"]["purpose"] == "Цел"


def test_admin_update_page_and_section(cookies_db):
    page = cookies_service.update_page(
        {"title_en": "Cookie details", "title_bg": "Данни за бисквитки"}
    )
    assert page["title_en"] == "Cookie details"
    assert page["title_bg"] == "Данни за бисквитки"

    section = cookies_service.update_section(
        "control",
        {
            "title_en": "Controls updated",
            "title_bg": "Контрол обновен",
            "body_en": ["First paragraph", "Second paragraph"],
            "body_bg": ["Първи параграф"],
        },
    )
    assert section["title_en"] == "Controls updated"
    assert section["body_en"] == ["First paragraph", "Second paragraph"]

    public = cookies_service.get_public_cookies("bg")
    controls = next(section for section in public["sections"] if section["id"] == "control")
    assert controls["title"] == "Контрол обновен"
    assert controls["body"] == ["Първи параграф"]


def test_detected_inventory_sync_upserts_and_hides_stale_auto_rows(cookies_db):
    rows = cookies_service.sync_detected_inventory(
        [
            {
                "name": "deploy_cookie",
                "purpose_en": "Detected during deploy.",
                "type_en": "Browser cookie",
                "duration_en": "Session cookie.",
                "observed_on": ["/en"],
            }
        ]
    )
    synced = next(row for row in rows if row["name"] == "deploy_cookie")
    assert synced["auto_detected"] is True
    assert synced["is_active"] is True
    assert synced["observed_on"] == ["/en"]
    public_cookies = cookies_service.get_public_cookies()["cookies"]
    assert any(item["name"] == "deploy_cookie" for item in public_cookies)

    cookies_service.sync_detected_inventory(
        [
            {
                "name": "replacement_cookie",
                "purpose_en": "Detected later.",
                "type_en": "Browser cookie",
                "duration_en": "Session cookie.",
            }
        ]
    )
    public_names = {item["name"] for item in cookies_service.get_public_cookies()["cookies"]}
    assert "replacement_cookie" in public_names
    assert "deploy_cookie" not in public_names


def test_seed_runs_once_and_does_not_clobber_edits_or_deletions(tmp_path):
    path = str(tmp_path / "seed.db")
    init_db(path)

    with get_db() as conn:
        conn.execute("UPDATE cookies_page SET title_en = 'Edited cookies' WHERE id = 'cookies'")
        conn.execute("DELETE FROM cookies_sections WHERE slug = 'control'")

    init_db(path)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    title = conn.execute("SELECT title_en FROM cookies_page WHERE id = 'cookies'").fetchone()[0]
    assert title == "Edited cookies"
    assert conn.execute("SELECT 1 FROM cookies_sections WHERE slug = 'control'").fetchone() is None
    conn.close()


def test_invalid_cookie_updates_are_rejected(cookies_db):
    with pytest.raises(CookiesValidationError):
        cookies_service.update_page({"title_en": ""})
    with pytest.raises(CookiesValidationError):
        cookies_service.update_section("control", {"body_en": []})
    with pytest.raises(CookiesNotFoundError):
        cookies_service.update_section("missing", {"title_en": "Missing"})
