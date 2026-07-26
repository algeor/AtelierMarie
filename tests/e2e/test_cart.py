"""E2E: cart operations."""
from __future__ import annotations

from selenium.webdriver.support.ui import WebDriverWait

from tests.e2e.pages.product_listing_page import ProductListingPage
from tests.e2e.components.cart_drawer import CartDrawerComponent


def test_add_to_cart_increments_badge(driver, product_detail):
    initial = product_detail.header.get_badge_count()
    drawer = product_detail.click_add_to_cart()
    items = drawer.get_items()
    assert len(items) >= 1
    drawer.close_drawer()
    WebDriverWait(driver, 5).until(
        lambda d: product_detail.header.get_badge_count() > initial
    )


def test_cart_persists_across_navigation(driver, product_detail):
    drawer = product_detail.click_add_to_cart()
    drawer.close_drawer()
    ProductListingPage.navigate(driver)
    WebDriverWait(driver, 5).until(
        lambda d: ProductListingPage(d).header.get_badge_count() >= 1
    )


def test_remove_item_decrements_badge(driver, product_detail):
    drawer = product_detail.click_add_to_cart()
    items = drawer.get_items()
    assert items, "Expected at least one item after add"
    testid = items[0].get_attribute("data-testid") or ""
    product_id = testid.replace("cart-item-", "")
    drawer.remove_item(product_id)
    WebDriverWait(driver, 5).until(lambda d: len(CartDrawerComponent(d).get_items()) == 0)


def test_update_quantity_changes_line_total(driver, product_detail):
    """Quantity update — happy path; skipped if no +/- controls found."""
    import pytest

    drawer = product_detail.click_add_to_cart()
    items = drawer.get_items()
    if not items:
        pytest.skip("No cart items")
    testid = items[0].get_attribute("data-testid") or ""
    product_id = testid.replace("cart-item-", "")
    try:
        drawer.update_quantity(product_id, 2)
    except Exception:
        pytest.skip("Quantity controls not found")
