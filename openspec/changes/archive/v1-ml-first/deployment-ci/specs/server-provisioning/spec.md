## ADDED Requirements

### Requirement: One-time setup script provisions all server dependencies
The setup script SHALL install Python 3.11, nginx, certbot, and create the application user and directory structure.

#### Scenario: Fresh Ubuntu server provisioned
- **WHEN** `deploy/setup.sh` is executed on a fresh Ubuntu 22.04 ARM64 server
- **THEN** Python 3.11, pip, venv, nginx, and certbot are installed
- **AND** an `atelier` user is created with a home directory
- **AND** `/opt/atelier/app`, `/opt/atelier/venv`, `/opt/atelier/data`, `/opt/atelier/backups` directories exist

#### Scenario: Setup is idempotent
- **WHEN** `deploy/setup.sh` is run a second time on an already-provisioned server
- **THEN** it completes without error (all install commands are idempotent)

### Requirement: Setup creates virtualenv with correct Python version
The setup script SHALL create a Python 3.11 virtualenv at `/opt/atelier/venv`.

#### Scenario: Virtualenv created
- **WHEN** setup completes
- **THEN** `/opt/atelier/venv/bin/python --version` reports Python 3.11.x

### Requirement: Setup configures firewall
The setup script SHALL open ports 22 (SSH), 80 (HTTP), and 443 (HTTPS) and deny all other inbound traffic.

#### Scenario: Only required ports open
- **WHEN** setup completes
- **THEN** iptables (or ufw) allows inbound on ports 22, 80, 443 only

### Requirement: Setup grants limited sudo to deploy user
The setup script SHALL configure passwordless sudo for the `atelier` user restricted to restarting application services and reloading nginx.

#### Scenario: Deploy user can restart services
- **WHEN** `atelier` user runs `sudo systemctl restart atelier-api`
- **THEN** the command succeeds without password prompt

#### Scenario: Deploy user cannot escalate privileges
- **WHEN** `atelier` user runs `sudo su` or `sudo bash`
- **THEN** the command is denied

### Requirement: Setup clones the application repository
The setup script SHALL clone the git repository to `/opt/atelier/app`.

#### Scenario: Repository cloned
- **WHEN** setup completes
- **THEN** `/opt/atelier/app/.git` exists and contains the application code
