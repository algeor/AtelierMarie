"""Shared fixtures and hooks for the Selenium E2E suite.

Assumes both dev servers are already running:
  backend  → http://localhost:8000
  frontend → http://localhost:3000

Run with `make test-e2e`. Use `HEADLESS=0` for headed debug runs.
"""
from __future__ import annotations

import os
import socket
import sqlite3
import uuid
from pathlib import Path
from typing import Iterator

import httpx
import pytest
from _pytest.nodes import Item
from _pytest.reports import TestReport
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ─── .env autoload ───────────────────────────────────────────────────────────
#
# The E2E suite must sign JWTs with the same secret the backend verifies with,
# and must call the admin API with the same key. Both live in `.env`. Load
# them here so `make test-e2e` "just works" without the user having to remember
# to `export JWT_SECRET=... ADMIN_API_KEY=... make test-e2e` — a footgun that
# silently produces admin-page redirects (see HANDOFF, 2026-07-26).
#
# `setdefault` means externally-set env vars still win, so CI overrides remain
# possible.

def _load_dotenv() -> None:
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        # Strip surrounding quotes so `KEY="foo"` yields `foo`, matching how
        # pydantic-settings parses .env for the app itself.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


_load_dotenv()


# ─── Environment / constants ─────────────────────────────────────────────────

FRONTEND_URL = os.environ.get("E2E_FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.environ.get("E2E_BACKEND_URL", "http://localhost:8000")
BASE_LOCALE = os.environ.get("E2E_LOCALE", "en")
DB_PATH = os.environ.get("DB_PATH", "./atelier_marie.db")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
HEADLESS = os.environ.get("HEADLESS", "1") != "0"

_WORKER_ID = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
SEED_PRODUCT_ID = f"e2e-test-candle-{_WORKER_ID}"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"


# ─── Server reachability ─────────────────────────────────────────────────────

def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session", autouse=True)
def _require_servers_running() -> None:
    """Skip the whole suite if either dev server is unreachable."""
    missing: list[str] = []
    if not _is_port_open("localhost", 3000):
        missing.append("frontend (localhost:3000) — start with `make dev-frontend`")
    if not _is_port_open("localhost", 8000):
        missing.append("backend (localhost:8000) — start with `make dev-backend`")
    if missing:
        pytest.skip("E2E servers not reachable:\n  - " + "\n  - ".join(missing))


# ─── WebDriver ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def driver() -> Iterator[webdriver.Chrome]:
    """Session-scoped headless Chrome. Set HEADLESS=0 for headed runs."""
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,1000")

    service = Service(ChromeDriverManager().install())
    drv = webdriver.Chrome(service=service, options=options)
    drv.implicitly_wait(0)  # rely on explicit WebDriverWait everywhere
    try:
        yield drv
    finally:
        drv.quit()


# ─── Seed product (admin API) ────────────────────────────────────────────────

def _admin_headers() -> dict[str, str]:
    """Admin auth header. Fail loudly if ADMIN_API_KEY is missing — seeding needs it."""
    if not ADMIN_API_KEY:
        pytest.fail(
            "ADMIN_API_KEY env var not set. The seed step requires admin auth. "
            "Set ADMIN_API_KEY to a value matching the backend's config, e.g. "
            "ADMIN_API_KEY=dev-admin-key make test-e2e"
        )
    return {"Authorization": f"Bearer {ADMIN_API_KEY}"}


@pytest.fixture(scope="session", autouse=True)
def _seed_product(_require_servers_running: None) -> Iterator[None]:
    """Create `e2e-test-candle` via admin API; delete on teardown.

    Asserts the seed product is reachable at its public URL before yielding —
    catches misconfigured `is_active=0` or route regressions before tests run.
    """
    payload = {
        "id": SEED_PRODUCT_ID,
        "name_en": "E2E Test Candle",
        "description_en": "Seed product used by the Selenium suite.",
        "price_cents": 2500,
        "stock": 100,
        "is_active": True,
    }
    with httpx.Client(base_url=BACKEND_URL, timeout=10.0) as client:
        # Try to create; if the product already exists (soft-deleted from a prior
        # run, DELETE only sets is_active=0), fall back to PATCH to reactivate.
        resp = client.post("/v1/admin/products", json=payload, headers=_admin_headers())
        if resp.status_code == 409:
            patch_payload = {
                "name_en": payload["name_en"],
                "description_en": payload["description_en"],
                "price_cents": payload["price_cents"],
                "stock": payload["stock"],
                "is_active": True,
            }
            resp = client.patch(
                f"/v1/admin/products/{SEED_PRODUCT_ID}",
                json=patch_payload,
                headers=_admin_headers(),
            )
        if resp.status_code not in (200, 201):
            pytest.fail(
                f"Failed to seed product: {resp.status_code} {resp.text[:200]}"
            )

        # Verify public route serves it (is_active=1, not just DB-present).
        public_url = f"{FRONTEND_URL}/{BASE_LOCALE}/products/{SEED_PRODUCT_ID}"
        page_resp = httpx.get(public_url, timeout=10.0, follow_redirects=True)
        if page_resp.status_code != 200:
            pytest.fail(
                f"Seed product not reachable at {public_url}: {page_resp.status_code}"
            )

    yield

    with httpx.Client(base_url=BACKEND_URL, timeout=10.0) as client:
        client.delete(f"/v1/admin/products/{SEED_PRODUCT_ID}", headers=_admin_headers())


@pytest.fixture(scope="session")
def seed_product_id(_seed_product: None) -> str:
    """Return this worker's unique seed product ID."""
    return SEED_PRODUCT_ID


@pytest.fixture
def product_detail(driver: webdriver.Chrome, seed_product_id: str):
    """Clear cookies, then navigate directly to the seed product detail page.

    Clearing cookies here (rather than in each test body) ensures the fixture
    navigates with a clean session — required because the driver is session-scoped
    and may carry cookies from a prior test.
    """
    from tests.e2e.pages.product_detail_page import ProductDetailPage
    from tests.e2e.pages.base_page import BASE_URL, BASE_LOCALE

    driver.delete_all_cookies()
    driver.get(f"{BASE_URL}/{BASE_LOCALE}/products/{seed_product_id}")
    return ProductDetailPage(driver)


# ─── Screenshot on failure ───────────────────────────────────────────────────

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call) -> Iterator[None]:
    """Save `screenshots/{test_name}.png` when a test fails.

    Only fires for tests that used the `driver` fixture — nothing to screenshot
    otherwise.
    """
    outcome = yield
    report: TestReport = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    drv = item.funcargs.get("driver")
    if drv is None:
        return
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = item.name.replace("/", "_").replace("::", "__")
    try:
        drv.save_screenshot(str(SCREENSHOT_DIR / f"{safe_name}.png"))
    except Exception:  # noqa: BLE001 — screenshot failure must not mask test failure
        pass


# ─── Admin session injection (§7.1) ──────────────────────────────────────────

def _create_jwt(user_id: str, email: str, session_id: str) -> str:
    """Sign a JWT with the exact claim set `verify_jwt` expects.

    Missing any of `iss`, `aud`, `session_id`, `exp` → `verify_jwt` rejects.
    """
    import time

    import jwt  # runtime pyjwt

    secret = os.environ.get("JWT_SECRET", "dev-secret-do-not-use-in-production")
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "email": email,
        "is_admin": True,
        "session_id": session_id,
        "iss": "atelier-marie",
        "aud": "atelier-marie-web",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def inject_admin_session(driver: webdriver.Chrome) -> Iterator[dict[str, str]]:
    """Insert user + session rows into SQLite, then set both cookies on driver.

    Yields the created ids so tests can reference them. Teardown deletes both
    rows. Requires DB_PATH env var (or `./atelier_marie.db` default) to be the
    same DB the backend is reading.
    """
    user_id = f"e2e-admin-{uuid.uuid4().hex[:8]}"
    email = f"{user_id}@e2e.test"
    session_id = str(uuid.uuid4())

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO users (id, google_id, email, name, avatar_url, is_admin) "
            "VALUES (?, ?, ?, ?, NULL, 1)",
            (user_id, f"google-{user_id}", email, "E2E Admin"),
        )
        # sessions.expires_at is stored as ISO text elsewhere in the app;
        # any future date works. Use +7d.
        conn.execute(
            "INSERT INTO sessions (id, user_id, expires_at) "
            "VALUES (?, ?, datetime('now', '+7 days'))",
            (session_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()

    jwt_token = _create_jwt(user_id, email, session_id)

    # Navigate to the app once so add_cookie has a valid document.
    driver.get(f"{FRONTEND_URL}/{BASE_LOCALE}/")
    driver.delete_all_cookies()
    driver.add_cookie({"name": "session_id", "value": session_id, "path": "/"})
    driver.add_cookie({"name": "atelier_auth", "value": jwt_token, "path": "/"})

    try:
        yield {"user_id": user_id, "session_id": session_id, "email": email}
    finally:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()
        driver.delete_all_cookies()
