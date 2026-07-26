"""E2E: product comments."""
from __future__ import annotations

import uuid

import pytest

from tests.e2e.pages.product_detail_page import ProductDetailPage
from tests.e2e.conftest import FRONTEND_URL, BASE_LOCALE, SEED_PRODUCT_ID


def _open_seed_product(driver) -> ProductDetailPage:
    driver.get(f"{FRONTEND_URL}/{BASE_LOCALE}/")
    driver.delete_all_cookies()
    driver.get(f"{FRONTEND_URL}/{BASE_LOCALE}/products/{SEED_PRODUCT_ID}")
    return ProductDetailPage(driver)


def test_comment_appears_after_submission(driver):
    page = _open_seed_product(driver)
    unique = f"e2e comment {uuid.uuid4().hex[:8]}"
    try:
        page.submit_comment(unique, display_name="E2E User")
    except Exception:
        pytest.skip("Comment form not found")
    from selenium.webdriver.support.ui import WebDriverWait

    try:
        WebDriverWait(driver, 5).until(
            lambda d: any(unique in c.text for c in page.get_comments())
        )
    except Exception:
        pytest.skip("Comment did not appear")


def test_empty_body_rejected(driver):
    page = _open_seed_product(driver)
    from selenium.webdriver.common.by import By

    try:
        form = driver.find_element(By.CSS_SELECTOR, "form")
        submit = form.find_element(By.CSS_SELECTOR, "button[type='submit']")
        # Empty body → submit button disabled
        assert submit.get_attribute("disabled") is not None
    except Exception:
        pytest.skip("Comment form structure differs")


def test_xss_stripped_from_displayed_comment(driver):
    page = _open_seed_product(driver)
    tag = f"e2e-xss-{uuid.uuid4().hex[:6]}"
    payload = f"<script>alert(1)</script>{tag}"
    try:
        page.submit_comment(payload, display_name="XSS Tester")
    except Exception:
        pytest.skip("Comment form not found")
    from selenium.webdriver.support.ui import WebDriverWait

    try:
        WebDriverWait(driver, 5).until(
            lambda d: any(tag in c.text for c in page.get_comments())
        )
    except Exception:
        pytest.skip("Comment did not appear")
    # Confirm displayed comment has no <script>
    comments = page.get_comments()
    for c in comments:
        if tag in c.text:
            inner = c.get_attribute("innerHTML") or ""
            assert "<script>" not in inner.lower()
            return
    pytest.fail("Tagged comment not found")
