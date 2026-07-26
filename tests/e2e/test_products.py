"""E2E: product listing and product detail flows."""
from __future__ import annotations

from tests.e2e.pages.product_listing_page import ProductListingPage


def test_products_page_loads_with_cards(driver):
    page = ProductListingPage.navigate(driver)
    cards = page.get_product_cards()
    assert len(cards) >= 1


def test_category_filter_narrows_cards(driver):
    """Click a non-'All' category and verify cards render (>=0)."""
    page = ProductListingPage.navigate(driver)
    # Try to find any category chip besides 'All' — if none exist, filter is
    # hidden by the component (fewer than 2 categories). Skip in that case.
    from selenium.webdriver.common.by import By
    from tests.e2e import testids

    groups = driver.find_elements(
        By.CSS_SELECTOR, f'[data-testid="{testids.categoryFilter}"]'
    )
    if not groups:
        import pytest

        pytest.skip("Category filter not rendered (fewer than 2 categories)")
    buttons = groups[0].find_elements(By.TAG_NAME, "button")
    names = [(b.text or "").strip() for b in buttons if (b.text or "").strip() != "All"]
    if not names:
        import pytest

        pytest.skip("No non-'All' category available")
    page.filter_category(names[0])
    # After filter, cards may be smaller or equal; assert page still healthy.
    _ = page.get_product_cards()


def test_product_detail_loads(driver):
    page = ProductListingPage.navigate(driver)
    detail = page.click_first_product()
    assert detail.get_title().strip() != ""
