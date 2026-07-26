"""ContactPage — /en/contact."""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.e2e.pages.base_page import BASE_LOCALE, BASE_URL, BasePage


class ContactPage(BasePage):
    def __init__(self, driver, timeout: float = 10.0) -> None:
        super().__init__(driver, timeout)
        self.assert_url_contains("/contact")

    @classmethod
    def navigate(cls, driver, timeout: float = 10.0) -> "ContactPage":
        """Drive the browser to /contact, then construct (URL guard runs after nav)."""
        driver.get(f"{BASE_URL}/{BASE_LOCALE}/contact")
        return cls(driver, timeout)

    def fill_form(self, name: str, email: str, message: str) -> "ContactPage":
        self._fill("contact-name", name)
        self._fill("contact-email", email)
        self._fill("contact-message", message)
        return self

    def _fill(self, element_id: str, value: str) -> None:
        el = self.wait_for(EC.visibility_of_element_located((By.ID, element_id)))
        el.clear()
        el.send_keys(value)

    def submit(self) -> "ContactPage":
        # Contact form submit button — last button[type=submit] in the form.
        btns = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        for b in btns:
            if b.is_displayed():
                b.click()
                return self
        if btns:
            btns[0].click()
        return self

    def get_validation_errors(self) -> list[str]:
        # Field errors have id ending in "-error"
        errs = self.driver.find_elements(By.CSS_SELECTOR, "[id$='-error']")
        return [e.text for e in errs if e.text.strip()]
