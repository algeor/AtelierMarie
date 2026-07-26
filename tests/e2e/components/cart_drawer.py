"""CartDrawerComponent — the slide-in cart panel available on every page."""
from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tests.e2e import testids


class CartDrawerComponent:
    def __init__(self, driver: WebDriver, timeout: float = 10.0) -> None:
        self.driver = driver
        self.timeout = timeout

    # ─── Drawer visibility ──────────────────────────────────────────────────

    def _drawer_locator(self) -> tuple[str, str]:
        return (By.CSS_SELECTOR, f'[data-testid="{testids.cartDrawer}"]')

    def open_drawer(self) -> None:
        """Open the drawer by clicking the header cart affordance.

        The drawer is also opened programmatically by AddToCartButton — tests
        that added via the UI should skip this and just wait for the drawer.
        """
        # Header cart button opens the drawer. Cart badge lives inside it;
        # click the badge's ancestor button.
        badge_locator = (By.CSS_SELECTOR, f'[data-testid="{testids.cartBadge}"]')
        try:
            badge = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable(badge_locator)
            )
            badge.click()
        except Exception:
            # Fall back: the drawer may already be open (added via UI).
            pass
        self.wait_visible()

    def wait_visible(self) -> WebElement:
        return WebDriverWait(self.driver, self.timeout).until(
            EC.visibility_of_element_located(self._drawer_locator())
        )

    def close_drawer(self) -> None:
        self.wait_visible()
        # Send Escape via the body — drawer <div> is not itself focusable and
        # send_keys against non-interactable elements raises. Body is always
        # present and next-intl's drawer listens on document.
        from selenium.webdriver.common.keys import Keys

        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        # Wait for drawer to disappear so subsequent actions aren't blocked
        # by the overlay.
        WebDriverWait(self.driver, self.timeout).until(
            EC.invisibility_of_element_located(self._drawer_locator())
        )

    # ─── Items ──────────────────────────────────────────────────────────────

    def get_items(self) -> list[WebElement]:
        drawer = self.wait_visible()
        return drawer.find_elements(By.CSS_SELECTOR, '[data-testid^="cart-item-"]')

    def _item(self, product_id: str) -> WebElement:
        locator = (By.CSS_SELECTOR, f'[data-testid="{testids.cartItem(product_id)}"]')
        return WebDriverWait(self.driver, self.timeout).until(
            EC.visibility_of_element_located(locator)
        )

    def update_quantity(self, product_id: str, qty: int) -> None:
        """Set quantity on the given cart line.

        Cart items typically have +/- buttons or a number input; we look for a
        number input inside the item row first, else fall back to +/- clicks.
        """
        item = self._item(product_id)
        inputs = item.find_elements(By.CSS_SELECTOR, 'input[type="number"]')
        if inputs:
            inp = inputs[0]
            inp.clear()
            inp.send_keys(str(qty))
            inp.send_keys("\t")  # blur to trigger update
            return
        # Fallback: nudge with buttons named by aria-label
        current = int(item.get_attribute("data-quantity") or "1")
        delta = qty - current
        selector = "button[aria-label*='increase']" if delta > 0 else "button[aria-label*='decrease']"
        btn = item.find_element(By.CSS_SELECTOR, selector)
        for _ in range(abs(delta)):
            btn.click()

    def remove_item(self, product_id: str) -> None:
        locator = (By.CSS_SELECTOR, f'[data-testid="{testids.cartRemove(product_id)}"]')
        btn = WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(locator)
        )
        btn.click()
