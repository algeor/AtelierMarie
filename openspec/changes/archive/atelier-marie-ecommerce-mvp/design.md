## Context

Atelier Marie is a new luxury handmade candle brand with no existing digital presence. The MVP must deliver a complete e-commerce experience — from browsing to checkout — while laying the groundwork for data-driven personalization. The system must run on free infrastructure (Oracle Free VPS or local machine) with no paid services.

**Constraints:**
- Zero budget for hosting/services — SQLite + DuckDB, no managed databases
- Anonymous-first UX — users browse and buy without mandatory login
- Session-based analytics from day one — every interaction tracked for future ML
- Legally distinct from any reference site — original brand identity, layout, and code
- Must feel like a boutique luxury shop, not a generic template

**Stakeholders:** Brand owner (product/content), customers (browse/buy), future ML pipeline (event data consumers).

## Goals / Non-Goals

**Goals:**
- Beautiful, conversion-oriented luxury storefront that works on mobile and desktop
- Complete purchase flow: browse → PDP → cart → checkout
- Session-based event tracking pipeline feeding DuckDB for analytics and recommendations
- Co-occurrence recommendation engine with trending/similar/session-contextual fallbacks
- Google Sign-In with graceful anonymous-to-authenticated identity linking
- Admin dashboard for key e-commerce metrics
- Production-quality, modular code that's easy to extend

**Non-Goals:**
- Payment gateway integration (checkout creates order, payment is out of scope for MVP)
- Email/SMS notification system
- Inventory management beyond simple stock_quantity decrement
- User reviews/ratings system
- Multi-language/i18n support
- CMS for content management
- LightGBM/embedding-based ML (future-ready interfaces only)
- Real-time collaborative editing of admin content

## Decisions

### 1. Next.js 14 App Router + TypeScript + Tailwind CSS for frontend

**Choice:** Next.js with App Router (RSC where possible, client components for interactivity)

**Rationale:** App Router gives us server components for product pages (SEO + performance), streaming for grid loading, and route groups for clean organization. Tailwind CSS eliminates CSS maintenance for a luxury design system while keeping bundle size minimal.

**Alternatives considered:**
- Vite + React SPA: No SSR/SEO, worse initial load for product pages
- Remix: Good alternative but smaller ecosystem, less community support for e-commerce patterns
- Plain React + CSS Modules: More boilerplate, harder to maintain consistent luxury design tokens

### 2. FastAPI with SQLite (sync via aiosqlite) for backend

**Choice:** FastAPI with SQLAlchemy ORM, SQLite file database, async endpoints

**Rationale:** FastAPI gives us automatic OpenAPI docs, Pydantic validation, and async support. SQLite eliminates all database infrastructure — single file, zero config, handles the expected traffic volume (single-brand boutique shop) easily. WAL mode for concurrent reads.

**Alternatives considered:**
- Django: Heavier, ORM is synchronous-first, more boilerplate for a REST API
- Express/Node.js: Would require separate frontend/backend language skills
- PostgreSQL: Needs a running server, violates free-infrastructure constraint

### 3. DuckDB for analytics (append-only, OLAP workloads)

**Choice:** Separate DuckDB file for all event/analytics data

**Rationale:** DuckDB excels at analytical queries (aggregations, window functions) over append-only event data. Separating it from SQLite means analytics queries never block transactional operations. Native Parquet export for future data pipeline needs.

**Alternatives considered:**
- SQLite for everything: Analytics queries would compete with transactions; no columnar optimization
- ClickHouse: Needs a running server, too heavy for MVP traffic
- Plain JSON/CSV files: No query capability, manual aggregation required

### 4. Session-first identity model with deferred login

**Choice:** Generate UUID session_id on first visit, store in localStorage + cookie. Link to user_id on Google login.

**Rationale:** Most e-commerce visitors never log in. Tracking behavior by session means recommendations and analytics work for 100% of traffic from day one. When a user does authenticate, we retroactively link their session history.

**Alternatives considered:**
- Require login before tracking: Loses majority of behavioral data
- Device fingerprinting: Privacy concerns, unreliable, ethically questionable
- Server-side sessions only: Can't persist across browser restarts without cookies anyway

### 5. Co-occurrence recommendation engine with precomputed caches

**Choice:** Batch-compute item-item similarity scores from co-occurrence matrices (viewed-together, carted-together, bought-together). Store as JSON/Parquet. Serve from memory cache at request time.

**Rationale:** Simple, effective, no ML infrastructure needed. Precomputation avoids per-request computation cost. Session-contextual recommendations (based on current session's viewed products) use the same similarity matrix for real-time lookup.

**Alternatives considered:**
- Collaborative filtering: Needs user profiles, cold-start problem
- Content-based (embeddings): Requires ML inference infrastructure
- Real-time computation: Too expensive for free-tier hosting
- Third-party recommendation service: Paid, external dependency

### 6. Monorepo with `/frontend` and `/backend` directories

**Choice:** Single repository, two top-level directories, shared types via OpenAPI spec generation.

**Rationale:** Simplifies deployment on a single VPS, keeps frontend/backend changes atomic, single CI pipeline. OpenAPI spec (auto-generated by FastAPI) is the contract.

**Alternatives considered:**
- Separate repos: Overhead of coordinating deployments and API contracts
- Turborepo/Nx monorepo: Over-engineered for a two-package setup

### 7. Cart state: client-side with server sync

**Choice:** Cart state lives in React context + localStorage, synced to server on mutations.

**Rationale:** Instant UI feedback for add/remove/quantity changes. Server validates on sync and at checkout. Works offline/pre-login. Server cart is the source of truth for checkout.

**Alternatives considered:**
- Server-only cart: Latency on every interaction, bad UX for a luxury feel
- Client-only cart: Can't recover across devices, no server validation at checkout

## Risks / Trade-offs

- **[SQLite write contention]** → Mitigated by WAL mode and separating analytics writes to DuckDB. Boutique traffic volumes won't hit SQLite limits.
- **[Cold-start recommendations]** → Mitigated by trending-products fallback (most viewed in last 7 days), then category-based fallback. Co-occurrence needs ~100 sessions to produce meaningful results.
- **[Single-server SPOF]** → Accepted for MVP. Future: SQLite Litestream replication, static frontend on CDN.
- **[No payment processing]** → Checkout creates order with `pending` status. Payment integration is a follow-up milestone.
- **[DuckDB concurrent access]** → DuckDB handles concurrent reads well; writes are serialized. Event ingestion uses a write queue with batching (flush every 5s or 100 events).
- **[Session ID spoofing]** → Accepted for MVP analytics. Cart/order operations validate session ownership server-side. Future: signed session tokens.
- **[Image hosting]** → MVP uses local file serving or placeholder URLs. Future: S3-compatible object storage.
