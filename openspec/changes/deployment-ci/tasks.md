## 1. GitHub Actions CI Workflow

- [ ] 1.1 Create `.github/workflows/ci.yml` with lint job (ruff check .)
- [ ] 1.2 Add test job (pytest tests/ -v) that depends on lint passing
- [ ] 1.3 Add deploy job — runs only on main branch, depends on test job passing
- [ ] 1.4 Deploy job: SSH into VPS using secrets (VPS_HOST, VPS_USER, VPS_SSH_KEY), execute deploy script
- [ ] 1.5 Add `requirements-dev.txt` with ruff, pytest, httpx (test client)

## 2. Server Provisioning Script

- [ ] 2.1 Create `deploy/setup.sh` — install Python 3.11, pip, venv, nginx, certbot via apt
- [ ] 2.2 Add user creation: `atelier` user with home directory, SSH authorized_keys from GitHub
- [ ] 2.3 Create directory structure: /opt/atelier/{app,venv,data,backups,scripts}
- [ ] 2.4 Create virtualenv: /opt/atelier/venv with Python 3.11
- [ ] 2.5 Clone git repository to /opt/atelier/app
- [ ] 2.6 Configure firewall (ufw): allow 22, 80, 443 only
- [ ] 2.7 Add sudoers rule: atelier can restart atelier-* services and reload nginx without password
- [ ] 2.8 Make script idempotent (all commands use `--if-not-exists` patterns or conditional checks)

## 3. Systemd Service Files

- [ ] 3.1 Create `deploy/atelier-api.service` — uvicorn --workers 2, EnvironmentFile=/opt/atelier/.env, Restart=always, RestartSec=5, User=atelier
- [ ] 3.2 Create `deploy/atelier-ml.service` — python -m app.jobs.ml_compute --loop --interval 1800, same restart/user config
- [ ] 3.3 Add StartLimitBurst=5 and StartLimitIntervalSec=30 to prevent infinite restart loops
- [ ] 3.4 Add install/enable steps to setup.sh (systemctl enable atelier-api atelier-ml)

## 4. Nginx Configuration

- [ ] 4.1 Create `deploy/nginx.conf` — server block with HTTP→HTTPS redirect
- [ ] 4.2 Add HTTPS server block: proxy_pass to 127.0.0.1:8000, set forwarding headers (X-Real-IP, X-Forwarded-For, X-Forwarded-Proto)
- [ ] 4.3 Add client_max_body_size 10m for request size limiting
- [ ] 4.4 Add proxy_buffering on with appropriate buffer sizes
- [ ] 4.5 Add SSL certificate paths (Let's Encrypt locations)
- [ ] 4.6 Add certbot setup step to setup.sh (certbot --nginx -d <domain>)
- [ ] 4.7 Verify certbot auto-renewal timer is enabled (systemctl status certbot.timer)

## 5. Deploy Script

- [ ] 5.1 Create `deploy/deploy.sh` — git pull origin main
- [ ] 5.2 Add pip install -r requirements.txt --quiet (in venv)
- [ ] 5.3 Add schema initialization: python -c "from app.db.schema import init_db; init_db()" + SQLite init
- [ ] 5.4 Add pip cache cleanup: pip cache purge (prevent disk fill)
- [ ] 5.5 Add service restart: sudo systemctl restart atelier-api
- [ ] 5.6 Add health check verification: curl -sf http://localhost:8000/health || exit 1
- [ ] 5.7 Set script to exit on any error (set -e) and log timestamp on completion

## 6. Backup Script

- [ ] 6.1 Create `deploy/backup.sh` — SQLite backup using `sqlite3 .backup` command
- [ ] 6.2 Add DuckDB backup: acquire .batch.lock (flock), copy duckdb.db, release lock
- [ ] 6.3 Add retry logic: if lock unavailable, wait 60s, retry up to 3 times
- [ ] 6.4 Add compression: tar -czf backup-YYYY-MM-DD.tar.gz sqlite + duckdb backups
- [ ] 6.5 Add retention: find /opt/atelier/backups -mtime +7 -delete (keep most recent regardless)
- [ ] 6.6 Add output logging: files created, sizes, files deleted, duration
- [ ] 6.7 Add cron entry documentation: `0 3 * * * /opt/atelier/scripts/backup.sh`

## 7. Environment & Configuration

- [ ] 7.1 Create `deploy/.env.example` — template with all required vars (ATELIER_ADMIN_API_KEY, ATELIER_JWT_SECRET, ATELIER_GOOGLE_CLIENT_ID, ATELIER_GOOGLE_CLIENT_SECRET, ATELIER_GOOGLE_REDIRECT_URI, ATELIER_DATA_DIR, ATELIER_ALLOWED_ORIGINS)
- [ ] 7.2 Create `deploy/logrotate.conf` — rotate /var/log/atelier/*.log daily, keep 14 days, compress
- [ ] 7.3 Add logrotate install step to setup.sh (copy conf to /etc/logrotate.d/atelier)

## 8. Monitoring & Disk Management

- [ ] 8.1 Create `deploy/disk-check.sh` — check disk usage, log CRITICAL if >80%
- [ ] 8.2 Add cron entry for disk check (hourly)
- [ ] 8.3 Document UptimeRobot setup in README (manual: add HTTPS monitor on /health endpoint)

## 9. Documentation

- [ ] 9.1 Create `deploy/RESTORE.md` — step-by-step restore procedure (stop services, replace files, restart, verify)
- [ ] 9.2 Create `deploy/README.md` — overview of deployment architecture, first-time setup steps, secrets to configure
- [ ] 9.3 Document rollback procedure: git revert + push, or manual git checkout + restart
