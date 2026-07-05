## ADDED Requirements

### Requirement: API runs as a systemd service
The application API SHALL run as a systemd service named `atelier-api` using uvicorn with 2 workers.

#### Scenario: Service starts on boot
- **WHEN** the server boots
- **THEN** `atelier-api.service` starts automatically (WantedBy=multi-user.target)

#### Scenario: Service uses environment file
- **WHEN** `atelier-api.service` starts
- **THEN** it loads environment variables from `/opt/atelier/.env`

### Requirement: API auto-restarts on crash
The systemd service SHALL automatically restart the API process if it crashes.

#### Scenario: Process dies unexpectedly
- **WHEN** the uvicorn process exits with a non-zero exit code
- **THEN** systemd restarts it after a 5-second delay (Restart=always, RestartSec=5)

#### Scenario: Repeated crashes trigger failure state
- **WHEN** the process crashes more than 5 times within 30 seconds
- **THEN** systemd stops attempting restarts (StartLimitBurst=5, StartLimitIntervalSec=30)

### Requirement: Graceful shutdown on deploy
The service SHALL finish in-flight requests before shutting down when restarted.

#### Scenario: Active requests complete during restart
- **WHEN** `systemctl restart atelier-api` is issued while requests are in-flight
- **THEN** uvicorn receives SIGTERM, finishes active requests (up to 30s graceful timeout), then exits
- **AND** systemd starts the new process after the old one exits

### Requirement: ML batch job runs as a separate service
An optional systemd service `atelier-ml` SHALL run the ML computation loop as a separate process.

#### Scenario: ML service runs independently
- **WHEN** `atelier-ml.service` is enabled and started
- **THEN** it runs `python -m app.jobs.ml_compute --loop --interval 1800` as the `atelier` user

#### Scenario: ML service is optional
- **WHEN** `atelier-ml.service` is not enabled
- **THEN** the API still functions (ML compute runs in-process via the batch loader background task as fallback)

### Requirement: Services run as unprivileged user
All application services SHALL run as the `atelier` user, not root.

#### Scenario: Process ownership
- **WHEN** `atelier-api` is running
- **THEN** `ps aux | grep uvicorn` shows the process owned by user `atelier`
