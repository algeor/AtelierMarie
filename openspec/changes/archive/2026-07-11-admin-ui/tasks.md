## 1. Admin Layout & Auth

- [ ] 1.1 Create admin auth context/hook (`useAdmin`) that checks `is_admin` and provides user state
- [ ] 1.2 Create `AdminGuard` component that redirects non-admin users to `/`
- [ ] 1.3 Create admin sidebar component with navigation links (Dashboard, Products, Orders)
- [ ] 1.4 Create `app/admin/layout.tsx` with sidebar, AdminGuard, and main content area
- [ ] 1.5 Add responsive sidebar behavior (collapsed on tablet, expanded on desktop)

## 2. Admin Dashboard

- [ ] 2.1 Add admin stats types to `lib/types.ts` (AdminStats interface)
- [ ] 2.2 Add admin stats endpoint to mock API and API client
- [ ] 2.3 Create `StatsCard` component (icon, label, value)
- [ ] 2.4 Create `app/admin/page.tsx` dashboard page with three stats cards
- [ ] 2.5 Add loading skeleton state for dashboard

## 3. Admin Product List

- [ ] 3.1 Add admin product list/CRUD endpoints to mock API and API client
- [ ] 3.2 Create reusable `DataTable` component for admin tables
- [ ] 3.3 Create `app/admin/products/page.tsx` with product table (Name, Category, Price, Stock, Status, Actions)
- [ ] 3.4 Implement deactivate/activate toggle action in product table
- [ ] 3.5 Add "Create Product" button linking to `/admin/products/new`

## 4. Admin Product Form

- [ ] 4.1 Create product form component with fields: name, description, price (EUR input → cents), category dropdown, stock, image URL, is_featured checkbox
- [ ] 4.2 Add form validation (required fields: name, price, category)
- [ ] 4.3 Create `app/admin/products/new/page.tsx` for product creation
- [ ] 4.4 Create `app/admin/products/[id]/edit/page.tsx` for product editing (pre-filled form)
- [ ] 4.5 Handle form submission (create/update API call), success redirect, error display

## 5. Admin Order List

- [ ] 5.1 Add admin order list/update endpoints to mock API and API client
- [ ] 5.2 Create `StatusBadge` component with color-coded order statuses
- [ ] 5.3 Create `app/admin/orders/page.tsx` with order table (ID, Email, Total, Status, Date, Actions)
- [ ] 5.4 Add status filter (pill buttons: All, Pending, Confirmed, Shipped, Delivered, Cancelled)
- [ ] 5.5 Implement inline status update dropdown with valid transitions only
- [ ] 5.6 Handle status update failure with rollback and error message

## 6. Tests

- [ ] 6.1 Test admin route protection (redirect for non-admin, render for admin)
- [ ] 6.2 Test admin dashboard stats rendering and loading state
- [ ] 6.3 Test product list table rendering, deactivate/activate actions
- [ ] 6.4 Test product form validation and submission
- [ ] 6.5 Test order list filtering and status update
