# Admin Access Control — Spec

## ADDED Requirements

### Requirement: First Google sign-in auto-promotes to admin when no users exist

When the first user signs in via Google OAuth and the users table is empty, that user is automatically promoted to admin.

#### Scenario: First user becomes admin

WHEN a user signs in via Google OAuth
AND the users table contains zero existing users
THEN the user is created with is_admin=TRUE
AND subsequent API calls with that user's JWT can access /v1/admin/* endpoints

#### Scenario: Second user does not become admin

WHEN a user signs in via Google OAuth
AND the users table already contains one or more users
THEN the new user is created with is_admin=FALSE
AND that user cannot access /v1/admin/* endpoints

#### Scenario: First user retains admin on subsequent logins

WHEN the first user (who was auto-promoted to admin) signs in again
THEN their is_admin flag remains TRUE
AND they retain access to admin endpoints

---

### Requirement: Admin endpoints require valid JWT with is_admin=TRUE or valid API key

All /v1/admin/* endpoints are protected by an admin auth dependency that accepts either form of authentication.

#### Scenario: Admin user with valid JWT accesses admin endpoint

WHEN a user with is_admin=TRUE makes a request to GET /v1/admin/dashboard
AND the request includes a valid JWT in the Authorization header
THEN the request succeeds with HTTP 200
AND the dashboard data is returned

#### Scenario: Non-admin user with valid JWT is rejected

WHEN a user with is_admin=FALSE makes a request to GET /v1/admin/dashboard
AND the request includes a valid JWT in the Authorization header
THEN the response status is HTTP 403 Forbidden
AND the response body contains an error message indicating insufficient permissions

#### Scenario: Valid API key grants admin access

WHEN a request is made to GET /v1/admin/dashboard
AND the request includes X-Admin-API-Key header with a value matching the ATELIER_ADMIN_API_KEY env var
THEN the request succeeds with HTTP 200
AND the dashboard data is returned

#### Scenario: Invalid API key is rejected

WHEN a request is made to GET /v1/admin/dashboard
AND the request includes X-Admin-API-Key header with an incorrect value
THEN the response status is HTTP 403 Forbidden

---

### Requirement: Non-admin user gets HTTP 403 on /v1/admin/* endpoints

All admin endpoints consistently return 403 for unauthorized access attempts.

#### Scenario: Unauthenticated request returns 401

WHEN a request is made to GET /v1/admin/dashboard
AND no Authorization header or X-Admin-API-Key header is provided
THEN the response status is HTTP 401 Unauthorized

#### Scenario: Non-admin user gets 403 on events endpoint

WHEN a user with is_admin=FALSE makes a request to GET /v1/admin/events
THEN the response status is HTTP 403 Forbidden

#### Scenario: Non-admin user gets 403 on products endpoint

WHEN a user with is_admin=FALSE makes a request to GET /v1/admin/products
THEN the response status is HTTP 403 Forbidden

#### Scenario: Non-admin user gets 403 on orders endpoint

WHEN a user with is_admin=FALSE makes a request to GET /v1/admin/orders
THEN the response status is HTTP 403 Forbidden

---

### Requirement: API key access for programmatic and CLI tools

The X-Admin-API-Key mechanism enables non-interactive access for maintenance scripts, product imports, and CLI tooling.

#### Scenario: API key works without any user session

WHEN a request is made to GET /v1/admin/products
AND the request has no cookies or Authorization header
AND the X-Admin-API-Key header matches ATELIER_ADMIN_API_KEY
THEN the request succeeds with HTTP 200

#### Scenario: API key not configured returns 403 for key-based auth

WHEN the ATELIER_ADMIN_API_KEY environment variable is not set
AND a request includes X-Admin-API-Key header with any value
THEN the API key authentication path is skipped (treated as no key provided)
AND if no valid JWT is present, the response is HTTP 401

#### Scenario: Both JWT and API key provided — JWT takes precedence

WHEN a request includes both a valid admin JWT and a valid X-Admin-API-Key
THEN the JWT is used for authentication
AND the request succeeds with HTTP 200

#### Scenario: Expired JWT with valid API key still succeeds

WHEN a request includes an expired JWT in the Authorization header
AND a valid X-Admin-API-Key header is also provided
THEN the API key authentication succeeds
AND the request returns HTTP 200
