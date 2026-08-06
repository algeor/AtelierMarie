## ADDED Requirements

### Requirement: Products page accepts category deep links
The products page SHALL accept a category/type selection from the URL so homepage category entries can navigate directly to filtered product results. The selected value SHALL initialize the existing client-side filter state and remain keyboard/screen-reader accessible.

#### Scenario: Category query initializes filter
- **WHEN** a visitor opens `/[locale]/products` with a supported category/type query parameter
- **THEN** the product listing initializes with the matching category/type selected
- **AND** only matching products are shown until the visitor changes or clears the filter

#### Scenario: Invalid category query falls back safely
- **WHEN** a visitor opens the products page with an unsupported category/type query parameter
- **THEN** the page falls back to the default `All` product view without throwing an error

### Requirement: Product listing preserves existing filtering and commerce behavior
The products page SHALL preserve existing product grid, filtering, sorting/search where present, product card, pricing/discount, image/placeholder, empty, loading, and error behavior after the rebrand.

#### Scenario: Existing category pills still work
- **WHEN** a visitor selects a category pill on the products page
- **THEN** the product grid updates as before and the selected state remains visible and accessible

#### Scenario: Product cards retain commerce information
- **WHEN** product cards render after the rebrand
- **THEN** they continue to show product image or placeholder, product name, effective price/discount state, and detail-page navigation

### Requirement: Product cards use restrained luxury motion
Product cards MAY use subtle hover/focus motion such as image settling, slight zoom, or warm shadow/glow, but SHALL NOT obscure price, stock, discount, product safety, or add-to-cart related information.

#### Scenario: Reduced motion disables product card motion
- **WHEN** the user has `prefers-reduced-motion: reduce` enabled
- **THEN** product card decorative motion is disabled or reduced

#### Scenario: Product card motion preserves layout
- **WHEN** a product card is hovered or focused
- **THEN** the card animation does not resize the grid or cause neighboring cards to shift
