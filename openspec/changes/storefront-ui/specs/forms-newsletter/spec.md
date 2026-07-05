# Forms & Newsletter — Spec

## ADDED Requirements

### Requirement: Contact Form

A contact form allows customers to reach the brand with inquiries, with client-side validation ensuring data quality before submission.

#### Scenario: Contact form renders all fields

WHEN a user navigates to the contact page
THEN a form is displayed with the following fields: Name (text input, required), Email (email input, required), Phone (tel input, optional), Message (textarea, required)
AND a "Send message" submit button is displayed
AND required fields are indicated (asterisk or label text)

#### Scenario: Client-side validation prevents invalid submission

WHEN a user attempts to submit the form with empty required fields
THEN inline error messages appear below each invalid field (e.g., "Name is required", "Please enter a valid email", "Message is required")
AND the form does not submit
AND the first invalid field receives focus

#### Scenario: Email format validation

WHEN a user enters an invalid email format (e.g., "abc", "abc@", "abc@.", "@domain.com")
THEN an inline error message appears: "Please enter a valid email address"
WHEN the user corrects the email to a valid format (e.g., "user@example.com")
THEN the error message disappears

#### Scenario: Successful form submission

WHEN a user fills all required fields with valid data and clicks submit
THEN the form data is sent to POST /v1/contact
AND a success confirmation replaces the form (e.g., "Thank you! We'll get back to you soon.")
AND a contact_submit event is emitted with form data context

#### Scenario: Form submission error handling

WHEN the form submission request fails (network error or server error)
THEN an error message is displayed above the form (e.g., "Something went wrong. Please try again.")
AND the form data is preserved (user does not lose their input)
AND the user can retry submission

### Requirement: Newsletter Signup

A newsletter signup section captures email addresses for marketing communications with a clear value proposition and success feedback.

#### Scenario: Newsletter section renders with copy and input

WHEN the newsletter section is displayed (on homepage and/or footer)
THEN it shows the copy: "Join Atelier Marie for new releases, gift ideas, seasonal collections and special offers."
AND an email input field with placeholder text (e.g., "Enter your email")
AND a "Subscribe" button

#### Scenario: Newsletter signup succeeds

WHEN a user enters a valid email address and clicks Subscribe
THEN the email is submitted to POST /v1/newsletter/subscribe
AND the input and button are replaced with a success message (e.g., "Welcome to Atelier Marie! Check your inbox.")
AND a newsletter_signup event is emitted with the email

#### Scenario: Newsletter signup with invalid email

WHEN a user clicks Subscribe with an empty or invalid email
THEN an inline error appears: "Please enter a valid email address"
AND the form does not submit

#### Scenario: Newsletter signup handles duplicate email

WHEN a user submits an email that is already subscribed
THEN a friendly message is shown (e.g., "You're already part of our community!")
AND no error state is displayed (graceful handling)

### Requirement: Event Emission for Forms

Form interactions emit analytics events for tracking conversion funnel activity.

#### Scenario: contact_submit event is emitted

WHEN the contact form is successfully submitted
THEN a contact_submit event is emitted
AND the event payload includes: form context (page, timestamp)

#### Scenario: newsletter_signup event is emitted

WHEN the newsletter form is successfully submitted
THEN a newsletter_signup event is emitted
AND the event payload includes: email (hashed or partial for privacy) and source (homepage, footer, etc.)
