# Background Workers

The app has lightweight in-process background loops. They run from FastAPI lifespan.

## Worker List

| Worker | Function | Interval | Purpose |
|---|---:|---:|---|
| Runtime cleanup | `session_cleanup_loop` | 1 hour | Expired sessions, old contact messages, analytics retention, abandoned card orders. |
| Email outbox | `email_outbox_loop` | about 15 seconds | Send queued order/contact emails. |
| Video transcode | `video_transcode_loop` | config constant | Drain queued product video transcodes. |

## Runtime Cleanup

Main function: `cleanup_runtime_records()`.

It combines:

- expired session cleanup
- old contact message cleanup
- expired analytics event cleanup
- abandoned card order cancellation

Abandoned card order behavior:

- Only touches `payment_method = 'card'`.
- Only when `payment_status in ('pending', 'failed')`.
- Only older than 24 hours.
- Does not touch COD or bank transfer orders.
- Restores stock when cancelling.

## Email Outbox Worker

Main function: `drain_all_email_outboxes()`.

It drains:

- order email outbox
- contact owner notification outbox

Why this exists:

- Checkout/admin actions commit a durable intent to email.
- Provider calls can fail/retry later.
- HTTP responses do not wait on provider reliability.

Concurrency note:

- Multiple workers can run this loop.
- Claim rows and SQLite single-writer behavior prevent duplicate active sends.

## Video Transcode Worker

Main function: `drain_video_transcodes()`.

It:

- claims queued video rows
- validates/transcodes using ffmpeg/ffprobe
- extracts poster
- marks ready or failed
- refreshes lease while long work runs

Rules:

- Failed transcode must not break product browsing.
- Raw upload temp path must not be public.
- Admin can see failure status/reason.

## Shutdown Behavior

On shutdown the app cancels all worker tasks and waits briefly.

If analytics is enabled, shutdown also loads JSONL events to DuckDB.

## What Not To Put Here

Avoid adding a new loop unless needed.

Ask first:

- Can this be part of runtime cleanup?
- Can this be a durable outbox drain?
- Can this run on explicit admin action?
- Does this need a real external scheduler instead?

