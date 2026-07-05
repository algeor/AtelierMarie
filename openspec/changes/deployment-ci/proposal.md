## Why

The AtelierMarie platform has all application components designed but no way to run them in production. There is no CI pipeline, no server configuration, no process management, and no automated deployment. Without this, the platform exists only on a developer's local machine — it cannot serve real traffic, and code changes require manual SSH + restart.

## What Changes

- Add GitHub Actions CI workflow: lint (ruff), test (pytest), deploy (SSH to VPS) on push to main
- Create server provisioning script: installs Python 3.11, nginx, certbot, creates app user and directory structure
- Create deploy script: git pull, pip install, schema init, graceful systemd restart
- Add systemd service files for API (uvicorn --workers 2) and ML batch job
- Add nginx reverse proxy config with SSL termination (Let's Encrypt)
- Add automated daily backup script (SQLite .backup + DuckDB copy, 7-day retention)
- Add .env.example template documenting all required environment variables
- Add log rotation configuration for uvicorn access/error logs
- Add disk usage monitoring cron (alerts at >80% usage)

## Capabilities

### New Capabilities

- `ci-pipeline`: GitHub Actions workflow that runs linting and tests on every push/PR, and deploys to production on merge to main
- `server-provisioning`: One-time setup script that configures the Oracle Free Tier VPS with all dependencies, users, directories, and services
- `process-management`: Systemd service definitions for the API and ML batch job with auto-restart, environment files, and graceful shutdown
- `reverse-proxy-ssl`: Nginx configuration for HTTPS termination, rate limiting, and request proxying to uvicorn
- `backup-recovery`: Automated daily backup of SQLite and DuckDB with retention policy and restore documentation

### Modified Capabilities

<!-- No existing spec-level behavior changes — this is infrastructure, not application logic -->

## Impact

- **New files**: `deploy/` directory (6 scripts/configs), `.github/workflows/ci.yml`
- **Server**: Oracle Free Tier VPS configured with nginx, certbot, systemd services, cron jobs
- **GitHub**: Repository secrets required (VPS_HOST, VPS_USER, VPS_SSH_KEY)
- **DNS**: Domain must point to VPS IP (manual step, documented)
- **Network**: Ports 80, 443, 22 opened on VPS firewall
- **Dependencies**: No new Python dependencies. Server-side: nginx, certbot, logrotate (system packages)
