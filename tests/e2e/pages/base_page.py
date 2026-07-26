"""BasePage — shared behaviour for every full-page object.

Provides:
  - BASE_URL / BASE_LOCALE constants (matching conftest env)
  - `wait_for()` explicit-wait helper
  - `assert_url_contains()` URL-guard helper for `__init__` guards (D16)
  - `cart` / `header` properties returning Component Objects (D14)
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from tests.e2e.components.cart_drawer import CartDrawerComponent
    from tests.e2e.components.header import HeaderComponent


BASE_URL = os.environ.get("E2E_FRONTEND_URL", "http://localhost:3000")
BASE_LOCALE = os.environ.get("E2E_LOCALE", "en")
DEFAULT_TIMEOUT = float(os.environ.get("E2E_TIMEOUT", "10"))


class BasePage:
    """Root class for all page objects.

    Subclasses SHOULD call `self.assert_url_contains(pattern)` in `__init__`
    (D16) so navigation bugs fail loudly at construction, not on the first
    missing locator.
    """

    def __init__(self, driver: WebDriver, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.driver = driver
        self.timeout = timeout

    # ─── URL helpers ────────────────────────────────────────────────────────

    def localized(self, path: str) -> str:
        """Return an absolute URL with the base locale prefix."""
        path = path.lstrip("/")
        return f"{BASE_URL}/{BASE_LOCALE}/{path}"

    def assert_url_contains(self, pattern: str) -> None:
        """Fail fast with a clear message if the browser is not on `pattern`."""
        WebDriverWait(self.driver, self.timeout).until(
            EC.url_contains(pattern),
            message=f"Expected URL to contain {pattern!r}, was {self.driver.current_url!r}",
        )

    # ─── Wait helper ────────────────────────────────────────────────────────

    def wait_for(self, condition, timeout: float | None = None) -> WebElement:
        """Explicit wait; returns whatever the condition returns.

        Wraps `WebDriverWait(...).until(condition)` so tests never call
        `time.sleep`.
        """
        return WebDriverWait(self.driver, timeout or self.timeout).until(condition)

    # ─── Cross-page components ──────────────────────────────────────────────

    @property
    def cart(self) -> "CartDrawerComponent":
        # Lazy import to avoid circular reference — CartDrawerComponent takes
        # a driver, not a page, so it works from any page.
        from tests.e2e.components.cart_drawer import CartDrawerComponent

        return CartDrawerComponent(self.driver)

    @property
    def header(self) -> "HeaderComponent":
        from tests.e2e.components.header import HeaderComponent

        return HeaderComponent(self.driver)
