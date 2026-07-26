"""AdminPage — /en/admin and /en/admin/products."""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.e2e import testids
from tests.e2e.pages.base_page import BASE_LOCALE, BASE_URL, BasePage


class AdminPage(BasePage):
    def __init__(self, driver, timeout: float = 15.0) -> None:
        super().__init__(driver, timeout)
        self.assert_url_contains("/admin")

    @classmethod
    def navigate_dashboard(cls, driver, timeout: float = 15.0) -> "AdminPage":
        driver.get(f"{BASE_URL}/{BASE_LOCALE}/admin")
        return cls(driver, timeout)

    @classmethod
    def navigate_products(cls, driver, timeout: float = 15.0) -> "AdminPage":
        driver.get(f"{BASE_URL}/{BASE_LOCALE}/admin/products")
        return cls(driver, timeout)

    @classmethod
    def navigate_new_product(cls, driver, timeout: float = 15.0):
        from tests.e2e.pages.admin_product_form_page import AdminProductFormPage

        driver.get(f"{BASE_URL}/{BASE_LOCALE}/admin/products/new")
        return AdminProductFormPage(driver, timeout)

    def click_edit(self, product_id: str):
        from tests.e2e.pages.admin_product_form_page import AdminProductFormPage

        locator = (By.CSS_SELECTOR, f'[data-testid="{testids.adminEditLink(product_id)}"]')
        link = self.wait_for(EC.element_to_be_clickable(locator))
        link.click()
        return AdminProductFormPage(self.driver, self.timeout)

    def get_product_rows(self):
        # `[data-testid^="admin-product-row-"]` (prefix match) silently returns
        # 0 rows via chromedriver/Selenium even when querySelectorAll finds them
        # — a known W3C driver quirk with hyphens in attribute values. XPath is
        # bulletproof; use it for the "any row" selector.
        return self.driver.find_elements(
            By.XPATH, "//*[starts-with(@data-testid, 'admin-product-row-')]"
        )

    def has_product_row(self, product_id: str) -> bool:
        rows = self.driver.find_elements(
            By.CSS_SELECTOR, f'[data-testid="{testids.adminProductRow(product_id)}"]'
        )
        return len(rows) > 0
