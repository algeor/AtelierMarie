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

Product image uploads are capped at 25 MB by the app. Set the matching Nginx
limit in the production `server { }` block, or at the exact image-upload
location if larger upload routes are added later:

```nginx
client_max_body_size 25m;
```

Keep this at `25m` for image uploads. If product video uploads need a larger
limit, set that only on the video-upload location so image uploads still fail
fast at the proxy.

## Admin API key

The backend enforces `admin_api_key` >= 32 characters when
`environment != "development"` (see `app/config.py`). Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Store it in the systemd unit's `Environment=` or an EnvironmentFile — never
commit it. Rotate on any suspected leak. Comparison uses `hmac.compare_digest`
in `app/dependencies/auth.py`, so length variations do not leak via timing.

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
