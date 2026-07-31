# Config And Environment

All app config should come through `app/config.py`.

## Main Rule

Use:

```python
from app.config import get_settings
settings = get_settings()
```

Do not use `os.getenv()` inside app code.

## Settings Cache

`get_settings()` is cached with `lru_cache`.

Why:

- avoids reparsing env every request
- gives one consistent config object

Test rule:

- if a test changes env vars, call `get_settings.cache_clear()`.

## Important Settings By Area

### Core

- `environment`
- `database_path`
- `cors_origins`
- `static_file_path`

### Auth/admin

- `jwt_secret`
- `jwt_algorithm`
- `jwt_expiry_hours`
- `jwt_cookie_name`
- `google_client_id`
- `google_client_secret`
- `google_redirect_uri`
- `frontend_url`
- `admin_api_key`

### Sessions/cart

- `session_cookie_name`
- `session_max_age`
- `session_absolute_lifetime`
- `session_sliding_threshold`
- `session_cookie_secure`
- `session_skip_paths`
- `cart_max_quantity_per_item`
- `cart_max_distinct_items`

### Email

- `email_provider`
- `email_api_key`
- `email_from_address`
- `email_from_name`
- `email_reply_to`
- `admin_notification_email`
- `zeptomail_webhook_auth_key`
- `contact_message_retention_days`

### Payments

- `stripe_secret_key`
- `stripe_webhook_secret`
- `stripe_success_url`
- `stripe_cancel_url`
- `bank_iban`
- `bank_bic`
- `bank_name`

### Analytics

- `analytics_enabled`
- `analytics_legal_approved`
- `analytics_data_dir`
- `analytics_events_jsonl_path`
- `analytics_duckdb_path`
- `analytics_consent_version`
- `analytics_retention_days`

### Couriers

- `speedy_api_username`
- `speedy_api_password`
- `speedy_base_url`
- `speedy_client_id`
- `econt_api_username`
- `econt_api_password`
- `econt_calculate_url`
- `econt_sender_*`

### Video

- `ffmpeg_path`
- `ffprobe_path`
- `video_upload_temp_path`
- `max_video_upload_bytes`
- `max_video_duration_seconds`

## Production Guards

Production config refuses or warns on unsafe states.

Hard failures:

- default dev JWT secret in production
- missing admin API key in production
- short admin API key in production
- wildcard CORS in production
- analytics enabled in production without legal approval

Warnings:

- missing Google OAuth credentials
- ZeptoMail selected without API key
- incomplete Speedy credentials

## Session Skip Paths

Webhook paths are skipped by session middleware:

- `/v1/webhooks/zeptomail`
- `/v1/webhooks/stripe`

Health/docs paths are skipped too.

Rule: If you add a machine-to-machine webhook, add it to skip paths and verify its own signature.

