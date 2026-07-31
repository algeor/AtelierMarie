# Test Map

Use this to pick tests without running everything first.

## Backend Test Files

| Area | Test files |
|---|---|
| App/router/health | `tests/test_routers.py`, `tests/test_health.py`, `tests/test_lifespan.py` |
| Config | `tests/test_config.py` |
| Database/schema | `tests/test_database.py`, `tests/test_database_constraints.py` |
| Sessions | `tests/test_session.py`, `tests/test_session_hardened.py`, `tests/realapp/test_session*.py` |
| Auth | `tests/test_auth.py`, `tests/test_auth_integration.py` |
| Products | `tests/test_product_service.py`, `tests/test_product_routes.py`, `tests/test_models.py` |
| Product media | `tests/test_image.py`, `tests/test_product_image_service.py`, `tests/test_product_video_service.py`, `tests/test_video_service.py` |
| Taxonomy | `tests/test_taxonomy_service.py`, `tests/test_taxonomy_migration.py`, `tests/test_product_taxonomy_filters.py`, `tests/realapp/test_taxonomy_routes.py` |
| Promotions/discounts | `tests/test_promotions.py`, `tests/test_discounts.py`, `tests/test_pricing.py` |
| Cart | `tests/test_cart_service.py`, `tests/test_cart_routes.py` |
| Orders/checkout | `tests/test_order_service.py`, `tests/test_order_routes.py`, `tests/realapp/test_order_routes.py` |
| Payments/Stripe | `tests/test_payment_integration.py`, `tests/test_webhooks.py` |
| Shipping/delivery | `tests/test_checkout_shipping.py`, `tests/test_shipping_service.py`, `tests/test_delivery_routes.py`, `tests/test_delivery_calculate_routes.py`, `tests/test_courier_clients.py`, `tests/realapp/test_delivery_checkout.py` |
| Email | `tests/test_email_service.py`, `tests/test_email_renderer.py`, `tests/test_email_providers.py` |
| Contact | `tests/test_contact_service.py`, `tests/test_contact_routes.py` |
| FAQ/about | `tests/test_faq_service.py`, `tests/test_about_service.py`, `tests/realapp/test_faq_routes.py`, `tests/realapp/test_about_routes.py` |
| Comments/reactions | `tests/test_comment_service.py`, `tests/test_reaction_service.py`, `tests/realapp/test_comment_routes.py`, `tests/realapp/test_reaction_routes.py`, `tests/realapp/test_admin_comments.py` |
| Analytics | `tests/test_analytics.py` |
| Utilities | `tests/test_sanitize.py`, `tests/test_slugify.py`, `tests/test_row_access.py`, `tests/test_request_id_middleware.py` |

## Frontend Test Areas

| Area | Test files or folder |
|---|---|
| Checkout | `frontend/__tests__/app/checkout.test.tsx` |
| Order confirmation | `frontend/__tests__/app/order-confirmation.test.tsx` |
| Product detail | `frontend/__tests__/app/product-detail.test.tsx` |
| Legal pages | `frontend/__tests__/app/legal-pages.test.tsx`, `terms.test.tsx` |
| Account/orders | `frontend/__tests__/pages/account.test.tsx`, `orders.test.tsx` |
| Cart context | `frontend/__tests__/contexts/CartContext.test.tsx` |
| Auth context | `frontend/__tests__/contexts/AuthContext.test.tsx` |
| Consent context | `frontend/__tests__/contexts/CookieConsentContext.test.tsx` |
| API client/mock | `frontend/__tests__/lib/api-client.test.ts`, `mock-api.test.ts` |
| Analytics | `frontend/__tests__/lib/analytics.test.ts`, `components/analytics-*.test.*` |
| Media/video | `frontend/__tests__/lib/media.test.ts`, `components/ProductVideo.test.tsx` |
| Product media editor/lightbox | `frontend/__tests__/components/admin/ProductForm.test.tsx`, `frontend/__tests__/components/products/ProductGallery.test.tsx`, `frontend/__tests__/components/ProductVideo.test.tsx` |
| i18n | `frontend/__tests__/components/i18n-rendering.test.tsx`, `lib/api-locale.test.ts`, `lib/middleware-locale.test.ts` |

## Default Choice

If unsure, run:

```bash
make test-backend
make test-frontend
```

If you changed checkout/payment/shipping, do not rely on frontend tests alone. Run backend service/route tests too.
