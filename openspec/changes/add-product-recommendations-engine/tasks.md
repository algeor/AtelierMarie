## 1. Shared Contract Setup

- [ ] 1.1 Backend Engineer A defines the public recommendation response model using the existing product list/product response conventions
- [ ] 1.2 Frontend owner adds the matching TypeScript helper signature and mock response shape
- [ ] 1.3 All owners confirm the endpoint contract: `GET /v1/products/{product_id}/recommendations?locale=<locale>&limit=<n>`

## 2. Frontend Owner: Product Recommendations UI

- [ ] 2.1 Add `getProductRecommendations(productId, locale, limit)` to `frontend/lib/api.ts`
- [ ] 2.2 Add mock API recommendation behavior with deterministic products for local development
- [ ] 2.3 Add English and Bulgarian localized strings for the "Suggested for you" section
- [ ] 2.4 Update the product detail page to fetch recommendations without blocking selected product rendering
- [ ] 2.5 Render recommended products below the main detail content using existing product card/grid conventions
- [ ] 2.6 Omit the section when recommendations are empty or fail to load
- [ ] 2.7 Add frontend tests for visible recommendations, empty omission, failure omission, localized heading, and card navigation

## 3. Backend Engineer A: Recommendations API and Rule Scoring

- [ ] 3.1 Add backend Pydantic response model for product recommendations
- [ ] 3.2 Implement candidate loading that excludes the selected product, inactive products, and products not eligible for public detail
- [ ] 3.3 Implement deterministic scoring from product type, category, shared labels, stock/orderability, featured status, freshness, and stable tie-breaks
- [ ] 3.4 Implement `recommend_products(product_id, locale, limit)` service behavior using rule-only scoring first
- [ ] 3.5 Add public `GET /v1/products/{product_id}/recommendations` route with bounded limit validation and not-found handling
- [ ] 3.6 Add route and service tests for success, not found, inactive exclusion, selected-product exclusion, empty candidates, limit bounding, and ranking
- [ ] 3.7 Coordinate with Backend Engineer B on the extension point where semantic score will be added later

## 4. Backend Engineer B: Embeddings and Semantic Matching

- [ ] 4.1 Add Alembic migration for product embedding persistence with product ID, embedding model, vector payload, source text hash, and timestamps
- [ ] 4.2 Implement deterministic embedding input builder from names, descriptions, product type, category, labels, and materials
- [ ] 4.3 Implement source text hashing and stale-embedding detection
- [ ] 4.4 Add embedding refresh/backfill service or script that is repeatable for unchanged products
- [ ] 4.5 Implement cosine similarity or pgvector-backed similarity for compatible embeddings
- [ ] 4.6 Integrate semantic score into Backend Engineer A's recommendation scoring extension point while preserving rule-only fallback
- [ ] 4.7 Add tests for embedding persistence, stale detection, refresh idempotency, compatible model scoring, incompatible model exclusion, and missing-provider fallback

## 5. Integration and Verification

- [ ] 5.1 Run backend recommendation API tests and existing product service/search tests
- [ ] 5.2 Run frontend product detail and product card/grid tests in mock mode
- [ ] 5.3 Verify the real API product detail page renders recommended products when candidates exist
- [ ] 5.4 Run OpenSpec status/validation checks for this change
- [ ] 5.5 Document operational notes for refreshing embeddings and configuring the embedding model
