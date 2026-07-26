"""ProductListingPage — /en/products."""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.e2e import testids
from tests.e2e.pages.base_page import BASE_LOCALE, BASE_URL, BasePage


class ProductListingPage(BasePage):
    URL_PATH = "/products"

    def __init__(self, driver, timeout: float = 10.0) -> None:
        super().__init__(driver, timeout)
        self.assert_url_contains("/products")

    @classmethod
    def navigate(cls, driver, timeout: float = 10.0) -> "ProductListingPage":
        """Drive the browser to /products, then construct (URL guard runs after nav)."""
        # BASE_URL/BASE_LOCALE come from BasePage; build path without needing an instance.
        driver.get(f"{BASE_URL}/{BASE_LOCALE}/products")
        return cls(driver, timeout)

    def get_product_cards(self):
        # Wait for at least one card to render (SSR + hydration).
        return self.wait_for(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, f'[data-testid="{testids.productCard}"]')
            )
        )

    def filter_category(self, name: str) -> "ProductListingPage":
        group_locator = (By.CSS_SELECTOR, f'[data-testid="{testids.categoryFilter}"]')
        group = self.wait_for(EC.visibility_of_element_located(group_locator))
        for btn in group.find_elements(By.TAG_NAME, "button"):
            if (btn.text or "").strip() == name:
                btn.click()
                return self
        raise AssertionError(f"Category chip {name!r} not found")

    def click_first_product(self):
        from tests.e2e.pages.product_detail_page import ProductDetailPage

        cards = self.get_product_cards()
        # Card wraps a Link; click the link inside.
        cards[0].find_element(By.TAG_NAME, "a").click()
        return ProductDetailPage(self.driver, self.timeout)
