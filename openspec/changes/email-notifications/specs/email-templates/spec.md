## ADDED Requirements

### Requirement: Bilingual email templates rendered via Jinja2

The system SHALL render email content from Jinja2 template files organized by locale (en/bg). Each template file contains the subject on the first line, a blank line separator, and the email body.

#### Scenario: English template rendered for EN locale

- **WHEN** an email is triggered for an order with locale "en"
- **THEN** the system loads the template from `app/email/templates/en/{event}.txt` and renders it with order context

#### Scenario: Bulgarian template rendered for BG locale

- **WHEN** an email is triggered for an order with locale "bg"
- **THEN** the system loads the template from `app/email/templates/bg/{event}.txt` and renders it with order context

#### Scenario: Locale fallback to English

- **WHEN** a template file does not exist for the requested locale (e.g., `bg/order_delivered.txt` missing)
- **THEN** the system falls back to the English template (`en/order_delivered.txt`) and logs a warning

#### Scenario: Both locale templates missing

- **WHEN** neither the requested locale template nor the English fallback exists
- **THEN** the email is not sent and an error is logged with template path and event name

### Requirement: Template files use subject-in-first-line format

Each template `.txt` file SHALL have the email subject on the first line, followed by a blank line, followed by the body content.

#### Scenario: Subject extracted from template

- **WHEN** a template is rendered
- **THEN** the first line becomes the email subject and the remaining content becomes the body

#### Scenario: Template with Jinja2 variables in subject

- **WHEN** a template subject line contains `{{ order_id_short }}`
- **THEN** the variable is interpolated in the rendered subject

### Requirement: Order placed template contains order summary

The "order_placed" template SHALL include customer greeting, item list with quantities and prices, and order total.

#### Scenario: Order placed email with multiple items

- **WHEN** an order is placed with 3 items
- **THEN** the email body lists all 3 items with product name, quantity, and line price

#### Scenario: Order placed email without customer name

- **WHEN** the customer did not provide a name (customer_name is None)
- **THEN** the greeting uses a generic fallback (e.g., "Hi there" / "Здравейте")

### Requirement: Shipped template includes tracking information

The "order_shipped" template SHALL include tracking carrier, tracking number, and tracking URL when available.

#### Scenario: Shipped email with full tracking

- **WHEN** order is shipped with carrier="Speedy", number="123", url="https://speedy.bg/..."
- **THEN** the email body displays carrier name, tracking number, and a clickable tracking URL

#### Scenario: Shipped email with carrier but no URL

- **WHEN** order is shipped with carrier="other" and tracking_url is None
- **THEN** the email body shows carrier and tracking number but omits the tracking link section

### Requirement: Template context includes formatted prices

The system SHALL convert price_cents to locale-appropriate display strings before passing to templates. Templates SHALL NOT perform price arithmetic.

#### Scenario: English locale price format

- **WHEN** locale is "en" and total_cents is 4500
- **THEN** total_display is "€45.00"

#### Scenario: Bulgarian locale price format

- **WHEN** locale is "bg" and total_cents is 4500
- **THEN** total_display is "45.00 лв"

### Requirement: All order transition templates exist in English

The system SHALL include English templates for all 5 order transitions plus the admin alert.

#### Scenario: All EN templates present

- **WHEN** the application is deployed
- **THEN** the following template files exist: `en/order_placed.txt`, `en/order_confirmed.txt`, `en/order_shipped.txt`, `en/order_delivered.txt`, `en/order_cancelled.txt`, `en/admin_new_order.txt`

### Requirement: All order transition templates exist in Bulgarian

The system SHALL include Bulgarian templates for all 5 customer-facing order transitions.

#### Scenario: All BG templates present

- **WHEN** the application is deployed
- **THEN** the following template files exist: `bg/order_placed.txt`, `bg/order_confirmed.txt`, `bg/order_shipped.txt`, `bg/order_delivered.txt`, `bg/order_cancelled.txt`
