## ADDED Requirements

### Requirement: Product card uses the primary image
The product listing card SHALL render the product's `primary_image_url` (falling back to the gradient placeholder when it is null), replacing the removed single `image_url` field.

#### Scenario: Card renders primary image
- **WHEN** a product has a primary image
- **THEN** the card renders `primary_image_url` via next/image with the existing responsive `sizes`

#### Scenario: Card with no images
- **WHEN** a product has no images (`primary_image_url` is null)
- **THEN** the card renders the gradient placeholder with the product name
