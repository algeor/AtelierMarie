## 1. Project Scaffolding & Infrastructure

- [ ] 1.1 Initialize monorepo with /frontend (Next.js 14 + TypeScript + Tailwind CSS) and /backend (FastAPI + Python)
- [ ] 1.2 Configure Tailwind with luxury design tokens (colors, typography, spacing, border-radius)
- [ ] 1.3 Set up SQLite database with WAL mode and create migration script for all tables (users, products, orders, order_items, session_identity)
- [ ] 1.4 Set up DuckDB database and create events table schema
- [ ] 1.5 Configure FastAPI project structure (routers, models, schemas, services, database module)
- [ ] 1.6 Create shared TypeScript types/interfaces for API responses
- [ ] 1.7 Set up environment configuration (.env files, config module for both frontend/backend)

## 2. Database & Backend Foundation

- [ ] 2.1 Implement SQLAlchemy models for users, products, orders, order_items, session_identity
- [ ] 2.2 Implement DuckDB connection manager with write buffering (flush every 5s or 100 events)
- [ ] 2.3 Create Pydantic schemas for all API request/response models
- [ ] 2.4 Implement database initialization (idempotent migrations for SQLite + DuckDB)
- [ ] 2.5 Seed database with sample candle products (8-12 products across categories)

## 3. Authentication & Sessions

- [ ] 3.1 Implement session ID generation utility (UUID v4) for frontend (localStorage + cookie)
- [ ] 3.2 Implement POST /auth/google endpoint (Google ID token verification, user upsert, session token return)
- [ ] 3.3 Implement GET /auth/me endpoint (return authenticated user profile)
- [ ] 3.4 Implement POST /auth/logout endpoint (invalidate auth, preserve session)
- [ ] 3.5 Implement session-to-user identity linking (update session_identity on login, retroactive DuckDB event update)
- [ ] 3.6 Implement auth middleware (extract session_id and optional user from request headers)
- [ ] 3.7 Implement first-user-as-admin bootstrap logic

## 4. Product Catalog API

- [ ] 4.1 Implement GET /products endpoint (pagination, category filter, sorting)
- [ ] 4.2 Implement GET /products/{slug} endpoint (full product details)
- [ ] 4.3 Implement GET /products/search?q={query} endpoint (text search across name, description, category)
- [ ] 4.4 Implement POST /products/admin endpoint (create product with auto-slug, admin-only)
- [ ] 4.5 Implement stock quantity validation (reject out-of-stock adds, atomic decrement on checkout)

## 5. Cart & Orders API

- [ ] 5.1 Implement cart storage model (server-side, keyed by session_id)
- [ ] 5.2 Implement GET /cart endpoint (return cart items with product details and totals)
- [ ] 5.3 Implement POST /cart/add endpoint (add item, increment if exists, validate stock)
- [ ] 5.4 Implement PATCH /cart/item endpoint (update quantity, remove if 0)
- [ ] 5.5 Implement DELETE /cart/item endpoint (remove item from cart)
- [ ] 5.6 Implement POST /checkout endpoint (validate stock, create order + order_items, decrement stock, clear cart)
- [ ] 5.7 Implement GET /orders/{id} endpoint (order details, owner-only access)

## 6. Event Tracking System

- [ ] 6.1 Implement POST /events endpoint (single and batch event ingestion, validation)
- [ ] 6.2 Implement event write buffer (in-memory queue, flush to DuckDB every 5s or 100 events)
- [ ] 6.3 Create frontend event tracking utility (TypeScript module for emitting all event types)
- [ ] 6.4 Implement IntersectionObserver-based impression tracking for product grid
- [ ] 6.5 Wire up all frontend event emission points (session_start, product_view, click_product, search_query, add_to_cart, remove_from_cart, purchase, newsletter_signup, contact_submit)

## 7. Recommendations Engine

- [ ] 7.1 Implement co-occurrence matrix computation script (view, cart, purchase signals with weighted scoring)
- [ ] 7.2 Implement trending products computation (rolling 7-day window, hourly cache refresh)
- [ ] 7.3 Implement GET /recommendations?session_id={id} endpoint (session-based, trending fallback)
- [ ] 7.4 Implement GET /similar-products/{product_id} endpoint (co-occurrence based, category fallback)
- [ ] 7.5 Create recommendation cache layer (precomputed similarity scores, trending products)
- [ ] 7.6 Define future-ready personalization interface (user-based hooks, model-based ranking stubs)

## 8. Frontend — Layout & Design System

- [ ] 8.1 Create luxury design system component library (Button, Card, Badge, Input, Accordion, Typography, Container)
- [ ] 8.2 Implement announcement bar component (rotating messages, dismissible)
- [ ] 8.3 Implement header component (logo, navigation with Shop dropdown, utility icons)
- [ ] 8.4 Implement mobile navigation (hamburger menu, slide-out drawer)
- [ ] 8.5 Implement footer component (links, social icons, payment icon placeholders)
- [ ] 8.6 Create responsive layout wrapper (mobile-first breakpoints, consistent spacing)

## 9. Frontend — Homepage & Shop Pages

- [ ] 9.1 Implement hero section (editorial image placeholder, headline, subtext, CTAs)
- [ ] 9.2 Implement product grid component (responsive columns, luxury card design)
- [ ] 9.3 Implement product card component (image, name, price, quick-add, choose-options, wishlist)
- [ ] 9.4 Implement shop page with category filtering and sorting
- [ ] 9.5 Implement product detail page (gallery, attributes, quantity selector, add-to-cart, buy-now, accordions)
- [ ] 9.6 Implement recommended products section on PDP

## 10. Frontend — Cart, Search & Overlays

- [ ] 10.1 Implement cart context/state management (React context + localStorage, server sync)
- [ ] 10.2 Implement cart drawer component (slide-in, items list, quantity controls, remove, total, checkout button)
- [ ] 10.3 Implement empty cart state
- [ ] 10.4 Implement search overlay component (modal/fullscreen, input with live suggestions, trending products)
- [ ] 10.5 Implement search debounce and product suggestion fetching (300ms debounce)

## 11. Frontend — Auth, Contact & Newsletter

- [ ] 11.1 Implement Google Sign-In button and OAuth flow (frontend integration)
- [ ] 11.2 Implement user context (auth state management, anonymous-to-authenticated transition)
- [ ] 11.3 Implement contact form section (name, email, phone, message, validation, submission)
- [ ] 11.4 Implement newsletter signup section (email input, copy, success state)
- [ ] 11.5 Implement account icon behavior (login prompt when anonymous, user menu when authenticated)

## 12. Admin Dashboard

- [ ] 12.1 Implement GET /admin/dashboard endpoint (aggregate metrics from DuckDB)
- [ ] 12.2 Implement GET /admin/events endpoint (paginated event log with filters)
- [ ] 12.3 Implement GET /admin/products endpoint (products with view/order counts)
- [ ] 12.4 Implement GET /admin/orders endpoint (paginated order list)
- [ ] 12.5 Create admin dashboard frontend page (metrics cards, top products, conversion rates, search terms, session breakdown)
- [ ] 12.6 Implement recommendation performance metrics (CTR tracking and display)

## 13. Polish & Integration

- [ ] 13.1 Add smooth hover animations to product cards and buttons (200-300ms ease transitions)
- [ ] 13.2 Add loading states and skeleton screens for async content
- [ ] 13.3 Implement error boundary and user-friendly error states
- [ ] 13.4 Add beautiful placeholder images for products (gradient/pattern placeholders)
- [ ] 13.5 End-to-end integration test: browse → add to cart → checkout flow
- [ ] 13.6 Write README with setup instructions (prerequisites, install, run dev, seed data, environment variables)
