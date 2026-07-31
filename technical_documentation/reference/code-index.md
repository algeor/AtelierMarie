# Code Index

Quick map from task to source files.

## Backend

| Task | Files |
|---|---|
| App startup/router map | `app/main.py` |
| Settings/env | `app/config.py` |
| Schema/migrations | `app/database.py` |
| Error envelope | `app/exceptions.py`, `app/responses.py` |
| Session cookie | `app/middleware/session.py`, `app/dependencies/session.py` |
| Request ID | `app/middleware/request_id.py` |
| Google OAuth/JWT | `app/services/auth_service.py`, `app/routes/auth.py`, `app/dependencies/auth.py` |
| Products | `app/services/product_service.py`, `app/routes/products.py`, `app/models/products.py` |
| Product images | `app/services/image_service.py`, `app/services/product_image_service.py` |
| Product media editor/lightbox | `app/services/image_service.py`, `frontend/components/admin/ProductForm.tsx`, `frontend/components/admin/ImageCropEditor.tsx`, `frontend/lib/cropImage.ts`, `frontend/components/products/ProductGallery.tsx` |
| Product videos | `app/services/video_service.py`, `app/services/product_video_service.py` |
| Taxonomy | `app/services/taxonomy_service.py`, `app/routes/taxonomy.py`, `app/models/taxonomy.py` |
| Promotions/banner | `app/services/promotion_service.py`, `app/services/banner_service.py`, `app/routes/promotions.py` |
| Cart | `app/services/cart_service.py`, `app/routes/cart.py`, `app/models/cart.py` |
| Checkout/orders | `app/services/order_service.py`, `app/routes/orders.py`, `app/models/orders.py` |
| Payments/Stripe | `app/services/payment_service.py`, `app/routes/webhooks.py` |
| Delivery/shipping | `app/services/delivery_service.py`, `app/services/shipping_service.py`, `app/routes/delivery.py` |
| Econt/Speedy | `app/services/econt_client.py`, `app/services/speedy_client.py` |
| Email | `app/services/email_service.py`, `app/email/*` |
| Contact | `app/services/contact_service.py`, `app/routes/contact.py`, `app/models/contact.py` |
| FAQ | `app/services/faq_service.py`, `app/routes/faq.py`, `app/models/faq.py` |
| About/story | `app/services/about_service.py`, `app/routes/about.py`, `app/models/about.py` |
| Comments/reactions | `app/services/comment_service.py`, `app/services/reaction_service.py`, `app/routes/comments.py`, `app/routes/reactions.py` |
| Analytics | `app/services/analytics_service.py`, `app/routes/analytics.py`, `app/models/analytics.py` |
| GDPR helpers | `app/services/gdpr_service.py` |

## Frontend

| Task | Files |
|---|---|
| Locale middleware | `frontend/middleware.ts`, `frontend/i18n/*` |
| Global layout | `frontend/app/[locale]/layout.tsx` |
| API facade | `frontend/lib/api.ts`, `frontend/lib/api-client.ts`, `frontend/lib/mock-api.ts` |
| Types | `frontend/lib/types.ts` |
| Auth state | `frontend/contexts/AuthContext.tsx`, `frontend/components/auth/*` |
| Cart state | `frontend/contexts/CartContext.tsx`, `frontend/components/cart/*` |
| Consent/tracking | `frontend/contexts/CookieConsentContext.tsx`, `frontend/lib/analytics.ts`, `frontend/lib/tracking.ts` |
| Products | `frontend/app/[locale]/products/*`, `frontend/components/products/*` |
| Checkout | `frontend/app/[locale]/checkout/page.tsx`, `frontend/components/checkout/*` |
| Orders | `frontend/app/[locale]/orders/*`, `frontend/components/orders/*` |
| Admin | `frontend/app/[locale]/admin/*`, `frontend/components/admin/*` |
| FAQ | `frontend/app/[locale]/faq/page.tsx`, `frontend/components/faq/*` |
| About/story | `frontend/app/[locale]/atelier/page.tsx`, `frontend/components/atelier/*` |
| Contact | `frontend/app/[locale]/contact/page.tsx`, `frontend/components/contact/*` |
| Legal pages | `frontend/app/[locale]/terms`, `privacy`, `cookies` |
| Messages | `frontend/messages/en.json`, `frontend/messages/bg.json` |
