## 1. Database Schema & Utilities

- [ ] 1.1 Add `reactions` table to `_SCHEMA_SQL` in `app/database.py` (columns: session_id TEXT NOT NULL [no FK — denormalized snapshot], product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE, reaction_type TEXT CHECK IN ('heart','thumbs_up'), created_at TEXT; PK on (session_id, product_id, reaction_type); indexes on (product_id, reaction_type) and (session_id, created_at))
- [ ] 1.2 Add `reaction_toggle_log` table to `_SCHEMA_SQL` (columns: session_id TEXT NOT NULL, product_id TEXT NOT NULL, toggled_at TEXT NOT NULL DEFAULT datetime('now'); index on (session_id, toggled_at) for rate limit queries). Append-only; old rows cleaned lazily.
- [ ] 1.3 Add `comments` table to `_SCHEMA_SQL` in `app/database.py` (columns: id TEXT PK UUID4, product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE, session_id TEXT NOT NULL [no FK — denormalized snapshot], user_id TEXT REFERENCES users(id) ON DELETE SET NULL, display_name TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT; indexes on (product_id, created_at) and (session_id, created_at))
- [ ] 1.4 Create `app/utils/__init__.py` and `app/utils/sanitize.py` with `sanitize_text()` using `html.escape(text, quote=True)`, `is_url_only()` check (matches `^https?://\S+$` after trim), and `contains_blocked_word()` (case-insensitive substring match)
- [ ] 1.5 Create `app/utils/blocklist.py` with configurable word blocklist (list of lowercase strings) and export for use in sanitize module

## 2. Pydantic Models

- [ ] 2.1 Create `app/models/reactions.py` with `ReactionToggleRequest` (reaction_type: Literal["heart", "thumbs_up"]), `ReactionToggleResponse` (reaction_type, active: bool), and `ReactionCountsResponse` (heart: {count: int, reacted: bool}, thumbs_up: {count: int, reacted: bool})
- [ ] 2.2 Create `app/models/comments.py` with `CommentCreateRequest` (display_name: str | None, body: str), `CommentResponse` (id, display_name, body, created_at — excludes session_id, user_id, product_id), `AdminCommentResponse` (id, product_id, product_name, display_name, body, created_at), `CommentListResponse` (items: list[CommentResponse], total: int, page: int, limit: int), and `CommentSort = Literal["newest", "oldest"]`

## 3. Service Layer — Reactions

- [ ] 3.1 Create `app/services/reaction_service.py` with `toggle_reaction(session_id, product_id, reaction_type)` — uses INSERT OR IGNORE + rowcount check (if 1: added, if 0: DELETE). Atomic and idempotent.
- [ ] 3.2 Add `get_reaction_counts(product_id, session_id)` — returns aggregate counts per type and current session's reaction state. Uses GROUP BY with fallback to 0 for missing types.
- [ ] 3.3 Add product existence AND is_active=1 validation (raise `ProductNotFoundError` if product_id doesn't exist or is inactive)
- [ ] 3.4 Add reaction rate limiting: INSERT into `reaction_toggle_log` on every toggle, count rows by session_id in last 60 seconds from that table, raise `RateLimitExceededError` if >= 10. Clean up rows older than 1 hour lazily.

## 4. Service Layer — Comments

- [ ] 4.1 Create `app/services/comment_service.py` with `create_comment(session_id, user_id, product_id, display_name, body)` — display_name is always a resolved non-null string (route layer handles hybrid identity). Processing order: (1) trim whitespace, (2) validate lengths (2-50 name, 1-500 body) on raw text, (3) check display_name has at least one letter (`any(c.isalpha() for c in name)`), (4) check blocklist, (5) check URL-only, (6) check rate limits, (7) html.escape() inputs, (8) insert
- [ ] 4.2 Add rate limit checks: `_check_product_limit(session_id, product_id)` and `_check_hourly_limit(session_id)` — check BOTH, reject if EITHER exceeded. Raise custom `RateLimitExceededError` with appropriate message
- [ ] 4.3 Add `list_comments(product_id, sort, page, limit)` — paginated query with total count. Clamp limit to max 100. Sort maps to hardcoded SQL: {'newest': 'DESC', 'oldest': 'ASC'}[sort] — NEVER concatenate sort param into SQL.
- [ ] 4.4 Add `delete_comment(comment_id)` — hard delete, raises `CommentNotFoundError` if missing
- [ ] 4.5 Add `list_all_comments(page, limit, product_id_filter)` — admin endpoint for moderation view. JOIN comments with products ON comments.product_id = products.id (always valid since CASCADE prevents orphans). Clamp limit to 100.

## 5. Routes — Reactions

- [ ] 5.1 Create `app/routes/reactions.py` with `POST /v1/products/{product_id}/reactions` (toggle) and `GET /v1/products/{product_id}/reactions` (counts)
- [ ] 5.2 Wire session dependency to extract session_id from request
- [ ] 5.3 Register router in `app/main.py`

## 6. Routes — Comments

- [ ] 6.1 Create `app/routes/comments.py` with `POST /v1/products/{product_id}/comments` (create) and `GET /v1/products/{product_id}/comments` (list with sort/pagination)
- [ ] 6.2 Add hybrid identity resolution in route layer (not service): if session has user_id, look up users.name — if non-null use as display_name; if null or anonymous, require display_name in request body (422 if missing). Always pass resolved non-null display_name string to service.
- [ ] 6.3 Register router in `app/main.py`

## 7. Routes — Admin Moderation

- [ ] 7.1 Add `DELETE /v1/admin/comments/{comment_id}` to `app/routes/admin.py` with require_admin dependency
- [ ] 7.2 Add `GET /v1/admin/comments` to `app/routes/admin.py` with pagination (max 100) and optional product_id filter

## 8. Frontend — Reactions

- [ ] 8.1 Create `frontend/components/products/ReactionBar.tsx` — two emoji buttons with counts, toggle state, optimistic updates, 300ms debounce on clicks
- [ ] 8.2 Add API client functions in `frontend/lib/api-client.ts`: `toggleReaction()` and `getReactions()`
- [ ] 8.3 Add mock API equivalents in `frontend/lib/mock-api.ts`
- [ ] 8.4 Add TypeScript types for reaction API responses in `frontend/lib/types.ts`

## 9. Frontend — Comments

- [ ] 9.1 Create `frontend/components/products/CommentForm.tsx` — display name input (hidden if logged in with name), body textarea with char counter (counts visible text length), submit button
- [ ] 9.2 Create `frontend/components/products/CommentCard.tsx` — display name, body (plain text, rendered via React default escaping), relative timestamp
- [ ] 9.3 Create `frontend/components/products/CommentThread.tsx` — list of CommentCards, SortDropdown, pagination, empty state, graceful degradation if API fails
- [ ] 9.4 Create `frontend/components/products/SortDropdown.tsx` — "Newest first" / "Oldest first" toggle
- [ ] 9.5 Add API client functions: `postComment()`, `getComments()`
- [ ] 9.6 Add mock API equivalents and TypeScript types

## 10. Integration & Testing

- [ ] 10.1 Write unit tests for `sanitize.py`: html.escape behavior, URL-only detection (protocol required, embedded URLs allowed), blocklist (case-insensitive substring), legitimate text with < and > preserved as entities
- [ ] 10.2 Write service tests for `reaction_service.py`: toggle on/off (INSERT OR IGNORE pattern), counts, product validation (is_active check), rate limiting (10/minute), concurrent toggle idempotency
- [ ] 10.3 Write service tests for `comment_service.py`: create with processing order (escape → trim → validate → blocklist → URL → rate limit → store), rate limits (both per-product and hourly), list with sort/pagination/limit clamping, delete, display_name-too-short-after-escape edge case, display_name must contain a letter
- [ ] 10.4 Write route tests for reaction endpoints (201/200 toggle, 404 product, 404 inactive product, 422 invalid type, 429 rate limit)
- [ ] 10.5 Write route tests for comment endpoints (201 create, 422 validation, 422 empty-after-sanitize, 429 rate limit, pagination, sort, hybrid identity fallback for null users.name)
- [ ] 10.6 Write route tests for admin moderation endpoints (204 delete, 403 non-admin, 404 not found, limit clamped to 100)
- [ ] 10.7 Integration test: full flow — post comment, list it, react, verify counts, admin delete, verify cascade on product delete
