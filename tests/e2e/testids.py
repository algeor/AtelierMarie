"""
AUTO-GENERATED FILE - DO NOT EDIT MANUALLY.

Generated from frontend/lib/testids.ts by scripts/generate_testids.py.
To update: edit testids.ts, then run `make generate-testids`.
"""
from types import SimpleNamespace


# --- Static testids ---
productCard = "product-card"
categoryFilter = "category-filter"
cartBadge = "cart-badge"
cartDrawer = "cart-drawer"
addToCartBtn = "add-to-cart-btn"
commentForm = "comment-form"
commentCard = "comment-card"
orderStatus = "order-status"
loginButton = "login-button"


# --- Dynamic testids ---
def cartItem(productId: str) -> str:
    return f"cart-item-{productId}"

def cartRemove(productId: str) -> str:
    return f"cart-remove-{productId}"

def adminProductRow(id: str) -> str:
    return f"admin-product-row-{id}"

def adminEditLink(id: str) -> str:
    return f"admin-edit-{id}"

def orderRow(id: str) -> str:
    return f"order-row-{id}"


# --- Namespace for `from ... import TEST_IDS` style access ---
TEST_IDS = SimpleNamespace(
    productCard=productCard,
    categoryFilter=categoryFilter,
    cartBadge=cartBadge,
    cartDrawer=cartDrawer,
    addToCartBtn=addToCartBtn,
    commentForm=commentForm,
    commentCard=commentCard,
    orderStatus=orderStatus,
    loginButton=loginButton,
    cartItem=cartItem,
    cartRemove=cartRemove,
    adminProductRow=adminProductRow,
    adminEditLink=adminEditLink,
    orderRow=orderRow,
)
