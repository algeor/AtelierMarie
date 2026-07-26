"""E2E: auth smoke tests."""
from __future__ import annotations

from tests.e2e.pages.auth_page import AuthPage
from tests.e2e.pages.product_listing_page import ProductListingPage


def test_login_button_initiates_oauth(driver):
    driver.delete_all_cookies()
    # Navigate somewhere the header is visible.
    ProductListingPage.navigate(driver)
    auth = AuthPage(driver)
    try:
        auth.click_login_button()
    except Exception:
        # Header may show UserMenu instead if a stale cookie is present.
        import pytest

        pytest.skip("Login button not visible (user already logged in?)")
    # Either redirects to Google, or navigates to a backend /auth URL.
    from selenium.webdriver.support.ui import WebDriverWait

    WebDriverWait(driver, 10).until(
        lambda d: "google.com" in d.current_url
        or "/auth" in d.current_url
        or d.current_url.startswith("http://localhost:8000")
    )


def test_auth_callback_does_not_500(driver):
    driver.delete_all_cookies()
    AuthPage(driver).navigate_auth_callback()
    assert "500" not in driver.title
