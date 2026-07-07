## MODIFIED Requirements

### Requirement: Root layout provides global structure
The root layout (`frontend/app/layout.tsx`) SHALL wrap all pages with the global Header, Footer, and announcement bar components, and configure fonts (Playfair Display and Inter via next/font/google).

#### Scenario: Layout includes header and footer
- **WHEN** any page renders
- **THEN** the global Header renders above the page content and Footer renders below

#### Scenario: Layout includes announcement bar
- **WHEN** any page renders and the announcement has not been dismissed
- **THEN** the AnnouncementBar renders above the Header

#### Scenario: Fonts are loaded via next/font
- **WHEN** the app initializes
- **THEN** Playfair Display and Inter are loaded via next/font/google with font-display: swap and applied via CSS variables (`--font-playfair`, `--font-inter`). Layout applies both variables to `<html className={...}>`. `tailwind.config.ts` extends `fontFamily` to map `font-serif` → Playfair and `font-sans` → Inter using the CSS variables.

#### Scenario: Page content receives proper spacing
- **WHEN** any page renders
- **THEN** the `<main>` element in layout.tsx has NO max-width constraint. Each page controls its own width by wrapping content in `<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">`. Full-width sections (e.g., hero) live outside this wrapper at the page level.

## ADDED Requirements

### Requirement: Page routes exist for homepage and products
The frontend SHALL have routes for `/` (homepage), `/products` (listing), and `/products/[id]` (detail).

#### Scenario: Homepage route
- **WHEN** a user navigates to /
- **THEN** the homepage renders with hero and featured products

#### Scenario: Product listing route
- **WHEN** a user navigates to /products
- **THEN** the product listing page renders with grid and filters

#### Scenario: Product detail route
- **WHEN** a user navigates to /products/[id] (e.g., /products/lavender-dreams-300ml)
- **THEN** the product detail page renders for that product

### Requirement: Mock API integration in pages
Pages SHALL fetch data from the mock/real API layer (`frontend/lib/api.ts`) using the existing typed functions.

#### Scenario: Pages use api.ts switch layer
- **WHEN** pages fetch product data
- **THEN** they import from `lib/api.ts` which routes to mock or real based on `NEXT_PUBLIC_USE_MOCK_API` env var

#### Scenario: Type safety maintained
- **WHEN** pages consume API responses
- **THEN** all data is typed as `ProductResponse` or `ProductListResponse` from `lib/types.ts`

### Requirement: Shared price formatting utility
The frontend SHALL provide a shared `formatPrice(cents: number): string` function in `lib/utils.ts` used by all components displaying prices.

#### Scenario: Consistent price formatting
- **WHEN** any component displays a price
- **THEN** it uses the shared `formatPrice()` utility which formats price_cents as "€XX.XX" (euro prefix, period decimal separator, always two decimal places, e.g., 3200 → "€32.00", 100 → "€1.00"). Validates input: throws on negative/NaN/Infinity. Returns "€0.00" for 0. Period separator is intentional (English-language luxury brand aesthetic).

### Requirement: Loading and error boundaries at route level
Each route segment SHALL have corresponding `loading.tsx` and `error.tsx` files for graceful navigation and error handling.

#### Scenario: Route-level loading files exist
- **WHEN** a user navigates between routes
- **THEN** `app/loading.tsx`, `app/products/loading.tsx`, and `app/products/[id]/loading.tsx` display skeleton placeholders during the transition

#### Scenario: Route-level error boundaries exist
- **WHEN** a runtime error occurs on a products route
- **THEN** `app/products/error.tsx` (a Client Component with `'use client'`) receives `{ error, reset }` props, displays a branded error message with a retry button that calls `reset()` (re-renders the page, re-triggering server-side data fetch)

#### Scenario: Product detail not-found boundary
- **WHEN** `page.tsx` calls `notFound()` for an invalid or inactive product
- **THEN** `app/products/[id]/not-found.tsx` renders a branded "Product not found" message with a Link to /products
