# VPS Launch And Stress Test Plan

This plan is for launching Atelier Marie on the netcup x86 VPS using Docker
Compose, host Nginx, HTTPS, SQLite, and local media storage.

## Target Capacity Assumption

The current single-VPS deployment should be enough for an early boutique store.
Use these as planning estimates until a live stress test proves real numbers:

- Browsing traffic: roughly 500-2,000 visitors/hour.
- Active shoppers: roughly 100-500 shoppers/hour.
- Orders/checkouts: tens to low hundreds of orders/hour.

SQLite write contention and media/video processing are the most likely first
bottlenecks, not raw CPU.

## Target Architecture

- VPS: netcup x86, Ubuntu 24.04.
- Public web: Nginx on ports 80 and 443.
- Frontend: Next.js container bound to `127.0.0.1:3000`.
- Backend: FastAPI container bound to `127.0.0.1:8001`.
- Database: SQLite in Docker volume `atelier_db`.
- Media/static uploads: Docker volume `atelier_static`.
- Analytics data: Docker volume `atelier_analytics`.
- TLS: Let's Encrypt via Certbot.
- Deployment: `docker compose --env-file .env.docker up -d --build`.

## Launch Steps

1. SSH into the VPS.
2. Create a non-root deploy user, for example `atelier`.
3. Install base packages: Git, Nginx, Certbot, UFW, Docker Engine, Docker Compose plugin.
4. Open only SSH, HTTP, and HTTPS in the firewall.
5. Point domain DNS `A` records to the VPS IPv4.
6. Clone the repo to `/opt/atelier-marie/app`.
7. Copy `.env.docker.example` to `.env.docker` and set production secrets/domain values.
8. Build and start containers with Docker Compose.
9. Configure host Nginx to proxy `/` to frontend and `/v1`, `/health`, `/static` to backend.
10. Issue HTTPS certificates with Certbot.
11. Confirm storefront, API health, admin, checkout, and product upload flows.
12. Add daily backups for SQLite and static/media files.

## Required Production Env Values

At minimum, set these in `.env.docker`:

```env
ENVIRONMENT=production
JWT_SECRET=<long-random-secret>
ADMIN_API_KEY=<long-random-admin-key-at-least-32-chars>
FRONTEND_URL=https://yourdomain.com
CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]
SESSION_COOKIE_SECURE=true

NEXT_PUBLIC_API_URL=https://yourdomain.com
NEXT_PUBLIC_MEDIA_URL=https://yourdomain.com/static
NEXT_PUBLIC_SITE_URL=https://yourdomain.com
NEXT_PUBLIC_USE_MOCK_API=false

ANALYTICS_ENABLED=false
ANALYTICS_LEGAL_APPROVED=false
```

Generate secrets with:

```bash
openssl rand -base64 48
```

## Live Verification Checklist

Before stress testing, confirm:

- `https://yourdomain.com` loads.
- `https://yourdomain.com/health` returns `{"status":"ok"}`.
- Storefront browsing works in English and Bulgarian.
- Product listing/detail pages load real API data.
- Cart add/update/remove works.
- Checkout creates an order.
- Admin auth works.
- Admin order/product pages load.
- Product image upload works.
- Email/payment/delivery integrations are either tested or intentionally disabled.
- Backups produce restorable files.

## Stress Test Goals

Run the first stress test after the live deployment is stable. The goal is to
find the real bottleneck and set a safe operating limit, not to chase huge
numbers.

Test separately:

1. Homepage and catalog browsing.
2. Product detail pages.
3. Cart API operations.
4. Checkout/order creation.
5. Admin image upload separately, not during customer traffic tests.

Do not stress test payment provider live endpoints with real payment methods.
Use test mode or keep payment routes out of the first load test.

## Suggested Tools

Use one of:

- `k6` for realistic HTTP scenarios.
- `wrk` for simple high-throughput endpoint checks.
- `hey` for quick one-command smoke load.

`k6` is preferred because it can model browsing, cart, and checkout flows.

## Initial Load Test Plan

Start gently and increase only if the system stays healthy.

### Round 1: Browsing Smoke

- Duration: 5 minutes.
- Virtual users: 10.
- Routes: homepage, product listing, product detail.
- Expected: no errors, stable response times.

### Round 2: Boutique Traffic

- Duration: 10 minutes.
- Virtual users: 25-50.
- Routes: homepage, products, product detail, cart read.
- Expected: p95 response time under roughly 1 second for cached/static-heavy pages,
  under roughly 2 seconds for API-backed pages.

### Round 3: Shopping Flow

- Duration: 10 minutes.
- Virtual users: 10-25.
- Flow: browse, add to cart, update cart, start checkout, create test order.
- Expected: no database lock errors, no 5xx spikes, stable CPU/RAM.

### Round 4: Order Spike

- Duration: 5 minutes.
- Virtual users: 25-50.
- Flow: checkout/order creation only with safe test data.
- Expected: identify SQLite write ceiling and observe whether order creation slows
  or fails under contention.

## Metrics To Watch During Tests

On the VPS:

```bash
docker stats
docker compose logs -f backend
docker compose logs -f frontend
sudo journalctl -u nginx -f
htop
df -h
free -h
```

Watch for:

- 5xx responses.
- SQLite `database is locked` errors.
- Backend memory growth.
- High CPU sustained near 100%.
- Disk filling from logs/media/temp files.
- Slow product image/video processing.

## Success Criteria

The first live deployment is healthy if it can handle:

- 1,000 browsing visitors/hour equivalent.
- 100 orders/hour equivalent.
- No sustained 5xx errors.
- No SQLite lock errors during normal expected traffic.
- p95 response times acceptable for storefront browsing and checkout.

## If The Server Struggles

Apply fixes in this order:

1. Add/verify static asset caching in Nginx.
2. Ensure product media is optimized and not oversized.
3. Avoid admin video/image processing during peak traffic.
4. Tune Uvicorn worker count carefully after measuring memory.
5. Add Nginx rate limits for auth/admin/checkout routes.
6. Move media to object storage if upload/static serving becomes heavy.
7. Move from SQLite to Postgres if checkout/write contention becomes real.
8. Upgrade VPS RAM/CPU only after the software bottleneck is understood.

## Backup Requirement Before Stress Testing

Take a fresh backup before any write-heavy test:

```bash
mkdir -p /var/backups/atelier-marie
docker compose exec -T backend python - <<'PY'
import sqlite3
src = sqlite3.connect('/data/db/atelier_marie.db')
dst = sqlite3.connect('/data/db/atelier_marie-before-stress.db')
src.backup(dst)
dst.close()
src.close()
PY
docker run --rm -v ateliermarie_atelier_db:/data -v /var/backups/atelier-marie:/backup busybox \
  cp /data/atelier_marie-before-stress.db /backup/atelier_marie-before-stress-$(date +%F-%H%M).db
```

Also back up media:

```bash
docker run --rm -v ateliermarie_atelier_static:/data -v /var/backups/atelier-marie:/backup busybox \
  tar -czf /backup/static-before-stress-$(date +%F-%H%M).tar.gz -C /data .
```
