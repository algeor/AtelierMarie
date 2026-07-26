"""OrdersPage — /en/orders (list)."""
from __future__ import annotations

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.e2e import testids
from tests.e2e.pages.base_page import BASE_LOCALE, BASE_URL, BasePage


class OrdersPage(BasePage):
    def __init__(self, driver, timeout: float = 10.0) -> None:
        super().__init__(driver, timeout)
        # URL guard: /orders exact — not /orders/ (which is a detail page)
        self.assert_url_contains("/orders")

    @classmethod
    def navigate(cls, driver, timeout: float = 10.0) -> "OrdersPage":
        """Drive the browser to /orders, then construct (URL guard runs after nav)."""
        driver.get(f"{BASE_URL}/{BASE_LOCALE}/orders")
        return cls(driver, timeout)

    def get_order_rows(self):
        try:
            return self.wait_for(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, '[data-testid^="order-row-"]')
                ),
                timeout=3,
            )
        except TimeoutException:
            return []

    def navigate_to_order(self, order_id: str):
        from tests.e2e.pages.order_detail_page import OrderDetailPage

        locator = (By.CSS_SELECTOR, f'[data-testid="{testids.orderRow(order_id)}"]')
        link = self.wait_for(EC.element_to_be_clickable(locator))
        link.click()
        return OrderDetailPage(self.driver, self.timeout)
