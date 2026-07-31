# State, API, And Data Flow

This explains frontend state and backend communication.

## API Facade Rule

Components should import from:

```ts
@/lib/api
```

Do not import directly from `mock-api` or `api-client` in components.

Why:

- `lib/api.ts` switches between real and mock APIs.
- production bundles do not need mock data.
- contract changes have one public frontend facade.

## Real API Client

File: `frontend/lib/api-client.ts`.

It provides:

- `get`
- `post`
- `postForm`
- `patch`
- `put`
- `del`
- `ApiError`

Important behavior:

- Uses `NEXT_PUBLIC_API_URL`, default `http://localhost:8000`.
- Sends credentials for cookies.
- Parses the backend standard error envelope.
- Dispatches `session-rotated` when response header `X-Session-Rotated` is true.
- Returns `undefined` for 204 responses.

## Mock API

File: `frontend/lib/mock-api.ts`.

Mock API is enabled with:

```text
NEXT_PUBLIC_USE_MOCK_API=true
```

Rules:

- Keep mock responses aligned with backend models.
- Update mock API when changing `frontend/lib/types.ts`.
- Mock mode is for dev convenience, not proof that backend contract works.

## Types

File: `frontend/lib/types.ts`.

This mirrors Pydantic models.

When backend contracts change, update:

1. Pydantic model.
2. TypeScript interface/type.
3. API facade function if needed.
4. Mock API data/function.
5. Tests.

## Cart State

File: `frontend/contexts/CartContext.tsx`.

Cart behavior:

- hydrates on mount through `getCart(locale)`
- optimistically updates add/update/remove
- rolls back on API failure
- auto-clears visible errors after 5 seconds
- refreshes when `session-rotated` fires
- owns cart drawer open/close state

Important rule:

- Backend response is final. Optimistic state is temporary.

## Auth State

File: `frontend/contexts/AuthContext.tsx`.

Auth behavior:

- hydrates current user on mount
- stores login redirect path in session storage
- starts OAuth through backend `/v1/auth/login`
- listens for `session-rotated`
- logout treats user intent as final even if API call fails

Important rule:

- Frontend auth is UX. Backend still enforces admin/protected routes.

## Consent State

File: `frontend/contexts/CookieConsentContext.tsx`.

Consent controls analytics emission.

Rules:

- no consent means no frontend analytics events
- user can change consent later
- consent version can resurface banner
- checkout cannot require analytics consent

## Admin State

File: `frontend/contexts/AdminContext.tsx`.

Admin context and `AdminGuard` protect admin UI.

Rules:

- Do not rely on frontend guard alone.
- Backend admin dependency/API key checks are authoritative.

## Error Handling

Backend errors become `ApiError` with:

- `code`
- `message`
- `details`

Use localized error helpers where available. Do not show raw provider errors to customers unless sanitized.

