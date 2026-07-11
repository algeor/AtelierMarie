## ADDED Requirements

### Requirement: Product content stored in both languages
The system SHALL store product name and description in both English and Bulgarian using suffixed columns (`name_en`, `name_bg`, `description_en`, `description_bg`) in the products table.

#### Scenario: Product has both translations
- **WHEN** a product has `name_en = "Lavender Dream"` and `name_bg = "Лавандулов сън"`
- **THEN** both values are stored and retrievable independently

### Requirement: Locale-aware product content retrieval
The system SHALL return product content in the requested locale. If the requested locale's content is NULL or empty, the system SHALL fall back to the other language's content.

#### Scenario: Retrieve product in Bulgarian
- **WHEN** a client requests a product with `locale=bg` and the product has `name_bg = "Лавандулов сън"`
- **THEN** the response includes `name: "Лавандулов сън"` and `description` from `description_bg`

#### Scenario: Fallback when Bulgarian translation missing
- **WHEN** a client requests a product with `locale=bg` and `name_bg` is NULL
- **THEN** the response includes `name` from `name_en` (fallback to English)

#### Scenario: Fallback when English translation missing
- **WHEN** a client requests a product with `locale=en` and `name_en` is NULL
- **THEN** the response includes `name` from `name_bg` (fallback to Bulgarian)

### Requirement: Translation staleness tracking
The system SHALL track whether each language's translation is stale relative to the other. When content in one language is updated, the other language SHALL be flagged as stale.

#### Scenario: English update flags Bulgarian as stale
- **WHEN** an admin updates `description_en` for a product
- **THEN** `translation_stale_bg` is set to true for that product

#### Scenario: Bulgarian update flags English as stale
- **WHEN** an admin updates `name_bg` for a product
- **THEN** `translation_stale_en` is set to true for that product

#### Scenario: Updating stale side clears the flag
- **WHEN** an admin updates `description_bg` for a product that has `translation_stale_bg = true`
- **THEN** `translation_stale_bg` is set to false

### Requirement: Product search respects locale
The system SHALL search products using the FTS index corresponding to the active locale. Bulgarian locale searches the Bulgarian FTS index; English locale searches the English FTS index.

#### Scenario: Search in Bulgarian
- **WHEN** a user searches for "лавандула" with `locale=bg`
- **THEN** the system queries the Bulgarian FTS index and returns matching products

#### Scenario: Search in English
- **WHEN** a user searches for "lavender" with `locale=en`
- **THEN** the system queries the English FTS index and returns matching products
