# Authentication

OAuth, JWT, sessions, and access control.

## Session Cookies

Every user gets a session UUID:

- **Created:** On first request (eager middleware)
- **Stored:** `sessions` table in Postgres
- **Cookie:** HttpOnly, Secure (prod), SameSite=Lax
- **Lifetime:** 30 days
- **Rotation:** New ID issued on login, old one invalidated

```
User visits → Session UUID cookie created
  ↓
User browses, carts, checks out → all keyed to session_id
  ↓
User optionally logs in (Google OAuth) → session.user_id updated
```

---

## Google OAuth Flow

**Endpoints:**

```
GET /v1/auth/login?redirect_uri=...
  ↓ (redirects to Google consent screen)
GET /v1/auth/callback?code=...&state=...
  ↓ (backend exchanges code for user info)
POST /v1/auth/logout
```

**JWT Issued After Login:**

- **Payload:** `{sub: user_id, email, is_admin, iat, exp}`
- **Lifetime:** 7 days
- **Storage:** Secure HTTP-only cookie
- **Validation:** Signature + audience + issuer + expiry

---

## Admin Authentication

Two methods:

**1. JWT Cookie (for browser):**
```bash
# After Google OAuth login with is_admin=true
GET /v1/auth/me
# Returns: {id, email, is_admin: true}
```

**2. API Key (for scripts/automation):**
```bash
ADMIN_API_KEY=dev-admin-key  # Set in .env

curl -H "Authorization: Bearer dev-admin-key" \
  http://localhost:8000/v1/admin/products
```

API key comparison uses `hmac.compare_digest` (constant-time, prevents timing attacks).

---

## Public Routes (No Auth Required)

- `GET /v1/products` — List/search products
- `GET /v1/products/{id}` — Product detail
- `GET /v1/auth/login` — Start OAuth
- `GET /v1/auth/callback` — OAuth callback
- `GET /v1/faq` — FAQ list
- `GET /v1/about` — About page
- `POST /v1/contact` — Submit contact form

---

## Session-Required Routes (Cookie OR JWT)

- `GET /v1/cart` — Get cart
- `POST /v1/cart` — Add to cart
- `POST /v1/orders` — Create order
- `GET /v1/orders` — List my orders
- `POST /v1/products/{id}/reactions` — React to product
- `POST /v1/products/{id}/comments` — Post comment

---

## Admin-Required Routes

- `POST /v1/admin/products` — Create product
- `PUT /v1/admin/products/{id}` — Update product
- `GET /v1/admin/orders` — All orders
- `PATCH /v1/admin/orders/{id}/status` — Update status
- `GET /v1/admin/analytics` — Analytics dashboard

**Auth requirement:** Either JWT cookie (is_admin=true) OR Bearer API key

---

## First User is Admin

When the first user logs in via Google OAuth:
- User is automatically promoted to `is_admin = true`
- No manual DB edits needed
- Useful for local setup

---

## Session Rotation on Logout

```
POST /v1/auth/logout
  → Invalidate old session ID
  → Create new session ID (for anonymous browsing)
  → Clear JWT cookie
```

This prevents session reuse attacks.

---

## Error Responses

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing or invalid authentication"
  }
}
```

**Status codes:**
- `401 Unauthorized` — Missing/invalid auth
- `403 Forbidden` — Insufficient permissions

---

## Rate Limiting

- Login attempts: 10 per hour per email
- Reaction toggles: 5 per minute per session
- Comment posts: 10 per minute per session
- Contact form: 5 per minute per IP

Response headers:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`
