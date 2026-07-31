# Comments And Reactions

Comments and reactions are lightweight social proof for products.

## Main Backend Files

- `app/models/comments.py`
- `app/models/reactions.py`
- `app/routes/comments.py`
- `app/routes/reactions.py`
- `app/routes/admin.py` comment moderation endpoints
- `app/services/comment_service.py`
- `app/services/reaction_service.py`
- `app/utils/sanitize.py`

## Main Frontend Files

- `frontend/components/products/ReactionBar.tsx`
- `frontend/components/products/CommentThread.tsx`
- `frontend/components/products/CommentForm.tsx`
- `frontend/components/products/CommentCard.tsx`
- `frontend/components/products/ProductSocialSection.tsx`

## Reactions

Reactions are session-scoped.

Flow:

```text
user toggles reaction
  -> POST /v1/products/{id}/reactions
  -> validate product is active
  -> rate-limit toggle activity
  -> insert/delete reaction row
  -> return aggregate counts and active state
```

Rules:

- A session can toggle supported reaction types.
- Aggregate counts are product-level.
- Toggle log supports rate limiting.
- Missing/inactive products reject.

## Comments

Flow:

```text
user posts comment
  -> route resolves session and optional user
  -> display name resolved
  -> comment_service validates product, name, body
  -> rate limits checked
  -> text sanitized and stored
  -> public list returns unsanitized display text safely
```

Validation includes:

- display name length 2 to 50
- display name has at least one letter
- comment body length 1 to 500
- blocklist checks
- URL-only body rejection
- max 3 comments per session per product
- max 10 comments per session per hour

## Moderation

Admin can:

- list all comments with product context
- filter by product where supported
- delete comments

Comments are hard-deleted during moderation.

## GDPR Note

Comment body can contain PII. Erasure design treats comments as deleteable, not anonymized financial records.

## Safe Change Checklist

- Product must be active before comment/reaction.
- Rate limits still apply.
- Free text is sanitized.
- Admin delete works.
- Frontend handles empty comments and API errors.
- Reaction counts stay consistent after toggle.

