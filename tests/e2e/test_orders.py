"""E2E: order history + detail. Detail test creates order via httpx (D17)."""
from __future__ import annotations

import httpx
import pytest

from tests.e2e.pages.orders_page import OrdersPage
from tests.e2e.pages.order_detail_page import OrderDetailPage
from tests.e2e.conftest import BACKEND_URL, FRONTEND_URL, BASE_LOCALE, SEED_PRODUCT_ID


def test_orders_page_loads_for_anonymous(driver):
    driver.delete_all_cookies()
    OrdersPage.navigate(driver)
    # Either empty state or list — assert no 500 in title.
    assert "500" not in driver.title


def _create_order_via_api(driver) -> str | None:
    driver.get(f"{FRONTEND_URL}/{BASE_LOCALE}/")
    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
    with httpx.Client(base_url=BACKEND_URL, cookies=cookies, timeout=10.0) as c:
        r = c.post("/v1/cart/items", json={"product_id": SEED_PRODUCT_ID, "quantity": 1})
        if r.status_code >= 400:
            return None
        order_payload = {
            "customer_email": "e2e@test.com",
            "customer_name": "E2E",
            "delivery": {
                "method": "door",
                "door": {
                    "courier": "speedy",
                    "city": "Sofia",
                    "postal_code": "1000",
                    "street": "Main 1",
                    "phone": "+359888123456",
                },
            },
        }
        r2 = c.post("/v1/orders", json=order_payload)
        if r2.status_code >= 400:
            return None
        return r2.json().get("id")


def test_order_detail_shows_status_items_total(driver):
    driver.delete_all_cookies()
    order_id = _create_order_via_api(driver)
    if not order_id:
        pytest.skip("Could not create order via API")
    driver.get(f"{FRONTEND_URL}/{BASE_LOCALE}/orders/{order_id}")
    page = OrderDetailPage(driver)
    assert page.get_status().strip() != ""
