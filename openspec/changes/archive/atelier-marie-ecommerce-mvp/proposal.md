## Why

Atelier Marie needs a full-stack e-commerce MVP to sell handmade luxury candles online. The brand targets women 25–60 who value elegant, handcrafted home décor and gifting. There is no existing storefront — this builds the entire customer-facing shop, backend commerce logic, event-driven analytics pipeline, and session-based recommendation engine from scratch, prioritizing a beautiful conversion-oriented luxury experience over feature breadth.

## What Changes

- New responsive luxury storefront (Next.js + TypeScript + Tailwind CSS) with announcement bar, mega-nav, hero, product grid, PDP, cart drawer, search overlay, contact form, newsletter signup, login, and footer
- New FastAPI backend with auth, product catalog, cart, orders, events, and recommendations APIs
- SQLite schema for users, products, orders, order items, and session identity mapping
- DuckDB analytics schema for behavioral events (views, clicks, cart actions, purchases, searches)
- Google Sign-In integration with anonymous-first session model
- Session-based co-occurrence recommendation engine (trending, similar, session-contextual)
- Admin dashboard for product views, conversion metrics, search analytics, and session insights
- Event tracking system capturing all user interactions with session_id as primary key

## Capabilities

### New Capabilities
- `storefront-ui`: Responsive luxury frontend — announcement bar, header/nav, hero, product grid, PDP, cart drawer, search overlay, contact, newsletter, footer. Mobile-first, editorial luxury aesthetic.
- `product-catalog-api`: FastAPI product CRUD, slug-based lookup, category filtering, admin product management.
- `auth-sessions`: Google OAuth login, anonymous session tracking, session-to-user identity linking on login.
- `cart-orders`: Cart state management (add/update/remove), checkout flow, order creation, order history.
- `event-tracking`: Client-side event emission and server-side event ingestion into DuckDB (views, clicks, cart, purchases, searches, signups).
- `recommendations`: Session-based co-occurrence recommender, trending products, similar-products endpoint, precomputed caches.
- `admin-dashboard`: Internal analytics dashboard — product views, top products, conversion/add-to-cart rates, search terms, session breakdown, recommendation performance.
- `database-schema`: SQLite operational schema (users, products, orders, order_items, session_identity) and DuckDB analytics schema (events table).

### Modified Capabilities
<!-- No existing capabilities to modify — greenfield project. -->

## Impact

- **New codebase**: Full project structure with `frontend/` (Next.js) and `backend/` (FastAPI) directories
- **APIs introduced**: 15+ REST endpoints across auth, products, cart, orders, events, recommendations, and admin
- **Infrastructure**: Designed for free-tier hosting (Oracle Free VPS or local), SQLite + DuckDB, no paid services
- **Dependencies**: Next.js 14+, React 18+, Tailwind CSS, FastAPI, SQLAlchemy, DuckDB Python, Google Auth libraries
- **External integrations**: Google Sign-In (OAuth 2.0)
