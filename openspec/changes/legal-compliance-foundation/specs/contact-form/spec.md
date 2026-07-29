## ADDED Requirements

### Requirement: Contact form privacy notice
The localized contact form SHALL display a concise privacy notice near the submit button. The notice SHALL state that submitted contact details and message content are used to respond to the inquiry and SHALL link to the localized Privacy Policy.

#### Scenario: Contact privacy notice renders
- **WHEN** the contact page renders
- **THEN** the form displays a privacy notice with a link to `/privacy` through the localized Link component

#### Scenario: Notice appears before submission
- **WHEN** a visitor fills the contact form
- **THEN** the privacy notice is visible before the Send message button is submitted
