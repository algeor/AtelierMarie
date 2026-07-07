## ADDED Requirements

### Requirement: Seed script populates sample candle products
The system SHALL provide a `scripts/seed_products.py` script that populates the database with approximately 10 sample candle products across multiple categories. The script SHALL be idempotent (safe to run multiple times — uses upsert semantics). The products SHALL have realistic names, descriptions, prices, and stock levels matching the luxury candle brand aesthetic.

#### Scenario: Run seed script on empty database
- **WHEN** `python scripts/seed_products.py` is run against an empty database
- **THEN** approximately 10 products are inserted with realistic candle data across categories (dessert, luxury-jar, gift-set, seasonal)

#### Scenario: Run seed script on already-seeded database
- **WHEN** `python scripts/seed_products.py` is run against a database that already contains the seed products
- **THEN** existing products are updated (upsert), no duplicates are created, and no errors occur

#### Scenario: Seed products have valid data
- **WHEN** the seed script completes
- **THEN** every seeded product has: a kebab-case slug ID, a non-empty name, price_cents > 0, stock >= 0, is_active=1, a category, and a description

### Requirement: Seed script uses the product service
The seed script SHALL import and use the product service's `upsert_product` method (not raw SQL) to create/update products. This validates the service layer works end-to-end and ensures idempotency.

#### Scenario: Service layer validation applies
- **WHEN** the seed script runs
- **THEN** all products pass the same validation that the API enforces (valid price, non-negative stock, non-empty name)

#### Scenario: Upsert semantics via service
- **WHEN** the seed script runs on a database with existing seed products
- **THEN** existing products are updated via `upsert_product`, no DuplicateError is raised
