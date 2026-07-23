"""Email subsystem — provider abstraction, template rendering.

Layer 1 (production e-commerce): transactional order notifications. The
orchestration (idempotency, outbox draining) lives in
`app/services/email_service.py`; this package holds the provider protocol,
concrete providers, and the Jinja2 renderer.
"""
