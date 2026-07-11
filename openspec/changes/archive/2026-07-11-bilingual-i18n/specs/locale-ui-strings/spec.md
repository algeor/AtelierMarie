## ADDED Requirements

### Requirement: UI strings translated via message files
The system SHALL maintain JSON translation files (`messages/en.json`, `messages/bg.json`) containing all static UI strings (navigation, buttons, labels, form text, error display messages, announcement bar text).

#### Scenario: Navigation renders in Bulgarian
- **WHEN** a user views a page under `/bg/...`
- **THEN** navigation links show "Начало", "Магазин" (not "Home", "Shop")

#### Scenario: Navigation renders in English
- **WHEN** a user views a page under `/en/...`
- **THEN** navigation links show "Home", "Shop"

#### Scenario: Add to cart button in Bulgarian
- **WHEN** a user views a product page under `/bg/...`
- **THEN** the add-to-cart button shows "Добави в кошницата"

### Requirement: API error codes mapped to localized display text
The system SHALL map backend error codes (e.g., `CART_EMPTY`, `INSUFFICIENT_STOCK`) to localized user-facing messages in the active locale. The backend API SHALL always return English error codes regardless of locale.

#### Scenario: Out of stock error displayed in Bulgarian
- **WHEN** the API returns `{"error": {"code": "INSUFFICIENT_STOCK"}}` and user is on `/bg/...`
- **THEN** the frontend displays "Недостатъчна наличност" (or equivalent BG text)

#### Scenario: Out of stock error displayed in English
- **WHEN** the API returns `{"error": {"code": "INSUFFICIENT_STOCK"}}` and user is on `/en/...`
- **THEN** the frontend displays "Insufficient stock"

### Requirement: All user-facing surfaces use translation system
The system SHALL use the translation system for ALL user-facing text including: announcement bar, header, footer, product UI, cart, checkout, orders, admin panel, auth pages, and account pages. No hardcoded user-facing strings outside of translation files.

#### Scenario: Announcement bar translated
- **WHEN** a user views any page under `/bg/...`
- **THEN** the announcement bar content renders in Bulgarian

#### Scenario: Footer translated
- **WHEN** a user views any page under `/en/...`
- **THEN** the footer content renders in English
