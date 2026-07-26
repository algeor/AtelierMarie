"""E2E: contact form smoke tests."""
from __future__ import annotations

from tests.e2e.pages.contact_page import ContactPage


def test_contact_page_loads_with_fields(driver):
    ContactPage.navigate(driver)
    from selenium.webdriver.common.by import By

    assert driver.find_elements(By.ID, "contact-name")
    assert driver.find_elements(By.ID, "contact-email")
    assert driver.find_elements(By.ID, "contact-message")


def test_empty_submit_shows_validation_errors(driver):
    page = ContactPage.navigate(driver).submit()
    errors = page.get_validation_errors()
    assert errors, "Expected at least one validation error on empty submit"
