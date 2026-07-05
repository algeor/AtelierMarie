## Context

AtelierMarie is a FastAPI (Python 3.11) e-commerce ML platform using SQLite + DuckDB. All application code is written but runs only locally. The target production environment is an Oracle Cloud Free Tier ARM64 VPS (4 OCPU, 24GB RAM, 200GB storage) — permanently free.

**Current state:** No deployment automation, no server config, no CI pipeline. Code must be manually pushed and services manually restarted.

**Constraints:**
- Zero budget — Oracle Free Tier VPS, GitHub Actions free tier, Let's Encrypt SSL
- Single server — no load balancer, no redundancy
- ARM64 architecture (aarch64) — all packages must support ARM
- No Docker — systemd is the process manager
- All secrets via environment variables (`.env` file, never committed to git)

## Goals / Non-Goals

**Goals:**
- Automated test + lint on every push (catch bugs before deploy)
- Zero-downtime deploy on merge to main (graceful uvicorn restart)
- HTTPS with auto-renewing certificates
- Process auto-restart on crash
- Daily automated backups with 7-day retention
- Sub-60-second deploy time (git pull + pip install + restart)
- Documented, repeatable server setup (one script)

**Non-Goals:**
- Blue-green or canary deployments
- Container orchestration (Docker, k8s)
- Infrastructure-as-code (Terraform, Pulumi)
- Multi-server or multi-region
- Paid monitoring (Datadog, PagerDuty)
- Frontend deployment (separate concern, likely CDN-based)
- Database migration framework (schemas are additive-only)

## Decisions

### 1. Git-pull deploy over Docker image push

**Decision:** Deploy by SSH → `git pull` → `pip install` → `systemctl restart`.

**Alternatives considered:**
- *Docker image build + push + pull*: Adds Docker registry, image build time, and Docker runtime overhead on ARM. More complexity for one server. Rejected.
- *rsync/scp artifacts*: Doesn't leverage git history for rollback. Rejected.
- *Heroku/Fly.io buildpack*: Vendor lock-in, and Fly free tier is more limited than Oracle. Rejected.

**Rationale:** Simplest approach that works. Git gives us rollback (`git checkout`), history, and diffing. `pip install` is idempotent. systemd restart is atomic.

### 2. Systemd over supervisor/pm2/docker-compose

**Decision:** Use systemd for process management.

**Alternatives considered:**
- *Supervisor*: Extra dependency, less native integration, no socket activation. Rejected.
- *PM2*: Node.js-centric, poor Python support. Rejected.
- *Docker Compose*: Adds container layer for no benefit on single-server. Rejected.

**Rationale:** Systemd is built into every modern Linux. Auto-restart, dependency ordering, journal logging, socket activation — all native. The `EnvironmentFile=` directive cleanly loads `.env` without sourcing shell scripts.

### 3. 2 uvicorn workers (not 1, not 4)

**Decision:** `uvicorn main:app --workers 2` in the systemd service.

**Rationale:** Oracle Free Tier has 4 vCPUs. 2 workers for the API leaves 2 CPUs for: DuckDB batch loader, analytics compute, nginx, OS. The batch loader and analytics compute both run inside the main API process lifespan (file-lock guarded) — no separate systemd service is needed for ML compute or analytics. One worker handles API while the other's event loop is briefly busy with the batch. Under-provisioning (1 worker) risks blocking; over-provisioning (4 workers) starves background jobs.

### 4. Nginx for SSL termination (not uvicorn --ssl)

**Decision:** Nginx sits in front of uvicorn, terminates TLS, and proxies to `127.0.0.1:8000`.

**Alternatives considered:**
- *uvicorn --ssl-keyfile/--ssl-certfile*: No automatic cert renewal, no connection buffering, no rate limiting. Rejected.
- *Caddy*: Auto-HTTPS is nice but less common on ARM, less documentation. Acceptable alternative, but nginx is more battle-tested. Rejected for familiarity.
- *Traefik*: Overkill for single-server, designed for Docker/k8s. Rejected.

**Rationale:** Nginx handles slow clients (buffering), connection limiting, static file serving (if needed), and integrates natively with certbot for automatic cert renewal.

### 5. Deploy user with limited sudo

**Decision:** Create a non-root `atelier` user. Grant passwordless sudo only for `systemctl restart atelier-*` and `systemctl reload nginx`.

**Rationale:** If the GitHub Actions SSH key is compromised, the attacker can deploy code and restart services — but cannot modify system config, read other users' data, or escalate to root.

```
# /etc/sudoers.d/atelier
atelier ALL=(ALL) NOPASSWD: /bin/systemctl restart atelier-api, /bin/systemctl reload nginx
```

**Note:** The `atelier-ml` systemd service previously referenced here is no longer needed. The ML batch job (recommendation precomputation) and analytics compute both run inside the main API process lifespan as asyncio tasks — they share `.batch.lock` for DuckDB write coordination. No separate systemd service is required for ML compute or analytics.

### 6. SQLite backup via `.backup` command

**Decision:** Use SQLite's built-in `.backup` command (via `sqlite3` CLI) instead of file copy.

**Alternatives considered:**
- *`cp sqlite.db`*: Unsafe if a write is in progress (WAL mode helps but not guaranteed consistent). Rejected.
- *`VACUUM INTO`*: Creates a compact copy but holds a read lock for the duration. Acceptable but `.backup` is more standard.

**Rationale:** `.backup` creates a point-in-time consistent copy even while the application is writing. It uses SQLite's internal page-level copy mechanism.

### 7. DuckDB backup via file copy during quiet window

**Decision:** Copy DuckDB file during a window when no batch loader is running (acquire the `.batch.lock` first, copy, release).

**Rationale:** DuckDB doesn't have a `.backup` equivalent for hot copies. The batch loader runs every 60s and takes <5s. The backup script acquires the same file lock, copies the file, then releases. During this window, the batch loader skips its cycle (non-blocking lock attempt fails) — at most 60s of additional event latency.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Oracle changes Free Tier terms** | Backup scripts + documentation for migration to Fly.io/Render. DuckDB rebuildable from JSONL archive. |
| **Single point of failure** | Daily backups. DuckDB reconstructable from archive. SQLite backup to Object Storage (optional). |
| **SSH key compromised** | Limited sudo. Key rotation documented. GitHub branch protection requires PR review. |
| **Let's Encrypt renewal fails** | UptimeRobot alerts on HTTPS errors. Certbot cron runs twice daily (built-in retry). |
| **Disk full during deploy** | Daily cleanup cron. Disk usage monitoring (alert at 80%). pip cache pruned in deploy script. |
| **pip install introduces breaking change** | `requirements.txt` pinned versions. No `>=` specifiers in production deps. |
| **Rollback needed** | `git checkout <sha> + restart`. Data is append-only — no destructive schema changes to undo. |

## Migration Plan

**Initial deployment (one-time):**
1. Provision Oracle Free Tier instance (manual — ARM Ampere A1)
2. Point DNS A record to VPS IP (manual)
3. Run `deploy/setup.sh` on the VPS (provisions everything)
4. Copy `.env.example` to `.env`, fill in secrets
5. Run `deploy/deploy.sh` for initial deploy
6. Verify: `curl https://api.atelier.example.com/health`
7. Set up UptimeRobot monitor (manual)
8. Add GitHub Secrets (VPS_HOST, VPS_USER, VPS_SSH_KEY)
9. Push to main — CI deploys automatically

**Subsequent deploys:** Fully automated via GitHub Actions on merge to main.

**Rollback:** `git revert HEAD --no-edit && git push` (triggers redeploy of previous state).

## Open Questions

- **Domain name**: What domain will be used? (Affects nginx config and Let's Encrypt cert)
- **Object Storage backup**: Should we sync daily backups to Oracle Object Storage (free 10GB), or is local backup sufficient for MVP?
