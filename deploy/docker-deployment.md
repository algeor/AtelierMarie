# Docker Deployment

This deployment runs Atelier Marie as two containers on a VPS:

- `backend`: FastAPI/Uvicorn on `127.0.0.1:8001`
- `frontend`: Next.js on `127.0.0.1:3000`

Nginx stays on the host and is the only public web listener. Persistent runtime
data lives in Docker volumes, not inside disposable containers.

## Files

| File | Purpose |
|------|---------|
| `Dockerfile.backend` | Python/FastAPI runtime with `ffmpeg` for product video processing. |
| `frontend/Dockerfile` | Multi-stage Next.js production image. |
| `compose.yml` | Production-like two-service Compose stack. |
| `.env.docker.example` | Template for backend secrets and frontend build-time public env. |

## First Server Setup

Install Docker Engine and the Compose plugin on the VPS. On Ubuntu, use Docker's
official repository rather than the old distro package if possible.

Clone the repository:

```bash
git clone <repo-url> /opt/atelier-marie
cd /opt/atelier-marie
```

Create the Docker env file:

```bash
cp .env.docker.example .env.docker
chmod 600 .env.docker
```

Edit `.env.docker` and set real values for:

- `POSTGRES_PASSWORD` (local Compose Postgres password)
- `POSTGRES_HOST_PORT`, `BACKEND_HOST_PORT`, `FRONTEND_HOST_PORT` when local ports are occupied
- `JWT_SECRET`
- `ADMIN_API_KEY`
- `FRONTEND_URL`
- `CORS_ORIGINS`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_MEDIA_URL`
- `NEXT_PUBLIC_SITE_URL`
- payment/email/courier credentials when those features are ready

By default, Compose points `backend` and `migrate` at the in-stack `postgres` service.
The host ports are configurable with `POSTGRES_HOST_PORT`, `BACKEND_HOST_PORT`,
and `FRONTEND_HOST_PORT`; update `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_MEDIA_URL`,
`NEXT_PUBLIC_SITE_URL`, and OAuth callback URLs to match any public port/origin changes.

To use a managed/external Postgres without editing `compose.yml`, set
`COMPOSE_DATABASE_URL` and include the external DB override file:

```bash
COMPOSE_DATABASE_URL=postgresql://user:password@host:5432/database \
  docker compose -f compose.yml -f compose.external-db.yml up --build frontend
```

The override removes the app dependency on the local `postgres` service and uses
`COMPOSE_DATABASE_URL` for both `migrate` and `backend`.

Generate secrets with:

```bash
openssl rand -base64 48
```

## Build And Start

Compose reads `.env.docker` for the backend container, and Compose variable
interpolation also uses `.env.docker` when passed with `--env-file`.

```bash
docker compose --env-file .env.docker up -d --build
```

Check health:

```bash
docker compose ps
curl http://127.0.0.1:8001/health
curl -I http://127.0.0.1:3000
```

View logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

## Database Migrations

Schema lives entirely in Alembic migrations — there is no runtime schema
creation. The Compose stack runs a one-shot `migrate` service that executes
`alembic upgrade head` after Postgres is healthy and before the backend starts;
`backend` depends on `migrate` completing successfully, so a normal
`docker compose up` always brings the database to head first.

The backend also verifies at startup that the connected database is at the
Alembic head and fails fast otherwise, so a missing or stale migration surfaces
immediately instead of causing runtime errors.

To run migrations manually (e.g. after `git pull` on an already-running stack):

```bash
docker compose --env-file .env.docker run --rm migrate
```

This is a **pre-launch application**, so there is no live production database to
migrate off SQLite — the first `alembic upgrade head` against a fresh Postgres
volume creates the launch schema and seed rows outright. No data cutover is
required.

## Nginx Host Proxy

Use this as the site server block, then run Certbot.

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 27m;

    location /static/ {
        proxy_pass http://127.0.0.1:8001/static/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /v1/ {
        proxy_pass http://127.0.0.1:8001/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8001/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable HTTPS:

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

The rate-limit config in `deploy/nginx-ratelimit.conf` can be layered into this
server block after the basic site is live.

## Updating The App

`NEXT_PUBLIC_*` values are baked into the frontend image, so rebuild after
changing them.

```bash
cd /opt/atelier-marie
git pull
docker compose --env-file .env.docker up -d --build
docker image prune -f
```

After a successful deploy, refresh the public Cookie Policy inventory from the
live storefront audit. For Docker, the browser audit can run on the host, but
the DB write should happen inside the backend container:

```bash
FRONTEND_URL=https://yourdomain.com \
COOKIE_AUDIT_SYNC_COMMAND="docker compose --env-file .env.docker exec -T backend python scripts/sync_cookie_inventory.py" \
  make audit-cookie-inventory
```

The audit launches Chrome, visits public storefront routes, detects cookies and
browser storage, and writes the inventory into the backend database. If Chrome
is not available on the deploy host, run the registry-only fallback until a
browser-capable cron runner is configured:

```bash
docker compose --env-file .env.docker exec -T backend python scripts/sync_cookie_inventory.py
```

## Backups

The Compose stack creates these named volumes:

- `ateliermarie_atelier_postgres`
- `ateliermarie_atelier_static`
- `ateliermarie_atelier_analytics`
- `ateliermarie_atelier_video_temp`

Confirm exact names with:

```bash
docker volume ls | grep atelier
```

Postgres backup (logical dump via `pg_dump` against the running `postgres`
service):

```bash
mkdir -p /var/backups/atelier-marie
docker compose --env-file .env.docker exec -T postgres \
  pg_dump -U atelier -d atelier_marie --format=custom \
  > /var/backups/atelier-marie/atelier_marie-$(date +%F).dump
```

Restore into an empty database with `pg_restore`:

```bash
docker compose --env-file .env.docker exec -T postgres \
  pg_restore -U atelier -d atelier_marie --clean --if-exists \
  < /var/backups/atelier-marie/atelier_marie-YYYY-MM-DD.dump
```

Static/media backup:

```bash
docker run --rm -v ateliermarie_atelier_static:/data -v /var/backups/atelier-marie:/backup busybox \
  tar -czf /backup/static-$(date +%F).tar.gz -C /data .
```

Sync `/var/backups/atelier-marie` off the VPS regularly.

## Local Smoke Test

For a local production-style smoke test, set these values in `.env.docker`:

```env
ENVIRONMENT=development
JWT_SECRET=dev-secret-do-not-use-in-production
ADMIN_API_KEY=local-docker-admin-key-at-least-32-chars
CORS_ORIGINS=["http://localhost:3000"]
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_MEDIA_URL=http://localhost:8001/static
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_USE_MOCK_API=false
SESSION_COOKIE_SECURE=false
```

Then run:

```bash
docker compose --env-file .env.docker up -d --build
```
