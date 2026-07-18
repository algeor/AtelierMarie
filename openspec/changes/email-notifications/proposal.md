# Email Notifications for Order Status Changes

## Problem

Customers place orders but receive no email confirmation or updates as their order progresses through the fulfillment pipeline. For a luxury candle brand, this silence erodes trust and generates manual "where's my order?" inquiries.

The shop owner also has no push notification when a new order arrives — they must manually check the admin dashboard.

## Proposed Solution

Add a transactional email integration that fires on every order state transition, delivering bilingual (EN/BG) notifications to customers and admin alerts to the shop owner.

## Decisions Made

| Question | Answer |
|----------|--------|
| Brand name | Atelier Marie (real name) |
| Domain | Not yet registered — need to acquire one (`.com`, `.bg`, or both — check availability) |
| Registrar/DNS | Not yet — will be set up alongside domain purchase |
| Email provider | **Resend** (100 emails/day free, modern API, great DX) |
| Delivered email | Yes — send "your order has arrived" notification |
| Tracking numbers | Yes — full tracking info (number + carrier + link) on ship |
| Admin notifications | Yes — single owner email on new order |
| Carriers | Speedy, Econt, DHL/FedEx (international) |
| Templates | Plain text to start, bilingual (EN/BG), HTML later |
| Failure mode | Fire-and-forget — never blocks orders |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Trigger Points (existing code)                                  │
│                                                                   │
│  routes/orders.py  ──▶ checkout()        ──┐                     │
│  routes/admin.py   ──▶ update_status()   ──┤                     │
│                                             │                     │
│                                             ▼                     │
│                              ┌──────────────────────────┐         │
│                              │  FastAPI BackgroundTasks  │         │
│                              └────────────┬─────────────┘         │
│                                           │                       │
│                                           ▼                       │
│                              ┌──────────────────────────┐         │
│                              │  email_service.py         │         │
│                              │  - render template        │         │
│                              │  - call Resend API        │         │
│                              │  - log success/failure    │         │
│                              └────────────┬─────────────┘         │
│                                           │                       │
│                                           ▼                       │
│                              ┌──────────────────────────┐         │
│                              │  Resend API               │         │
│                              │  from: orders@<domain>    │         │
│                              └──────────────────────────┘         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Email Provider: Resend

### Why Resend (Not Gmail SMTP)

| Concern | Gmail SMTP | Resend |
|---------|-----------|--------|
| Deliverability | Medium-low (shared IP) | High (dedicated sending IPs) |
| Daily limit | ~500 | 100/day free (3000/month) |
| Spam risk | HIGH | Low |
| Custom "from" | Only your Gmail address | `orders@yourdomain.com` |
| Reliability | Google can block without notice | Built for this purpose |
| Tracking | None | Open/bounce/spam tracking |
| Cost | €0 | €0 free (≤~25 orders/day); Pro $20/mo for headroom |
| Code | smtplib + TLS + connection mgmt | One HTTP POST |

### Setup Requirements

1. Register a domain (see Domain section below)
2. Sign up at [resend.com](https://resend.com) (free)
3. Add domain in Resend dashboard
4. Add 3 DNS records at registrar:
   - **SPF** (TXT) — authorizes Resend to send for your domain
   - **DKIM** (TXT) — cryptographic signature proving emails aren't forged
   - **DMARC** (TXT) — policy for handling unverified emails
5. Resend verifies → sending enabled as `orders@yourdomain.com`

**Reply-To**: Owner's personal email (so customer replies go to inbox).

## Domain (TODO — Pre-requisite, Parked)

Domain not yet registered. Brand name / domain choice under review — does not block implementation. The `EMAIL_FROM_ADDRESS` is a config value that gets set once the domain is decided.

**Registrar recommendation**: Cloudflare (no markup pricing, best DNS, easy Resend integration).

When ready:
1. Register domain on Cloudflare
2. Add Resend SPF/DKIM/DMARC records (3 TXT records, 5 minutes)
3. Set `EMAIL_FROM_ADDRESS` env var
4. Done

## Emails to Send

| Event | Recipient | Content |
|-------|-----------|---------|
| Order placed (→ pending) | Customer | Confirmation, order summary, total |
| Order shipped | Customer | Tracking number, carrier, tracking link |
| Order delivered | Customer | "Your order has arrived — enjoy!" |
| Order cancelled | Customer | Cancellation notice + refund being processed |
| New order alert | Owner | Order summary, customer info, admin link |

_No "order confirmed" email — pending→confirmed is an internal admin step (see design Decision 9)._

## Shipping & Tracking

### Schema Addition (orders table)

When admin marks order as "shipped", they provide:

```sql
ALTER TABLE orders ADD COLUMN tracking_number TEXT;
ALTER TABLE orders ADD COLUMN tracking_carrier TEXT;  -- 'speedy', 'econt', 'dhl', 'fedex', etc.
ALTER TABLE orders ADD COLUMN tracking_url TEXT;
```

### Supported Carriers

| Carrier | Market | Tracking URL Pattern |
|---------|--------|---------------------|
| Speedy | Bulgaria | `https://www.speedy.bg/en/track-shipment?shipmentNumber={num}` |
| Econt | Bulgaria | `https://www.econt.com/services/track-shipment/{num}` |
| DHL | International | `https://www.dhl.com/en/express/tracking.html?AWB={num}` |
| FedEx | International | `https://www.fedex.com/fedextrack/?trknbr={num}` |

Admin can also paste a custom tracking URL directly (for carriers not in the list).

### Admin UI for Shipping

When transitioning to "shipped", the admin form expands to show:
- Tracking number (required)
- Carrier (dropdown: Speedy, Econt, DHL, FedEx, Other)
- Tracking URL (auto-generated from carrier + number, or manual override)

## Design Decisions

### 1. Fire-and-Forget (Never Blocks Orders)

Email sending happens in `BackgroundTasks` — the HTTP response returns immediately. If the email service is down or the send fails:
- Log the failure via structlog
- The order still succeeds
- No retry queue (at this scale, a manual re-send from admin dashboard is sufficient)

Email is important but never critical-path.

### 2. Bilingual Templates (EN/BG)

Templates selected based on the order's `locale` (already tracked in the session):

```
app/
  email/
    templates/
      en/
        order_placed.txt
        order_confirmed.txt
        order_shipped.txt
        order_delivered.txt
        order_cancelled.txt
        admin_new_order.txt
      bg/
        order_placed.txt
        order_confirmed.txt
        order_shipped.txt
        order_delivered.txt
        order_cancelled.txt
```

Plain text to start. HTML templates added later for luxury brand aesthetic.

### 3. Template Rendering (Jinja2)

Already a transitive dependency of FastAPI/Starlette:

```
Subject: Your Atelier Marie Order #{{ order_id_short }}

Hi {{ customer_name | default("there") }},

Thank you for your order! Here's what you ordered:

{% for item in items %}
- {{ item.product_name }} × {{ item.quantity }} — {{ item.price_display }}
{% endfor %}

Total: {{ total_display }}

We'll notify you when your order ships.

With love,
Atelier Marie
```

Shipped template includes:

```
Your order has been shipped!

Carrier: {{ carrier }}
Tracking number: {{ tracking_number }}
Track your package: {{ tracking_url }}
```

### 4. Configuration

New env vars in `app/config.py`:

```python
# Email
email_provider: Literal["resend", "console"] = "console"
email_api_key: str = ""
email_from_address: str = "orders@ateliermarie.com"
email_from_name: str = "Atelier Marie"
email_reply_to: str = ""
admin_notification_email: str = ""
```

The `"console"` provider logs emails to stdout in development — no real sends during `make dev-backend` or tests.

### 5. Module Structure

```
app/
  services/
    email_service.py         # send_order_email(), send_admin_alert()
  email/
    __init__.py
    providers/
      __init__.py            # EmailProvider protocol
      resend_provider.py     # Resend API implementation
      console_provider.py    # Dev/test: logs to stdout
    templates/
      en/
        order_placed.txt
        order_confirmed.txt
        order_shipped.txt
        order_delivered.txt
        order_cancelled.txt
        admin_new_order.txt
      bg/
        order_placed.txt
        order_confirmed.txt
        order_shipped.txt
        order_delivered.txt
        order_cancelled.txt
    renderer.py              # Jinja2 template loading + rendering
```

### 6. Admin Notifications

Triggered on **new order** only. Sent to `ADMIN_NOTIFICATION_EMAIL` (single owner address). Contains:
- Order ID + total
- Customer name + email
- Items ordered
- Link to admin dashboard order detail

### 7. Status Update API Change

`PATCH /v1/admin/orders/{order_id}/status` body expands for "shipped":

```json
{
  "status": "shipped",
  "tracking_number": "1234567890",
  "tracking_carrier": "speedy",
  "tracking_url": "https://www.speedy.bg/en/track-shipment?shipmentNumber=1234567890"
}
```

Tracking fields optional for other transitions, required when `status = "shipped"`.

## Failure Modes

| Failure | Impact | Handling |
|---------|--------|----------|
| Resend API down | Customer doesn't get email | Log warning, order succeeds |
| Invalid customer email | Bounce | Log, no retry |
| Template rendering error | No email sent | Log error with full context |
| DNS not configured | All emails fail | Startup warning log |
| Rate limit hit (100/day) | Some emails delayed | Log, degrade gracefully |
| Tracking URL invalid | Broken link in email | Admin's responsibility (validated at input) |

## Scope

> **Recommended split (see design-gaps.md #16):** the inbound-deliverability suite — `POST /v1/webhooks/resend` + Svix verification, `suppressed_emails`, and the audit read endpoint — is a separable follow-up change (a new public route family with its own security surface). It is kept here for now; confirm the boundary before implementation kickoff so the notification core can ship and review independently.

### In Scope
- Email service with Resend provider
- Console provider for dev/test
- Plain text templates (EN + BG) for the customer transitions (placed, shipped, delivered, cancelled)
- Admin new-order notification (single recipient)
- Tracking number/carrier/URL on shipped transition
- Schema migration for tracking fields, order locale snapshot, and `order_emails` log
- Admin UI expansion for shipping form
- Configuration via env vars
- Structured logging of all send attempts + `order_emails` audit rows
- Bilingual subject lines and bodies
- Deliverability: sending subdomain, SPF/DKIM/DMARC, tracking disabled, idempotency keys, Cyrillic subject encoding
- Bounce/complaint/suppression webhook endpoint (mark recipient undeliverable)
- Email format validation at checkout

### Out of Scope (Future)
- HTML rich templates (luxury brand design)
- Retry queue / dead letter
- Email preference management (unsubscribe)
- Marketing emails (abandoned cart, promotions)
- Carrier auto-detection from tracking number format
- Delivery webhooks from Resend
- Multiple admin notification recipients
- Domain registration (separate prerequisite task)

## Prerequisites (Before Implementation)

1. **Register a domain** — check availability of `ateliermarie.com` / `.bg`
2. **Sign up for Resend** — free tier at [resend.com](https://resend.com); plan to upgrade to Pro ($20/mo) once above ~25 orders/day
3. **Create the Resend domain in the EU region** (`eu-west-1`) on a sending **subdomain** (`send.…`), not the root
4. **Configure DNS** — add SPF (TXT + MX), DKIM, DMARC (`p=none` to start) records
5. **Verify domain in Resend** — takes minutes once DNS propagates
6. **Sign Resend's DPA** and document Resend as a GDPR processor
7. **Verify domain in Google Postmaster Tools**; prepare real abv.bg / mail.bg test inboxes for pre-launch deliverability checks

## Dependencies

- `resend` Python SDK (`pip install resend`)
- `jinja2` — explicit dependency (NOT installed as transitive dep — must add to `pyproject.toml`)
- Domain with DNS access
- Resend API key

## Implementation Order

1. Schema migration (add tracking columns to orders)
2. Update `UpdateOrderStatusRequest` model (add optional tracking fields)
3. Update `update_status()` service (persist tracking data, validate required on ship)
4. Email provider abstraction + console provider
5. Resend provider
6. Template renderer + templates (EN/BG)
7. Email service (orchestrates render → send)
8. Wire into routes via BackgroundTasks
9. Admin UI: shipping form expansion
10. Frontend: show tracking info on order detail page
