"""OrderConfirmationPage — /en/orders/{id}/confirmation."""
from __future__ import annotations

from selenium.webdriver.common.by import By

from tests.e2e.pages.base_page import BasePage


class OrderConfirmationPage(BasePage):
    def __init__(self, driver, timeout: float = 15.0) -> None:
        super().__init__(driver, timeout)
        self.assert_url_contains("/orders/")
        self.assert_url_contains("/confirmation")

    def get_order_id(self) -> str:
        """Return the order id extracted from the URL: /orders/{id}/confirmation."""
        url = self.driver.current_url
        parts = url.split("/orders/")
        if len(parts) < 2:
            raise AssertionError(f"URL {url!r} does not contain /orders/")
        tail = parts[1]
        return tail.split("/")[0]

    def get_order_id_from_page(self) -> str:
        # The confirmation page renders "Order #{id}" somewhere; fall back to URL.
        try:
            return self.get_order_id()
        except AssertionError:
            body = self.driver.find_element(By.TAG_NAME, "body").text
            return body
