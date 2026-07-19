# Email Setup — theateliermarie.com

Operational runbook for Atelier Marie email. Two separate concerns share one
domain:

1. **Human inbox** — the Zoho mailbox a person logs into and reads replies from.
2. **Transactional sender** — the machine-to-machine service the backend uses to
   send order/shipping emails. No mailbox; API only.

> ✅ **This reflects the ACTUAL verified setup as of 2026-07-19** (confirmed from
> the live Cloudflare zone + a delivered test email). Where earlier drafts of
> this file guessed (SPF `include:` merge, `send.` subdomain), this version is
> the real thing.

**At a glance:**

- **DNS host:** Cloudflare (nameservers `edward` / `jessica.ns.cloudflare.com`)
- **Inbox:** Zoho Mail **EU**, `contacts@theateliermarie.com` (verified; receives mail)
- **Sender (app):** Zoho **ZeptoMail EU** (transactional), from `orders@theateliermarie.com`
- **Cloudflare Email Routing:** **disabled** (it auto-enabled itself earlier and was replaced by Zoho MX)

> ⚠️ **Config reconcile (implementation-time):** `app/config.py` still ships old
> defaults (`orders@example.invalid`, historically `ateliermarie.com`). Set the
> defaults/`.env` per Part C below, and make `email_api_key` a `SecretStr`
> (design-gaps #12).

---

## Part A — Human inbox (Zoho Mail EU, for replies)

Mailbox: **`contacts@theateliermarie.com`**. Backs `EMAIL_REPLY_TO` and
`ADMIN_NOTIFICATION_EMAIL`. Verified and confirmed receiving (a test email from
an external address arrived in the inbox).

**Inbound mail — MX (Zoho EU):**
```
theateliermarie.com.  MX  10  mx.zoho.eu.
theateliermarie.com.  MX  20  mx2.zoho.eu.
theateliermarie.com.  MX  50  mx3.zoho.eu.
```

**SPF (single record — authorizes Zoho to send as the domain):**
```
theateliermarie.com.  TXT  "v=spf1 include:zoho.eu include:zohomail.eu ~all"
```

**Zoho DKIM (selector `dkim` — signs replies sent from the Zoho inbox):**
```
dkim._domainkey.theateliermarie.com.  TXT  "v=DKIM1; k=rsa; p=MIGf…QIDAQAB"   (verified in Zoho)
```

> **Aliases:** the app's From is `orders@theateliermarie.com`. To make sure any
> reply that lands on a From/alias address reaches the inbox, add `orders@` (and
> optionally `support@`, `hello@`, `noreply@`) as **aliases of `contacts@`** in
> the Zoho admin console. ZeptoMail can send as any address on the verified
> domain regardless — the alias only matters for *receiving* replies.

> **Zoho plan note:** the free plan is web/mobile only (no IMAP/POP/SMTP client
> access for new accounts). Fine — the app does **not** send through this
> mailbox; it sends via ZeptoMail (Part B).

---

## Part B — Transactional sender (Zoho ZeptoMail, EU)

Order/shipping emails are sent by the backend through **ZeptoMail** — Zoho's
transactional product (the SES/Resend equivalent), created in the **EU data
center** so sending data stays in-region. This is **not** the Zoho Mail SMTP that
backs the inbox.

ZeptoMail authenticates with **DKIM + a bounce CNAME** — there is **no root-SPF
change** for ZeptoMail (the CNAME carries its return-path + SPF alignment):

**ZeptoMail DKIM (selector `19154433`, Default, 1024-bit):**
```
19154433._domainkey.theateliermarie.com.  TXT  "k=rsa; p=MIGf…QIDAQAB"   (verified in ZeptoMail)
```

**Bounce / return-path CNAME:**
```
bounce-zem.theateliermarie.com.  CNAME  cluster89.zeptomail.eu.   (verified in ZeptoMail)
```

DKIM is signed on `theateliermarie.com`, so DMARC passes on DKIM alignment; the
bounce CNAME adds SPF alignment on top. An optional 2048-bit ZeptoMail selector
(`1916479283`) was offered but not published — the 1024-bit Default is fine.

**Transport:** the app uses the ZeptoMail **HTTP API** (design.md Decision 24).
SMTP (`smtp.zeptomail.eu`, 587 STARTTLS, username `emailapikey`, password = Send
Mail token) is a validated fallback, not the default.

**Remaining action (implementation-time):** generate a **Send Mail token** in the
ZeptoMail console → this becomes `EMAIL_API_KEY`.

---

## DMARC (covers the whole domain)

```
_dmarc.theateliermarie.com.  TXT  "v=DMARC1; p=none; rua=mailto:contacts@theateliermarie.com"
```

Aggregate reports land in the `contacts@` inbox. Progression: `p=none` →
`p=quarantine` → `p=reject` after a few weeks of clean reports.

---

## Part C — Wire into the app

Set these env vars (`.env`, mirroring `app/config.py`):

```dotenv
EMAIL_PROVIDER=zeptomail
EMAIL_API_KEY=<ZeptoMail Send Mail token>       # store as SecretStr
EMAIL_FROM_ADDRESS=orders@theateliermarie.com   # ZeptoMail-authenticated (DKIM + bounce CNAME)
EMAIL_FROM_NAME=Atelier Marie
EMAIL_REPLY_TO=contacts@theateliermarie.com     # Zoho inbox — replies land here
ADMIN_NOTIFICATION_EMAIL=contacts@theateliermarie.com
```

`EMAIL_FROM_ADDRESS` is authenticated by ZeptoMail; `EMAIL_REPLY_TO` points at the
Zoho inbox so customer replies reach a human.

---

## Webhooks (deferred)

Bounce/complaint handling (`POST /v1/webhooks/zeptomail`) consumes ZeptoMail's
`hard_bounce` / `soft_bounce` / `fbl_complaint` events and needs
`ZEPTOMAIL_WEBHOOK_AUTH_KEY`. Verification uses ZeptoMail's `producer-signature`
header (HMAC-SHA256; parts `ts`, `s`, `s-algorithm`) over the **raw body**, with
±5-min replay rejection and constant-time compare — **not** Svix. Per
`design-gaps.md` (gaps #5 and #16) this is a recommended **follow-up change**,
not required for launch.

---

## DNS summary (live state, 2026-07-19)

| Host / Name              | Type / Value                                   | Status | Purpose                         |
|--------------------------|------------------------------------------------|--------|---------------------------------|
| `theateliermarie.com`    | MX → `mx.zoho.eu` (10), `mx2` (20), `mx3` (50) | ✅ verified | inbound → Zoho inbox         |
| `theateliermarie.com`    | TXT SPF `v=spf1 include:zoho.eu include:zohomail.eu ~all` | ✅ | one SPF record, Zoho send auth |
| `dkim._domainkey`        | TXT — Zoho DKIM (`v=DKIM1;…`)                   | ✅ verified | signs replies from Zoho inbox |
| `19154433._domainkey`    | TXT — ZeptoMail DKIM (1024-bit, Default)        | ✅ verified | signs outbound order emails  |
| `bounce-zem`             | CNAME → `cluster89.zeptomail.eu`               | ✅ verified | ZeptoMail bounce + SPF align  |
| `_dmarc.theateliermarie.com` | TXT `v=DMARC1; p=none; rua=…contacts@…`     | ✅     | policy, whole domain            |

No `send.` subdomain; no root-SPF merge (ZeptoMail uses the bounce CNAME);
Cloudflare Email Routing disabled in favor of Zoho MX.

### Tidiness (optional, harmless)

Two Zoho ownership-verification TXT records exist at the root and are no longer
needed once the domain is verified:

```
theateliermarie.com.  TXT  "zoho-verification=zb06502485.zmverify.zoho.eu"
theateliermarie.com.  TXT  "zoho-verification=zb44573982.zmverify.zoho.eu"
```

Safe to delete both (or leave them — they do nothing). If Zoho ever asks you to
re-verify ownership, it will hand you a fresh one to add.
