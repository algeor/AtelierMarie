## 1. Dependencies & Configuration

- [ ] 1.1 Add `resend` and `jinja2` to `pyproject.toml` dependencies
- [ ] 1.2 Add email settings to `app/config.py` (email_provider, email_api_key, email_from_address, email_from_name, email_reply_to, admin_notification_email)
- [ ] 1.3 Add production validation for email settings (warn if resend provider but no API key)

## 2. Database Schema — Tracking Fields

- [ ] 2.1 Add `tracking_number`, `tracking_carrier`, `tracking_url` columns to orders table in `app/database.py` schema
- [ ] 2.2 Add carrier URL pattern mapping (speedy, econt, dhl, fedex) as a utility in `app/services/order_service.py` or new `app/utils/carriers.py`
- [ ] 2.3 Write tests for tracking URL auto-generation from carrier + number

## 3. Order Status API — Tracking Support

- [ ] 3.1 Update `UpdateOrderStatusRequest` model to include optional `tracking_number`, `tracking_carrier`, `tracking_url` fields
- [ ] 3.2 Add validation: tracking_number and tracking_carrier required when status="shipped" (return 422 TRACKING_REQUIRED otherwise)
- [ ] 3.3 Update `update_status()` service to persist tracking fields and auto-generate tracking_url from known carriers
- [ ] 3.4 Update `OrderResponse` model to include tracking_number, tracking_carrier, tracking_url (nullable)
- [ ] 3.5 Update `_fetch_order_with_items()` to include tracking fields in returned OrderData
- [ ] 3.6 Write tests for shipped-with-tracking, shipped-without-tracking (rejected), and tracking URL auto-generation

## 4. Email Provider Abstraction

- [ ] 4.1 Create `app/email/__init__.py`
- [ ] 4.2 Create `app/email/providers/__init__.py` with `EmailProvider` Protocol (method: `send(to, subject, body, reply_to, tags)`)
- [ ] 4.3 Implement `app/email/providers/console_provider.py` — logs email to structlog, no network
- [ ] 4.4 Implement `app/email/providers/resend_provider.py` — sends via `resend.Emails.send()`
- [ ] 4.5 Create provider factory function: returns provider based on `settings.email_provider`
- [ ] 4.6 Write tests for console provider (verify log output) and resend provider (mock resend SDK)

## 5. Template Renderer

- [ ] 5.1 Create `app/email/renderer.py` with Jinja2 Environment + FileSystemLoader pointing to templates dir
- [ ] 5.2 Implement `render_template(event, locale, context)` → `(subject, body)` with first-line-is-subject parsing
- [ ] 5.3 Implement locale fallback (missing BG → try EN → log error if both missing)
- [ ] 5.4 Write tests for template rendering: variable interpolation, loops, conditionals, locale fallback

## 6. Email Templates (Plain Text)

- [ ] 6.1 Create `app/email/templates/en/order_placed.txt` — greeting, item list, total, "we'll notify you when it ships"
- [ ] 6.2 Create `app/email/templates/en/order_confirmed.txt` — "we're preparing your order"
- [ ] 6.3 Create `app/email/templates/en/order_shipped.txt` — tracking carrier, number, URL
- [ ] 6.4 Create `app/email/templates/en/order_delivered.txt` — "your order has arrived, enjoy!"
- [ ] 6.5 Create `app/email/templates/en/order_cancelled.txt` — cancellation notice
- [ ] 6.6 Create `app/email/templates/en/admin_new_order.txt` — order summary, customer info, admin link
- [ ] 6.7 Create `app/email/templates/bg/order_placed.txt`
- [ ] 6.8 Create `app/email/templates/bg/order_confirmed.txt`
- [ ] 6.9 Create `app/email/templates/bg/order_shipped.txt`
- [ ] 6.10 Create `app/email/templates/bg/order_delivered.txt`
- [ ] 6.11 Create `app/email/templates/bg/order_cancelled.txt`

## 7. Email Service (Orchestration)

- [ ] 7.1 Create `app/services/email_service.py` with `send_order_email(to, order_id, event, locale, context)` function
- [ ] 7.2 Implement context builder: `_build_email_context(order_data, locale)` — converts cents to display prices, formats items
- [ ] 7.3 Implement `send_admin_alert(order_data)` for new-order notification to owner
- [ ] 7.4 Add comprehensive error handling: catch all provider/render exceptions, log, never raise
- [ ] 7.5 Write tests for email service: mock provider, verify correct template/locale selection, verify context building

## 8. Route Integration (BackgroundTasks)

- [ ] 8.1 Add `BackgroundTasks` parameter to `create_order` route in `app/routes/orders.py`
- [ ] 8.2 Fire `send_order_email(event="pending")` + `send_admin_alert()` after successful checkout
- [ ] 8.3 Add `BackgroundTasks` parameter to `admin_update_order_status` route in `app/routes/admin.py`
- [ ] 8.4 Fire `send_order_email(event=new_status)` after successful status transition
- [ ] 8.5 Pass locale from session to email context (read preferred_locale in admin route)
- [ ] 8.6 Write integration tests: verify BackgroundTasks are added (mock email service)

## 9. Frontend — Order Tracking Display

- [ ] 9.1 Update `OrderResponse` TypeScript type in `frontend/lib/types.ts` to include tracking fields
- [ ] 9.2 Display tracking info (carrier, number, link) on order detail page when status is shipped/delivered
- [ ] 9.3 Add tracking section to order status timeline component

## 10. Frontend — Admin Shipping Form

- [ ] 10.1 Expand admin order status update form: show tracking fields when "shipped" is selected
- [ ] 10.2 Add carrier dropdown (Speedy, Econt, DHL, FedEx, Other)
- [ ] 10.3 Auto-generate tracking URL preview when carrier + number entered
- [ ] 10.4 Validate tracking_number required before allowing ship submission
- [ ] 10.5 Write frontend tests for shipping form behavior
