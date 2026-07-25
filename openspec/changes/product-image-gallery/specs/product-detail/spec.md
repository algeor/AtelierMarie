## MODIFIED Requirements

### Requirement: Product image display with next/image
The system SHALL render a product image gallery on the detail page using next/image, showing the primary image prominently with the remaining images selectable, all in `sort_order`.

#### Scenario: Gallery with multiple images
- **WHEN** a product has multiple images
- **THEN** the primary image renders large (via next/image, `sizes="(max-width: 1024px) 100vw, 50vw"`, aspect ratio 4:5, `priority` loading) and the other images render as selectable thumbnails in `sort_order`; selecting one shows it in the main view

#### Scenario: Single image
- **WHEN** a product has exactly one image
- **THEN** that image renders large with no additional thumbnails

#### Scenario: Gradient placeholder for no images
- **WHEN** a product has no images OR the primary image fails to load (404/timeout)
- **THEN** a large CSS gradient placeholder renders (warm-ivory → dusty-pink, 135deg) with the product name centered in Playfair Display, using `role="img"` and `aria-label={product.name}`
