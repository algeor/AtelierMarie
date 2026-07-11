## Context

The frontend is a Next.js 14 App Router application with a complete shopping flow (products, cart, checkout, order confirmation). There is no admin UI yet. The backend has admin endpoints (`/v1/admin/*`) for product CRUD, order management, and stats. The `UserResponse` type already includes `is_admin: boolean`. Mock API includes a `MOCK_USER` with `is_admin: true`.

The storefront uses a luxury palette (warm-ivory, cream, champagne-beige, dusty-pink, soft-brown, charcoal, muted-gold) with Playfair Display headings and Inter body text. The admin UI will reuse these tokens but with a more functional, data-dense layout appropriate for back-office work.

## Goals / Non-Goals

**Goals:**
- Admin layout with sidebar navigation (Dashboard, Products, Orders) separate from the storefront header/footer
- Dashboard with at-a-glance business metrics
- Full product management (list, create, edit, deactivate) with image upload
- Order management with status filtering and inline status updates
- Route protection: redirect non-admin users to login

**Non-Goals:**
- Real-time updates (polling or websockets) — manual refresh is sufficient
- Customer management / user list
- Analytics / Layer 2 integration
- Mobile-optimized admin (desktop-first; responsive but not mobile-priority)
- Bulk operations (batch delete, batch status update)

## Decisions

### 1. Separate layout at `/admin` path with sidebar navigation
**Rationale:** Admin pages have fundamentally different navigation needs (sidebar with sections) vs storefront (top nav with cart). Using a nested layout at `app/admin/layout.tsx` gives a clean separation without affecting the storefront layout.
**Alternative considered:** Modal/overlay admin panel — rejected because admin tasks are complex enough to need full pages.

### 2. Client-side route protection with auth context
**Rationale:** Check `is_admin` from an auth context/hook. If not admin, redirect to `/` (or a login page when it exists). This matches the existing client component pattern used for the cart context. Server-side protection would be ideal but requires cookie-based auth parsing in middleware — deferred to a future iteration.
**Alternative considered:** Next.js middleware redirect — would need to parse JWT/session cookie server-side, adding complexity. Client-side is pragmatic for now since the backend still enforces auth on API calls.

### 3. Mock API extensions for admin endpoints
**Rationale:** The frontend already uses a mock API toggled by env var. Extending it for admin endpoints (stats, product CRUD, order updates) keeps the frontend independently developable without the backend running.
**Alternative considered:** Only real API — rejected because it couples frontend development to backend availability.

### 4. Data tables as custom components (not a library)
**Rationale:** The admin has simple tables (products: ~20-100 rows, orders: paginated). A lightweight custom table component with sorting/filtering is sufficient. Adding a table library (TanStack Table, AG Grid) is overkill for this scale.
**Alternative considered:** TanStack Table — powerful but heavy dependency for what's essentially < 100 rows per page.

### 5. Image upload as URL input (not file upload)
**Rationale:** The backend doesn't have a file upload endpoint yet. For now, the product form accepts an image URL. File upload with a proper storage backend (local disk or S3-compatible) will come in a future iteration.
**Alternative considered:** File upload to `/v1/admin/products/upload` — requires backend work not in scope for this change.

## Risks / Trade-offs

- **[Client-side auth only]** → Admin API calls still require valid admin credentials on the backend, so a non-admin user seeing the admin layout briefly before redirect is cosmetic only, not a security risk.
- **[No real-time data]** → Stats may be stale; mitigated by showing "last updated" timestamp and a refresh button.
- **[Image URL instead of upload]** → Less user-friendly for non-technical users; acceptable for the business owner who can host images or use the future upload feature.
