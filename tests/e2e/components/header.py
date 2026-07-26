"""HeaderComponent — the site header (cart badge, login button).

Present on every page, hence a Component Object rather than a Page Object.
"""
from __future__ import annotations

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tests.e2e import testids


class HeaderComponent:
    def __init__(self, driver: WebDriver, timeout: float = 10.0) -> None:
        self.driver = driver
        self.timeout = timeout

    def get_badge_count(self) -> int:
        """Wait briefly for the cart badge to hydrate, then return its count.

        The badge is only rendered when the cart has items — an empty cart
        means the badge element is absent. Returns 0 in that case.
        """
        locator = (By.CSS_SELECTOR, f'[data-testid="{testids.cartBadge}"]')
        try:
            elem = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located(locator)
            )
        except TimeoutException:
            return 0
        text = (elem.text or "").strip()
        try:
            return int(text)
        except ValueError:
            return 0

    def click_login_button(self) -> None:
        locator = (By.CSS_SELECTOR, f'[data-testid="{testids.loginButton}"]')
        elem = WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(locator)
        )
        elem.click()
