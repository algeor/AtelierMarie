# Email Setup — theateliermarie.com

Operational runbook for provisioning email for Atelier Marie. Covers two
separate concerns that are often conflated:

1. **Human mailboxes** — inboxes a person logs into and reads replies from.
2. **Transactional sender** — the machine-to-machine service the backend uses
   to send order/shipping emails. No mailbox; API only.

Both live on the same domain; DNS is what ties them together.

> ⚠️ **Domain note:** the real domain is `theateliermarie.com`, but the specs
> and `app/config.py:44` still reference `ateliermarie.com` (and the config
> default `orders@example.invalid`). Reconcile those before production.

---

## Part A — Human mailboxes (for replies)

These back `EMAIL_REPLY_TO` and `ADMIN_NOTIFICATION_EMAIL`. Use a small-business
email host (Zoho Mail's free tier fits a shop this size; Google Workspace or
Microsoft 365 also work).

Mailboxes to create:

- `hello@theateliermarie.com` — general / reply-to
- `orders@theateliermarie.com` — admin order notifications

DNS on the **root** domain (Zoho EU example — use the exact records your host
gives you):

```
theateliermarie.com.   MX   10  mx.zoho.eu.
theateliermarie.com.   MX   20  mx2.zoho.eu.
theateliermarie.com.   MX   50  mx3.zoho.eu.
theateliermarie.com.   TXT      "v=spf1 include:zoho.eu ~all"
<selector>._domainkey  TXT      (DKIM key from your mailbox host)
```

These serve **inbound** mail to your human inboxes.

---

## Part B — Transactional sender (Resend)

Per `specs/email-deliverability/spec.md`, transactional mail is sent from a
dedicated **subdomain** so sending reputation stays isolated from human
mailboxes. No mailbox is created here.

1. **Sign up for Resend** and add the domain **`send.theateliermarie.com`**.

2. Add the records Resend provides, on the **subdomain**:

   ```
   send.theateliermarie.com.        MX    10 feedback-smtp.us-east-1.amazonses.com
   send.theateliermarie.com.        TXT      "v=spf1 include:amazonses.com ~all"
   resend._domainkey.send…          TXT      (long DKIM key from Resend)
   ```

3. **DMARC** on the root domain — start in monitor mode, then tighten:

   ```
   _dmarc.theateliermarie.com.  TXT  "v=DMARC1; p=none; rua=mailto:hello@theateliermarie.com"
   ```

   Progression: `p=none` → `p=quarantine` → `p=reject` once mail passes cleanly.

4. Wait until Resend shows the domain **verified**, then create an **API key**.

---

## Part C — Wire into the app

Set these env vars (`.env`, mirroring `app/config.py:41-47`):

```dotenv
EMAIL_PROVIDER=resend
EMAIL_API_KEY=re_xxxxxxxx                        # from Resend
EMAIL_FROM_ADDRESS=orders@send.theateliermarie.com   # Resend-authenticated subdomain
EMAIL_FROM_NAME=Atelier Marie
EMAIL_REPLY_TO=hello@theateliermarie.com         # real Zoho mailbox — replies land here
ADMIN_NOTIFICATION_EMAIL=orders@theateliermarie.com
```

Key point: `EMAIL_FROM_ADDRESS` is on the **`send.`** subdomain (so Resend can
authenticate it), but `EMAIL_REPLY_TO` points at a **human** mailbox so customer
replies go somewhere a person reads. That is the entire reason for having both
Part A and Part B.

---

## Webhooks (deferred)

Bounce/complaint handling (`POST /v1/webhooks/resend`) needs
`RESEND_WEBHOOK_SECRET` and Svix signature verification. Per `design-gaps.md`
(gaps #5 and #16), this is **not built yet** and is recommended to split into a
follow-up change. Not required for initial launch — the Part C config above is
enough to start sending.

---

## DNS summary

| Host                        | Records                        | Purpose                       |
|-----------------------------|--------------------------------|-------------------------------|
| `theateliermarie.com`       | MX + SPF (+ DKIM)              | inbound → human mailboxes     |
| `send.theateliermarie.com`  | MX + SPF + DKIM                | outbound → Resend transactional |
| `_dmarc.theateliermarie.com`| DMARC TXT                      | policy, covers both           |
