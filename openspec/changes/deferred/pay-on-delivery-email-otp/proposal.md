# Pay On Delivery Email OTP - Deferred Proposal

## Motivation

Pay on delivery creates a higher abuse surface than card payment because the shop
reserves stock and may prepare fulfillment before collecting money. Email OTP can
raise confidence that the customer controls the submitted email address before a
pay-on-delivery order is accepted.

## Deferred Scope

- Send a short-lived one-time code to the checkout email address when the customer
  selects pay on delivery.
- Require successful OTP verification before creating a pay-on-delivery order.
- Rate-limit OTP sends and verification attempts per email, session, and IP.
- Keep card-payment checkout unaffected.

## Why Deferred

The payment MVP already includes lower-cost controls: phone number collection,
admin-configured pay-on-delivery enablement, EUR 50 maximum amount, strict order
rate limits, and admin cancellation. OTP adds email-delivery dependencies and extra
checkout friction, so it should be introduced after observing real abuse risk or
owner preference.

## Open Questions

- Should OTP be email-only, or should phone OTP be considered later?
- What is the code lifetime: 5 minutes or 10 minutes?
- Should verified emails be remembered for the session to avoid repeated prompts?
