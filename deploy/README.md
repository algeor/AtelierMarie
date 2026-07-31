# Atelier Marie — Deployment

Reference config and notes for deploying AtelierMarie to the target host
(Oracle Cloud Free Tier VPS, systemd, Nginx front-end).

## Files

| File | Purpose |
|------|---------|
| `nginx-ratelimit.conf` | Nginx `limit_req_zone` / `map` directives (http context) plus a commented example `server { }` block with `limit_req`, custom 429 handler, and reverse-proxy setup. |
| `free-deployment-plan.md` | Narrative plan for the Oracle Cloud Free Tier deployment (VPS sizing, systemd units, backup strategy). |

## Wiring `nginx-ratelimit.conf` into Nginx

The `limit_req_zone` and `map` directives MUST be in the `http { }` context.
Two options:

**Option A — drop-in (recommended):** Nginx auto-includes any
`*.conf` in `/etc/nginx/conf.d/`, which is already inside `http { }`:

```bash
sudo cp deploy/nginx-ratelimit.conf /etc/nginx/conf.d/ratelimit.conf
```

**Option B — explicit include:** add to your main `nginx.conf` inside `http { }`:

```nginx
http {
    # ... existing directives ...
    include /etc/nginx/atelier/ratelimit.conf;
}
```

Then copy the example `server { }` block from the bottom of
`nginx-ratelimit.conf` into your site's server file (adapt `server_name`,
TLS cert paths, and upstream ports as needed). Reload with:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Upload body size

Product image uploads are capped at 25 MB by the app. Set the Nginx request
body limit slightly higher so multipart form overhead does not make an exact
25 MB file fail at the proxy. Put this in the production `server { }` block,
or at the exact image-upload location if larger upload routes are added later:

```nginx
client_max_body_size 27m;
```

Keep this at `27m` for image uploads; the app remains the source of truth for
the 25 MB file cap. If product video uploads need a larger limit, set that only
on the video-upload location so image uploads still fail fast at the proxy.

Stripe and ZeptoMail webhook endpoints cap raw request bodies at 64 KB in the
app. Keep the reverse-proxy limit aligned for `/v1/webhooks/stripe` and
`/v1/webhooks/zeptomail` so oversized payloads fail before signature work:

```nginx
location /v1/webhooks/stripe {
    client_max_body_size 64k;
    proxy_pass http://127.0.0.1:8001;
}

location /v1/webhooks/zeptomail {
    client_max_body_size 64k;
    proxy_pass http://127.0.0.1:8001;
}
```

## Stripe payments

Stripe secrets are environment-only. Do not store them in admin settings or in
frontend env files. Configure the backend environment with:

```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SUCCESS_URL=https://theateliermarie.com/orders/{order_id}/confirmation?token={payment_return_token}
STRIPE_CANCEL_URL=https://theateliermarie.com/orders/{order_id}/retry-payment?token={payment_return_token}
```

Admin-managed payment method settings live at `/admin/settings/payments` and are
stored in the database. Production card checkout cannot be enabled unless Stripe
configuration health reports live keys and a webhook secret.

Before enabling live card payments, verify local webhook handling with Stripe CLI
and repeat the same flow against the production webhook endpoint after deployment.
The local verification command record is in `docs/test-plans/payment-integration.md`.

### Memory headroom

Each in-flight image upload is memory-heavy: the 25 MB body is buffered in
memory, then Pillow decodes it (up to the 25-megapixel cap ≈ 75 MB as raw RGB)
and produces three derivatives (thumbnail, main, zoom). Peak resident memory can
reach a few hundred MB per concurrent upload. On the single 1 GB Oracle Free
Tier VPS this is safe for the expected single-admin usage, but a handful of
overlapping uploads could exhaust RAM. Uploads run off the request event loop
(`run_in_threadpool`), so customer traffic is not stalled; if concurrent admin
uploads ever become common, add a small upload concurrency limit rather than
raising RAM blindly.


## Admin API key

The backend enforces `admin_api_key` >= 32 characters when
`environment != "development"` (see `app/config.py`). Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Store it in the systemd unit's `Environment=` or an EnvironmentFile — never
commit it. Rotate on any suspected leak. Comparison uses `hmac.compare_digest`
in `app/dependencies/auth.py`, so length variations do not leak via timing.

## First-party analytics production gate

Analytics is disabled by default and must stay disabled until the consent popup,
privacy/cookie policy copy, and admin analytics monitoring are live. Production
startup refuses `ANALYTICS_ENABLED=true` unless legal approval is explicitly
recorded through `ANALYTICS_LEGAL_APPROVED=true`.

After owner/legal approval of the English and Bulgarian privacy/cookie copy,
set these backend environment variables in the production systemd unit or
EnvironmentFile:

```bash
ANALYTICS_ENABLED=true
ANALYTICS_LEGAL_APPROVED=true
ANALYTICS_DATA_DIR=/var/lib/atelier-marie/analytics
ANALYTICS_EVENTS_JSONL_PATH=/var/lib/atelier-marie/analytics/events.jsonl
ANALYTICS_DUCKDB_PATH=/var/lib/atelier-marie/analytics/analytics.duckdb
ANALYTICS_CONSENT_VERSION=2026-07-31
ANALYTICS_RETENTION_DAYS=395
ANALYTICS_DELIVERY_TOLERANCE=0
```

Create the analytics directory with ownership matching the backend service user,
and include it in operational backups if analytics reports must survive a host
rebuild. If legal approval is withdrawn or the dashboard shows delivery issues,
set `ANALYTICS_ENABLED=false` and restart the backend; the storefront will keep
working and the consent UI remains available for future preferences.

## Product video processing

Product video uploads require `ffmpeg` and `ffprobe` on the backend host:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

If either binary is missing, only video upload/transcode is unavailable; the
storefront, cart, checkout, and normal product browsing continue to work. Raw
uploads are staged under `VIDEO_UPLOAD_TEMP_PATH` and normalized MP4/poster
files are stored under `STATIC_FILE_PATH/products`. Keep
`MAX_VIDEO_UPLOAD_BYTES` bounded for disk protection; the default is 200 MB.

## Running behind a reverse proxy / load balancer

If Nginx sits behind another proxy or LB (e.g. Cloudflare, an Oracle Cloud
load balancer), `$binary_remote_addr` will be the proxy's IP — every request
will look like it's from the same client and rate limits will apply
globally. To fix, add to the site's `server { }` block:

```nginx
# Trust the proxy range(s) that front this box.
set_real_ip_from 10.0.0.0/8;         # example: internal LB CIDR
set_real_ip_from 173.245.48.0/20;    # example: Cloudflare
real_ip_header   X-Forwarded-For;
real_ip_recursive on;
```

After this, `$binary_remote_addr` reflects the real client IP and the
per-IP zones (`auth`, `admin`, `checkout_ip_backstop`) work as intended.

## Testing rate limits

With the config live, exceed the auth limit and confirm the JSON envelope:

```bash
for i in $(seq 1 10); do
  curl -i -s -o /dev/null -w '%{http_code}\n' \
    -X POST https://ateliermarie.com/v1/auth/login
done
# Expect: 200 (or 4xx from the app) up to burst=5+1, then 429 for the rest.

curl -i -X POST https://ateliermarie.com/v1/auth/login
# Sample 429 response:
#   HTTP/1.1 429 Too Many Requests
#   Retry-After: 60
#   Content-Type: application/json
#
#   {"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please try again later.", "details": null}}
```

## Deployment context

- **Host:** Oracle Cloud Free Tier (Ampere A1 / VM.Standard.E2.1.Micro).
- **Process manager:** systemd — one unit for `uvicorn` (backend, port 8001)
  and one for `next start` (frontend, port 3000). Both listen on localhost;
  Nginx is the only public listener.
- **TLS:** Let's Encrypt via `certbot --nginx`.
- **Backups:** `sqlite3 .backup` cron + off-box sync (see
  `free-deployment-plan.md`).

Keep this file terse — deep operational runbooks belong in
`free-deployment-plan.md` or the project wiki.
