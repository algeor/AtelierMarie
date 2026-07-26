"""AdminProductFormPage — /en/admin/products/new and /en/admin/products/{id}/edit."""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.e2e.pages.base_page import BasePage


class AdminProductFormPage(BasePage):
    def __init__(self, driver, timeout: float = 15.0) -> None:
        super().__init__(driver, timeout)
        self.assert_url_contains("/admin/products")

    def fill_product_form(self, data: dict) -> "AdminProductFormPage":
        """Fill known form fields. Only fields present in the DOM are set.

        Expected keys: id, name_en, name_bg, price_cents, stock, category,
        description_en, description_bg.
        """
        # Fields with known ids (from the ProductForm component)
        stable_ids = {
            "description_en": "description_en",
            "description_bg": "description_bg",
            "category": "category",
        }
        for key, field_id in stable_ids.items():
            if key in data and data[key] is not None:
                els = self.driver.find_elements(By.ID, field_id)
                if els:
                    els[0].clear()
                    els[0].send_keys(str(data[key]))
        # Other fields — locate by name attribute or placeholder.
        for key in ("id", "name_en", "name_bg", "price_cents", "stock"):
            if key in data and data[key] is not None:
                self._fill_by_name_or_placeholder(key, str(data[key]))
        return self

    def _fill_by_name_or_placeholder(self, key: str, value: str) -> None:
        # Try name= attribute first
        matches = self.driver.find_elements(By.CSS_SELECTOR, f"input[name='{key}']")
        if not matches:
            matches = self.driver.find_elements(By.CSS_SELECTOR, f"input[id='{key}']")
        if not matches:
            # Last resort: placeholder contains key fragment
            for inp in self.driver.find_elements(By.CSS_SELECTOR, "input"):
                ph = (inp.get_attribute("placeholder") or "").lower()
                if key.replace("_", " ") in ph:
                    matches = [inp]
                    break
        if matches:
            matches[0].clear()
            matches[0].send_keys(value)

    def submit_expecting_success(self):
        from tests.e2e.pages.admin_page import AdminPage

        self._click_submit()
        # Wait until URL leaves the form page.
        self.wait_for(EC.url_matches(r".*/admin/products(\?.*)?$"))
        return AdminPage(self.driver, self.timeout)

    def submit_expecting_error(self) -> "AdminProductFormPage":
        self._click_submit()
        return self

    def _click_submit(self) -> None:
        btns = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        for b in btns:
            if b.is_displayed() and b.is_enabled():
                b.click()
                return
        if btns:
            btns[0].click()
