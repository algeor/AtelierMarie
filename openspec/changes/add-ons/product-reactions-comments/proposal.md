## Why

AtelierMarie has no way for customers to interact with products beyond adding to cart. A lightweight social layer — reactions and comments — builds trust through visible social proof, encourages engagement without the overhead of a full reviews system, and maintains the luxury-minimalist aesthetic (no star ratings, no "was this helpful?" noise).

## What Changes

- **Product reactions** — Two positive-only emoji buttons (❤️, 👍) below product details. Session-based toggle (one per type per session per product). Displays aggregate count. No login required.
- **Product comments** — Minimalistic comment thread per product. Username + body (max 500 chars) + timestamp. Sort by newest (default) or oldest. Hybrid identity: logged-in users get name from Google profile, anonymous users type a display name.
- **Rate limiting** — Max 3 comments per session per product. Max 10 comments per session per hour globally. Reactions are toggle-only (not accumulative).
- **Admin moderation** — Admin can hard-delete any comment. No hide/flag system.
- **Security hardening** — HTML tag stripping before storage, plain text only rendering, Pydantic `Literal` validation for sort/reaction types, session-based abuse prevention, URL-only comment blocking, basic word blocklist.

## Capabilities

### New Capabilities
- `product-reactions`: Toggle-based emoji reactions (❤️, 👍) per product, session-scoped, with aggregate counts displayed on product pages
- `product-comments`: Comment thread per product with username, body (500 char max), timestamp, sort order (newest/oldest), hybrid identity (auto-fill for logged-in, free-text for anonymous), rate limiting, and spam prevention
- `comment-moderation`: Admin ability to hard-delete any comment via authenticated endpoint

### Modified Capabilities
<!-- No existing specs are being modified. The product detail page and database schema
     don't have existing spec-level requirements to delta against. -->

## Impact

- **Backend:** Two new tables (`reactions`, `comments`), two new service modules (`reaction_service.py`, `comment_service.py`), new route modules (`routes/reactions.py`, `routes/comments.py`), input sanitization utility
- **Frontend:** New components (`ReactionBar`, `CommentThread`, `CommentForm`, `CommentCard`, `SortDropdown`) under `frontend/components/products/`
- **Database:** Two new tables with indexes and constraints; no changes to existing tables
- **API:** New endpoints under `/v1/products/{product_id}/reactions` and `/v1/products/{product_id}/comments`
- **Dependencies:** None — uses existing Pydantic validation, SQLite, React escaping
