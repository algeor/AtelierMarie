"""AuthPage — auth-related URLs (login initiation + callback)."""
from __future__ import annotations

from tests.e2e.pages.base_page import BasePage


class AuthPage(BasePage):
    """Not a specific URL — used for auth flow assertions after the login click."""

    def __init__(self, driver, timeout: float = 10.0) -> None:
        # No URL guard — auth flow may bounce through multiple hosts.
        self.driver = driver
        self.timeout = timeout

    def click_login_button(self) -> None:
        self.header.click_login_button()

    def get_current_url(self) -> str:
        return self.driver.current_url

    def navigate_auth_callback(self) -> "AuthPage":
        self.driver.get(self.localized("auth/callback"))
        return self
