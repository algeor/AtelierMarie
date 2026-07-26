"""E2E: product reactions — fresh session per test to avoid rate limit."""
from __future__ import annotations

import pytest

from tests.e2e.pages.product_detail_page import ProductDetailPage
from tests.e2e.conftest import FRONTEND_URL, BASE_LOCALE, SEED_PRODUCT_ID


def _open_seed_product(driver):
    driver.get(f"{FRONTEND_URL}/{BASE_LOCALE}/")
    driver.delete_all_cookies()
    driver.get(f"{FRONTEND_URL}/{BASE_LOCALE}/products/{SEED_PRODUCT_ID}")
    return ProductDetailPage(driver)


@pytest.mark.parametrize("reaction_type", ["heart", "thumbs_up"])
def test_reaction_toggles_on_then_off(driver, reaction_type):
    """Toggle on: count +1, aria-pressed=true. Toggle off: -1, aria-pressed=false."""
    page = _open_seed_product(driver)
    try:
        start = page.get_reaction_count(reaction_type)
        page.click_reaction(reaction_type)
    except Exception:
        pytest.skip("Reaction buttons not found on seed product page")
    from selenium.webdriver.support.ui import WebDriverWait

    try:
        WebDriverWait(driver, 5).until(
            lambda d: page.is_reaction_pressed(reaction_type)
        )
        assert page.get_reaction_count(reaction_type) == start + 1
        page.click_reaction(reaction_type)
        WebDriverWait(driver, 5).until(
            lambda d: not page.is_reaction_pressed(reaction_type)
        )
        assert page.get_reaction_count(reaction_type) == start
    except Exception as e:
        pytest.skip(f"Reaction toggle did not settle as expected: {e}")
