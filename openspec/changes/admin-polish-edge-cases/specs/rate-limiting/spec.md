## ADDED Requirements

### Requirement: Auth endpoints rate-limited by IP
The system's Nginx configuration SHALL limit requests to `/v1/auth/` endpoints to 5 requests per minute per client IP address. Excess requests MUST receive HTTP 429 Too Many Requests.

#### Scenario: Normal auth usage passes
- **WHEN** a client makes 5 requests to `/v1/auth/login` within 1 minute
- **THEN** all 5 requests are proxied to the backend normally

#### Scenario: Auth rate limit exceeded
- **WHEN** a client makes a 6th request to `/v1/auth/login` within 1 minute (no burst allowance remaining)
- **THEN** Nginx returns 429 with a `Retry-After` header indicating seconds until the next request is allowed

#### Scenario: Burst allowance for auth
- **WHEN** a client makes 7 rapid requests to `/v1/auth/callback` (rate=5r/m, burst=5 nodelay configured)
- **THEN** the first 6 requests are processed (1 current slot + 5 burst), and the 7th within the same window receives 429

Note: In Nginx `limit_req` semantics, `rate=5r/m` means 1 request per 12 seconds. With `burst=5 nodelay`, the total immediate capacity is `1 + burst = 6` requests. After that, requests are rejected until slots refill at the configured rate.

### Requirement: Checkout endpoint rate-limited by session with IP backstop
The system's Nginx configuration SHALL limit `POST /v1/orders` to 10 requests per minute per session cookie value (`$cookie_session_id` — matching the cookie name in `app/config.py`). This prevents automated checkout abuse while allowing legitimate rapid retries.

The rate limit zone MUST use a `map` directive to handle empty session cookies: `map $cookie_session_id $checkout_rate_key { "" "no_session"; default $cookie_session_id; }`. This ensures all cookieless requests share a single bucket (fail-closed) and provides portable behavior across Nginx versions.

Additionally, a secondary IP-based rate limit of 30 requests per minute per IP SHALL apply to `POST /v1/orders` as a backstop. This prevents abuse by clients that rotate or omit session cookies. Requests without a session cookie share a single session-based bucket (intentionally restrictive — effectively fail-closed for cookieless clients).

#### Scenario: Normal checkout passes
- **WHEN** a session makes 10 `POST /v1/orders` requests within 1 minute
- **THEN** all 10 requests are proxied normally

#### Scenario: Checkout rate limit exceeded
- **WHEN** a session makes an 11th `POST /v1/orders` within 1 minute (no burst remaining)
- **THEN** Nginx returns 429

#### Scenario: Different sessions not affected
- **WHEN** session A hits its rate limit on checkout, and session B makes a checkout request
- **THEN** session B's request is processed normally (limits are per-session)

#### Scenario: Cookieless checkout limited by IP backstop
- **WHEN** a client sends `POST /v1/orders` requests without a session cookie, exceeding 30 per minute from the same IP
- **THEN** Nginx returns 429 (IP backstop catches abuse that session-based limiting cannot)

### Requirement: Admin endpoints rate-limited by IP
The system's Nginx configuration SHALL limit requests to `/v1/admin/` endpoints to 30 requests per minute per client IP address (burst=10). This protects against compromised API keys being used for automated abuse while remaining generous for legitimate admin workflows.

#### Scenario: Normal admin usage passes
- **WHEN** an admin makes 30 requests to admin endpoints within 1 minute
- **THEN** all requests are proxied normally

#### Scenario: Admin rate limit exceeded
- **WHEN** a client makes more than 40 requests (30 + 10 burst) to admin endpoints within 1 minute
- **THEN** Nginx returns 429

### Requirement: Rate limit response format
The system SHALL return rate-limit responses with:
- HTTP status 429
- `Retry-After` header (static value matching the zone's rate period, e.g., `12` for 5r/m zones, `6` for 10r/m zones)
- JSON body: `{"error": {"code": "RATE_LIMITED", "message": "Too many requests", "details": {"retry_after": <seconds>}}}`

Note: Nginx does not natively expose a dynamic "time until next slot" variable. The `retry_after` value in the body and the `Retry-After` header are both static estimates based on the zone's configured rate. This is achieved via `error_page 429 = @429_json` pointing to a location that returns a static JSON file. Ensure `server_tokens off;` is set to suppress Nginx version in error pages.

#### Scenario: 429 response body format
- **WHEN** a rate limit is triggered on an auth endpoint (5r/m zone)
- **THEN** the response body matches the ErrorResponse envelope with code `"RATE_LIMITED"`, includes `retry_after: 12` in details, and has `Retry-After: 12` header

### Requirement: Rate limiting config is separate and includable
The rate limiting configuration SHALL live in `deploy/nginx-rate-limit.conf` as an includable file. The main Nginx server block SHALL include it via `include /etc/nginx/conf.d/rate-limit.conf;`.

#### Scenario: Config file structure
- **WHEN** the deployment is configured
- **THEN** `deploy/nginx-rate-limit.conf` contains `limit_req_zone` directives at http context level and `limit_req` directives for use in location blocks

### Requirement: Admin API key entropy
The admin API key (`ATELIER_ADMIN_API_KEY`) MUST be at least 32 bytes of cryptographically random data (e.g., generated via `secrets.token_urlsafe(32)`). The application MUST reject startup if the configured API key is shorter than 32 characters in production mode.

#### Scenario: Weak API key rejected at startup
- **WHEN** the application starts with `ATELIER_ADMIN_API_KEY` shorter than 32 characters and environment is not "development"
- **THEN** the application logs an error and refuses to start
