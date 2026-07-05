## ADDED Requirements

### Requirement: All traffic served over HTTPS
The system SHALL redirect all HTTP (port 80) traffic to HTTPS (port 443).

#### Scenario: HTTP redirects to HTTPS
- **WHEN** a client connects to `http://api.example.com/health`
- **THEN** nginx returns HTTP 301 redirect to `https://api.example.com/health`

### Requirement: Nginx proxies to uvicorn
Nginx SHALL forward HTTPS requests to the uvicorn backend on `127.0.0.1:8000`.

#### Scenario: Request proxied correctly
- **WHEN** a client sends `GET https://api.example.com/v1/products`
- **THEN** nginx terminates TLS and forwards the request to uvicorn on port 8000
- **AND** the response is returned to the client over HTTPS

#### Scenario: Real IP forwarded
- **WHEN** a request passes through nginx
- **THEN** headers `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto` are set for the backend

### Requirement: SSL certificates auto-renew via Let's Encrypt
The system SHALL use certbot to obtain and automatically renew TLS certificates.

#### Scenario: Initial certificate obtained
- **WHEN** `certbot --nginx -d api.example.com` runs during setup
- **THEN** a valid TLS certificate is installed and nginx is configured to use it

#### Scenario: Certificate auto-renewal
- **WHEN** the certificate is within 30 days of expiry
- **THEN** the certbot systemd timer renews it automatically and reloads nginx

#### Scenario: Renewal failure detected
- **WHEN** certificate renewal fails
- **THEN** external monitoring (UptimeRobot) detects the HTTPS error and sends an alert

### Requirement: Nginx buffers slow clients
Nginx SHALL buffer request/response bodies to protect uvicorn from slow client connections.

#### Scenario: Slow client upload
- **WHEN** a client sends a large request body slowly (e.g., CSV product import)
- **THEN** nginx buffers the full request before forwarding to uvicorn (uvicorn is not held waiting)

### Requirement: Request size limited
Nginx SHALL reject request bodies larger than a configured maximum (default: 10MB).

#### Scenario: Oversized request rejected
- **WHEN** a client sends a request body larger than 10MB
- **THEN** nginx returns HTTP 413 Request Entity Too Large without forwarding to uvicorn
