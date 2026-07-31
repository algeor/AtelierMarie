# Troubleshooting

Fast paths for common breakages.

## Frontend Shows Mock Data

Check `frontend/.env.local`:

```text
NEXT_PUBLIC_USE_MOCK_API=true
```

Set it to false when testing backend contracts:

```text
NEXT_PUBLIC_USE_MOCK_API=false
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Restart the frontend dev server after env changes.

## API Returns `VALIDATION_ERROR`

Check:

- request body shape against Pydantic model
- content type is `application/json` for JSON endpoints
- locale is `en` or `bg`
- payment method/status literals
- delivery payload has matching `method` and sub-object

Backend logs include failing validation fields.

## Cart Looks Wrong After Login/Logout

Check:

- backend sends `X-Session-Rotated: true` on rotation
- frontend API client dispatches `session-rotated`
- `CartContext` refresh listener is active
- `AuthContext` refresh listener is active

## Checkout Fails With Stock Error

Check:

- product is active
- product stock >= cart quantity
- another checkout did not decrement stock first
- cart quantity does not exceed configured max

Remember: checkout uses `BEGIN IMMEDIATE` and DB stock constraint.

## Card Checkout Returns No Stripe URL

Check:

- `STRIPE_SECRET_KEY` is configured
- order was created but Stripe session creation failed
- logs for `stripe_session_create_failed`
- retry endpoint `/v1/orders/{id}/stripe-session`

## Stripe Webhook Does Nothing

Check:

- endpoint is `/v1/webhooks/stripe`
- path is in `session_skip_paths`
- raw body is used for signature verification
- `STRIPE_WEBHOOK_SECRET` matches sender
- event has `client_reference_id` matching order id
- event id is not already in `stripe_events`

## Email Not Sending

Check:

- `EMAIL_PROVIDER` value
- `EMAIL_API_KEY` for ZeptoMail
- `admin_notification_email` if admin/contact email expected
- `order_emails` row status
- `order_email_send_claims` row lease/status
- `suppressed_emails` for recipient
- template exists in the order locale

## Shipping Quote Falls Back

Check:

- Speedy/Econt credentials
- `speedy_client_id` is numeric
- courier API availability
- city/office data resolves
- free shipping threshold behavior
- logs from courier client

Fallback quote is expected during API/credential trouble. Checkout should still be possible if business rules allow it.

## Product Video Stuck

Check:

- `ffmpeg_path` and `ffprobe_path`
- `video_upload_temp_path` exists and is not public static
- `product_videos.status`
- `lease_expires_at`
- logs from `video_transcode_loop`

## Analytics Empty

Check:

- `ANALYTICS_ENABLED=true`
- production also needs `ANALYTICS_LEGAL_APPROVED=true`
- user accepted consent
- backend `analytics_consents` row has current version
- JSONL path and DuckDB path exist
- admin date range includes events

## Admin 401/403

Check:

- logged-in user is admin in DB
- admin API key configured and sent correctly where applicable
- production admin API key length
- frontend guard is not the source of truth

