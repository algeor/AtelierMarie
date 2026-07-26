"""CheckoutPage — /en/checkout."""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.e2e.pages.base_page import BASE_LOCALE, BASE_URL, BasePage


class CheckoutPage(BasePage):
    def __init__(self, driver, timeout: float = 10.0) -> None:
        super().__init__(driver, timeout)
        self.assert_url_contains("/checkout")

    @classmethod
    def navigate(cls, driver, timeout: float = 10.0) -> "CheckoutPage":
        """Drive the browser to /checkout, then construct (URL guard runs after nav)."""
        driver.get(f"{BASE_URL}/{BASE_LOCALE}/checkout")
        return cls(driver, timeout)

    def fill_email(self, email: str) -> "CheckoutPage":
        el = self.wait_for(EC.visibility_of_element_located((By.ID, "checkout-email")))
        el.clear()
        el.send_keys(email)
        return self

    def fill_name(self, name: str) -> "CheckoutPage":
        el = self.wait_for(EC.visibility_of_element_located((By.ID, "checkout-name")))
        el.clear()
        el.send_keys(name)
        return self

    def select_door_delivery(self, courier: str, address: dict) -> "CheckoutPage":
        """Fill door-delivery: method=door, courier, city/postal/street/phone."""
        # Select method=door
        for radio in self.driver.find_elements(By.CSS_SELECTOR, "input[name='delivery-method']"):
            if radio.get_attribute("value") == "door":
                self.driver.execute_script("arguments[0].click();", radio)
                break
        # Select courier
        self.wait_for(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[name='delivery-courier']")
        ))
        for radio in self.driver.find_elements(By.CSS_SELECTOR, "input[name='delivery-courier']"):
            if radio.get_attribute("value") == courier:
                self.driver.execute_script("arguments[0].click();", radio)
                break
        # Address fields — inputs identified by their surrounding label text is
        # brittle; the fields are the only text inputs in the door form. Use
        # placeholder attribute to find them.
        def fill_by_placeholder_key(placeholder_fragment: str, value: str):
            for inp in self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']"):
                ph = (inp.get_attribute("placeholder") or "").lower()
                if placeholder_fragment.lower() in ph:
                    inp.clear()
                    inp.send_keys(value)
                    return
        fill_by_placeholder_key("city", address.get("city", ""))
        fill_by_placeholder_key("postal", address.get("postal_code", ""))
        fill_by_placeholder_key("street", address.get("street", ""))
        # Phone — type=tel
        phones = self.driver.find_elements(By.CSS_SELECTOR, "input[type='tel']")
        if phones:
            phones[0].clear()
            phones[0].send_keys(address.get("phone", ""))
        return self

    def submit_expecting_success(self):
        from tests.e2e.pages.order_confirmation_page import OrderConfirmationPage

        self._click_submit()
        return OrderConfirmationPage(self.driver, self.timeout)

    def submit_expecting_error(self) -> "CheckoutPage":
        self._click_submit()
        return self

    def _click_submit(self) -> None:
        btns = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        # Multiple submits exist (mobile + desktop); click the first visible.
        for b in btns:
            if b.is_displayed():
                b.click()
                return
        btns[0].click()

    def get_validation_errors(self) -> list[str]:
        alerts = self.driver.find_elements(By.CSS_SELECTOR, "[role='alert']")
        return [a.text for a in alerts if a.text.strip()]
