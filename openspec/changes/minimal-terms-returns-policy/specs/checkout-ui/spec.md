## ADDED Requirements

### Requirement: Checkout legal disclosure
The checkout page SHALL display a small legal disclosure near every visible Place Order button. The disclosure SHALL link to `/[locale]/terms` and SHALL state that placing an order means the customer agrees to the Terms & Conditions, including delivery, withdrawal, and returns information.

#### Scenario: Desktop checkout shows disclosure
- **WHEN** a customer views checkout on a desktop viewport with items in cart
- **THEN** a legal disclosure is visible near the desktop Place Order button
- **AND** the Terms & Conditions text links to the localized terms page

#### Scenario: Mobile checkout shows disclosure
- **WHEN** a customer views checkout on a mobile viewport with items in cart
- **THEN** a legal disclosure is visible near the mobile Place Order button
- **AND** the Terms & Conditions text links to the localized terms page

#### Scenario: Disclosure remains quiet
- **WHEN** the checkout page renders
- **THEN** the disclosure uses subdued styling compared with form labels and the primary order button
- **AND** it does not advertise returns as a commercial benefit

#### Scenario: Disclosure is present before submit
- **WHEN** a customer is ready to place an order
- **THEN** the disclosure is visible before order submission without requiring a separate modal or hidden accordion
