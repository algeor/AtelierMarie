"""OrderDetailPage — /en/orders/{id}."""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.e2e import testids
from tests.e2e.pages.base_page import BasePage


class OrderDetailPage(BasePage):
    def __init__(self, driver, timeout: float = 10.0) -> None:
        super().__init__(driver, timeout)
        url = driver.current_url
        if "/orders/" not in url or url.rstrip("/").endswith("/confirmation"):
            raise AssertionError(f"Not on order detail page: {url!r}")
        # Positive guard: wait for the status badge to appear
        self.wait_for(EC.presence_of_element_located(
            (By.CSS_SELECTOR, f'[data-testid="{testids.orderStatus}"]')
        ))

    def get_status(self) -> str:
        el = self.driver.find_element(
            By.CSS_SELECTOR, f'[data-testid="{testids.orderStatus}"]'
        )
        return (el.text or "").strip()

    def get_items(self):
        # No dedicated testid — items list rendered as list items in the page.
        return self.driver.find_elements(By.CSS_SELECTOR, "li")

    def get_total(self) -> str:
        # Simple heuristic: look for text containing currency in the body.
        return self.driver.find_element(By.TAG_NAME, "body").text
