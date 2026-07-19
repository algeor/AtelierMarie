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
| Domain | **`theateliermarie.com`** (registered; MX already pointed at Zoho for the `contacts@` mailbox) |
| Registrar/DNS | DNS managed at the domain registrar; Zoho MX/SPF/DKIM already present for inbound mail |
| Email provider | **Zoho ZeptoMail (EU data center)** — transactional API, pay-as-you-go, keeps sending data in-region |
| Sending identity | **Root domain with aliases** (`orders@theateliermarie.com`, `noreply@…`) — no `send.` subdomain |
| Human mailbox | Zoho Mail `contacts@theateliermarie.com` — backs `Reply-To` + admin notifications (aliases funnel into it) |
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
│                              │  - POST ZeptoMail API     │         │
│                              │  - log success/failure    │         │
│                              └────────────┬─────────────┘         │
│                                           │                       │
│                                           ▼                       │
│                              ┌──────────────────────────┐         │
│                              │  ZeptoMail API (EU)       │         │
│                              │  from: orders@theatelier… │         │
│                              │  reply-to: contacts@…     │         │
│                              └──────────────────────────┘         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Email Provider: Zoho ZeptoMail (EU)

### Why ZeptoMail (Not Zoho Mail SMTP, Not Gmail SMTP)

The shop's human mailbox (`contacts@theateliermarie.com`) is on Zoho Mail, but a
**mailbox is not a transactional sender**. Order emails go through **ZeptoMail** —
Zoho's dedicated transactional product (the SES/Resend equivalent) — not through
the Zoho Mail SMTP that backs the inbox.

| Concern | Gmail SMTP | Zoho Mail SMTP (`smtppro.zoho.com`) | **ZeptoMail (chosen)** |
|---------|-----------|--------------------------------------|------------------------|
| Purpose | personal inbox | personal inbox | **built for transactional** |
| Plan needed | Gmail account | **paid Zoho Mail plan** (free = web only) | free tier, then pay-as-you-go |
| Reputation | shared, fragile | **your human-mail reputation** | isolated sender reputation |
| Custom "from" | only your Gmail | your mailbox address | any address on the domain |
| Bounce/complaint feedback | none | none | **webhooks** (hard/soft bounce, FBL) |
| Data residency | US | EU (zoho.eu) | **EU DC — data stays in-region** |
| Cost | €0 | ~€1/user/mo | free 10k credit, then ~€2.50/10k |
| Send interface | SMTP | SMTP | **HTTP API** (or SMTP) |

**Why not Zoho Mail SMTP even though we already pay for the mailbox:** it needs a
paid plan for SMTP access, is rate-limited for human use, and — critically —
blasting order emails through it couples the store's sending reputation to the
`contacts@` inbox it depends on. That is the exact reputation risk this change
sets out to avoid.

**GDPR note:** ZeptoMail EU keeps sending/processing data in the EU, matching the
`zoho.eu` mailbox — simpler than Resend, which sends from the EU but stores
account data in the US.

### Setup Requirements

1. Sign up for **ZeptoMail** and create a Mail Agent in the **EU data center**
2. Add and verify the domain **`theateliermarie.com`** (root — see Sending Identity)
3. Add the DNS records ZeptoMail provides:
   - **SPF** — ZeptoMail's `include:` **merged into the existing Zoho SPF record** (one `v=spf1` record only — see below)
   - **DKIM** (TXT) — ZeptoMail's selector, coexists with Zoho's DKIM selector
   - **DMARC** (TXT) — single policy on `_dmarc`, covers both senders
4. ZeptoMail verifies → generate a **Send Mail token** (API key)
5. Send via the ZeptoMail HTTP API as `orders@theateliermarie.com`

**Reply-To**: `contacts@theateliermarie.com` (Zoho mailbox — customer replies land in a human inbox).

## Sending Identity: Root Domain + Aliases (no subdomain)

Transactional mail is sent from the **root domain** using aliases
(`orders@theateliermarie.com`, `noreply@theateliermarie.com`), **not** a `send.`
subdomain. This is a deliberate simplification for a transactional-only,
low-volume sender; the tradeoff is that order-mail reputation is not isolated
from the human `contacts@` inbox.

**DNS mechanism (as verified).** ZeptoMail authenticates the domain with a
**DKIM TXT** record (selector `19154433`, marked Default) plus a **bounce
CNAME** (`bounce-zem.theateliermarie.com → cluster89.zeptomail.eu`). The CNAME
handles the return-path and SPF alignment, so **the existing Zoho SPF record is
left untouched — no root-SPF merge is needed.** DKIM is aligned on the root
domain, so DMARC passes on DKIM; the bounce CNAME adds SPF alignment on top.
DMARC is a single record on `_dmarc`.

> General caution (did not apply here): a domain may have only **one** `v=spf1`
> record — two produces an SPF `permerror`. If a future provider ever asks you
> to add an SPF `include:`, merge it into the single existing record rather than
> adding a second.

**Forward note:** any future *marketing* stream (newsletter, promotions) MUST use
a dedicated subdomain — never the root — so it can never harm transactional or
human-mail deliverability.

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
email_provider: Literal["zeptomail", "console"] = "console"
email_api_key: SecretStr = SecretStr("")             # ZeptoMail Send Mail token
email_from_address: str = "orders@theateliermarie.com"
email_from_name: str = "Atelier Marie"
email_reply_to: str = "contacts@theateliermarie.com" # Zoho human mailbox
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
      zeptomail_provider.py  # ZeptoMail HTTP API implementation
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
| ZeptoMail API down | Customer doesn't get email | Log warning, order succeeds |
| Invalid customer email | Bounce | Log, no retry |
| Template rendering error | No email sent | Log error with full context |
| DNS not configured / two SPF records | All emails fail (SPF permerror) | Startup warning log; single merged SPF record (see Sending Identity) |
| Sending quota / credit exhausted | Some emails delayed | Log, degrade gracefully |
| Tracking URL invalid | Broken link in email | Admin's responsibility (validated at input) |

## Scope

> **Recommended split (see design-gaps.md #16):** the inbound-deliverability suite — `POST /v1/webhooks/zeptomail` + `producer-signature` HMAC verification, `suppressed_emails`, and the audit read endpoint — is a separable follow-up change (a new public route family with its own security surface). It is kept here for now; confirm the boundary before implementation kickoff so the notification core can ship and review independently.

### In Scope
- Email service with ZeptoMail (EU) HTTP API provider
- Console provider for dev/test
- Plain text templates (EN + BG) for the customer transitions (placed, shipped, delivered, cancelled)
- Admin new-order notification (single recipient)
- Tracking number/carrier/URL on shipped transition
- Schema migration for tracking fields, order locale snapshot, and `order_emails` log
- Admin UI expansion for shipping form
- Configuration via env vars
- Structured logging of all send attempts + `order_emails` audit rows
- Bilingual subject lines and bodies
- Deliverability: root-domain sending identity, merged SPF + DKIM + DMARC, tracking disabled, Cyrillic subject encoding
- Bounce/complaint/suppression webhook endpoint (mark recipient undeliverable)
- Email format validation at checkout

### Out of Scope (Future)
- HTML rich templates (luxury brand design)
- Retry queue / dead letter
- Email preference management (unsubscribe)
- Marketing emails (abandoned cart, promotions) — MUST use a dedicated subdomain when added
- Carrier auto-detection from tracking number format
- Open/click/delivery event webhooks from ZeptoMail (only bounce/complaint consumed)
- Multiple admin notification recipients

## Prerequisites (Before Implementation)

1. **Domain** — `theateliermarie.com` is registered; Zoho MX/SPF/DKIM already present for the `contacts@` mailbox
2. **Sign up for ZeptoMail** — free 10k-email credit to start; then pay-as-you-go (~€2.50 / 10k, credits valid 6 months, no daily cap)
3. **Create the ZeptoMail Mail Agent in the EU data center** and verify the **root** domain `theateliermarie.com`
4. **Configure DNS** — **merge** ZeptoMail's SPF `include:` into the existing Zoho `v=spf1` record (one record only), add ZeptoMail's DKIM selector, keep DMARC `p=none` to start
5. **Verify domain in ZeptoMail** and generate a **Send Mail token**; store it as `EMAIL_API_KEY` (SecretStr)
6. **Sign ZeptoMail's DPA** and document ZeptoMail (Zoho, EU DC) as a GDPR processor
7. **Verify domain in Google Postmaster Tools**; prepare real abv.bg / mail.bg test inboxes for pre-launch deliverability checks

## Dependencies

- `zeptomail` Python SDK (`pip install zeptomail`) **or** a thin `httpx` POST (httpx is already present — no new dep required)
- `jinja2` — explicit dependency (NOT installed as transitive dep — must add to `pyproject.toml`)
- Domain with DNS access (SPF merge)
- ZeptoMail Send Mail token

## Implementation Order

1. Schema migration (add tracking columns to orders)
2. Update `UpdateOrderStatusRequest` model (add optional tracking fields)
3. Update `update_status()` service (persist tracking data, validate required on ship)
4. Email provider abstraction + console provider
5. ZeptoMail provider (HTTP API)
6. Template renderer + templates (EN/BG)
7. Email service (orchestrates render → send)
8. Wire into routes via BackgroundTasks
9. Admin UI: shipping form expansion
10. Frontend: show tracking info on order detail page
