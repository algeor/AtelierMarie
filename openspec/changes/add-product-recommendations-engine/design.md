## Context

The storefront already has a FastAPI product API, a product service with listing/search/detail behavior, and a Next.js product detail page that renders product information with existing product card/grid components. Product discovery is currently driven by listing filters, featured products, and text search, but a shopper viewing one product does not receive contextual product suggestions.

The project uses Postgres with Alembic-managed schema. Product records already expose useful recommendation signals: product type, category, labels, localized names/descriptions, materials, active state, stock/orderability, featured status, and media.

## Goals / Non-Goals

**Goals:**

- Add product-to-product recommendations on public product detail pages.
- Use a hybrid ranking model: rules remain authoritative and embeddings improve semantic matching when available.
- Store product embeddings so future semantic search can reuse the same indexed product vectors.
- Keep the API stable for frontend consumers and safe when embeddings are missing.
- Split implementation into independent Backend/API and Frontend/UI work lanes.

**Non-Goals:**

- Build a separate external vector database.
- Replace the existing full-text search endpoint.
- Build personalized recommendations from user behavior, purchases, or saved products.
- Add admin UI for manually tuning recommendation weights.

## Decisions

### Decision 1: Use Postgres plus optional pgvector, not a separate vector DB

Store product embeddings in a `product_embeddings` table keyed by product ID and embedding model. Prefer a pgvector column and index when the deployment supports the extension. If local/test environments cannot enable pgvector, the system can still store vectors as JSON/text and rely on rule-only ranking or in-process cosine scoring for small catalogs.

Alternatives considered:

- Dedicated vector DB: more operational work than needed for the current catalog.
- No persisted vectors: simpler, but makes recommendations slower and blocks reuse for semantic search.

### Decision 2: Hybrid scoring keeps deterministic rules first

Recommendations SHALL combine rule score and optional embedding score. Rule score uses product type, category, shared labels, stock/orderability, featured status, and freshness. Embedding similarity contributes only when both selected and candidate products have compatible embeddings.

This keeps results explainable and prevents semantically close but commercially poor suggestions from outranking obvious related products.

### Decision 3: Add one public recommendations endpoint

Add `GET /v1/products/{product_id}/recommendations?locale=<en|bg>&limit=<n>` returning a `ProductListResponse`-style payload. It excludes the selected product, inactive products, and products that cannot be publicly viewed. It returns an empty list when no candidates exist.

Keeping recommendations separate from `GET /v1/products/{product_id}` avoids inflating product detail payloads and lets the frontend degrade gracefully if recommendations fail.

### Decision 4: Embedding generation is a backend maintenance concern

Embedding refresh should live behind a service/script that can be called after product create/update/import and run as a backfill. The embedding input text should be deterministic and locale-aware enough to support both English and Bulgarian content:

`name_en + name_bg + description_en + description_bg + product_type + category + labels + materials`

The preferred model should be multilingual, such as `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` or `intfloat/multilingual-e5-small`. The exact model should be configurable and stored with each embedding.

### Decision 5: Frontend consumes recommendations as a normal product list

The product detail page fetches the selected product and its recommendations server-side. It renders a localized "Suggested for you" section below the main detail content and before or near social proof, using existing product card/grid patterns.

If recommendations fail or return zero products, the section is omitted.

## Risks / Trade-offs

- Embedding dependency increases install/runtime complexity -> keep rule-only recommendations functional without embeddings.
- pgvector may not be enabled in every environment -> make the migration and query path tolerate a non-vector fallback where practical, or document pgvector as required for semantic scoring.
- Hybrid scores can feel arbitrary -> centralize score weights in one service and cover ordering behavior with tests.
- Product updates can leave stale embeddings -> track source text hash/model version and refresh when product content or taxonomy changes.
- Frontend and backend work can conflict on API shape -> define response models and fixture/mock updates early, then let UI work proceed against that contract.

## Migration Plan

1. Add schema for product embeddings and indexes.
2. Add backend service and route with rule-only ranking first.
3. Add embedding generation and hybrid scoring behind feature-safe fallbacks.
4. Add frontend API helper and product detail section.
5. Backfill embeddings for existing products.
6. Verify route, service, and product detail tests.

Rollback: remove or hide the product detail recommendations section first. The backend endpoint can remain unused. If needed, drop the embeddings table in a follow-up rollback migration.

## Parallel Work Plan

**Frontend owner — `product-recommendations-frontend`:** owns the product detail UI, API client helper, TypeScript types, mock API parity, localization, and frontend tests. This lane is intentionally frontend-only so the frontend engineer can move without database or service ownership.

**Backend Engineer A — `product-recommendations-api`:** owns the public route, response model, rule-based scoring, filtering, limit handling, and route/service tests. This gives a newer engineer a complete vertical API slice: model → service → route → tests.

**Backend Engineer B — `product-semantic-matching`:** owns embedding storage, source text hashing, refresh/backfill logic, semantic score calculation, safe fallbacks, and persistence/scoring tests. This gives a newer engineer a focused data/ML-adjacent slice: migration → persistence → algorithm → tests.

The shared handoff is the recommendation response contract. Backend Engineer A should land the response model and route signature early; the frontend owner can use mock data until the route is complete. Backend Engineer B can integrate semantic scoring behind the same service after rule-only recommendations work.
