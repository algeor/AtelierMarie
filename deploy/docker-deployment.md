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

- `JWT_SECRET`
- `ADMIN_API_KEY`
- `FRONTEND_URL`
- `CORS_ORIGINS`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_MEDIA_URL`
- `NEXT_PUBLIC_SITE_URL`
- payment/email/courier credentials when those features are ready

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

## Backups

The Compose stack creates these named volumes:

- `ateliermarie_atelier_db`
- `ateliermarie_atelier_static`
- `ateliermarie_atelier_analytics`
- `ateliermarie_atelier_video_temp`

Confirm exact names with:

```bash
docker volume ls | grep atelier
```

SQLite backup:

```bash
mkdir -p /var/backups/atelier-marie
docker compose exec -T backend python - <<'PY'
import sqlite3
src = sqlite3.connect('/data/db/atelier_marie.db')
dst = sqlite3.connect('/data/db/atelier_marie-backup.db')
src.backup(dst)
dst.close()
src.close()
PY
docker run --rm -v ateliermarie_atelier_db:/data -v /var/backups/atelier-marie:/backup busybox \
  cp /data/atelier_marie-backup.db /backup/atelier_marie-$(date +%F).db
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
