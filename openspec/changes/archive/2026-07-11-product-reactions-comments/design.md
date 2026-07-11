## Context

AtelierMarie is a single-VPS candle e-commerce platform with SQLite (WAL) as the sole production database. The store is anonymous-first: users can browse, cart, and checkout without an account. Sessions are UUID4 cookies created eagerly by middleware.

Currently, product pages display product info and an "Add to Cart" button. There is no social interaction layer. The existing schema has `products`, `sessions`, `users`, `cart_items`, `orders`, and `order_items` tables.

This design adds reactions and comments as a lightweight social proof layer, staying within Layer 1 (production e-commerce) since social proof directly supports conversion.

## Goals / Non-Goals

**Goals:**
- Enable anonymous users to react to and comment on products without login
- Provide visible social proof (reaction counts, comment threads) on product pages
- Keep the implementation minimal and secure (plain text only, session-based rate limiting)
- Allow admin moderation of comments
- Maintain <200ms response time for all new endpoints

**Non-Goals:**
- Nested replies / threaded conversations
- Rich text, markdown, or media in comments
- Upvote/downvote on comments
- Edit history or soft-delete ("deleted by moderator" placeholders)
- Email notifications on new comments
- Spam detection ML (basic blocklist only)
- Cursor-based pagination (offset pagination is sufficient for expected volume)
- IP-based rate limiting (acceptable tradeoff for privacy; admin moderation handles spam)

## Decisions

### 1. Reactions and comments live in Layer 1 (not Layer 2)

**Decision:** New tables and services live in the main `app/` tree alongside products/cart/orders.

**Rationale:** Social proof directly influences purchase decisions. If reactions/comments are in Layer 2 (analytics), they'd be optional and could vanish — defeating the purpose. They must be as reliable as the product catalog itself.

**Alternative considered:** Layer 2 with graceful degradation. Rejected because the feature's entire value is visibility; an intermittent feature erodes trust rather than building it.

### 2. Session-scoped identity (no separate "commenter" table)

**Decision:** Reactions and comments store `session_id` as a denormalized snapshot (NOT a foreign key). Comments additionally store `display_name` inline alongside `session_id`.

**Rationale:** Matches the anonymous-first philosophy. Sessions expire after 30 days and are cleaned up by `cleanup_expired_sessions()`. Reactions and comments are permanent social proof that must survive session expiry. Making `session_id` a FK would either block cleanup (RESTRICT) or cascade-delete social proof (CASCADE). Instead, `session_id` is stored as an immutable historical record — not a live reference.

**Alternative considered:** A `commenters` table mapping session → persistent identity. Rejected as over-engineering for the expected volume (<100 comments/month). Also considered FK with ON DELETE SET NULL, but this breaks the reactions PK (which includes session_id) and complicates rate-limit queries.

### 3. Aggregate reaction counts via SQL COUNT (no denormalized counter)

**Decision:** Reaction counts are computed per-request via `SELECT reaction_type, COUNT(*) FROM reactions WHERE product_id = ? GROUP BY reaction_type`.

**Rationale:** With <1000 products and <10K reactions, this query is trivially fast with the composite index. A denormalized counter column introduces update races and consistency issues for negligible performance gain.

**Alternative considered:** `heart_count`/`thumbs_up_count` columns on `products` table. Rejected — adds write complexity (UPDATE on every toggle), risks drift, and the query is already fast.

### 4. Rate limiting in the service layer (not middleware)

**Decision:** Rate limit checks (3 comments/product/session, 10 comments/hour/session) are enforced in `comment_service.py` via SQL COUNT queries before INSERT.

**Rationale:** These are business rules specific to comments, not generic HTTP rate limiting. Keeping them in the service layer makes them testable without HTTP and keeps the middleware simple.

**Alternative considered:** Generic rate-limiting middleware (e.g., slowapi). Rejected — the rate limits are per-feature, not per-endpoint, and the session-based identity doesn't map cleanly to IP-based rate limiters.

### 5. Input sanitization as a shared utility

**Decision:** A `app/utils/sanitize.py` module with `sanitize_text(text: str) -> str` using `html.escape(text, quote=True)` from stdlib. This converts `<>"'&` to HTML entities, preventing any HTML rendering while preserving all original text content.

**Rationale:** HTML entity escaping is strictly better than regex stripping for this use case:
- Regex `re.sub(r'<[^>]*>', '', text)` fails on unclosed tags (`<script no close`) and corrupts legitimate text containing `<` and `>` (e.g., "size < 8oz").
- `html.escape()` is lossless (original text recoverable), stdlib (no dependency), and safe in all rendering contexts.
- Combined with React's default escaping on frontend, provides defense-in-depth.

**Additional utilities in the same module:**
- `is_url_only(text: str) -> bool`: returns True if body matches `^https?://\S+$` after trimming (single URL with protocol, no surrounding text). URLs embedded in sentences are allowed.
- `contains_blocked_word(text: str, blocklist: list[str]) -> bool`: lowercase both input and blocklist, check substring match. ASCII-only blocklist (admin adds variations like 'admin', 'adm1n' manually).

**Alternative considered:** Bleach/html-sanitizer library. Rejected — `html.escape()` is simpler and we render as plain text anyway.

### 6. Comments use offset pagination (page/limit)

**Decision:** `GET /v1/products/{product_id}/comments?page=1&limit=20&sort=newest` with standard pagination response.

**Rationale:** Consistent with existing product list pagination. Expected volume is low (<50 comments per product). Offset pagination is simple and sufficient.

### 7. Separate route modules (not extensions to products.py)

**Decision:** New files `routes/reactions.py` and `routes/comments.py` with routers mounted under `/v1/products/{product_id}/`.

**Rationale:** Keeps route modules focused and small. The existing `routes/products.py` handles product CRUD; social features are conceptually separate. FastAPI's router composition makes this clean.

### 8. Input processing order

**Decision:** Validation and sanitization happen in a strict order within the service layer:
1. Strip leading/trailing whitespace from raw input
2. Validate length constraints on the raw text (2–50 for display_name, 1–500 for body)
3. Check display_name contains at least one letter (`any(c.isalpha() for c in name)`)
4. Check blocklist (case-insensitive substring match on raw text)
5. Check URL-only pattern (body only, on raw text)
6. `html.escape()` the validated input for storage

**Rationale:** Length validation MUST happen on the raw (pre-escape) text because html.escape() expands characters unpredictably (`&` → `&amp;` = 5 chars, `<` → `&lt;` = 4 chars). Validating post-escape would reject users typing normal ampersands or angle brackets. Blocklist and URL checks also operate on raw text (what the user intended). html.escape() is the final step before INSERT — it's a storage safety measure, not a business validation. Frontend character counter counts raw input characters (matching what users type).

### 9. Atomic toggle for reactions

**Decision:** The toggle operation uses `INSERT OR IGNORE` followed by checking `cursor.rowcount`:
- If `rowcount == 1`: reaction was added → return `active: true`
- If `rowcount == 0`: reaction already existed → `DELETE` it → return `active: false`

Wrapped in a single connection (SQLite serializes writes via WAL), this is atomic and idempotent. No TOCTOU race.

**Rationale:** Avoids separate SELECT-then-INSERT/DELETE pattern that races on double-clicks. `INSERT OR IGNORE` + rowcount check is a standard SQLite upsert pattern. Frontend also debounces clicks (300ms) as defense-in-depth.

### 10. Reaction rate limiting uses a separate log table

**Decision:** Rate limiting for reaction toggles is tracked in a `reaction_toggle_log` table (session_id TEXT, product_id TEXT, toggled_at TEXT). Every toggle (both add and remove) appends a row. The rate limit query is `SELECT COUNT(*) FROM reaction_toggle_log WHERE session_id = ? AND toggled_at > datetime('now', '-60 seconds')`.

**Rationale:** The `reactions` table can't track rate limits because DELETE (toggle-off) removes the row. If we counted only existing rows, an attacker could bypass limits by alternating add/remove (each remove deletes the evidence). A separate append-only log accurately counts all toggle operations regardless of final state. Old rows (>1 hour) are cleaned up lazily by a periodic task or on next write (not critical — they're tiny).

### 11. Standardized error messages for rate limiting

**Decision:** Rate limit 429 responses use generic messages that do NOT reveal counts, session IDs, or timestamps:
- Per-product limit: `"Comment limit reached for this product"`
- Hourly limit: `"Too many comments. Please try again later."`
- Reaction rate limit: `"Too many reactions. Please slow down."`

**Rationale:** Prevents attackers from probing exact boundaries or confirming session association.

## Risks / Trade-offs

**[Risk] Comment volume on a single product could grow unbounded** → Mitigated by rate limiting (3 per session per product) and pagination. For a small candle business, organic volume won't be a problem. If it somehow grows, add a hard cap per product later.

**[Risk] Session rotation on logout creates "orphaned" reactions/comments** → Acceptable. The old session's reactions/comments remain visible (they're valid social proof). The user loses the ability to un-react or know they already commented from the new session. This is fine — it's the same behavior as clearing cookies.

**[Risk] Display name impersonation (anonymous user types "Admin" or the brand name)** → Mitigated by word blocklist checking display names. Admin comments could be distinguished by a badge in a future iteration, but that's a non-goal now.

**[Risk] Regex-based HTML stripping could miss edge cases** → Resolved: switched to `html.escape()` which is lossless and complete. Combined with React's default escaping on frontend (defense in depth).

**[Risk] Session-based rate limits are bypassable via cookie rotation** → An attacker can delete their session cookie to get a fresh session and bypass per-session limits. Acceptable for a small family candle business: real spam volume will be low, admin can delete spam, and implementing IP-based rate limiting would require storing IP addresses (privacy concern). If spam becomes a problem in practice, add IP-based rate limiting as a backstop (30 comments/IP/hour).

**[Risk] Same user inflates reaction counts after session rotation** → User logs out (new session), re-reacts on same product → count shows 2 from same physical person. Acceptable for a small store where reaction counts are social proof, not billing metrics. If counts become critical, deduplicate by user_id (requires login-only reactions).

**[Trade-off] No edit/delete for comment authors** → Keeps the system simpler and avoids needing to track "ownership" across session rotations. Authors who regret a comment can ask admin to delete it (acceptable for low volume).

**[Trade-off] Hard delete (no audit trail)** → Appropriate for a small business. Moderation at this scale is "delete obvious spam" not "review flagged content." An audit trail would be over-engineering.
