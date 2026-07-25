## MODIFIED Requirements

### Requirement: CSV import supports dual-language columns
The `POST /v1/admin/products/import` endpoint SHALL accept CSV files with columns `name_en`, `name_bg`, `description_en`, `description_bg`. The `name_en` column is required; BG columns are optional. The endpoint SHALL determine which rows are inserts vs. updates by pre-fetching all existing product IDs in a single `SELECT id FROM products WHERE id = ANY($1::text[])` query, and SHALL perform inserts/updates using PostgreSQL `INSERT ... ON CONFLICT (id) DO UPDATE SET ...` (upsert). Per-row errors SHALL be reported without aborting the batch.

#### Scenario: Import CSV with both languages
- **WHEN** admin uploads a CSV with `name_en`, `name_bg`, `description_en`, `description_bg` columns
- **THEN** products are created or upserted via `INSERT ... ON CONFLICT (id) DO UPDATE` with content in both languages

#### Scenario: Import CSV with English only
- **WHEN** admin uploads a CSV with only `name_en` and `description_en` columns
- **THEN** products are created with BG fields as NULL

#### Scenario: Duplicate SKU updates existing row
- **WHEN** admin uploads a CSV row with `id` matching an existing product
- **THEN** the existing row is updated via the ON CONFLICT clause, `updated_at` is refreshed, and the per-row result reports `action="updated"`

#### Scenario: Malformed row does not abort batch
- **WHEN** row 42 of a 500-row CSV fails validation (missing required `name_en`) but rows 1–41 and 43–500 are valid
- **THEN** rows 1–41 and 43–500 are upserted successfully, row 42 is reported in the response's `errors` array with `row_number=42`, and the transaction for the successful rows commits
