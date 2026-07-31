"""Tests for Pydantic request/response models — valid and invalid data."""

import pytest
from pydantic import ValidationError

from app.models.cart import AddToCartRequest, CartResponse, UpdateCartItemRequest
from app.models.common import ErrorDetail, ErrorResponse, PaginationParams
from app.models.orders import CreateOrderRequest, UpdateOrderStatusRequest
from app.models.products import (
    CreateProductRequest,
    ProductImage,
    ProductResponse,
    UpdateProductRequest,
)
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
            effective_price_cents=3200,
            category="Floral",
            category_name="Floral",
            product_type="candles",
            product_type_name="Candles",
            labels=[],
            images=[
                {
                    "id": "image-1",
                    "image_url": "/static/products/lavender-dream-300ml.webp",
                    "thumbnail_url": "/static/products/lavender-dream-300ml_thumb.webp",
                    "zoom_url": "/static/products/lavender-dream-300ml_zoom.webp",
                    "sort_order": 0,
                    "is_primary": True,
                }
            ],
            primary_image_url="/static/products/lavender-dream-300ml.webp",
            primary_thumbnail_url="/static/products/lavender-dream-300ml_thumb.webp",
            stock=24,
            is_active=True,
            is_featured=True,
            created_at="2024-06-01T10:00:00Z",
            updated_at="2024-06-01T10:00:00Z",
        )
        assert p.price_cents == 3200
        assert p.description == "A lovely candle"
        assert p.images[0].zoom_url == "/static/products/lavender-dream-300ml_zoom.webp"

    def test_product_image_zoom_url_defaults_to_none(self):
        """Externally-sourced/legacy images omit zoom_url; it must default to None."""
        image = ProductImage(
            id="image-1",
            image_url="/static/products/x.webp",
            thumbnail_url="/static/products/x_thumb.webp",
            sort_order=0,
            is_primary=True,
        )
        assert image.zoom_url is None

    def test_product_response_nullable_fields(self):
        p = ProductResponse(
            id="prod-002",
            name="Test",
            description=None,
            materials=None,
            days_to_craft=None,
            price_cents=1000,
            effective_price_cents=1000,
            category=None,
            category_name=None,
            product_type="candles",
            product_type_name="Candles",
            labels=[],
            stock=0,
            is_active=True,
            is_featured=False,
            created_at="2024-06-01T10:00:00Z",
            updated_at="2024-06-01T10:00:00Z",
        )
        assert p.description is None
        assert p.category is None
        assert p.images == []
        assert p.primary_image_url is None

    def test_create_product_valid(self):
        req = CreateProductRequest(
            id="new-candle-200ml", name_en="New Candle", price_cents=2500, stock=10
        )
        assert req.is_active is True
        assert req.is_featured is False

    def test_create_product_rejects_oversized_safety_text(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(
                id="new-candle-200ml",
                name_en="New Candle",
                price_cents=2500,
                stock=10,
                safety_warnings_en="x" * 2001,
            )

    def test_update_product_rejects_oversized_care_text(self):
        with pytest.raises(ValidationError):
            UpdateProductRequest(care_instructions_bg="x" * 2001)

    def test_create_product_weight_defaults_to_300(self):
        req = CreateProductRequest(
            id="new-candle-200ml", name_en="New Candle", price_cents=2500, stock=10
        )
        assert req.weight_grams == 300

    def test_create_product_explicit_weight_persists(self):
        req = CreateProductRequest(
            id="heavy-candle", name_en="Heavy", price_cents=2500, stock=5, weight_grams=550
        )
        assert req.weight_grams == 550

    def test_create_product_invalid_weight_zero(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(
                id="bad-candle", name_en="Bad", price_cents=1000, stock=5, weight_grams=0
            )

    def test_create_product_invalid_weight_exceeds_max(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(
                id="bad-candle", name_en="Bad", price_cents=1000, stock=5, weight_grams=100_001
            )

    def test_update_product_changes_weight(self):
        req = UpdateProductRequest(weight_grams=420)
        assert req.weight_grams == 420

    def test_update_product_weight_omitted_is_none(self):
        req = UpdateProductRequest(stock=3)
        assert req.weight_grams is None

    def test_create_product_weight_boundary_min(self):
        req = CreateProductRequest(
            id="min-weight", name_en="Min", price_cents=1000, stock=1, weight_grams=1
        )
        assert req.weight_grams == 1

    def test_create_product_weight_boundary_max(self):
        req = CreateProductRequest(
            id="max-weight", name_en="Max", price_cents=1000, stock=1, weight_grams=100_000
        )
        assert req.weight_grams == 100_000

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
            AddToCartRequest(product_id="lavender-dream-300ml", quantity=11)

    def test_add_to_cart_quantity_at_max_allowed(self):
        req = AddToCartRequest(product_id="lavender-dream-300ml", quantity=10)
        assert req.quantity == 10

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
        req = CreateOrderRequest(
            customer_email="test@example.com",
            delivery={
                "method": "office",
                "office": {
                    "courier": "econt",
                    "office_id": "1",
                    "office_name": "Sofia",
                    "office_type": "office",
                    "city": "София",
                    "phone": "+359888123456",
                },
            },
        )
        assert req.customer_name is None
        assert req.delivery.method == "office"

    def test_create_order_invalid_email(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                customer_email="not-an-email",
                delivery={
                    "method": "office",
                    "office": {
                        "courier": "econt",
                        "office_id": "1",
                        "office_name": "Sofia",
                        "office_type": "office",
                        "phone": "+359888123456",
                    },
                },
            )

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
        req = AddToCartRequest(product_id="test-candle", quantity=10)
        assert req.quantity == 10

    def test_add_to_cart_quantity_over_max_rejected(self):
        with pytest.raises(ValidationError):
            AddToCartRequest(product_id="test-candle", quantity=11)

    def test_update_cart_item_quantity_at_max(self):
        from app.models.cart import UpdateCartItemRequest

        req = UpdateCartItemRequest(quantity=10)
        assert req.quantity == 10

    def test_update_cart_item_quantity_over_max_rejected(self):
        from app.models.cart import UpdateCartItemRequest

        with pytest.raises(ValidationError):
            UpdateCartItemRequest(quantity=11)

    def test_create_product_name_too_long(self):
        with pytest.raises(ValidationError):
            CreateProductRequest(id="test-candle", name_en="x" * 201, price_cents=1000, stock=5)

    def test_create_order_notes_too_long(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                customer_email="test@example.com",
                notes="x" * 2001,
                delivery={
                    "method": "office",
                    "office": {
                        "courier": "econt",
                        "office_id": "1",
                        "office_name": "Sofia",
                        "office_type": "office",
                        "phone": "+359888123456",
                    },
                },
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

    def test_zeptomail_provider_is_valid_and_warns_without_api_key(self, monkeypatch):
        from app import config

        warnings = []

        class FakeLogger:
            def warning(self, message):
                warnings.append(message)

        monkeypatch.setattr(config, "_logger", FakeLogger())

        s = config.Settings(email_provider="zeptomail", email_api_key="")

        assert s.email_provider == "zeptomail"
        assert warnings == [
            "EMAIL_PROVIDER is set to zeptomail but EMAIL_API_KEY is empty. "
            "Email sending will be unavailable."
        ]

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


class TestSection2ChangedBehavior:
    """Tests for validation tightening in admin-polish-edge-cases (2.6)."""

    def test_add_to_cart_quantity_11_rejected(self):
        """le=10 rejects quantity=11 (previously accepted under le=99)."""
        with pytest.raises(ValidationError):
            AddToCartRequest(product_id="lavender-dream-300ml", quantity=11)

    def test_create_product_non_string_name_clean_error(self):
        """Non-string name_en produces clean ValidationError, not TypeError from .strip()."""
        with pytest.raises(ValidationError):
            CreateProductRequest(id="test-candle", name_en=123, price_cents=1000, stock=5)

    def test_create_order_whitespace_only_customer_name_rejected(self):
        """customer_name='   ' rejected after strip (previously accepted)."""
        with pytest.raises(ValidationError):
            CreateOrderRequest(customer_email="a@b.com", customer_name="   ")


class TestCalculateOffset:
    """Tests for `calculate_offset` helper in app/models/common.py (task 4.4)."""

    def test_page_one_returns_zero(self):
        from app.models.common import calculate_offset

        assert calculate_offset(1, 20) == 0

    def test_page_two_limit_twenty_returns_twenty(self):
        from app.models.common import calculate_offset

        assert calculate_offset(2, 20) == 20

    def test_page_three_limit_ten(self):
        from app.models.common import calculate_offset

        assert calculate_offset(3, 10) == 20
