## ADDED Requirements

### Requirement: Contact page with submission form
The system SHALL provide a contact page at `/contact` containing a form with fields for name, email address, and message, allowing visitors to send inquiries to the shop owner.

#### Scenario: Contact page renders with form
- **WHEN** a visitor navigates to `/contact`
- **THEN** the page displays a heading ("Contact Us" or "Get in Touch"), a brief intro paragraph, and a form with labeled fields for name (text input), email (email input), and message (textarea)

#### Scenario: Form requires all fields
- **WHEN** a visitor attempts to submit the form with any field empty
- **THEN** the form displays inline validation errors for the empty fields and does NOT submit

#### Scenario: Form validates email format
- **WHEN** a visitor enters an invalid email address and attempts to submit
- **THEN** the form displays an inline validation error on the email field indicating the format is invalid

#### Scenario: Successful form submission
- **WHEN** a visitor fills all fields with valid data and submits
- **THEN** the form submits to `POST /v1/contact`, displays a success message ("Thank you! We'll get back to you soon."), and clears the form fields

#### Scenario: Form shows error on submission failure
- **WHEN** the backend returns an error (5xx or rate limit 429)
- **THEN** the form displays a user-friendly error message ("Something went wrong. Please try again later.") without clearing the entered data

#### Scenario: Form is accessible
- **WHEN** a keyboard user interacts with the contact form
- **THEN** all fields are focusable in logical order, labels are associated with inputs via `htmlFor`/`id`, and the submit button is keyboard-activatable

### Requirement: Backend contact endpoint receives and delivers messages
The system SHALL expose a `POST /v1/contact` endpoint that validates the submission, persists it to the database, and sends an email notification to the configured owner address.

#### Scenario: Valid submission is persisted and emailed
- **WHEN** a valid POST request is received with `name`, `email`, and `message` fields
- **THEN** the system persists the message to the `contact_messages` table, sends an email to the configured `CONTACT_EMAIL` address, and returns HTTP 201 with `{"status": "sent"}`

#### Scenario: Missing required fields returns 422
- **WHEN** a POST request is missing any of the required fields (name, email, message)
- **THEN** the system returns HTTP 422 with validation error details

#### Scenario: Invalid email format returns 422
- **WHEN** a POST request contains an email field that is not a valid email address
- **THEN** the system returns HTTP 422 with a validation error for the email field

#### Scenario: Rate limiting prevents spam
- **WHEN** the same IP address submits more than 5 contact messages within one hour
- **THEN** the system returns HTTP 429 with `{"detail": "Too many requests. Please try again later."}`

#### Scenario: Email delivery failure does not lose the message
- **WHEN** email delivery fails (SMTP error, timeout)
- **THEN** the message remains persisted in the database, the error is logged, and the endpoint still returns HTTP 201 (message is saved even if email is delayed)

#### Scenario: Honeypot field catches bots
- **WHEN** a POST request includes a non-empty value for the hidden `website` field (honeypot)
- **THEN** the system returns HTTP 201 (pretends success) but does NOT persist or email the submission

### Requirement: Contact messages stored in database
The system SHALL persist all valid contact form submissions in a `contact_messages` table for audit and admin review.

#### Scenario: Message schema
- **WHEN** a contact message is persisted
- **THEN** the record contains: `id` (auto-increment), `name` (text), `email` (text), `message` (text), `ip_address` (text), `created_at` (ISO timestamp), `email_sent` (boolean)

#### Scenario: Admin can view messages (future)
- **WHEN** the admin dashboard is extended
- **THEN** contact messages are queryable from the `contact_messages` table with newest first
