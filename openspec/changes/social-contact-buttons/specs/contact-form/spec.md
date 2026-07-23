## ADDED Requirements

### Requirement: Localized contact page with submission form
The system SHALL provide a localized contact page at `/{locale}/contact` for supported locales (`en`, `bg`) containing a form with fields for name, email address, and message. Requests to `/contact` SHALL continue through the existing locale middleware and redirect to the detected localized route.

#### Scenario: Contact page renders localized form
- **WHEN** a visitor navigates to `/en/contact` or `/bg/contact`
- **THEN** the page displays localized heading/body text and a form with labeled fields for name, email, and message

#### Scenario: Unprefixed contact path uses locale middleware
- **WHEN** a visitor navigates to `/contact`
- **THEN** the existing middleware redirects them to `/{detected-locale}/contact`

#### Scenario: Form requires all human-visible fields
- **WHEN** a visitor attempts to submit the form with name, email, or message empty after trimming whitespace
- **THEN** the form displays inline validation errors and does not submit the request

#### Scenario: Form validates email format
- **WHEN** a visitor enters an invalid email address and attempts to submit
- **THEN** the form displays an inline validation error on the email field

#### Scenario: Form preserves entered data on failure
- **WHEN** `POST /v1/contact` returns a non-success response such as 429 or 5xx
- **THEN** the form displays a user-safe error message and keeps the entered name, email, and message values

#### Scenario: Successful form submission
- **WHEN** a visitor fills all fields with valid data and submits
- **THEN** the form posts to `POST /v1/contact`, displays a localized success message, and clears the visible fields

#### Scenario: Form is accessible
- **WHEN** a keyboard or screen-reader user interacts with the contact form
- **THEN** all controls are reachable in logical order, labels are associated with inputs, validation errors are announced or referenced with ARIA attributes, and the submit button is keyboard-activatable

### Requirement: Contact page has an elegant storefront-native presentation
The contact page SHALL use the existing Atelier Marie storefront design system with restrained typography, generous spacing, accessible form states, and a layout that supports direct customer action without decorative clutter.

#### Scenario: Desktop layout is balanced and useful
- **WHEN** the contact page renders on a desktop viewport
- **THEN** the main content uses a two-column layout with short contextual copy and direct contact/social links in one column and the contact form in the other
- **AND** the page avoids oversized hero treatment, decorative gradients, nested cards, and card-heavy marketing composition

#### Scenario: Mobile layout stacks cleanly
- **WHEN** the contact page renders on a mobile viewport
- **THEN** the contextual copy, direct links, and form stack in a single readable column without overlapping text or controls

#### Scenario: Form styling matches the storefront
- **WHEN** the contact form renders
- **THEN** fields, labels, helper/error text, focus states, and the submit button use the existing storefront color, typography, border, and spacing conventions

#### Scenario: Success and error states stay calm
- **WHEN** the form shows a success or submission-error state
- **THEN** the message is inline, readable, and visually consistent with the rest of the page without modal popups or disruptive decoration

### Requirement: Backend contact endpoint persists accepted messages
The system SHALL expose `POST /v1/contact` accepting JSON contact submissions with `name`, `email`, `message`, `locale`, and optional hidden honeypot field `website`. Valid non-honeypot submissions SHALL be persisted before any email delivery attempt.

#### Scenario: Valid submission is persisted and queued
- **WHEN** a valid contact request is received with empty or absent `website`
- **THEN** the system inserts a `contact_messages` row with the submitted name, email, message, locale, IP address when available, `email_status='queued'`, and a creation timestamp
- **AND** the endpoint returns HTTP 201 with a received status

#### Scenario: Missing required fields returns validation error
- **WHEN** a contact request is missing name, email, or message
- **THEN** the system returns HTTP 422 with validation error details

#### Scenario: Invalid email format returns validation error
- **WHEN** a contact request contains an invalid email value
- **THEN** the system returns HTTP 422 with a validation error for email

#### Scenario: Invalid locale returns validation error
- **WHEN** a contact request contains a locale other than `en` or `bg`
- **THEN** the system returns HTTP 422 with a validation error for locale

#### Scenario: Honeypot field silently drops bot submission
- **WHEN** a contact request includes a non-empty `website` value
- **THEN** the system returns HTTP 201 with the same user-facing success shape
- **AND** no contact message is persisted and no email is queued

#### Scenario: Rate limiting prevents repeated submissions
- **WHEN** the same IP address has already made 5 accepted contact submissions within the last rolling hour
- **THEN** the next non-honeypot submission returns HTTP 429 with a user-safe error
- **AND** no additional contact message is persisted

### Requirement: Contact notifications use durable email delivery
The system SHALL deliver owner notifications for accepted contact messages through the existing email provider and template architecture, using a durable contact-message queue state rather than FastAPI `BackgroundTasks` or the order-specific `order_emails` table.

#### Scenario: Queued contact email is sent by sweeper
- **WHEN** a contact message row has `email_status='queued'`
- **AND** the email outbox drain runs
- **THEN** the system renders the `contact_message` template, sends it through the configured email provider, and marks the row sent with sent timestamp/provider result

#### Scenario: Owner recipient uses admin notification email
- **WHEN** a contact notification is sent
- **THEN** the recipient is `settings.admin_notification_email`
- **AND** no separate contact-recipient setting is required

#### Scenario: Reply-To uses submitter email
- **WHEN** the contact notification is sent
- **THEN** the provider call sets `reply_to` to the submitter's email address

#### Scenario: Missing owner recipient does not fail visitor submission
- **WHEN** `ADMIN_NOTIFICATION_EMAIL` is not configured
- **THEN** accepted contact messages are still persisted
- **AND** the email delivery state records a skipped/no-recipient or terminal failure reason without returning an error to the visitor

#### Scenario: Provider failure does not lose message
- **WHEN** email delivery fails because of provider/network/template failure
- **THEN** the contact message remains persisted
- **AND** retryable failures remain eligible for a later drain with incremented attempts/backoff
- **AND** permanent failures are marked terminal and logged

#### Scenario: Concurrent drain sends at most once
- **WHEN** two app workers attempt to drain the same queued contact message
- **THEN** a SQLite-backed claim prevents duplicate owner notification sends

#### Scenario: Contact templates are localized
- **WHEN** a contact notification is rendered for locale `en` or `bg`
- **THEN** the system renders `app/email/templates/{locale}/contact_message.txt`, falling back according to the existing renderer behavior if needed
