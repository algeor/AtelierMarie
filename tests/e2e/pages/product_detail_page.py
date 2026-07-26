"""ProductDetailPage — /en/products/{id}."""
from __future__ import annotations

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from tests.e2e import testids
from tests.e2e.pages.base_page import BasePage

# aria-label → reaction-type mapping (matches ReactionBar.tsx translation keys
# `comments.loveProduct` / `comments.likeProduct`; the vitest mock returns the key
# itself so the *rendered* aria-label ends up as the translation key. In the
# real running app the values are the localized strings — we match by
# aria-pressed presence instead by walking both buttons.)
REACTION_ORDER = ["heart", "thumbs_up"]


class ProductDetailPage(BasePage):
    def __init__(self, driver, timeout: float = 10.0) -> None:
        super().__init__(driver, timeout)
        self.assert_url_contains("/products/")

    def get_title(self) -> str:
        return self.wait_for(EC.visibility_of_element_located((By.TAG_NAME, "h1"))).text

    def get_price(self) -> str:
        # Price rendered somewhere on page — grab first element containing $/€/лв
        return self.driver.find_element(By.CSS_SELECTOR, "[class*='text-']").text

    def click_add_to_cart(self):
        from tests.e2e.components.cart_drawer import CartDrawerComponent

        btn = self.wait_for(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, f'[data-testid="{testids.addToCartBtn}"]')
            )
        )
        btn.click()
        # Drawer opens programmatically; wait for it.
        drawer = CartDrawerComponent(self.driver, self.timeout)
        drawer.wait_visible()
        return drawer

    def _reaction_buttons(self):
        # Reaction buttons live in a container of type button[aria-pressed]
        return self.driver.find_elements(By.CSS_SELECTOR, "button[aria-pressed]")

    def _reaction_button(self, reaction_type: str):
        idx = REACTION_ORDER.index(reaction_type)
        # First two aria-pressed buttons in the DOM within the product page
        # are the reaction buttons (heart, thumbs_up).
        btns = [
            b for b in self._reaction_buttons()
            if b.get_attribute("type") == "button"
        ]
        # Filter to those with an emoji span (❤️ / 👍)
        reaction_btns = [b for b in btns if b.find_elements(By.CSS_SELECTOR, "span[aria-hidden='true']")]
        return reaction_btns[idx]

    def click_reaction(self, reaction_type: str):
        btn = self._reaction_button(reaction_type)
        btn.click()

    def get_reaction_count(self, reaction_type: str) -> int:
        btn = self._reaction_button(reaction_type)
        spans = btn.find_elements(By.CSS_SELECTOR, "span.tabular-nums")
        if not spans:
            return 0
        try:
            return int((spans[0].text or "0").strip())
        except ValueError:
            return 0

    def is_reaction_pressed(self, reaction_type: str) -> bool:
        return self._reaction_button(reaction_type).get_attribute("aria-pressed") == "true"

    def submit_comment(self, text: str, display_name: str) -> None:
        form_loc = (By.CSS_SELECTOR, f'[data-testid="{testids.commentForm}"]')
        form = self.wait_for(EC.visibility_of_element_located(form_loc))
        # Display name field only present for anonymous users
        name_inputs = form.find_elements(By.ID, "comment-display-name")
        if name_inputs:
            name_inputs[0].clear()
            name_inputs[0].send_keys(display_name)
        body = form.find_element(By.ID, "comment-body")
        body.clear()
        body.send_keys(text)
        form.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    def get_comments(self):
        try:
            return self.wait_for(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, f'[data-testid="{testids.commentCard}"]')
                ),
                timeout=3,
            )
        except TimeoutException:
            return []
