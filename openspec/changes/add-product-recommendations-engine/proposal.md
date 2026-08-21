## Why

Product detail pages should help shoppers discover relevant items without requiring manual merchandising for every product. A reusable recommendations foundation also gives the store a path toward semantic product search using the same product embeddings later.

## What Changes

- Add a public product recommendations API that returns active products related to a selected product.
- Rank recommendations with a hybrid score: deterministic product rules first, then optional embedding similarity when product embeddings exist.
- Store generated product embeddings in Postgres so recommendations and future semantic search can reuse the same vectors.
- Add a storefront "Suggested for you" section below product details using the existing product card/grid patterns.
- Add operational support to refresh product embeddings when product text or taxonomy changes.
- No breaking API changes.

## Capabilities

### New Capabilities
- `product-recommendations-frontend`: Storefront "Suggested for you" UI, frontend API client behavior, localization, and graceful empty/error states.
- `product-recommendations-api`: Public recommendations endpoint, response contract, deterministic rule ranking, filtering, and API/service tests.
- `product-semantic-matching`: Product embedding persistence, embedding refresh, semantic similarity scoring, and future search reuse.

### Modified Capabilities
- None.

## Impact

- Backend: product recommendation service, product recommendations route, product embedding persistence, embedding refresh script/service, tests.
- Database: new product embeddings table and optional pgvector extension/index when available.
- Frontend: API client helper, localized strings, product detail recommendations section, frontend tests.
- Dependencies: sentence-transformers-compatible embedding generation path or configurable provider; pgvector support preferred but fallback storage/query behavior should keep local development workable.
