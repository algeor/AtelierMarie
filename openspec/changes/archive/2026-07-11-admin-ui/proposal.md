## Why

The store needs an admin interface for the business owner to manage products, monitor orders, and view key business metrics without direct database access or API calls. This is essential for day-to-day operations of the candle business.

## What Changes

- Add admin layout with separate navigation (Dashboard, Products, Orders)
- Build admin dashboard with stats cards (orders today, revenue this week, product count)
- Create admin product list with table view, edit and deactivate actions
- Build admin product form for create/edit (name, description, price, category, stock, image upload)
- Create admin order list with status filter and status update dropdown
- Protect all admin routes with auth check (redirect to login if not admin)

## Capabilities

### New Capabilities
- `admin-layout`: Admin shell with sidebar navigation, protected route wrapper, and responsive layout
- `admin-dashboard`: Stats cards showing orders today, revenue this week, active product count
- `admin-products`: Product table with search, edit/deactivate actions, and create/edit form with image upload
- `admin-orders`: Order table with status filter and inline status update dropdown

### Modified Capabilities

## Impact

- New directory: `frontend/app/admin/` with layout and page components
- New components: `frontend/components/admin/` (stats cards, data tables, forms, status dropdowns)
- Mock API additions: admin-specific endpoints (stats, product CRUD, order status updates)
- Uses existing design tokens (luxury palette) with admin-appropriate styling
- Depends on existing `UserResponse.is_admin` and auth context for route protection
