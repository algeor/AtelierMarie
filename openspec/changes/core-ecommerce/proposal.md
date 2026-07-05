# Core E-Commerce — Proposal

## Motivation

Atelier Marie needs a working online store. Customers (primarily local, found via Instagram/word-of-mouth) need to browse candles, add to cart, and place orders. The shop owner needs to manage products and fulfill orders.

This is the **entire product**. Everything else (analytics, ML) is optional.

## Scope

This change delivers a complete, deployable e-commerce system:

### Capabilities

1. **Product Catalog** — Browse and search candles by category, view details with images
2. **Shopping Cart** — Add/remove items, persist across sessions, works without login
3. **Checkout** — Place an order with email + shipping address, guest or authenticated
4. **Order Management** — Customer views order history; admin updates status
5. **Authentication** — Optional Google OAuth login, JWT sessions
6. **Admin Panel** — CRUD products, manage orders, view basic stats (order count, revenue)

### Out of Scope (deferred to Layer 2)

- Event/analytics tracking
- ML recommendations
- A/B testing
- Custom browser SDK
- Session identity resolution for analytics

## Technical Approach

- **Backend:** FastAPI with SQLite (WAL mode)
- **Frontend:** Next.js 14 (separate app, communicates via JSON API)
- **Auth:** Google OAuth 2.0 + JWT (PyJWT)
- **Deploy:** Oracle Cloud Free Tier, Nginx + Let's Encrypt, systemd

## Impact

- Enables revenue generation (the actual business goal)
- Provides foundation for optional analytics/ML layers
- Deployable in ~2 weeks by one developer
