"""Tests for Pydantic request/response models — valid and invalid data."""

import pytest
from pydantic import ValidationError

from app.models.cart import AddToCartRequest, CartResponse, UpdateCartItemRequest
from app.models.common import ErrorDetail, ErrorResponse, PaginationParams
from app.models.orders import CreateOrderRequest, UpdateOrderStatusRequest
from app.models.products import CreateProductRequest, ProductResponse, UpdateProductRequest
from app.models.users import UserResponse


class TestProductModels:
    def test_product_response_valid(self):
        p = ProductResponse(
            id="lavender-dream-300ml",
            name="Lavender Dreams",
            description="A lovely candle",
            materials="Soy wax, lavender oil",
            days_to_craft=3,
            price_cents=3200,
            category="Floral",
            image_url="/static/products/lavender-dream-300ml.webp",
            stock=24,
            is_active=True,
            is_featured=True,
            created_at="2024-06-01T10:00:00Z",
            updated_at="2024-06-01T10:00:00Z",
        )
        assert p.price_cents == 3200
        assert p.description == "A lovely candle"

    def test_product_response_nullable_fields(self):
        p = ProductResponse(
            id="prod-002",
            name="Test",
            description=None,
            materials=None,
            days_to_craft=None,
            price_cents=1000,
            category=None,
            image_url=None,
            stock=0,
            is_active=True,
            is_featured=False,
            created_at="2024-06-01T10:00:00Z",
            updated_at="2024-06-01T10:00:00Z",
        )
        assert p.description is None
        assert p.category is None
        assert p.image_url is None

    def test_create_product_valid(self):
        req = CreateProductRequest(
            id="new-candle-200ml", name_en="New Candle", price_cents=2500, stock=10
        )
        assert req.is_active is True
        assert req.is_featured is False

    def test_create_product_invalid_price_zero(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="bad-candle", name_en="Bad", price_cents=0, stock=5)

    def test_create_product_invalid_price_negative(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="bad-candle", name_en="Bad", price_cents=-100, stock=5)

    def test_create_product_invalid_stock_negative(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="bad-candle", name_en="Bad", price_cents=1000, stock=-1)

    def test_create_product_boundary_price_one(self):
        req = CreateProductRequest(id="cheap-candle", name_en="Cheap", price_cents=1, stock=0)
        assert req.price_cents == 1
        assert req.stock == 0

    def test_create_product_invalid_name_empty_string(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="bad-candle", name_en="", price_cents=1000, stock=5)

    def test_create_product_invalid_id_format(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="BAD ID!", name_en="Bad", price_cents=1000, stock=5)

    def test_create_product_invalid_id_uppercase(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="Bad-Candle", name_en="Bad", price_cents=1000, stock=5)

    def test_create_product_invalid_days_to_craft_negative(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(
                id="test-candle", name_en="Test", price_cents=1000, stock=5, days_to_craft=-1
            )

    def test_update_product_all_optional(self):
        req = UpdateProductRequest()
        assert req.name_en is None
        assert req.price_cents is None

    def test_update_product_partial(self):
        req = UpdateProductRequest(price_cents=1500)
        assert req.price_cents == 1500
        assert req.name_en is None

    def test_update_product_invalid_price_zero(self):
        with pytest.raises(ValidationError):
            UpdateProductRequest(price_cents=0)

    def test_update_product_empty_name_en_becomes_none(self):
        """Empty string is treated as 'not provided' for PATCH semantics."""
        req = UpdateProductRequest(name_en="")
        assert req.name_en is None

    def test_update_product_explicit_null_name_en_rejected(self):
        with pytest.raises(ValidationError):
            UpdateProductRequest.model_validate({"name_en": None})


class TestCartModels:
    def test_add_to_cart_valid(self):
        req = AddToCartRequest(product_id="lavender-dream-300ml", quantity=3)
        assert req.quantity == 3

    def test_add_to_cart_default_quantity(self):
        req = AddToCartRequest(product_id="lavender-dream-300ml")
        assert req.quantity == 1

    def test_add_to_cart_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            AddToCartRequest(product_id="lavender-dream-300ml", quantity=0)

    def test_add_to_cart_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            AddToCartRequest(product_id="lavender-dream-300ml", quantity=-1)

    def test_add_to_cart_quantity_exceeds_max_rejected(self):
        with pytest.raises(ValidationError):
            AddToCartRequest(product_id="lavender-dream-300ml", quantity=100)

    def test_add_to_cart_quantity_at_max_allowed(self):
        req = AddToCartRequest(product_id="lavender-dream-300ml", quantity=99)
        assert req.quantity == 99

    def test_add_to_cart_invalid_product_id_format(self):
        with pytest.raises(ValidationError):
            AddToCartRequest(product_id="INVALID ID!", quantity=1)

    def test_update_cart_item_zero_allowed(self):
        req = UpdateCartItemRequest(quantity=0)
        assert req.quantity == 0

    def test_update_cart_item_negative_rejected(self):
        with pytest.raises(ValidationError):
            UpdateCartItemRequest(quantity=-1)

    def test_cart_response_uses_total_cents(self):
        cart = CartResponse(items=[], total_cents=6400, item_count=2)
        assert cart.total_cents == 6400


class TestOrderModels:
    def test_create_order_valid(self):
        req = CreateOrderRequest(customer_email="test@example.com")
        assert req.customer_name is None

    def test_create_order_invalid_email(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(customer_email="not-an-email")

    def test_update_order_status_valid(self):
        req = UpdateOrderStatusRequest(status="confirmed")
        assert req.status == "confirmed"

    def test_update_order_status_invalid(self):
        with pytest.raises(ValidationError):
            UpdateOrderStatusRequest(status="unknown_status")

    def test_all_valid_statuses(self):
        for status in ("pending", "confirmed", "shipped", "delivered", "cancelled"):
            req = UpdateOrderStatusRequest(status=status)
            assert req.status == status


class TestUserModels:
    def test_user_response_valid(self):
        u = UserResponse(
            id="user-001",
            email="marie@example.com",
            name="Marie",
            avatar_url="https://example.com/avatar.jpg",
            is_admin=True,
        )
        assert u.is_admin is True

    def test_user_response_nullable(self):
        u = UserResponse(
            id="user-002",
            email="anon@example.com",
            name=None,
            avatar_url=None,
            is_admin=False,
        )
        assert u.name is None


class TestCommonModels:
    def test_error_response(self):
        err = ErrorResponse(
            error=ErrorDetail(code="NOT_FOUND", message="Product not found", details=None)
        )
        assert err.error.code == "NOT_FOUND"

    def test_pagination_defaults(self):
        p = PaginationParams()
        assert p.page == 1
        assert p.limit == 20

    def test_pagination_limit_over_100_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(limit=101)

    def test_pagination_page_zero_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(page=0)

    def test_pagination_limit_zero_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)

    def test_pagination_page_negative_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(page=-1)

    def test_pagination_boundaries_valid(self):
        p1 = PaginationParams(page=1, limit=1)
        assert p1.limit == 1
        p100 = PaginationParams(page=1, limit=100)
        assert p100.limit == 100


class TestBoundaryConstraints:
    """Upper-bound and max_length tests for business-rule constraints."""

    def test_add_to_cart_quantity_at_max(self):
        req = AddToCartRequest(product_id="test-candle", quantity=99)
        assert req.quantity == 99

    def test_add_to_cart_quantity_over_max_rejected(self):
        with pytest.raises(ValidationError):
            AddToCartRequest(product_id="test-candle", quantity=100)

    def test_update_cart_item_quantity_at_max(self):
        from app.models.cart import UpdateCartItemRequest

        req = UpdateCartItemRequest(quantity=99)
        assert req.quantity == 99

    def test_update_cart_item_quantity_over_max_rejected(self):
        from app.models.cart import UpdateCartItemRequest

        with pytest.raises(ValidationError):
            UpdateCartItemRequest(quantity=100)

    def test_create_product_name_too_long(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="test-candle", name_en="x" * 201, price_cents=1000, stock=5)

    def test_create_order_shipping_address_too_long(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                customer_email="test@example.com",
                shipping_address="x" * 1001,
            )

    def test_create_order_notes_too_long(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                customer_email="test@example.com",
                notes="x" * 2001,
            )


class TestProductionConfigValidation:
    """Settings model_validator rejects insecure defaults in production."""

    def test_production_rejects_default_jwt_secret(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.config import Settings

        with pytest.raises(PydanticValidationError):
            Settings(environment="production", jwt_secret="dev-secret-do-not-use-in-production")

    def test_production_rejects_empty_admin_api_key(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.config import Settings

        with pytest.raises(PydanticValidationError):
            Settings(
                environment="production",
                jwt_secret="a-real-production-secret-key",
                admin_api_key="",
                google_client_id="123456.apps.googleusercontent.com",
                google_client_secret="GOCSPX-secret",
            )

    def test_production_rejects_short_admin_api_key(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.config import Settings

        with pytest.raises(PydanticValidationError):
            Settings(
                environment="production",
                jwt_secret="a-real-production-secret-key",
                admin_api_key="too-short",
                google_client_id="123456.apps.googleusercontent.com",
                google_client_secret="GOCSPX-secret",
            )

    def test_staging_rejects_default_jwt_secret(self):
        from pydantic import ValidationError as PydanticValidationError

        from app.config import Settings

        with pytest.raises(PydanticValidationError):
            Settings(
                environment="staging",
                jwt_secret="dev-secret-do-not-use-in-production",
            )

    def test_production_accepts_valid_config(self):
        from app.config import Settings

        s = Settings(
            environment="production",
            jwt_secret="a-real-production-secret-key",
            admin_api_key="a-long-enough-production-api-key-here",
            google_client_id="123456.apps.googleusercontent.com",
            google_client_secret="GOCSPX-secret",
        )
        assert s.environment == "production"

    def test_production_accepts_missing_google_creds(self):
        """Missing Google creds in production logs a warning but doesn't block startup."""
        from app.config import Settings

        s = Settings(
            environment="production",
            jwt_secret="a-real-production-secret-key",
            admin_api_key="a-long-enough-production-api-key-here",
            google_client_id="",
            google_client_secret="",
        )
        assert s.environment == "production"


class TestProductIdPatternEdgeCases:
    """Verify the product ID regex rejects malformed slugs."""

    def test_create_product_invalid_id_trailing_hyphen(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="lavender-", name_en="Bad", price_cents=1000, stock=5)

    def test_create_product_invalid_id_leading_hyphen(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="-lavender", name_en="Bad", price_cents=1000, stock=5)

    def test_create_product_invalid_id_double_hyphen(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="lavender--dream", name_en="Bad", price_cents=1000, stock=5)

    def test_create_product_invalid_id_only_hyphens(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="---", name_en="Bad", price_cents=1000, stock=5)

    def test_create_product_valid_id_single_segment(self):
        req = CreateProductRequest(id="lavender", name_en="Good", price_cents=1000, stock=5)
        assert req.id == "lavender"

    def test_create_product_valid_id_multi_segment(self):
        req = CreateProductRequest(
            id="lavender-dream-300ml", name_en="Good", price_cents=1000, stock=5
        )
        assert req.id == "lavender-dream-300ml"
