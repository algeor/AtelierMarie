"""initial postgres schema

Revision ID: 20260802_0001
Revises:
Create Date: 2026-08-02 12:02:43.324902

"""

# ruff: noqa: E501

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260802_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _exec(sql: str) -> None:
    op.execute(sql)


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    _exec(
        """
        CREATE TABLE products
        (
            id                   TEXT PRIMARY KEY,
            name_en              TEXT        NOT NULL,
            name_bg              TEXT,
            description_en       TEXT,
            description_bg       TEXT,
            safety_warnings_en   TEXT,
            safety_warnings_bg   TEXT,
            care_instructions_en TEXT,
            care_instructions_bg TEXT,
            materials            TEXT,
            days_to_craft        INTEGER,
            price_cents          INTEGER     NOT NULL CHECK (price_cents > 0),
            category             TEXT,
            product_type_slug    TEXT        NOT NULL DEFAULT 'candles',
            category_slug        TEXT,
            discount_percent     INTEGER CHECK (
                discount_percent IS NULL OR discount_percent BETWEEN 1 AND 99
                ),
            discount_starts_at   TIMESTAMPTZ,
            discount_ends_at     TIMESTAMPTZ,
            stock                INTEGER     NOT NULL DEFAULT 0 CHECK (stock >= 0),
            weight_grams         INTEGER     NOT NULL DEFAULT 300 CHECK (weight_grams > 0),
            is_active            INTEGER     NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            is_featured          INTEGER     NOT NULL DEFAULT 0 CHECK (is_featured IN (0, 1)),
            translation_stale_bg INTEGER     NOT NULL DEFAULT 0
                CHECK (translation_stale_bg IN (0, 1)),
            translation_stale_en INTEGER     NOT NULL DEFAULT 0
                CHECK (translation_stale_en IN (0, 1)),
            created_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE product_types
        (
            slug       TEXT PRIMARY KEY,
            name_en    TEXT        NOT NULL,
            name_bg    TEXT,
            sort_order INTEGER     NOT NULL DEFAULT 0,
            is_active  INTEGER     NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE product_categories
        (
            slug       TEXT PRIMARY KEY,
            name_en    TEXT        NOT NULL,
            name_bg    TEXT,
            sort_order INTEGER     NOT NULL DEFAULT 0,
            is_active  INTEGER     NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE product_labels
        (
            slug       TEXT PRIMARY KEY,
            name_en    TEXT        NOT NULL,
            name_bg    TEXT,
            sort_order INTEGER     NOT NULL DEFAULT 0,
            is_active  INTEGER     NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE product_label_assignments
        (
            product_id TEXT NOT NULL REFERENCES products (id) ON DELETE CASCADE,
            label_slug TEXT NOT NULL REFERENCES product_labels (slug) ON DELETE RESTRICT,
            PRIMARY KEY (product_id, label_slug)
        );

        CREATE TABLE taxonomy_category_migration
        (
            original_value TEXT PRIMARY KEY,
            label_slug     TEXT NOT NULL
        );

        CREATE INDEX idx_label_assignments_label
            ON product_label_assignments (label_slug);
        CREATE INDEX idx_products_type_slug ON products (product_type_slug);
        CREATE INDEX idx_products_category_slug ON products (category_slug);
        CREATE INDEX idx_products_category ON products (category);
        CREATE INDEX idx_products_is_active ON products (is_active);
        """
    )
    _exec(
        """
        CREATE TABLE finance_periods
        (
            id                      TEXT PRIMARY KEY,
            period_start            DATE        NOT NULL,
            period_end              DATE        NOT NULL,
            currency                TEXT        NOT NULL DEFAULT 'EUR',
            status                  TEXT        NOT NULL DEFAULT 'open' CHECK (
                status IN ('open', 'review', 'closed', 'exported', 'accepted', 'reopened')
                ),
            summary_totals_json     TEXT,
            created_by_admin_id     TEXT,
            updated_by_admin_id     TEXT,
            closed_by_admin_id      TEXT,
            closed_at               TIMESTAMPTZ,
            accepted_at             TIMESTAMPTZ,
            reopened_from_export_id TEXT,
            reopen_reason           TEXT,
            created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (period_start <= period_end)
        );

        CREATE TABLE seller_legal_profile_versions
        (
            id                        INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            effective_date            DATE        NOT NULL,
            reviewed                  INTEGER     NOT NULL DEFAULT 0 CHECK (reviewed IN (0, 1)),
            company_display_name      TEXT,
            legal_name                TEXT,
            uic_eik                   TEXT,
            vat_identification_number TEXT,
            registered_address_json   TEXT,
            contact_email             TEXT,
            bank_details_json         TEXT,
            default_currency          TEXT        NOT NULL DEFAULT 'EUR',
            created_by_admin_id       TEXT,
            created_at                TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE vat_fiscal_settings_versions
        (
            id                             INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            effective_date                 DATE        NOT NULL,
            reviewed                       INTEGER     NOT NULL DEFAULT 0
                CHECK (reviewed IN (0, 1)),
            vat_mode                       TEXT        NOT NULL DEFAULT 'unknown' CHECK (
                vat_mode IN ('unknown', 'not_registered', 'registered', 'oss_registered')
                ),
            oss_mode                       TEXT        NOT NULL DEFAULT 'not_applicable' CHECK (
                oss_mode IN ('not_applicable', 'not_registered', 'registered', 'review_required')
                ),
            default_domestic_vat_treatment TEXT,
            fiscal_document_mode           TEXT        NOT NULL DEFAULT 'external_reference' CHECK (
                fiscal_document_mode IN (
                                         'external_reference',
                                         'app_invoice_reference',
                                         'fiscal_device_reference',
                                         'alternative_sales_document',
                                         'not_configured'
                    )
                ),
            document_rules_json            TEXT,
            threshold_warnings_json        TEXT,
            tolerance_cents                INTEGER     NOT NULL DEFAULT 1
                CHECK (tolerance_cents >= 0),
            warning_text                   TEXT,
            created_by_admin_id            TEXT,
            created_at                     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_finance_periods_status_dates
            ON finance_periods (status, period_start, period_end);
        CREATE INDEX idx_seller_legal_profile_reviewed_effective
            ON seller_legal_profile_versions (reviewed, effective_date);
        CREATE INDEX idx_vat_fiscal_settings_reviewed_effective
            ON vat_fiscal_settings_versions (reviewed, effective_date);
        """
    )
    _exec(
        """
        CREATE TABLE faq_sections
        (
            slug       TEXT PRIMARY KEY,
            title_en   TEXT        NOT NULL,
            title_bg   TEXT,
            icon       TEXT,
            sort_order INTEGER     NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE faq_items
        (
            id           INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            section      TEXT        NOT NULL REFERENCES faq_sections (slug),
            question_en  TEXT        NOT NULL,
            question_bg  TEXT,
            answer_en    TEXT        NOT NULL,
            answer_bg    TEXT,
            sort_order   INTEGER     NOT NULL DEFAULT 0,
            is_published INTEGER     NOT NULL DEFAULT 1 CHECK (is_published IN (0, 1)),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_faq_items_section_order ON faq_items (section, sort_order);

        CREATE TABLE terms_page
        (
            id                    TEXT PRIMARY KEY CHECK (id = 'terms'),
            meta_title_en         TEXT        NOT NULL,
            meta_title_bg         TEXT,
            meta_description_en   TEXT        NOT NULL,
            meta_description_bg   TEXT,
            eyebrow_en            TEXT        NOT NULL,
            eyebrow_bg            TEXT,
            title_en              TEXT        NOT NULL,
            title_bg              TEXT,
            subtitle_en           TEXT        NOT NULL,
            subtitle_bg           TEXT,
            last_updated_en       TEXT        NOT NULL,
            last_updated_bg       TEXT,
            identity_intro_en     TEXT        NOT NULL,
            identity_intro_bg     TEXT,
            policy_links_title_en TEXT        NOT NULL,
            policy_links_title_bg TEXT,
            privacy_link_en       TEXT        NOT NULL,
            privacy_link_bg       TEXT,
            cookies_link_en       TEXT        NOT NULL,
            cookies_link_bg       TEXT,
            nav_label_en          TEXT        NOT NULL,
            nav_label_bg          TEXT,
            back_to_top_en        TEXT        NOT NULL,
            back_to_top_bg        TEXT,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE terms_sections
        (
            slug                TEXT PRIMARY KEY,
            title_en            TEXT        NOT NULL,
            title_bg            TEXT,
            nav_en              TEXT        NOT NULL,
            nav_bg              TEXT,
            body_en             TEXT        NOT NULL,
            body_bg             TEXT,
            model_form_title_en TEXT,
            model_form_title_bg TEXT,
            model_form_intro_en TEXT,
            model_form_intro_bg TEXT,
            model_form_lines_en TEXT,
            model_form_lines_bg TEXT,
            sort_order          INTEGER     NOT NULL DEFAULT 0,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_terms_sections_order ON terms_sections (sort_order, slug);

        CREATE TABLE privacy_page
        (
            id                  TEXT PRIMARY KEY CHECK (id = 'privacy'),
            meta_title_en       TEXT        NOT NULL,
            meta_title_bg       TEXT,
            meta_description_en TEXT        NOT NULL,
            meta_description_bg TEXT,
            eyebrow_en          TEXT        NOT NULL,
            eyebrow_bg          TEXT,
            title_en            TEXT        NOT NULL,
            title_bg            TEXT,
            subtitle_en         TEXT        NOT NULL,
            subtitle_bg         TEXT,
            last_updated_en     TEXT        NOT NULL,
            last_updated_bg     TEXT,
            controller_title_en TEXT        NOT NULL,
            controller_title_bg TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE privacy_sections
        (
            slug       TEXT PRIMARY KEY,
            title_en   TEXT        NOT NULL,
            title_bg   TEXT,
            nav_en     TEXT        NOT NULL,
            nav_bg     TEXT,
            body_en    TEXT        NOT NULL,
            body_bg    TEXT,
            sort_order INTEGER     NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_privacy_sections_order ON privacy_sections (sort_order, slug);
        """
    )
    _exec(
        """
        CREATE TABLE cookies_page
        (
            id                  TEXT PRIMARY KEY CHECK (id = 'cookies'),
            meta_title_en       TEXT        NOT NULL,
            meta_title_bg       TEXT,
            meta_description_en TEXT        NOT NULL,
            meta_description_bg TEXT,
            eyebrow_en          TEXT        NOT NULL,
            eyebrow_bg          TEXT,
            title_en            TEXT        NOT NULL,
            title_bg            TEXT,
            subtitle_en         TEXT        NOT NULL,
            subtitle_bg         TEXT,
            last_updated_en     TEXT        NOT NULL,
            last_updated_bg     TEXT,
            inventory_title_en  TEXT        NOT NULL,
            inventory_title_bg  TEXT,
            header_name_en      TEXT        NOT NULL,
            header_name_bg      TEXT,
            header_purpose_en   TEXT        NOT NULL,
            header_purpose_bg   TEXT,
            header_type_en      TEXT        NOT NULL,
            header_type_bg      TEXT,
            header_duration_en  TEXT        NOT NULL,
            header_duration_bg  TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE cookies_inventory
        (
            name            TEXT PRIMARY KEY,
            purpose_en      TEXT        NOT NULL,
            purpose_bg      TEXT,
            type_en         TEXT        NOT NULL,
            type_bg         TEXT,
            duration_en     TEXT        NOT NULL,
            duration_bg     TEXT,
            source          TEXT        NOT NULL DEFAULT 'seed',
            first_seen_at   TIMESTAMPTZ,
            last_seen_at    TIMESTAMPTZ,
            last_audited_at TIMESTAMPTZ,
            observed_on     TEXT,
            is_active       INTEGER     NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            auto_detected   INTEGER     NOT NULL DEFAULT 0 CHECK (auto_detected IN (0, 1)),
            sort_order      INTEGER     NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_cookies_inventory_order ON cookies_inventory (sort_order, name);

        CREATE TABLE cookies_sections
        (
            slug       TEXT PRIMARY KEY,
            title_en   TEXT        NOT NULL,
            title_bg   TEXT,
            body_en    TEXT        NOT NULL,
            body_bg    TEXT,
            sort_order INTEGER     NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_cookies_sections_order ON cookies_sections (sort_order, slug);

        CREATE TABLE product_images
        (
            id            TEXT PRIMARY KEY,
            product_id    TEXT        NOT NULL REFERENCES products (id) ON DELETE CASCADE,
            image_url     TEXT        NOT NULL,
            thumbnail_url TEXT        NOT NULL,
            zoom_url      TEXT,
            sort_order    INTEGER     NOT NULL DEFAULT 0,
            is_primary    INTEGER     NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_product_images_product ON product_images (product_id, sort_order);
        CREATE UNIQUE INDEX idx_product_images_one_primary
            ON product_images (product_id) WHERE is_primary = 1;

        CREATE TABLE product_videos
        (
            id               TEXT PRIMARY KEY,
            product_id       TEXT        NOT NULL UNIQUE REFERENCES products (id) ON DELETE CASCADE,
            status           TEXT        NOT NULL CHECK (
                status IN ('queued', 'transcoding', 'ready', 'failed')
                ),
            source_path      TEXT,
            video_url        TEXT,
            poster_url       TEXT,
            duration_secs    DOUBLE PRECISION,
            sort_order       INTEGER     NOT NULL DEFAULT 0,
            failure_reason   TEXT,
            lease_expires_at TIMESTAMPTZ,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_product_videos_status ON product_videos (status);

        CREATE TABLE users
        (
            id            TEXT PRIMARY KEY,
            google_id     TEXT UNIQUE NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            name          TEXT,
            avatar_url    TEXT,
            is_admin      INTEGER     NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMPTZ
        );

        CREATE TABLE sessions
        (
            id               TEXT PRIMARY KEY,
            user_id          TEXT REFERENCES users (id),
            preferred_locale TEXT        NOT NULL DEFAULT 'en',
            created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at       TIMESTAMPTZ NOT NULL
        );

        CREATE INDEX idx_sessions_expires_at ON sessions (expires_at);

        CREATE TABLE analytics_consents
        (
            session_id      TEXT PRIMARY KEY REFERENCES sessions (id) ON DELETE CASCADE,
            analytics       INTEGER     NOT NULL CHECK (analytics IN (0, 1)),
            consent_version TEXT        NOT NULL,
            locale          TEXT        NOT NULL DEFAULT 'en' CHECK (locale IN ('en', 'bg')),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_analytics_consents_current
            ON analytics_consents (session_id, consent_version, analytics);

        CREATE TABLE cart_items
        (
            session_id TEXT        NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
            product_id TEXT        NOT NULL REFERENCES products (id),
            quantity   INTEGER     NOT NULL DEFAULT 1 CHECK (quantity >= 1 AND quantity <= 10),
            added_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (session_id, product_id)
        );

        CREATE INDEX idx_cart_items_session_id ON cart_items (session_id);
        """
    )
    _exec(
        """
        CREATE TABLE orders
        (
            id TEXT PRIMARY KEY,
            internal_sequence INTEGER UNIQUE,
            order_number TEXT UNIQUE,
            session_id TEXT NOT NULL,
            user_id TEXT REFERENCES users (id),
            status TEXT NOT NULL DEFAULT 'pending' CHECK (
                status IN (
                    'pending', 'confirmed', 'shipped', 'delivered',
                    'return_in_transit', 'returned', 'cancelled'
                    )
                ),
            total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
            customer_email TEXT NOT NULL,
            customer_name TEXT,
            shipping_cents INTEGER NOT NULL DEFAULT 0 CHECK (shipping_cents >= 0),
            shipping_price_source TEXT NOT NULL DEFAULT 'live',
            shipping_is_fallback INTEGER NOT NULL DEFAULT 0
                CHECK (shipping_is_fallback IN (0, 1)),
            shipping_quoted_at TIMESTAMPTZ,
            delivery_method TEXT CHECK (delivery_method IN ('office', 'door')),
            delivery_courier TEXT CHECK (delivery_courier IN ('speedy', 'econt')),
            delivery_details TEXT,
            tracking_number TEXT,
            tracking_carrier TEXT,
            tracking_url TEXT,
            courier_status TEXT,
            label_url TEXT,
            courier_provider TEXT CHECK (courier_provider IN ('speedy', 'econt')),
            courier_order_id TEXT,
            courier_shipment_number TEXT,
            courier_label_url TEXT,
            courier_label_created_at TIMESTAMPTZ,
            courier_sync_status TEXT,
            courier_last_error TEXT,
            courier_last_synced_at TIMESTAMPTZ,
            courier_last_polled_at TIMESTAMPTZ,
            courier_next_poll_at TIMESTAMPTZ,
            courier_poll_attempts INTEGER NOT NULL DEFAULT 0
                CHECK (courier_poll_attempts >= 0),
            courier_poll_lease_token TEXT,
            courier_poll_lease_expires_at TIMESTAMPTZ,
            locale TEXT NOT NULL DEFAULT 'en',
            notes TEXT,
            payment_method TEXT NOT NULL DEFAULT 'cod' CHECK (
                payment_method IN ('cod', 'card', 'bank_transfer')
                ),
            payment_status TEXT NOT NULL DEFAULT 'cod_pending' CHECK (
                payment_status IN (
                    'pending', 'paid', 'cod_pending', 'failed',
                    'review_required', 'refund_pending', 'partially_refunded',
                    'refunded', 'dispute_open', 'dispute_won', 'dispute_lost'
                    )
                ),
            reserved_until TIMESTAMPTZ,
            paid_at TIMESTAMPTZ,
            collected_at TIMESTAMPTZ,
            payment_return_token TEXT UNIQUE,
            stripe_checkout_session_id TEXT,
            stripe_payment_intent_id TEXT,
            invoice_profile_json TEXT,
            accounting_currency TEXT NOT NULL DEFAULT 'EUR',
            seller_legal_profile_version_id INTEGER
                REFERENCES seller_legal_profile_versions (id),
            vat_fiscal_settings_version_id INTEGER
                REFERENCES vat_fiscal_settings_versions (id),
            accounting_classification_state TEXT NOT NULL DEFAULT 'unreviewed' CHECK (
                accounting_classification_state IN (
                    'unreviewed', 'domestic_default', 'business_vat_id_provided',
                    'cross_border_candidate', 'manual_review_required'
                    )
                ),
            accounting_snapshot_json TEXT,
            accounting_readiness_status TEXT NOT NULL DEFAULT 'unreviewed' CHECK (
                accounting_readiness_status IN (
                    'unreviewed', 'ready', 'review_required', 'blocked'
                    )
                ),
            finance_period_id TEXT REFERENCES finance_periods (id) ON DELETE SET NULL,
            analytics_consent INTEGER NOT NULL DEFAULT 0
                CHECK (analytics_consent IN (0, 1)),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    _exec(
        """
        CREATE TABLE payments
        (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
            provider TEXT NOT NULL,
            amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
            currency TEXT NOT NULL DEFAULT 'EUR',
            stripe_checkout_session_id TEXT UNIQUE,
            stripe_payment_intent_id TEXT,
            provider_status TEXT,
            provider_details TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE payment_events
        (
            id TEXT PRIMARY KEY,
            order_id TEXT REFERENCES orders (id) ON DELETE CASCADE,
            payment_id TEXT REFERENCES payments (id) ON DELETE SET NULL,
            event_type TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'system',
            stripe_event_id TEXT UNIQUE,
            stripe_event_type TEXT,
            provider TEXT,
            provider_status TEXT,
            processing_status TEXT NOT NULL DEFAULT 'processed',
            details TEXT,
            admin_user_id TEXT,
            admin_email TEXT,
            admin_note TEXT,
            request_id TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_payments_order_id ON payments (order_id);
        CREATE INDEX idx_payments_provider ON payments (provider);
        CREATE INDEX idx_payments_stripe_checkout_session_id
            ON payments (stripe_checkout_session_id);
        CREATE INDEX idx_payments_stripe_payment_intent_id
            ON payments (stripe_payment_intent_id);
        CREATE INDEX idx_payment_events_order_id
            ON payment_events (order_id, created_at);
        CREATE INDEX idx_payment_events_stripe_event_id
            ON payment_events (stripe_event_id);
        """
    )

    # BEGIN generated schema completion
    _exec(
        """
-- Remaining launch schema tables.

CREATE TABLE about_sections (
    slug TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    heading_en TEXT NOT NULL,
    heading_bg TEXT,
    subheading_en TEXT,
    subheading_bg TEXT,
    body_en TEXT,
    body_bg TEXT,
    cta_label_en TEXT,
    cta_label_bg TEXT,
    cta_href TEXT,
    image_id TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_published INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0, 1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE accounting_category_mappings (
    id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    mapping_key TEXT NOT NULL UNIQUE,
    category_code TEXT,
    category_label TEXT NOT NULL,
    is_required INTEGER NOT NULL DEFAULT 0 CHECK (is_required IN (0, 1)),
    reviewed INTEGER NOT NULL DEFAULT 0 CHECK (reviewed IN (0, 1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE accounting_export_schema_settings (
    id TEXT PRIMARY KEY DEFAULT 'default' CHECK (id = 'default'),
    workbook_language TEXT NOT NULL DEFAULT 'en' CHECK (workbook_language IN ('en', 'bg')),
    date_format TEXT NOT NULL DEFAULT 'yyyy-mm-dd',
    decimal_separator TEXT NOT NULL DEFAULT '.' CHECK (decimal_separator IN ('.', ',')),
    default_period_range TEXT NOT NULL DEFAULT 'monthly',
    included_tabs_json TEXT,
    custom_columns_json TEXT,
    reviewed INTEGER NOT NULL DEFAULT 0 CHECK (reviewed IN (0, 1)),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE admin_alerts (
    id TEXT PRIMARY KEY,
    alert_type TEXT NOT NULL,
    order_id TEXT REFERENCES orders(id) ON DELETE CASCADE,
    source TEXT NOT NULL DEFAULT 'system',
    severity TEXT NOT NULL DEFAULT 'warning',
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    is_read INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cod_settlements (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    settlement_date TIMESTAMPTZ NOT NULL,
    courier_reference TEXT,
    notes TEXT,
    mismatch_review INTEGER NOT NULL DEFAULT 0 CHECK (mismatch_review IN (0, 1)),
    created_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE comments (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE contact_messages (
    id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
    email TEXT NOT NULL CHECK (length(email) BETWEEN 3 AND 254),
    message TEXT NOT NULL CHECK (length(message) BETWEEN 1 AND 2000),
    locale TEXT NOT NULL DEFAULT 'en' CHECK (locale IN ('en', 'bg')),
    ip_address TEXT,
    email_status TEXT NOT NULL DEFAULT 'queued'
                          CHECK (email_status IN (
                              'queued', 'in_flight', 'sent', 'failed',
                              'failed_permanent', 'skipped_suppressed'
                          )),
    email_attempts INTEGER NOT NULL DEFAULT 0 CHECK (email_attempts >= 0),
    email_next_attempt_at TIMESTAMPTZ,
    email_claimed_until TIMESTAMPTZ,
    email_sent_at TIMESTAMPTZ,
    email_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE delivery_settings (
    id TEXT PRIMARY KEY DEFAULT 'default',
    speedy_office_enabled INTEGER NOT NULL DEFAULT 1 CHECK (speedy_office_enabled IN (0, 1)),
    speedy_door_enabled INTEGER NOT NULL DEFAULT 1 CHECK (speedy_door_enabled IN (0, 1)),
    econt_office_enabled INTEGER NOT NULL DEFAULT 1 CHECK (econt_office_enabled IN (0, 1)),
    econt_door_enabled INTEGER NOT NULL DEFAULT 1 CHECK (econt_door_enabled IN (0, 1)),
    cod_enabled INTEGER NOT NULL DEFAULT 1 CHECK (cod_enabled IN (0, 1)),
    card_enabled INTEGER NOT NULL DEFAULT 1 CHECK (card_enabled IN (0, 1)),
    bank_transfer_enabled INTEGER NOT NULL DEFAULT 1 CHECK (bank_transfer_enabled IN (0, 1)),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE econt_settings (
    id TEXT PRIMARY KEY DEFAULT 'default'
                               CHECK (id = 'default'),
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    environment TEXT NOT NULL DEFAULT 'demo'
                               CHECK (environment IN ('demo', 'production')),
    shop_id TEXT,
    credential_source TEXT NOT NULL DEFAULT 'env'
                               CHECK (credential_source IN ('env', 'stored')),
    sender_delivery_mode TEXT NOT NULL DEFAULT 'office'
                               CHECK (sender_delivery_mode IN ('office', 'door')),
    sender_office_code TEXT,
    sender_city TEXT,
    sender_post_code TEXT,
    sender_address TEXT,
    sender_quarter TEXT,
    sender_street TEXT,
    sender_num TEXT,
    sender_other TEXT,
    default_pack_count INTEGER NOT NULL DEFAULT 1 CHECK (default_pack_count BETWEEN 1 AND 99),
    shipment_description TEXT NOT NULL DEFAULT 'Atelier Marie order',
    declared_value_enabled INTEGER NOT NULL DEFAULT 0 CHECK (declared_value_enabled IN (0, 1)),
    default_payment_side TEXT NOT NULL DEFAULT 'receiver'
                               CHECK (default_payment_side IN ('sender', 'receiver')),
    return_parcel_destination TEXT NOT NULL DEFAULT 'sender',
    days_until_return INTEGER NOT NULL DEFAULT 7 CHECK (days_until_return BETWEEN 0 AND 30),
    return_parcel_payment_side TEXT NOT NULL DEFAULT 'sender'
                               CHECK (return_parcel_payment_side IN ('sender', 'receiver')),
    reject_action TEXT NOT NULL DEFAULT 'return_to_sender',
    reject_payment_side TEXT NOT NULL DEFAULT 'sender'
                               CHECK (reject_payment_side IN ('sender', 'receiver')),
    reject_return_payment_side TEXT NOT NULL DEFAULT 'sender'
                               CHECK (reject_return_payment_side IN ('sender', 'receiver')),
    courier_currency TEXT NOT NULL DEFAULT 'EUR'
                               CHECK (courier_currency IN ('EUR', 'BGN')),
    currency_conversion_rate DOUBLE PRECISION CHECK (currency_conversion_rate IS NULL OR currency_conversion_rate > 0),
    office_locator_enabled INTEGER NOT NULL DEFAULT 0 CHECK (office_locator_enabled IN (0, 1)),
    auto_confirm_on_label INTEGER NOT NULL DEFAULT 0 CHECK (auto_confirm_on_label IN (0, 1)),
    auto_delivered_on_trace INTEGER NOT NULL DEFAULT 0 CHECK (auto_delivered_on_trace IN (0, 1)),
    last_health_status TEXT,
    last_health_checked_at TIMESTAMPTZ,
    last_health_error TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE expense_evidence (
    id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    supplier_identifier TEXT,
    document_number TEXT,
    document_date DATE,
    purchase_date DATE NOT NULL,
    payment_date DATE,
    payment_status TEXT NOT NULL DEFAULT 'unpaid' CHECK (payment_status IN (
                    'unpaid', 'paid', 'partially_paid', 'reimbursed', 'cancelled'
                )),
    category_key TEXT,
    net_amount_cents INTEGER CHECK (net_amount_cents IS NULL OR net_amount_cents >= 0),
    tax_amount_cents INTEGER NOT NULL DEFAULT 0 CHECK (tax_amount_cents >= 0),
    gross_amount_cents INTEGER NOT NULL CHECK (gross_amount_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'EUR',
    attachment_reference TEXT,
    linked_product_id TEXT REFERENCES products(id) ON DELETE SET NULL,
    linked_material_name TEXT,
    linked_courier TEXT CHECK (linked_courier IS NULL OR linked_courier IN ('speedy', 'econt')),
    linked_order_id TEXT REFERENCES orders(id) ON DELETE SET NULL,
    review_status TEXT NOT NULL DEFAULT 'unreviewed' CHECK (review_status IN (
                    'unreviewed', 'reviewed', 'missing_document', 'waived', 'rejected'
                )),
    notes TEXT,
    created_by_admin_id TEXT,
    updated_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE expense_evidence_settings (
    id TEXT PRIMARY KEY DEFAULT 'default' CHECK (id = 'default'),
    required_document_categories_json TEXT,
    allowed_payment_statuses_json TEXT,
    default_category_mappings_json TEXT,
    close_behavior TEXT NOT NULL DEFAULT 'warn' CHECK (close_behavior IN ('warn', 'block')),
    reviewed INTEGER NOT NULL DEFAULT 0 CHECK (reviewed IN (0, 1)),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE finance_audit_events (
    id TEXT PRIMARY KEY,
    actor_user_id TEXT,
    actor_email TEXT,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    request_id TEXT,
    before_json TEXT,
    after_json TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE finance_exceptions (
    id TEXT PRIMARY KEY,
    period_id TEXT REFERENCES finance_periods(id) ON DELETE CASCADE,
    exception_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'blocking' CHECK (severity IN ('blocking', 'warning')),
    target_type TEXT,
    target_id TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN (
                    'open', 'resolved', 'waived'
                )),
    message TEXT NOT NULL,
    details_json TEXT,
    waived_by_admin_id TEXT,
    waiver_reason TEXT,
    waived_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE finance_export_packages (
    id TEXT PRIMARY KEY,
    period_id TEXT NOT NULL REFERENCES finance_periods(id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK (version >= 1),
    schema_version TEXT NOT NULL DEFAULT 'accounting-finance-hub.v1',
    xlsx_path TEXT,
    csv_dir_path TEXT,
    manifest_path TEXT,
    manifest_json TEXT,
    generated_by_admin_id TEXT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accepted_by_admin_id TEXT,
    accepted_at TIMESTAMPTZ,
    accountant_name TEXT,
    accountant_reference TEXT,
    acceptance_note TEXT,
    current_final INTEGER NOT NULL DEFAULT 1 CHECK (current_final IN (0, 1)),
    UNIQUE (period_id, version)
);

CREATE TABLE inventory_closes (
    id TEXT PRIMARY KEY,
    period_id TEXT REFERENCES finance_periods(id) ON DELETE SET NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
                    'draft', 'reviewed', 'closed', 'blocked'
                )),
    currency TEXT NOT NULL DEFAULT 'EUR',
    valuation_method TEXT NOT NULL CHECK (valuation_method IN ('weighted_average', 'fifo')),
    policy_snapshot_json TEXT,
    opening_value_cents INTEGER NOT NULL DEFAULT 0 CHECK (opening_value_cents >= 0),
    receipts_value_cents INTEGER NOT NULL DEFAULT 0 CHECK (receipts_value_cents >= 0),
    production_consumption_value_cents INTEGER NOT NULL DEFAULT 0 CHECK (production_consumption_value_cents >= 0),
    finished_output_value_cents INTEGER NOT NULL DEFAULT 0 CHECK (finished_output_value_cents >= 0),
    sales_cogs_value_cents INTEGER NOT NULL DEFAULT 0 CHECK (sales_cogs_value_cents >= 0),
    returns_value_cents INTEGER NOT NULL DEFAULT 0 CHECK (returns_value_cents >= 0),
    adjustments_value_cents INTEGER NOT NULL DEFAULT 0 CHECK (adjustments_value_cents >= 0),
    ending_value_cents INTEGER NOT NULL DEFAULT 0 CHECK (ending_value_cents >= 0),
    exception_count INTEGER NOT NULL DEFAULT 0 CHECK (exception_count >= 0),
    official INTEGER NOT NULL DEFAULT 0 CHECK (official IN (0, 1)),
    reviewed_by_admin_id TEXT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (period_start <= period_end)
);

CREATE TABLE inventory_exceptions (
    id TEXT PRIMARY KEY,
    period_id TEXT REFERENCES finance_periods(id) ON DELETE CASCADE,
    exception_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'blocking' CHECK (severity IN ('blocking', 'warning')),
    target_type TEXT,
    target_id TEXT,
    source_type TEXT,
    source_id TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN (
                    'open', 'resolved', 'waived'
                )),
    message TEXT NOT NULL,
    details_json TEXT,
    created_by_admin_id TEXT,
    resolved_by_admin_id TEXT,
    resolved_at TIMESTAMPTZ,
    waived_by_admin_id TEXT,
    waiver_reason TEXT,
    waived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory_settings (
    id TEXT PRIMARY KEY DEFAULT 'default' CHECK (id = 'default'),
    ledger_mode TEXT NOT NULL DEFAULT 'setup' CHECK (ledger_mode IN (
                    'legacy', 'setup', 'ledger_managed'
                )),
    valuation_enabled INTEGER NOT NULL DEFAULT 0 CHECK (valuation_enabled IN (0, 1)),
    valuation_method TEXT NOT NULL DEFAULT 'weighted_average' CHECK (valuation_method IN (
                    'weighted_average', 'fifo'
                )),
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    cogs_date_basis TEXT NOT NULL DEFAULT 'order_date' CHECK (cogs_date_basis IN (
                    'order_date', 'payment_date', 'shipment_date',
                    'delivery_date', 'period_close'
                )),
    rounding_policy TEXT NOT NULL DEFAULT 'half_up_2dp' CHECK (rounding_policy IN (
                    'half_up_2dp', 'half_up_4dp'
                )),
    missing_cost_behavior TEXT NOT NULL DEFAULT 'block_official' CHECK (
                    missing_cost_behavior IN ('allow_estimate', 'warn', 'block_official')
                ),
    included_cost_components_json TEXT,
    write_off_mapping_json TEXT,
    currency TEXT NOT NULL DEFAULT 'EUR',
    settings_version INTEGER NOT NULL DEFAULT 1 CHECK (settings_version >= 1),
    accountant_reviewed INTEGER NOT NULL DEFAULT 0 CHECK (accountant_reviewed IN (0, 1)),
    reviewed_by_admin_id TEXT,
    reviewed_by_name TEXT,
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE materials (
    id TEXT PRIMARY KEY,
    sku TEXT UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'material',
    stock_uom TEXT NOT NULL,
    purchase_uom TEXT,
    purchase_to_stock_factor DOUBLE PRECISION CHECK (
                    purchase_to_stock_factor IS NULL OR purchase_to_stock_factor > 0
                ),
    preferred_supplier_name TEXT,
    preferred_supplier_sku TEXT,
    reorder_threshold DOUBLE PRECISION CHECK (reorder_threshold IS NULL OR reorder_threshold >= 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    lot_tracked INTEGER NOT NULL DEFAULT 0 CHECK (lot_tracked IN (0, 1)),
    expiry_tracked INTEGER NOT NULL DEFAULT 0 CHECK (expiry_tracked IN (0, 1)),
    evidence_required INTEGER NOT NULL DEFAULT 0 CHECK (evidence_required IN (0, 1)),
    notes TEXT,
    created_by_admin_id TEXT,
    updated_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_courier_events (
    id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    courier TEXT NOT NULL CHECK (courier IN ('speedy', 'econt')),
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    request_json TEXT,
    response_json TEXT,
    error_json TEXT,
    actor_user_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_email_send_claims (
    order_id TEXT NOT NULL REFERENCES orders(id),
    event TEXT NOT NULL,
    status TEXT NOT NULL,  -- in_flight | sent | failed
    lease_expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, event)
);

CREATE TABLE order_emails (
    id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    order_id TEXT NOT NULL REFERENCES orders(id),
    event TEXT NOT NULL,  -- placed | shipped | delivered | cancelled | admin_new_order
    recipient TEXT NOT NULL,
    -- queued | sent | failed | failed_permanent
    --   | skipped_duplicate | skipped_in_flight | skipped_suppressed
    status TEXT NOT NULL,
    reason TEXT,           -- provider error (failed) or skip detail
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ,           -- backoff gate; NULL = eligible immediately
    sent_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    order_id TEXT NOT NULL REFERENCES orders(id),
    product_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    quantity INTEGER NOT NULL CHECK (quantity >= 1 AND quantity <= 99),
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE order_returns (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    reason TEXT NOT NULL CHECK (reason IN (
                    'not_picked_up', 'refused_delivery', 'customer_return',
                    'wrong_address', 'unreachable_customer', 'damaged_by_courier',
                    'lost_by_courier', 'merchant_error', 'other'
                )),
    source TEXT NOT NULL DEFAULT 'admin' CHECK (source IN (
                    'admin', 'speedy', 'econt', 'customer', 'stripe', 'system'
                )),
    status TEXT NOT NULL DEFAULT 'requested' CHECK (status IN (
                    'requested', 'return_in_transit', 'received',
                    'inspected', 'rejected', 'closed'
                )),
    refund_amount_cents INTEGER CHECK (
                    refund_amount_cents IS NULL OR refund_amount_cents >= 0
                ),
    courier_return_fee_cents INTEGER NOT NULL DEFAULT 0
                    CHECK (courier_return_fee_cents >= 0),
    courier_claim_id TEXT,
    courier_claim_status TEXT NOT NULL DEFAULT 'none' CHECK (courier_claim_status IN (
                    'none', 'filed', 'approved', 'rejected', 'paid'
                )),
    courier_claim_amount_cents INTEGER CHECK (
                    courier_claim_amount_cents IS NULL OR courier_claim_amount_cents >= 0
                ),
    restock_decision TEXT NOT NULL DEFAULT 'pending' CHECK (restock_decision IN (
                    'pending', 'restock', 'do_not_restock', 'partial'
                )),
    returned_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    inspected_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    notes TEXT,
    created_by_admin_id TEXT,
    updated_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payment_rate_limit_events (
    id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    action TEXT NOT NULL,
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payment_refunds (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    payment_id TEXT REFERENCES payments(id) ON DELETE SET NULL,
    provider TEXT NOT NULL CHECK (provider IN (
                    'stripe', 'manual', 'bank_transfer', 'cod_adjustment'
                )),
    provider_refund_id TEXT,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
                    'pending', 'succeeded', 'failed', 'cancelled'
                )),
    reason TEXT,
    idempotency_key TEXT,
    failure_reason TEXT,
    created_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMPTZ
);

CREATE TABLE product_cost_settings (
    id TEXT PRIMARY KEY DEFAULT 'default' CHECK (id = 'default'),
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    costing_basis TEXT NOT NULL DEFAULT 'manual_snapshot' CHECK (costing_basis IN (
                    'manual_snapshot', 'recipe_bom', 'imported_estimate'
                )),
    include_labor INTEGER NOT NULL DEFAULT 0 CHECK (include_labor IN (0, 1)),
    include_overhead INTEGER NOT NULL DEFAULT 0 CHECK (include_overhead IN (0, 1)),
    missing_cost_policy TEXT NOT NULL DEFAULT 'warning' CHECK (missing_cost_policy IN (
                    'none', 'warning', 'blocking'
                )),
    reviewed INTEGER NOT NULL DEFAULT 0 CHECK (reviewed IN (0, 1)),
    estimate_label TEXT NOT NULL DEFAULT 'management_estimate',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_cost_versions (
    id TEXT PRIMARY KEY,
    product_id TEXT REFERENCES products(id) ON DELETE SET NULL,
    sku TEXT,
    product_name TEXT NOT NULL,
    effective_date DATE NOT NULL,
    costing_basis TEXT NOT NULL DEFAULT 'manual_snapshot' CHECK (costing_basis IN (
                    'manual_snapshot', 'recipe_bom', 'imported_estimate'
                )),
    material_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (material_cost_cents >= 0),
    packaging_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (packaging_cost_cents >= 0),
    labor_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (labor_cost_cents >= 0),
    overhead_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (overhead_cost_cents >= 0),
    estimated_unit_cost_cents INTEGER NOT NULL CHECK (estimated_unit_cost_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'EUR',
    reviewed INTEGER NOT NULL DEFAULT 0 CHECK (reviewed IN (0, 1)),
    accountant_reviewed INTEGER NOT NULL DEFAULT 0 CHECK (accountant_reviewed IN (0, 1)),
    review_status TEXT NOT NULL DEFAULT 'estimate' CHECK (review_status IN (
                    'estimate', 'reviewed', 'accountant_reviewed', 'archived'
                )),
    source_expense_ids_json TEXT,
    notes TEXT,
    created_by_admin_id TEXT,
    updated_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE promotion_campaigns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    note TEXT,
    discount_percent INTEGER NOT NULL
                  CHECK (discount_percent BETWEEN 1 AND 99),
    discount_starts_at TIMESTAMPTZ,
    discount_ends_at TIMESTAMPTZ,
    target_type TEXT NOT NULL CHECK (target_type IN ('ids', 'filter')),
    target_ids TEXT,   -- JSON array of product IDs when target_type = 'ids'
    target_filter TEXT,   -- JSON filter descriptor when target_type = 'filter'
    applied_at TIMESTAMPTZ,   -- NULL until first applied
    removed_at TIMESTAMPTZ,   -- NULL unless discount has been removed
    last_result TEXT,   -- JSON summary of the most recent apply/remove result
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reaction_toggle_log (
    session_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    toggled_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reactions (
    session_id TEXT NOT NULL,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    reaction_type TEXT NOT NULL CHECK (reaction_type IN ('heart', 'thumbs_up')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, product_id, reaction_type)
);

CREATE TABLE recipe_versions (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    version_label TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
                    'draft', 'active', 'archived'
                )),
    effective_date DATE NOT NULL,
    output_quantity DOUBLE PRECISION NOT NULL CHECK (output_quantity > 0),
    output_uom TEXT NOT NULL DEFAULT 'unit',
    review_state TEXT NOT NULL DEFAULT 'estimate' CHECK (review_state IN (
                    'estimate', 'reviewed', 'accountant_reviewed', 'invalid'
                )),
    accountant_reviewed INTEGER NOT NULL DEFAULT 0 CHECK (accountant_reviewed IN (0, 1)),
    reviewed_by_admin_id TEXT,
    reviewed_at TIMESTAMPTZ,
    notes TEXT,
    created_by_admin_id TEXT,
    updated_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (product_id, version_label)
);

CREATE TABLE site_banners (
    id TEXT PRIMARY KEY DEFAULT 'default',
    message_en TEXT,
    message_bg TEXT,
    link_label_en TEXT,
    link_label_bg TEXT,
    link_url TEXT,
    is_enabled INTEGER NOT NULL DEFAULT 0 CHECK (is_enabled IN (0, 1)),
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE site_setting_events (
    id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    setting_key TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    admin_id TEXT,
    admin_email TEXT,
    request_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE site_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'json',
    is_public INTEGER NOT NULL DEFAULT 0 CHECK (is_public IN (0, 1)),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stock_counts (
    id TEXT PRIMARY KEY,
    count_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
                    'draft', 'posted', 'cancelled'
                )),
    scope_notes TEXT,
    created_by_admin_id TEXT,
    posted_by_admin_id TEXT,
    posted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stripe_balance_transactions (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL DEFAULT 'stripe' CHECK (provider = 'stripe'),
    balance_transaction_id TEXT NOT NULL UNIQUE,
    reporting_category TEXT,
    transaction_type TEXT,
    provider_created_at TIMESTAMPTZ,
    available_on TIMESTAMPTZ,
    gross_amount_cents INTEGER NOT NULL,
    fee_amount_cents INTEGER NOT NULL DEFAULT 0,
    net_amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'EUR',
    payment_intent_id TEXT,
    charge_id TEXT,
    provider_refund_id TEXT,
    dispute_id TEXT,
    payout_id TEXT,
    payout_effective_at TIMESTAMPTZ,
    payout_arrival_at TIMESTAMPTZ,
    payout_status TEXT,
    trace_id TEXT,
    status TEXT NOT NULL DEFAULT 'imported' CHECK (status IN (
                    'imported', 'matched', 'unmatched', 'duplicate', 'ignored'
                )),
    match_status TEXT NOT NULL DEFAULT 'unmatched' CHECK (match_status IN (
                    'unmatched', 'matched', 'mismatch', 'duplicate', 'ignored'
                )),
    raw_row_json TEXT,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stripe_events (
    event_id TEXT PRIMARY KEY,   -- Stripe's evt_xxx — dedup key
    order_id TEXT,               -- nullable: some events may not map to an order
    event_type TEXT NOT NULL,      -- e.g. 'checkout.session.completed'
    received_at TIMESTAMPTZ NOT NULL       -- YYYY-MM-DD HH:MM:SS UTC
);

CREATE TABLE suppressed_emails (
    email TEXT PRIMARY KEY,
    reason TEXT NOT NULL,  -- hard_bounce | soft_bounce | fbl_complaint
    suppressed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE about_items (
    id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    section TEXT NOT NULL REFERENCES about_sections(slug) ON DELETE CASCADE,
    title_en TEXT NOT NULL,
    title_bg TEXT,
    text_en TEXT,
    text_bg TEXT,
    image_id TEXT,
    link_href TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_published INTEGER NOT NULL DEFAULT 1 CHECK (is_published IN (0, 1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE accounting_documents (
    id TEXT PRIMARY KEY,
    document_type TEXT NOT NULL CHECK (document_type IN (
                    'invoice', 'credit_note', 'fiscal_receipt',
                    'alternative_sales_document', 'external_document'
                )),
    source_system TEXT NOT NULL DEFAULT 'external',
    document_number TEXT,
    issue_date DATE NOT NULL,
    order_id TEXT REFERENCES orders(id) ON DELETE SET NULL,
    refund_id TEXT REFERENCES payment_refunds(id) ON DELETE SET NULL,
    period_id TEXT REFERENCES finance_periods(id) ON DELETE SET NULL,
    currency TEXT NOT NULL DEFAULT 'EUR',
    net_amount_cents INTEGER CHECK (net_amount_cents IS NULL OR net_amount_cents >= 0),
    tax_amount_cents INTEGER CHECK (tax_amount_cents IS NULL OR tax_amount_cents >= 0),
    gross_amount_cents INTEGER CHECK (gross_amount_cents IS NULL OR gross_amount_cents >= 0),
    vat_summary_json TEXT,
    original_document_id TEXT REFERENCES accounting_documents(id) ON DELETE SET NULL,
    file_reference TEXT,
    status TEXT NOT NULL DEFAULT 'recorded' CHECK (status IN (
                    'draft', 'recorded', 'void', 'corrected', 'missing', 'review_required'
                )),
    notes TEXT,
    created_by_admin_id TEXT,
    updated_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory_adjustments (
    id TEXT PRIMARY KEY,
    order_id TEXT REFERENCES orders(id) ON DELETE SET NULL,
    order_return_id TEXT REFERENCES order_returns(id) ON DELETE SET NULL,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    reason TEXT NOT NULL CHECK (reason IN (
                        'return_restock', 'return_partial_restock', 'manual_correction'
                    )),
    source TEXT NOT NULL DEFAULT 'admin' CHECK (source IN ('admin', 'system')),
    notes TEXT,
    created_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE material_receipts (
    id TEXT PRIMARY KEY,
    material_id TEXT NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    receipt_date DATE NOT NULL DEFAULT CURRENT_DATE,
    quantity DOUBLE PRECISION NOT NULL CHECK (quantity > 0),
    uom TEXT NOT NULL,
    stock_quantity DOUBLE PRECISION NOT NULL CHECK (stock_quantity > 0),
    stock_uom TEXT NOT NULL,
    unit_cost_amount TEXT,
    total_cost_cents INTEGER CHECK (total_cost_cents IS NULL OR total_cost_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'EUR',
    supplier_name TEXT,
    supplier_lot TEXT,
    expiry_date DATE,
    use_by_date DATE,
    expense_evidence_id TEXT REFERENCES expense_evidence(id) ON DELETE SET NULL,
    document_reference TEXT,
    review_state TEXT NOT NULL DEFAULT 'draft' CHECK (review_state IN (
                    'draft', 'needs_review', 'reviewed', 'rejected'
                )),
    created_by_admin_id TEXT,
    updated_by_admin_id TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_return_events (
    id TEXT PRIMARY KEY,
    order_return_id TEXT REFERENCES order_returns(id) ON DELETE CASCADE,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'admin' CHECK (source IN (
                        'admin', 'speedy', 'econt', 'customer', 'stripe', 'system'
                    )),
    payload_json TEXT,
    admin_user_id TEXT,
    admin_email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_cost_components (
    id TEXT PRIMARY KEY,
    cost_version_id TEXT NOT NULL REFERENCES product_cost_versions(id) ON DELETE CASCADE,
    component_type TEXT NOT NULL CHECK (component_type IN (
                    'material', 'packaging', 'labor', 'overhead', 'waste', 'other'
                )),
    description TEXT NOT NULL,
    quantity DOUBLE PRECISION CHECK (quantity IS NULL OR quantity >= 0),
    unit TEXT,
    unit_cost_cents INTEGER CHECK (unit_cost_cents IS NULL OR unit_cost_cents >= 0),
    total_cost_cents INTEGER NOT NULL CHECK (total_cost_cents >= 0),
    source_expense_id TEXT REFERENCES expense_evidence(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE promotion_campaign_products (
    campaign_id TEXT NOT NULL
                      REFERENCES promotion_campaigns(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL,
    applied_percent INTEGER,
    applied_starts_at TIMESTAMPTZ,
    applied_ends_at TIMESTAMPTZ,
    PRIMARY KEY (campaign_id, product_id)
);

CREATE TABLE recipe_components (
    id TEXT PRIMARY KEY,
    recipe_version_id TEXT NOT NULL REFERENCES recipe_versions(id) ON DELETE CASCADE,
    material_id TEXT NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    quantity DOUBLE PRECISION NOT NULL CHECK (quantity > 0),
    uom TEXT NOT NULL,
    quantity_basis TEXT NOT NULL DEFAULT 'per_batch' CHECK (quantity_basis IN (
                    'per_unit', 'per_batch'
                )),
    wastage_percent DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (wastage_percent >= 0),
    required INTEGER NOT NULL DEFAULT 1 CHECK (required IN (0, 1)),
    substitute_group TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    review_state TEXT NOT NULL DEFAULT 'valid' CHECK (review_state IN (
                    'valid', 'warning', 'invalid'
                )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recipe_cost_snapshots (
    id TEXT PRIMARY KEY,
    recipe_version_id TEXT NOT NULL REFERENCES recipe_versions(id) ON DELETE CASCADE,
    currency TEXT NOT NULL DEFAULT 'EUR',
    material_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (material_cost_cents >= 0),
    packaging_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (packaging_cost_cents >= 0),
    labor_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (labor_cost_cents >= 0),
    overhead_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (overhead_cost_cents >= 0),
    batch_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (batch_cost_cents >= 0),
    expected_unit_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (expected_unit_cost_cents >= 0),
    source_cost_references_json TEXT,
    missing_cost_count INTEGER NOT NULL DEFAULT 0 CHECK (missing_cost_count >= 0),
    estimate_label TEXT NOT NULL DEFAULT 'management_estimate',
    review_state TEXT NOT NULL DEFAULT 'estimate' CHECK (review_state IN (
                    'estimate', 'incomplete', 'reviewed', 'accountant_reviewed'
                )),
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE material_lots (
    id TEXT PRIMARY KEY,
    material_id TEXT NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    receipt_id TEXT REFERENCES material_receipts(id) ON DELETE SET NULL,
    supplier_lot TEXT,
    expiry_date DATE,
    use_by_date DATE,
    received_quantity DOUBLE PRECISION NOT NULL CHECK (received_quantity > 0),
    stock_uom TEXT NOT NULL,
    remaining_quantity_snapshot DOUBLE PRECISION CHECK (
                    remaining_quantity_snapshot IS NULL OR remaining_quantity_snapshot >= 0
                ),
    unit_cost_amount TEXT,
    currency TEXT NOT NULL DEFAULT 'EUR',
    supplier_name TEXT,
    review_state TEXT NOT NULL DEFAULT 'draft' CHECK (review_state IN (
                    'draft', 'needs_review', 'reviewed', 'rejected'
                )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE production_batches (
    id TEXT PRIMARY KEY,
    batch_number TEXT NOT NULL UNIQUE,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    recipe_version_id TEXT REFERENCES recipe_versions(id) ON DELETE SET NULL,
    planned_output_quantity DOUBLE PRECISION NOT NULL CHECK (planned_output_quantity > 0),
    actual_output_quantity DOUBLE PRECISION CHECK (actual_output_quantity IS NULL OR actual_output_quantity >= 0),
    output_uom TEXT NOT NULL DEFAULT 'unit',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
                    'draft', 'produced', 'cancelled'
                )),
    production_date DATE NOT NULL,
    ready_date DATE,
    cost_snapshot_id TEXT REFERENCES recipe_cost_snapshots(id) ON DELETE SET NULL,
    variance_review_state TEXT NOT NULL DEFAULT 'not_reviewed' CHECK (
                    variance_review_state IN ('not_reviewed', 'warning', 'reviewed')
                ),
    actor_user_id TEXT,
    notes TEXT,
    created_by_admin_id TEXT,
    updated_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory_movements (
    id TEXT PRIMARY KEY,
    item_type TEXT NOT NULL CHECK (item_type IN ('material', 'finished_good')),
    item_id TEXT NOT NULL,
    movement_type TEXT NOT NULL CHECK (movement_type IN (
                    'receipt', 'opening_balance', 'production_consumption',
                    'production_output', 'sale_issue', 'cancellation_reversal',
                    'return_restock', 'return_write_off', 'adjustment', 'spoilage',
                    'write_off', 'stock_count_correction', 'valuation_adjustment',
                    'reversal'
                )),
    quantity_delta DOUBLE PRECISION NOT NULL CHECK (quantity_delta != 0),
    uom TEXT NOT NULL,
    source_type TEXT,
    source_id TEXT,
    material_lot_id TEXT REFERENCES material_lots(id) ON DELETE SET NULL,
    product_id TEXT REFERENCES products(id) ON DELETE SET NULL,
    order_id TEXT REFERENCES orders(id) ON DELETE SET NULL,
    order_item_key TEXT,
    actor_user_id TEXT,
    actor_email TEXT,
    reason TEXT,
    notes TEXT,
    reversal_of_movement_id TEXT REFERENCES inventory_movements(id) ON DELETE SET NULL,
    review_state TEXT NOT NULL DEFAULT 'unreviewed' CHECK (review_state IN (
                    'unreviewed', 'reviewed', 'estimate', 'official', 'reversed'
                )),
    metadata_json TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_inventory_profiles (
    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    inventory_mode TEXT NOT NULL DEFAULT 'legacy' CHECK (inventory_mode IN (
                    'legacy', 'fallback', 'ledger_managed'
                )),
    stock_source TEXT NOT NULL DEFAULT 'product_stock' CHECK (stock_source IN (
                    'product_stock', 'inventory_ledger', 'mixed'
                )),
    requires_recipe INTEGER NOT NULL DEFAULT 0 CHECK (requires_recipe IN (0, 1)),
    opening_balance_state TEXT NOT NULL DEFAULT 'unreviewed' CHECK (
                    opening_balance_state IN ('not_required', 'unreviewed', 'reviewed', 'blocked')
                ),
    latest_batch_id TEXT REFERENCES production_batches(id) ON DELETE SET NULL,
    valuation_readiness TEXT NOT NULL DEFAULT 'setup_required' CHECK (
                    valuation_readiness IN ('setup_required', 'estimate_only', 'ready', 'blocked')
                ),
    notes TEXT,
    created_by_admin_id TEXT,
    updated_by_admin_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory_valuation_layers (
    id TEXT PRIMARY KEY,
    movement_id TEXT REFERENCES inventory_movements(id) ON DELETE SET NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('material', 'finished_good')),
    item_id TEXT NOT NULL,
    quantity DOUBLE PRECISION NOT NULL CHECK (quantity != 0),
    unit_value_amount TEXT,
    total_value_cents INTEGER CHECK (total_value_cents IS NULL OR total_value_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'EUR',
    valuation_method TEXT NOT NULL CHECK (valuation_method IN (
                    'weighted_average', 'fifo', 'revaluation'
                )),
    source_type TEXT,
    source_id TEXT,
    valuation_date DATE NOT NULL,
    review_state TEXT NOT NULL DEFAULT 'estimate' CHECK (review_state IN (
                    'estimate', 'reviewed', 'official', 'reversed'
                )),
    method_metadata_json TEXT,
    reversal_layer_id TEXT REFERENCES inventory_valuation_layers(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE production_batch_consumption (
    id TEXT PRIMARY KEY,
    production_batch_id TEXT NOT NULL REFERENCES production_batches(id) ON DELETE CASCADE,
    recipe_component_id TEXT REFERENCES recipe_components(id) ON DELETE SET NULL,
    material_id TEXT NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    material_lot_id TEXT REFERENCES material_lots(id) ON DELETE SET NULL,
    expected_quantity DOUBLE PRECISION CHECK (expected_quantity IS NULL OR expected_quantity >= 0),
    actual_quantity DOUBLE PRECISION CHECK (actual_quantity IS NULL OR actual_quantity >= 0),
    waste_quantity DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (waste_quantity >= 0),
    uom TEXT NOT NULL,
    unit_cost_amount TEXT,
    currency TEXT NOT NULL DEFAULT 'EUR',
    movement_id TEXT REFERENCES inventory_movements(id) ON DELETE SET NULL,
    review_state TEXT NOT NULL DEFAULT 'draft' CHECK (review_state IN (
                    'draft', 'needs_review', 'reviewed', 'rejected'
                )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE production_batch_outputs (
    id TEXT PRIMARY KEY,
    production_batch_id TEXT NOT NULL REFERENCES production_batches(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    batch_number TEXT NOT NULL,
    quantity DOUBLE PRECISION NOT NULL CHECK (quantity > 0),
    uom TEXT NOT NULL DEFAULT 'unit',
    unit_cost_amount TEXT,
    currency TEXT NOT NULL DEFAULT 'EUR',
    movement_id TEXT REFERENCES inventory_movements(id) ON DELETE SET NULL,
    remaining_quantity_snapshot DOUBLE PRECISION CHECK (
                    remaining_quantity_snapshot IS NULL OR remaining_quantity_snapshot >= 0
                ),
    valuation_review_state TEXT NOT NULL DEFAULT 'estimate' CHECK (
                    valuation_review_state IN ('estimate', 'reviewed', 'official')
                ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stock_count_lines (
    id TEXT PRIMARY KEY,
    stock_count_id TEXT NOT NULL REFERENCES stock_counts(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL CHECK (item_type IN ('material', 'finished_good')),
    item_id TEXT NOT NULL,
    expected_quantity DOUBLE PRECISION CHECK (expected_quantity IS NULL OR expected_quantity >= 0),
    counted_quantity DOUBLE PRECISION NOT NULL CHECK (counted_quantity >= 0),
    variance_quantity DOUBLE PRECISION,
    uom TEXT NOT NULL,
    correction_movement_id TEXT REFERENCES inventory_movements(id) ON DELETE SET NULL,
    reason TEXT,
    review_state TEXT NOT NULL DEFAULT 'draft' CHECK (review_state IN (
                    'draft', 'needs_review', 'reviewed'
                )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cogs_ledger (
    id TEXT PRIMARY KEY,
    order_id TEXT REFERENCES orders(id) ON DELETE SET NULL,
    order_number TEXT,
    order_item_key TEXT,
    product_id TEXT REFERENCES products(id) ON DELETE SET NULL,
    quantity_sold DOUBLE PRECISION NOT NULL CHECK (quantity_sold > 0),
    cogs_date TEXT NOT NULL,
    unit_cost_amount TEXT,
    total_cost_cents INTEGER NOT NULL CHECK (total_cost_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'EUR',
    valuation_method TEXT NOT NULL CHECK (valuation_method IN ('weighted_average', 'fifo')),
    source_movement_id TEXT REFERENCES inventory_movements(id) ON DELETE SET NULL,
    source_valuation_layer_id TEXT REFERENCES inventory_valuation_layers(id) ON DELETE SET NULL,
    source_finished_batch_id TEXT REFERENCES production_batches(id) ON DELETE SET NULL,
    review_state TEXT NOT NULL DEFAULT 'estimate' CHECK (review_state IN (
                    'estimate', 'reviewed', 'official', 'reversed'
                )),
    reversal_cogs_id TEXT REFERENCES cogs_ledger(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Remaining launch schema indexes.

CREATE INDEX IF NOT EXISTS idx_about_items_section_order
    ON about_items(section, sort_order);

CREATE INDEX IF NOT EXISTS idx_accounting_documents_order_issue
    ON accounting_documents(order_id, issue_date);

CREATE INDEX IF NOT EXISTS idx_accounting_documents_period_issue
    ON accounting_documents(period_id, issue_date);

CREATE INDEX IF NOT EXISTS idx_admin_alerts_order_id
    ON admin_alerts(order_id, created_at);

CREATE INDEX IF NOT EXISTS idx_admin_alerts_unread_created
    ON admin_alerts(is_read, created_at);

CREATE INDEX IF NOT EXISTS idx_cod_settlements_mismatch
    ON cod_settlements(mismatch_review, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cod_settlements_order_id
    ON cod_settlements(order_id);

CREATE INDEX IF NOT EXISTS idx_cogs_ledger_order_product_date
    ON cogs_ledger(order_id, product_id, cogs_date);

CREATE INDEX IF NOT EXISTS idx_cogs_ledger_product_date
    ON cogs_ledger(product_id, cogs_date);

CREATE INDEX IF NOT EXISTS idx_comments_product_created ON comments(product_id, created_at);

CREATE INDEX IF NOT EXISTS idx_comments_session_created ON comments(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_contact_messages_created_at
    ON contact_messages(created_at);

CREATE INDEX IF NOT EXISTS idx_contact_messages_email_status
    ON contact_messages(email_status, email_next_attempt_at);

CREATE INDEX IF NOT EXISTS idx_contact_messages_ip_created
    ON contact_messages(ip_address, created_at);

CREATE INDEX IF NOT EXISTS idx_expense_evidence_purchase_category
    ON expense_evidence(purchase_date, category_key);

CREATE INDEX IF NOT EXISTS idx_expense_evidence_review_status
    ON expense_evidence(review_status, purchase_date);

CREATE INDEX IF NOT EXISTS idx_finance_audit_events_target_created
    ON finance_audit_events(target_type, target_id, created_at);

CREATE INDEX IF NOT EXISTS idx_finance_exceptions_period_status
    ON finance_exceptions(period_id, status, severity);

CREATE INDEX IF NOT EXISTS idx_finance_exceptions_target
    ON finance_exceptions(target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_finance_export_packages_period_version
    ON finance_export_packages(period_id, version);

CREATE INDEX IF NOT EXISTS idx_inventory_adjustments_product_created
    ON inventory_adjustments(product_id, created_at);

CREATE INDEX IF NOT EXISTS idx_inventory_adjustments_reason_created
    ON inventory_adjustments(reason, created_at);

CREATE INDEX IF NOT EXISTS idx_inventory_adjustments_return_created
    ON inventory_adjustments(order_return_id, created_at);

CREATE INDEX IF NOT EXISTS idx_inventory_closes_period
    ON inventory_closes(period_id, period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_inventory_exceptions_period_status
    ON inventory_exceptions(period_id, status, severity);

CREATE INDEX IF NOT EXISTS idx_inventory_exceptions_target
    ON inventory_exceptions(target_type, target_id, status);

CREATE INDEX IF NOT EXISTS idx_inventory_movements_item_date
    ON inventory_movements(item_type, item_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_inventory_movements_source
    ON inventory_movements(source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_inventory_movements_type_date
    ON inventory_movements(movement_type, occurred_at);

CREATE INDEX IF NOT EXISTS idx_inventory_valuation_layers_item_date
    ON inventory_valuation_layers(item_type, item_id, valuation_date);

CREATE INDEX IF NOT EXISTS idx_inventory_valuation_layers_movement
    ON inventory_valuation_layers(movement_id);

CREATE INDEX IF NOT EXISTS idx_material_lots_material_expiry
    ON material_lots(material_id, expiry_date);

CREATE INDEX IF NOT EXISTS idx_material_receipts_material_date
    ON material_receipts(material_id, receipt_date);

CREATE INDEX IF NOT EXISTS idx_materials_category_active
    ON materials(category, active);

CREATE INDEX IF NOT EXISTS idx_order_courier_events_courier_action
    ON order_courier_events(courier, action, status);

CREATE INDEX IF NOT EXISTS idx_order_courier_events_order_created
    ON order_courier_events(order_id, created_at);

CREATE INDEX IF NOT EXISTS idx_order_emails_order_id ON order_emails(order_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_order_emails_sent_unique
    ON order_emails(order_id, event) WHERE status = 'sent';

CREATE INDEX IF NOT EXISTS idx_order_return_events_order_created
    ON order_return_events(order_id, created_at);

CREATE INDEX IF NOT EXISTS idx_order_return_events_return_created
    ON order_return_events(order_return_id, created_at);

CREATE INDEX IF NOT EXISTS idx_order_returns_claim_status
    ON order_returns(courier_claim_status, created_at);

CREATE INDEX IF NOT EXISTS idx_order_returns_order_id
    ON order_returns(order_id, created_at);

CREATE INDEX IF NOT EXISTS idx_order_returns_reason
    ON order_returns(reason, created_at);

CREATE INDEX IF NOT EXISTS idx_order_returns_restock_decision
    ON order_returns(restock_decision, created_at);

CREATE INDEX IF NOT EXISTS idx_order_returns_status
    ON order_returns(status, created_at);

CREATE INDEX IF NOT EXISTS idx_orders_accounting_classification
    ON orders(accounting_classification_state, created_at);

CREATE INDEX IF NOT EXISTS idx_orders_courier_poll_due
    ON orders(courier_provider, status, courier_next_poll_at, courier_poll_lease_expires_at);

CREATE INDEX IF NOT EXISTS idx_orders_courier_provider ON orders(courier_provider);

CREATE INDEX IF NOT EXISTS idx_orders_courier_shipment_number
    ON orders(courier_shipment_number);

CREATE INDEX IF NOT EXISTS idx_orders_courier_sync_status
    ON orders(courier_sync_status);

CREATE INDEX IF NOT EXISTS idx_orders_finance_period_id
    ON orders(finance_period_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_internal_sequence ON orders(internal_sequence);

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number);

CREATE INDEX IF NOT EXISTS idx_orders_payment_method ON orders(payment_method);

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_payment_return_token
    ON orders(payment_return_token);

CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status);

CREATE INDEX IF NOT EXISTS idx_orders_reserved_until ON orders(reserved_until);

CREATE INDEX IF NOT EXISTS idx_orders_session_id ON orders(session_id);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

CREATE INDEX IF NOT EXISTS idx_orders_stripe_checkout_session_id
    ON orders(stripe_checkout_session_id);

CREATE INDEX IF NOT EXISTS idx_orders_stripe_payment_intent_id
    ON orders(stripe_payment_intent_id);

CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);

CREATE INDEX IF NOT EXISTS idx_payment_rate_limit_lookup
    ON payment_rate_limit_events(action, scope, key, created_at);

CREATE INDEX IF NOT EXISTS idx_payment_refunds_order_id
    ON payment_refunds(order_id, created_at);

CREATE INDEX IF NOT EXISTS idx_payment_refunds_payment_id
    ON payment_refunds(payment_id, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_refunds_provider_idempotency
    ON payment_refunds(provider, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_payment_refunds_status
    ON payment_refunds(status, created_at);

CREATE INDEX IF NOT EXISTS idx_product_cost_components_version
    ON product_cost_components(cost_version_id);

CREATE INDEX IF NOT EXISTS idx_product_cost_versions_product_effective
    ON product_cost_versions(product_id, effective_date);

CREATE INDEX IF NOT EXISTS idx_product_inventory_profiles_mode
    ON product_inventory_profiles(inventory_mode, valuation_readiness);

CREATE INDEX IF NOT EXISTS idx_production_batch_consumption_batch
    ON production_batch_consumption(production_batch_id);

CREATE INDEX IF NOT EXISTS idx_production_batch_consumption_lot
    ON production_batch_consumption(material_lot_id);

CREATE INDEX IF NOT EXISTS idx_production_batch_outputs_product_batch
    ON production_batch_outputs(product_id, batch_number);

CREATE INDEX IF NOT EXISTS idx_production_batches_product_status_date
    ON production_batches(product_id, status, production_date);

CREATE INDEX IF NOT EXISTS idx_promotion_campaign_products_product
    ON promotion_campaign_products(product_id);

CREATE INDEX IF NOT EXISTS idx_promotion_campaigns_created
    ON promotion_campaigns(created_at);

CREATE INDEX IF NOT EXISTS idx_reaction_toggle_log_session_time
    ON reaction_toggle_log(session_id, toggled_at);

CREATE INDEX IF NOT EXISTS idx_reactions_product_type ON reactions(product_id, reaction_type);

CREATE INDEX IF NOT EXISTS idx_reactions_session_created ON reactions(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_recipe_components_material
    ON recipe_components(material_id);

CREATE INDEX IF NOT EXISTS idx_recipe_components_version_sort
    ON recipe_components(recipe_version_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_recipe_cost_snapshots_version_calculated
    ON recipe_cost_snapshots(recipe_version_id, calculated_at);

CREATE INDEX IF NOT EXISTS idx_recipe_versions_product_effective_status
    ON recipe_versions(product_id, effective_date, status);

CREATE INDEX IF NOT EXISTS idx_site_setting_events_key_created
    ON site_setting_events(setting_key, created_at);

CREATE INDEX IF NOT EXISTS idx_stock_count_lines_item
    ON stock_count_lines(item_type, item_id);

CREATE INDEX IF NOT EXISTS idx_stripe_balance_transactions_match
    ON stripe_balance_transactions(match_status, imported_at);

CREATE INDEX IF NOT EXISTS idx_stripe_balance_transactions_payout
    ON stripe_balance_transactions(payout_id, provider_created_at);

-- Updated-at triggers.

CREATE TRIGGER about_items_updated_at
BEFORE UPDATE ON about_items
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER about_sections_updated_at
BEFORE UPDATE ON about_sections
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER accounting_category_mappings_updated_at
BEFORE UPDATE ON accounting_category_mappings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER accounting_documents_updated_at
BEFORE UPDATE ON accounting_documents
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER accounting_export_schema_settings_updated_at
BEFORE UPDATE ON accounting_export_schema_settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER analytics_consents_updated_at
BEFORE UPDATE ON analytics_consents
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER cod_settlements_updated_at
BEFORE UPDATE ON cod_settlements
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER cookies_inventory_updated_at
BEFORE UPDATE ON cookies_inventory
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER cookies_page_updated_at
BEFORE UPDATE ON cookies_page
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER cookies_sections_updated_at
BEFORE UPDATE ON cookies_sections
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER delivery_settings_updated_at
BEFORE UPDATE ON delivery_settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER econt_settings_updated_at
BEFORE UPDATE ON econt_settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER expense_evidence_updated_at
BEFORE UPDATE ON expense_evidence
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER expense_evidence_settings_updated_at
BEFORE UPDATE ON expense_evidence_settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER faq_items_updated_at
BEFORE UPDATE ON faq_items
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER faq_sections_updated_at
BEFORE UPDATE ON faq_sections
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER finance_exceptions_updated_at
BEFORE UPDATE ON finance_exceptions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER finance_periods_updated_at
BEFORE UPDATE ON finance_periods
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER inventory_closes_updated_at
BEFORE UPDATE ON inventory_closes
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER inventory_exceptions_updated_at
BEFORE UPDATE ON inventory_exceptions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER inventory_settings_updated_at
BEFORE UPDATE ON inventory_settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER material_lots_updated_at
BEFORE UPDATE ON material_lots
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER material_receipts_updated_at
BEFORE UPDATE ON material_receipts
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER materials_updated_at
BEFORE UPDATE ON materials
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER order_email_send_claims_updated_at
BEFORE UPDATE ON order_email_send_claims
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER order_returns_updated_at
BEFORE UPDATE ON order_returns
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER orders_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER payments_updated_at
BEFORE UPDATE ON payments
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER privacy_page_updated_at
BEFORE UPDATE ON privacy_page
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER privacy_sections_updated_at
BEFORE UPDATE ON privacy_sections
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER product_categories_updated_at
BEFORE UPDATE ON product_categories
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER product_cost_settings_updated_at
BEFORE UPDATE ON product_cost_settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER product_cost_versions_updated_at
BEFORE UPDATE ON product_cost_versions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER product_inventory_profiles_updated_at
BEFORE UPDATE ON product_inventory_profiles
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER product_labels_updated_at
BEFORE UPDATE ON product_labels
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER product_types_updated_at
BEFORE UPDATE ON product_types
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER product_videos_updated_at
BEFORE UPDATE ON product_videos
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER production_batch_consumption_updated_at
BEFORE UPDATE ON production_batch_consumption
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER production_batches_updated_at
BEFORE UPDATE ON production_batches
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER promotion_campaigns_updated_at
BEFORE UPDATE ON promotion_campaigns
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER recipe_components_updated_at
BEFORE UPDATE ON recipe_components
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER recipe_versions_updated_at
BEFORE UPDATE ON recipe_versions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER site_banners_updated_at
BEFORE UPDATE ON site_banners
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER site_settings_updated_at
BEFORE UPDATE ON site_settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER stock_counts_updated_at
BEFORE UPDATE ON stock_counts
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER terms_page_updated_at
BEFORE UPDATE ON terms_page
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER terms_sections_updated_at
BEFORE UPDATE ON terms_sections
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- Product full-text search indexes.

CREATE INDEX idx_products_search_en ON products USING GIN (to_tsvector('simple'::regconfig, COALESCE(name_en, '') || ' ' || COALESCE(description_en, '')));

CREATE INDEX idx_products_search_bg ON products USING GIN (to_tsvector('simple'::regconfig, COALESCE(name_bg, '') || ' ' || COALESCE(description_bg, '')));

-- Structural seed data.

INSERT INTO product_types (slug, name_en, name_bg, sort_order, is_active)
VALUES
    ('candles', 'Candles', 'Свещи', 0, 1),
    ('boxes', 'Boxes', 'Кутии', 1, 1)
ON CONFLICT DO NOTHING;

INSERT INTO product_categories (slug, name_en, name_bg, sort_order, is_active)
VALUES
    ('small', 'Small', 'Малка', 0, 1),
    ('medium', 'Medium', 'Средна', 1, 1),
    ('premium', 'Premium', 'Премиум', 2, 1)
ON CONFLICT DO NOTHING;

INSERT INTO product_labels (slug, name_en, name_bg, sort_order, is_active)
VALUES
    ('floral', 'Floral', 'Флорални', 0, 1),
    ('woody', 'Woody', 'Дървесни', 1, 1),
    ('fresh', 'Fresh', 'Свежи', 2, 1),
    ('gourmand', 'Gourmand', 'Гурме', 3, 1),
    ('spicy', 'Spicy', 'Пикантни', 4, 1),
    ('citrus', 'Citrus', 'Цитрусови', 5, 1),
    ('winter', 'Winter', 'Зима', 6, 1),
    ('gift', 'Gift', 'Подарък', 7, 1),
    ('christmas', 'Christmas', 'Коледа', 8, 1)
ON CONFLICT DO NOTHING;

INSERT INTO faq_sections (slug, title_en, title_bg, icon, sort_order)
VALUES
    ('candles', 'About Our Candles', 'За нашите свещи', '🕯', 0),
    ('care', 'Candle Care & Safety', 'Грижа и безопасност', '✨', 1),
    ('custom', 'Custom Orders & Gifts', 'Поръчки по заявка и подаръци', '🎁', 2),
    ('shipping', 'Orders, Shipping & Returns', 'Поръчки, доставка и връщане', '📦', 3)
ON CONFLICT DO NOTHING;

INSERT INTO faq_items (section, question_en, question_bg, answer_en, answer_bg, sort_order, is_published)
VALUES
    ('candles', 'Are your candles handmade?', 'Ръчно изработени ли са вашите свещи?', 'Yes. Every candle is lovingly handcrafted in our atelier, making each piece truly one of a kind. Because they are made by hand, slight variations in colour, finish, or decorative details are part of their unique charm.', 'Да. Всяка свещ е изработена с любов на ръка в нашето ателие, което прави всяко изделие наистина уникално. Тъй като са изработени ръчно, леките разлики в цвета, финиша или декоративните детайли са част от техния неповторим чар.', 0, 1),
    ('candles', 'What wax do you use?', 'Какъв восък използвате?', 'We carefully select different premium wax blends depending on the candle''s design and intended performance. The exact wax type used for each candle is listed in its individual product description.', 'Внимателно подбираме различни висококачествени восъчни смеси в зависимост от дизайна и предназначението на свещта. Точният вид восък за всяка свещ е посочен в описанието на съответния продукт.', 1, 1),
    ('candles', 'What type of wick do you use?', 'Какъв вид фитил използвате?', 'We use different wick types depending on the candle''s size and design to ensure the best possible performance. The wick information for each candle can be found on its product page.', 'Използваме различни видове фитили в зависимост от размера и дизайна на свещта, за да осигурим възможно най-добро горене. Информация за фитила на всяка свещ можете да намерите на нейната продуктова страница.', 2, 1),
    ('candles', 'Where are your candles made?', 'Къде се произвеждат вашите свещи?', 'All of our candles are handcrafted in our atelier with great attention to detail and quality.', 'Всички наши свещи са изработени ръчно в нашето ателие с изключително внимание към детайла и качеството.', 3, 1),
    ('candles', 'What sizes do you offer?', 'Какви размери предлагате?', 'Our collection includes candles in a variety of sizes. Please refer to each product page for the exact dimensions and weight.', 'Нашата колекция включва свещи в различни размери. Моля, вижте всяка продуктова страница за точните размери и тегло.', 4, 1),
    ('candles', 'What makes your candles different?', 'Какво отличава вашите свещи?', 'Our candles are designed to be more than just home fragrance—they''re decorative pieces made to elevate your space. Combining handcrafted craftsmanship, luxurious fragrances, elegant designs, and premium materials, each candle is created to bring beauty and warmth into your home. Many of our products can also be customised, making them a thoughtful and unique gift.', 'Нашите свещи са замислени да бъдат нещо повече от аромат за дома — те са декоративни изделия, създадени да облагородят пространството ви. Съчетавайки ръчна изработка, изискани аромати, елегантен дизайн и първокласни материали, всяка свещ е създадена да внесе красота и топлина в дома ви. Много от нашите продукти могат да бъдат персонализирани, което ги прави обмислен и уникален подарък.', 5, 1),
    ('care', 'Are all of your candles meant to be burned?', 'Всички ваши свещи ли са предназначени за горене?', 'Not necessarily. Some of our candles are designed primarily as decorative pieces, while others are suitable for burning. Please check the product description before lighting your candle.', 'Не непременно. Някои от нашите свещи са създадени предимно като декоративни изделия, докато други са подходящи за горене. Моля, проверете описанието на продукта, преди да запалите свещта си.', 0, 1),
    ('care', 'Do I need to trim the wick before the first burn?', 'Трябва ли да подрязвам фитила преди първото горене?', 'No. Every candle arrives with the wick pre-trimmed and ready to light. If you burn your candle multiple times, trimming the wick before each subsequent burn will help maintain a cleaner flame.', 'Не. Всяка свещ пристига с предварително подрязан фитил, готова за палене. Ако горите свещта многократно, подрязването на фитила преди всяко следващо палене ще помогне за по-чист пламък.', 1, 1),
    ('care', 'How long should I burn my candle?', 'Колко дълго да горя свещта си?', 'Recommended burn times vary depending on the candle''s size and design. Please refer to the individual product description for guidance.', 'Препоръчителното време за горене варира в зависимост от размера и дизайна на свещта. Моля, вижте описанието на съответния продукт за насоки.', 2, 1),
    ('care', 'Will decorative candles drip?', 'Капят ли декоративните свещи?', 'Yes. Sculptural candles and decorative designs naturally lose their shape as they burn and may drip wax. Always place them on a heat-resistant tray or dish large enough to catch any melted wax.', 'Да. Скулптурните свещи и декоративните дизайни естествено губят формата си при горене и могат да капят восък. Винаги ги поставяйте върху топлоустойчива подложка или чиния, достатъчно голяма да събере разтопения восък.', 3, 1),
    ('care', 'How should I display decorative candles?', 'Как да излагам декоративните свещи?', 'To preserve their appearance, keep decorative candles away from direct sunlight, radiators, or other heat sources. Prolonged exposure may cause colours to fade or change over time.', 'За да запазите външния им вид, дръжте декоративните свещи далеч от пряка слънчева светлина, радиатори и други източници на топлина. Продължителното излагане може да доведе до избледняване или промяна на цветовете с времето.', 4, 1),
    ('care', 'Will my candle look exactly like the photos?', 'Ще изглежда ли свещта ми точно като на снимките?', 'We do our best to ensure every candle closely matches the product photos. Because each piece is handmade, small variations in decorative elements—such as fruit toppings or other handcrafted details—may occur. These slight differences make every candle unique while maintaining the same overall design and colour palette.', 'Правим всичко възможно всяка свещ да съответства максимално на продуктовите снимки. Тъй като всяко изделие е ръчно изработено, възможни са малки разлики в декоративните елементи — като плодови акценти или други ръчно изработени детайли. Тези леки разлики правят всяка свещ уникална, като запазват същия цялостен дизайн и цветова палитра.', 5, 1),
    ('care', 'Candle Safety', 'Безопасност при работа със свещи', '* Never leave a burning candle unattended.
* Keep candles away from children and pets.
* Always burn candles on a stable, heat-resistant surface.
* Keep away from curtains, furniture, and other flammable materials.
* Never move a candle while it is burning or while the wax is still hot.
* Extinguish the candle before it burns completely.', '* Никога не оставяйте горяща свещ без надзор.
* Дръжте свещите далеч от деца и домашни любимци.
* Винаги горете свещите върху стабилна, топлоустойчива повърхност.
* Дръжте далеч от завеси, мебели и други запалими материали.
* Никога не местете свещ, докато гори или докато восъкът е още горещ.
* Изгасете свещта, преди да изгори напълно.', 6, 1),
    ('custom', 'Can I customise my candle?', 'Мога ли да персонализирам свещта си?', 'Yes. We love bringing our customers'' ideas to life. If you have a specific design, colour palette, fragrance, or occasion in mind, we''d be delighted to discuss a custom order.', 'Да. Обичаме да претворяваме идеите на нашите клиенти. Ако имате конкретен дизайн, цветова палитра, аромат или повод предвид, с удоволствие ще обсъдим поръчка по заявка.', 0, 1),
    ('custom', 'Can I request a custom candle bouquet?', 'Мога ли да поръчам персонализиран букет от свещи?', 'Absolutely. We create personalised candle bouquets and custom colour palettes for birthdays, weddings, anniversaries, baby showers, corporate gifts, and many other special occasions.', 'Разбира се. Създаваме персонализирани букети от свещи и индивидуални цветови палитри за рождени дни, сватби, годишнини, бебешки партита, корпоративни подаръци и много други специални поводи.', 1, 1),
    ('custom', 'Can I include a gift message?', 'Мога ли да добавя подаръчно съобщение?', 'Of course. Simply leave a note with your order and send your gift message through our Contact Form. We''ll include it with your order.', 'Разбира се. Просто оставете бележка към поръчката си и изпратете подаръчното съобщение чрез нашата форма за контакт. Ще го приложим към поръчката ви.', 2, 1),
    ('custom', 'Are your candles suitable as gifts?', 'Подходящи ли са вашите свещи за подарък?', 'Yes. Every candle is beautifully presented in our custom gift-ready packaging, making it perfect for gifting without the need for additional wrapping.', 'Да. Всяка свещ е красиво представена в нашата специална подаръчна опаковка, което я прави идеална за подарък без нужда от допълнително опаковане.', 3, 1),
    ('shipping', 'How long does it take to prepare my order?', 'Колко време отнема подготовката на поръчката ми?', 'Preparation times vary depending on the product and whether it is made to order. Estimated processing times are displayed on each product page and during checkout.', 'Времето за подготовка варира в зависимост от продукта и дали е изработван по заявка. Ориентировъчните срокове за обработка са посочени на всяка продуктова страница и при плащане.', 0, 1),
    ('shipping', 'Can I change or cancel my order?', 'Мога ли да променя или отменя поръчката си?', 'If your order has not yet entered production or been dispatched, we''ll do our very best to accommodate your request. Please contact us as soon as possible.', 'Ако поръчката ви все още не е влязла в производство или не е изпратена, ще направим всичко възможно да удовлетворим молбата ви. Моля, свържете се с нас възможно най-скоро.', 1, 1),
    ('shipping', 'What should I do if my order arrives damaged?', 'Какво да направя, ако поръчката ми пристигне повредена?', 'We take great care when packaging every order, but if your item arrives damaged, please contact us as soon as possible through our Contact Form or by email. Include your order number along with clear photos of the item and its packaging so we can resolve the issue promptly.', 'Опаковаме всяка поръчка с изключително внимание, но ако изделието ви пристигне повредено, моля, свържете се с нас възможно най-скоро чрез нашата форма за контакт или по имейл. Приложете номера на поръчката си заедно с ясни снимки на изделието и опаковката, за да разрешим проблема бързо.', 2, 1),
    ('shipping', 'Do you accept returns?', 'Приемате ли връщания?', 'Uncollected or refused courier parcels are reviewed before refund timing, refund amount, or next steps are confirmed. See the [Terms & Conditions returns section](/en/terms#returns) for the full policy.', 'Непотърсените или отказани куриерски пратки се преглеждат, преди да потвърдим срок, сума за възстановяване или следваща стъпка. Вижте [раздела за връщания в Общите условия](/bg/terms#returns) за пълната политика.', 3, 1),
    ('shipping', 'How can I contact you?', 'Как мога да се свържа с вас?', 'You can contact us anytime through our Contact Form or by email. We aim to respond to all enquiries as quickly as possible.', 'Можете да се свържете с нас по всяко време чрез нашата форма за контакт или по имейл. Стремим се да отговаряме на всички запитвания възможно най-бързо.', 4, 1)
ON CONFLICT DO NOTHING;

INSERT INTO terms_page (id, meta_title_en, meta_title_bg, meta_description_en, meta_description_bg, eyebrow_en, eyebrow_bg, title_en, title_bg, subtitle_en, subtitle_bg, last_updated_en, last_updated_bg, identity_intro_en, identity_intro_bg, policy_links_title_en, policy_links_title_bg, privacy_link_en, privacy_link_bg, cookies_link_en, cookies_link_bg, nav_label_en, nav_label_bg, back_to_top_en, back_to_top_bg)
VALUES
    ('terms', 'Terms & Conditions | Atelier Marie', 'Общи условия | Ателие Мари', 'Terms and conditions for Atelier Marie orders, delivery, withdrawal, returns, custom products, faulty items, and refunds.', 'Общи условия за поръчки, доставка, отказ, връщане, персонализирани продукти, повредени артикули и възстановяване на суми от Ателие Мари.', 'Atelier Marie', 'Ателие Мари', 'Terms & Conditions', 'Общи условия', 'Please read these terms before placing an order. They explain ordering, delivery, withdrawal, returns, custom products, faulty items, and refunds.', 'Моля, прочетете тези условия преди да направите поръчка. Те обясняват поръчките, доставката, правото на отказ, връщанията, персонализираните продукти, повредените артикули и възстановяването на суми.', 'Last updated: 29 July 2026', 'Последна актуализация: 29 юли 2026 г.', 'The legal identity, address, registration, VAT/tax status, and responsible-party details are placeholders and must be reviewed before launch.', 'Юридическата идентичност, адресът, регистрацията, ДДС/данъчният статус и данните за отговорното лице са временни стойности и трябва да бъдат прегледани преди публикуване.', 'Related policies', 'Свързани политики', 'Privacy Policy', 'Политика за поверителност', 'Cookie Policy', 'Политика за бисквитки', 'Terms sections', 'Раздели в условията', 'Back to top', 'Нагоре')
ON CONFLICT DO NOTHING;

INSERT INTO terms_sections (slug, title_en, title_bg, nav_en, nav_bg, body_en, body_bg, model_form_title_en, model_form_title_bg, model_form_intro_en, model_form_intro_bg, model_form_lines_en, model_form_lines_bg, sort_order)
VALUES
    ('seller', 'Seller information', 'Информация за търговеца', 'Seller', 'Търговец', '["This website is operated by Atelier Marie. Full legal identity, geographic address, registration, and VAT/tax status are shown in the trader details on this page and must be reviewed before launch.", "For order questions, withdrawal notices, returns, damaged items, privacy requests, or other support, contact us through the Contact Form or by email at contacts@theateliermarie.com."]', '["Този уебсайт се управлява от Ателие Мари. Пълните данни за юридическа идентичност, географски адрес, регистрация и ДДС/данъчен статус са показани в данните за търговеца на тази страница и трябва да бъдат прегледани преди публикуване.", "За въпроси относно поръчки, уведомления за отказ, връщания, повредени артикули, заявки за поверителност или друго съдействие, свържете се с нас чрез формата за контакт или по имейл на contacts@theateliermarie.com."]', NULL, NULL, NULL, NULL, NULL, NULL, 0),
    ('products', 'Products and handmade variations', 'Продукти и ръчна изработка', 'Products', 'Продукти', '["Atelier Marie candles are handmade. Small variations in colour, finish, decorative details, weight, or appearance may occur and are part of the handmade character of the product.", "Product photos and descriptions are prepared carefully, but handmade items may not be identical to the exact photographed piece."]', '["Свещите на Ателие Мари са ръчно изработени. Възможни са малки разлики в цвета, финиша, декоративните детайли, теглото или външния вид, които са част от характера на ръчната изработка.", "Снимките и описанията на продуктите се подготвят внимателно, но ръчно изработените артикули може да не са напълно идентични с конкретния продукт на снимката."]', NULL, NULL, NULL, NULL, NULL, NULL, 1),
    ('orders', 'Orders and payment', 'Поръчки и плащане', 'Orders', 'Поръчки', '["When you place an order, you must provide accurate contact and delivery details so we can process and deliver it.", "Product prices are shown in the storefront currency before you place the order. VAT/tax wording must match the final owner-provided VAT status before launch.", "Available payment methods and any known delivery charges are shown during checkout before you place the order. An order may require confirmation before dispatch."]', '["Когато правите поръчка, трябва да предоставите точни данни за контакт и доставка, за да можем да я обработим и доставим.", "Цените на продуктите се показват във валутата на магазина преди изпращане на поръчката. Текстът за ДДС/данъци трябва да съответства на окончателния ДДС статус, предоставен от собственика преди публикуване.", "Наличните начини на плащане и всички известни разходи за доставка се показват при плащане преди изпращане на поръчката. Поръчката може да изисква потвърждение преди изпращане."]', NULL, NULL, NULL, NULL, NULL, NULL, 2),
    ('delivery', 'Delivery', 'Доставка', 'Delivery', 'Доставка', '["Delivery options, courier details, and any delivery charges are shown during checkout before you place the order.", "If preparation or delivery is delayed, we will contact you using the details provided with the order."]', '["Възможностите за доставка, данните за куриера и всички разходи за доставка се показват при плащане преди да изпратите поръчката.", "Ако подготовката или доставката се забави, ще се свържем с вас чрез данните, предоставени към поръчката."]', NULL, NULL, NULL, NULL, NULL, NULL, 3),
    ('returns', 'Right of withdrawal and returns', 'Право на отказ и връщане', 'Returns', 'Връщане', '["For standard products bought online, consumers have the right to withdraw from the contract within 14 days from the day they receive the goods, without giving a reason.", "To exercise the right of withdrawal, contact us by email or through the Contact Form before the 14-day period expires.", "Any clear statement that you wish to withdraw from the order is sufficient. You may use the model withdrawal form below, but it is not required.", "After you tell us that you withdraw, you generally have another 14 days to send the goods back. We will provide return instructions and the return address after receiving your message.", "For ordinary withdrawal, photos are not required and you do not need to give a reason.", "If a courier-office parcel is not collected, or a delivery is refused, we review the courier status, the order record, and any return costs before confirming refund timing, refund amount, or next steps. Courier status alone does not automatically finalize a refund, restock, or accounting decision.", "For card-paid orders, any approved refund is returned through the original card payment where possible. For payment-on-delivery orders where no card payment was collected, there may be no card refund to issue; any amounts already paid or due are reviewed separately.", "Please return items with their original packaging where possible. You may inspect the item as you would in a shop.", "You may be responsible for any loss in value caused by handling beyond what is necessary to inspect the product, including lighting, using, damaging, or over-handling a candle.", "Unless we agree otherwise or the item is faulty, damaged, or incorrect, you are responsible for the direct cost of returning goods under the right of withdrawal. Return shipping, courier return fees, or legally permitted diminished-value deductions may affect the final refund amount where applicable."]', '["За стандартни продукти, закупени онлайн, потребителите имат право да се откажат от договора в срок от 14 дни от деня, в който получат стоките, без да посочват причина.", "За да упражните правото си на отказ, свържете се с нас по имейл или чрез формата за контакт преди изтичане на 14-дневния срок.", "Достатъчно е ясно заявление, че желаете да се откажете от поръчката. Можете да използвате примерния формуляр по-долу, но това не е задължително.", "След като ни уведомите за отказа, обикновено имате още 14 дни, за да изпратите стоките обратно. Ще ви предоставим инструкции за връщане и адрес за връщане след като получим съобщението ви.", "При обикновен отказ снимки не се изискват и не е нужно да посочвате причина.", "Ако пратка до офис на куриер не бъде потърсена или доставката бъде отказана, преглеждаме куриерския статус, данните за поръчката и евентуалните разходи за връщане, преди да потвърдим срок, сума за възстановяване или следваща стъпка. Само куриерският статус не финализира автоматично възстановяване на сума, връщане на склад или счетоводно решение.", "За поръчки, платени с карта, всяко одобрено възстановяване се извършва чрез първоначалното картово плащане, когато е възможно. За поръчки с наложен платеж, при които не е събрано картово плащане, може да няма сума за възстановяване по карта; всички вече платени или дължими суми се преглеждат отделно.", "Моля, върнете артикулите с оригиналната им опаковка, когато е възможно. Можете да прегледате артикула така, както бихте го направили в магазин.", "Може да носите отговорност за намалена стойност, причинена от боравене извън необходимото за преглед на продукта, включително запалване, използване, повреждане или прекомерно боравене със свещта.", "Освен ако не се договорим друго или артикулът е дефектен, повреден или грешен, вие поемате преките разходи за връщане на стоки при упражняване на правото на отказ. Разходи за връщане, куриерски такси за връщане или законово допустими удръжки за намалена стойност могат да повлияят на крайната сума за възстановяване, когато са приложими."]', 'Model withdrawal form', 'Примерен формуляр за отказ', 'You may copy this text into an email or contact-form message:', 'Можете да копирате този текст в имейл или съобщение през формата за контакт:', '["To Atelier Marie:", "I hereby give notice that I withdraw from my contract of sale for the following goods:", "Ordered on / received on:", "Order number:", "Consumer name:", "Consumer address:", "Date:"]', '["До Ателие Мари:", "С настоящото уведомявам, че се отказвам от договора за продажба на следните стоки:", "Поръчано на / получено на:", "Номер на поръчка:", "Име на потребителя:", "Адрес на потребителя:", "Дата:"]', 4),
    ('custom-products', 'Custom and personalized products', 'Персонализирани продукти', 'Custom', 'Персонални', '["The statutory right of withdrawal does not apply, where legally permitted, to products made to your specifications or clearly personalized.", "This includes candles with custom names, messages, logos, photos, bespoke colours, fragrances, or made-to-order designs requested by you.", "This exception is used narrowly. Choosing a standard size, standard scent, or in-stock design does not by itself make a product personalized."]', '["Законовото право на отказ не се прилага, когато законът позволява това, за продукти, изработени по ваши спецификации или ясно персонализирани.", "Това включва свещи с персонални имена, съобщения, лога, снимки, индивидуални цветове, аромати или дизайни по ваша заявка.", "Това изключение се прилага ограничено. Изборът на стандартен размер, стандартен аромат или наличен дизайн сам по себе си не прави продукта персонализиран."]', NULL, NULL, NULL, NULL, NULL, NULL, 5),
    ('faulty-items', 'Faulty, damaged, or incorrect items', 'Дефектни, повредени или грешни артикули', 'Faulty items', 'Проблеми', '["The 14-day withdrawal right is separate from your statutory rights for faulty, damaged, incorrect, or non-conforming goods. Those rights remain unaffected.", "If your item arrives damaged, faulty, or incorrect, contact us as soon as possible. Please include your order number and clear photos of the item, packaging, and courier label where relevant so we can resolve the issue quickly.", "If a parcel is damaged or lost by the courier, Atelier Marie may record courier claim details and follow up with the courier. You do not need to manage the courier claim yourself, and your statutory rights remain unaffected.", "For faulty, damaged, or incorrect items, we will handle the appropriate remedy in accordance with applicable consumer law."]', '["14-дневното право на отказ е отделно от законовите ви права при дефектни, повредени, грешни или несъответстващи стоки. Тези права остават незасегнати.", "Ако артикулът пристигне повреден, дефектен или грешен, свържете се с нас възможно най-скоро. Моля, включете номера на поръчката и ясни снимки на артикула, опаковката и куриерския етикет, когато е приложимо, за да решим случая бързо.", "Ако пратка е повредена или изгубена от куриера, Ателие Мари може да запише данни за куриерска претенция и да проследи случая с куриера. Не е нужно вие да управлявате куриерската претенция, а законовите ви права остават незасегнати.", "При дефектни, повредени или грешни артикули ще предложим подходящо решение съгласно приложимото потребителско законодателство."]', NULL, NULL, NULL, NULL, NULL, NULL, 6),
    ('refunds', 'Refunds', 'Възстановяване на суми', 'Refunds', 'Суми', '["For valid withdrawal, we will reimburse payments due to you within the required legal deadline. For goods, we may wait until we receive the goods back or you provide evidence that you sent them back, whichever happens first.", "Where required, the refund includes the product price and the least expensive standard delivery option offered for the original order. Extra delivery upgrades, such as express delivery chosen by you, may not be refundable beyond the standard delivery cost.", "For uncollected, refused, or returned parcels, refund timing and amount may depend on review of the returned parcel, courier return costs, payment method, and any legally permitted deductions. We do not treat a courier return status as an automatic full refund.", "Refunds are made using the original payment method where possible. For cash-on-delivery or bank-transfer orders, refunds may be made by bank transfer."]', '["При валиден отказ ще възстановим дължимите суми в законовия срок. За стоки можем да изчакаме, докато получим стоките обратно или докато предоставите доказателство, че сте ги изпратили обратно, което настъпи по-рано.", "Когато е приложимо, възстановяването включва цената на продукта и най-евтината стандартна доставка, предложена за първоначалната поръчка. Допълнителни доставки, избрани от вас, като експресна доставка, може да не бъдат възстановени над стойността на стандартната доставка.", "При непотърсени, отказани или върнати пратки срокът и сумата за възстановяване могат да зависят от преглед на върнатата пратка, куриерските разходи за връщане, начина на плащане и всички законово допустими удръжки. Не третираме куриерски статус за връщане като автоматично пълно възстановяване.", "Възстановяването се извършва чрез първоначалния начин на плащане, когато е възможно. За поръчки с наложен платеж или банков превод възстановяването може да бъде направено по банков път."]', NULL, NULL, NULL, NULL, NULL, NULL, 7),
    ('contact', 'Contact', 'Контакт', 'Contact', 'Контакт', '["For questions about these terms, your order, withdrawal, returns, damaged items, or refunds, contact us through the Contact Form or by email at contacts@theateliermarie.com."]', '["За въпроси относно тези условия, вашата поръчка, отказ, връщания, повредени артикули или възстановяване на суми, свържете се с нас чрез формата за контакт или по имейл на contacts@theateliermarie.com."]', NULL, NULL, NULL, NULL, NULL, NULL, 8)
ON CONFLICT DO NOTHING;

INSERT INTO privacy_page (id, meta_title_en, meta_title_bg, meta_description_en, meta_description_bg, eyebrow_en, eyebrow_bg, title_en, title_bg, subtitle_en, subtitle_bg, last_updated_en, last_updated_bg, controller_title_en, controller_title_bg)
VALUES
    ('privacy', 'Privacy Policy | Atelier Marie', 'Политика за поверителност | Ателие Мари', 'How Atelier Marie processes order, delivery, contact, account, comment, payment, cookie, and email data.', 'Как Ателие Мари обработва данни за поръчки, доставка, контакт, профил, коментари, плащания, бисквитки и имейли.', 'Legal information', 'Правна информация', 'Privacy Policy', 'Политика за поверителност', 'This policy explains how we use personal data when you browse the store, contact us, create an account, comment, or place an order.', 'Тази политика обяснява как използваме лични данни, когато разглеждате магазина, пишете ни, създавате профил, коментирате или правите поръчка.', 'Last updated: 29 July 2026', 'Последна актуализация: 29 юли 2026 г.', 'Controller details', 'Данни за администратора')
ON CONFLICT DO NOTHING;

INSERT INTO privacy_sections (slug, title_en, title_bg, nav_en, nav_bg, body_en, body_bg, sort_order)
VALUES
    ('data', 'Personal data we process', 'Лични данни, които обработваме', 'Data', 'Данни', '["We process the details you provide when using the store: name, email address, delivery information, phone number for courier delivery, order notes, contact-form messages, and product comments or reactions.", "If you sign in with Google, we receive the account identifiers needed to create and secure your account, such as your email, name, Google ID, and avatar URL when provided by Google.", "For payments, we store order and payment status references. Card payment details are handled by Stripe and are not stored by Atelier Marie. Cash-on-delivery and bank-transfer orders store only the payment method and order status needed to process the order.", "The app also stores session, authentication, locale, cart, order, email-delivery, suppression, security, and technical log data needed to run the service."]', '["Обработваме данните, които предоставяте при използване на магазина: име, имейл адрес, данни за доставка, телефон за куриера, бележки към поръчка, съобщения през формата за контакт и коментари или реакции към продукти.", "Ако влезете с Google, получаваме данните, нужни за създаване и защита на профила ви, като имейл, име, Google ID и аватар, когато Google ги предостави.", "При плащания съхраняваме данни за поръчката и статуса на плащане. Данните за картово плащане се обработват от Stripe и не се съхраняват от Ателие Мари. При наложен платеж и банков превод съхраняваме само начина на плащане и статуса, нужни за обработка на поръчката.", "Приложението съхранява и данни за сесии, удостоверяване, език, кошница, поръчки, доставка на имейли, списъци за потискане, сигурност и технически логове, нужни за работата на услугата."]', 0),
    ('purposes', 'Why we use the data', 'Защо използваме данните', 'Purposes', 'Цели', '["We use order, cart, delivery, and payment data to take steps before entering into a contract, perform the sales contract, arrange delivery, provide order support, and keep purchase records.", "We use contact-form messages and replies to handle your inquiry and any custom-order request. We use account/session data to authenticate you and protect the service.", "With your consent, we use first-party analytics events to understand product discovery, cart, checkout, delivery, payment handoff, and purchase confirmation. Analytics events are stored on the Atelier Marie backend and are not sent to a third-party analytics provider. They are linked to the existing session cookie as a pseudonymous session key and do not include email, phone, name, address, order notes, card data, advertising pixels, session replay, heatmaps, cross-site tracking, or profiling.", "We use comments and reactions to provide public product feedback features. We use operational logs, fraud-prevention data, and email delivery records for legitimate interests in security, reliability, and customer support.", "Where the law requires records to be kept, we process the relevant data to comply with legal obligations."]', '["Използваме данни за поръчки, кошница, доставка и плащане, за да предприемем стъпки преди договор, да изпълним договора за продажба, да организираме доставка, да предоставим съдействие и да пазим търговски записи.", "Използваме съобщенията от формата за контакт, за да отговорим на запитване или заявка за персонална поръчка. Използваме данни за профил и сесия за удостоверяване и защита на услугата.", "С Ваше съгласие използваме първостранни аналитични събития, за да разбираме откриване на продукти, кошница, плащане, доставка, пренасочване към плащане и потвърдена покупка. Аналитичните събития се съхраняват в backend системата на Ателие Мари и не се изпращат към външен доставчик на аналитика. Те се свързват със съществуващата сесийна бисквитка като псевдонимен ключ и не включват имейл, телефон, име, адрес, бележки към поръчка, картови данни, рекламни пиксели, запис на сесии, heatmap-и, проследяване между сайтове или профилиране.", "Използваме коментари и реакции, за да предоставим публични функции за обратна връзка за продукти. Използваме логове, данни за предотвратяване на злоупотреби и записи за доставка на имейли за легитимни интереси, свързани със сигурност, надеждност и обслужване.", "Когато законът изисква съхранение на записи, обработваме съответните данни за изпълнение на законови задължения."]', 1),
    ('recipients', 'Recipients and processors', 'Получатели и обработващи', 'Recipients', 'Получатели', '["We share data only where needed for the current store features: hosting and infrastructure providers, email delivery providers, Google OAuth when you choose Google sign-in, Stripe for card-payment processing references, and courier/order-fulfilment partners where delivery is required.", "Optional first-party analytics stays on the Atelier Marie backend and is not sent to a third-party analytics provider. We do not use advertising pixels, cross-site tracking, session replay, heatmaps, newsletter marketing tracking, or profiling."]', '["Споделяме данни само когато е нужно за текущите функции на магазина: хостинг и инфраструктура, доставчици на имейл услуги, Google OAuth при вход с Google, Stripe за картови плащания, както и куриери или партньори за изпълнение на поръчки, когато е необходима доставка.", "Незадължителната първостранна аналитика остава в backend системата на Ателие Мари и не се изпраща към външен доставчик на аналитика. Не използваме рекламни пиксели, проследяване между сайтове, запис на сесии, heatmap-и, маркетингово проследяване за бюлетин или профилиране."]', 2),
    ('retention', 'Retention', 'Срокове за съхранение', 'Retention', 'Срокове', '["Order and accounting records are kept for the period required by applicable law and for handling customer support, returns, withdrawal, and warranty questions.", "First-party analytics events are retained for the configured analytics retention period, currently up to 395 days, unless consent is withdrawn for future events or a valid erasure request requires deletion or irreversible pseudonymization sooner.", "Contact messages, email delivery audit rows, suppression records, sessions, carts, comments, and technical logs are kept only as long as needed for the feature, security, support, or legal reason that created them. The executable deletion and erasure workflow is tracked separately from this policy baseline."]', '["Записите за поръчки и счетоводство се пазят за срока, изискван от приложимото право, както и за обработка на въпроси за обслужване, връщане, отказ и гаранция.", "Първостранните аналитични събития се пазят за конфигурирания срок за аналитика, в момента до 395 дни, освен ако съгласието бъде оттеглено за бъдещи събития или валидна заявка за изтриване изисква по-ранно изтриване или необратима псевдонимизация.", "Съобщенията за контакт, записите за доставка на имейли, данните за потискане, сесиите, кошниците, коментарите и техническите логове се пазят само докато са нужни за функцията, сигурността, обслужването или законовата причина, поради която са създадени. Изпълнимият процес за изтриване и заличаване се проследява отделно от тази базова политика."]', 3),
    ('rights', 'Your rights', 'Вашите права', 'Rights', 'Права', '["Depending on the situation, you may have rights to access, correct, erase, restrict, object to processing, and receive a copy of your personal data. You may also complain to a data protection authority.", "To exercise privacy rights, contact us using the privacy contact email shown on this page. We may need to verify your identity before acting on a request."]', '["В зависимост от случая може да имате право на достъп, корекция, изтриване, ограничаване, възражение срещу обработване и получаване на копие от личните си данни. Може също да подадете жалба до орган за защита на данните.", "За да упражните права, свържете се с нас на имейла за поверителност, посочен на тази страница. Може да е нужно да потвърдим самоличността ви преди изпълнение на заявката."]', 4),
    ('cookies', 'Cookies and similar storage', 'Бисквитки и подобно съхранение', 'Cookies', 'Бисквитки', '["The store uses necessary session/authentication cookies, a locale preference cookie, and a first-party consent preference cookie. See the Cookie Policy for the current cookie inventory and retention notes.", "Optional first-party analytics runs only after consent. You can withdraw analytics consent from Cookie settings; future behavioral analytics events stop and unsent events are discarded."]', '["Магазинът използва необходими бисквитки за сесия/удостоверяване, бисквитка за предпочитан език и първостранна бисквитка за предпочитание за съгласие. Вижте Политиката за бисквитки за текущия списък и бележки за сроковете.", "Незадължителната първостранна аналитика работи само след съгласие. Можете да оттеглите съгласието от настройките за бисквитки; бъдещите поведенчески събития спират и неизпратените събития се изчистват."]', 5),
    ('contact', 'Privacy contact', 'Контакт за поверителност', 'Contact', 'Контакт', '["For privacy requests or questions, contact Atelier Marie at the email address shown in the controller details above. You can also use the Contact page for ordinary order or product questions."]', '["За заявки или въпроси относно поверителността се свържете с Ателие Мари на имейла, показан в данните за администратора по-горе. За обикновени въпроси за поръчки или продукти можете да използвате и страницата Контакт."]', 6)
ON CONFLICT DO NOTHING;

INSERT INTO cookies_page (id, meta_title_en, meta_title_bg, meta_description_en, meta_description_bg, eyebrow_en, eyebrow_bg, title_en, title_bg, subtitle_en, subtitle_bg, last_updated_en, last_updated_bg, inventory_title_en, inventory_title_bg, header_name_en, header_name_bg, header_purpose_en, header_purpose_bg, header_type_en, header_type_bg, header_duration_en, header_duration_bg)
VALUES
    ('cookies', 'Cookie Policy | Atelier Marie', 'Политика за бисквитки | Ателие Мари', 'Current cookie inventory for Atelier Marie session, authentication, and locale cookies.', 'Текущ списък с бисквитки на Ателие Мари за сесия, удостоверяване и език.', 'Legal information', 'Правна информация', 'Cookie Policy', 'Политика за бисквитки', 'This policy lists the cookies and similar storage currently used by the store.', 'Тази политика описва бисквитките и подобното съхранение, които магазинът използва в момента.', 'Last updated: 29 July 2026', 'Последна актуализация: 29 юли 2026 г.', 'Current cookie inventory', 'Текущ списък с бисквитки', 'Name', 'Име', 'Purpose', 'Цел', 'Type', 'Тип', 'Duration', 'Срок')
ON CONFLICT DO NOTHING;

INSERT INTO cookies_inventory (name, purpose_en, purpose_bg, type_en, type_bg, duration_en, duration_bg, source, first_seen_at, observed_on, is_active, auto_detected, sort_order)
VALUES
    ('session_id', 'Keeps the visitor session, cart, locale preference, and checkout flow associated with the same browser.', 'Запазва сесията на посетителя, кошницата, езиковото предпочитание и процеса на плащане в един и същ браузър.', 'Necessary session cookie', 'Необходима сесийна бисквитка', 'Up to the configured session lifetime or until cleared by the browser.', 'До конфигурирания срок на сесията или докато бъде изтрита от браузъра.', 'seed', NULL, NULL, 1, 0, 0),
    ('atelier_auth', 'Keeps a signed-in account authenticated after Google OAuth login.', 'Поддържа профила вписан след вход чрез Google OAuth.', 'Necessary authentication cookie', 'Необходима бисквитка за удостоверяване', 'Up to the configured authentication lifetime or until sign-out/expiry.', 'До конфигурирания срок за удостоверяване или до изход/изтичане.', 'seed', NULL, NULL, 1, 0, 1),
    ('NEXT_LOCALE', 'Stores the selected language so localized pages open in the chosen locale.', 'Запазва избрания език, за да се отварят страниците в предпочитания език.', 'Preference cookie', 'Бисквитка за предпочитание', 'Persistent preference cookie unless cleared by the browser.', 'Постоянна бисквитка за предпочитание, освен ако бъде изтрита от браузъра.', 'seed', NULL, NULL, 1, 0, 2),
    ('atelier_cookie_consent', 'Stores the current cookie preference, consent version, analytics choice, locale, and timestamp. It does not contain a tracking ID.', 'Запазва текущото предпочитание за бисквитки, версията на съгласието, избора за аналитика, езика и времето на избора. Не съдържа проследяващ идентификатор.', 'Consent preference cookie', 'Бисквитка за предпочитание за съгласие', 'Up to 12 months or until changed or cleared by the browser.', 'До 12 месеца или докато бъде променена или изтрита от браузъра.', 'seed', NULL, NULL, 1, 0, 3)
ON CONFLICT DO NOTHING;

INSERT INTO cookies_sections (slug, title_en, title_bg, body_en, body_bg, sort_order)
VALUES
    ('necessary', 'Necessary and preference cookies', 'Необходими бисквитки и предпочитания', '["The current store uses cookies needed to provide the cart, checkout, account session, language selection, security, and basic site operation.", "Without the necessary session and authentication cookies, core features such as cart continuity, checkout, and account sign-in may not work correctly."]', '["Текущият магазин използва бисквитки, нужни за кошницата, плащането, профилната сесия, избора на език, сигурността и основната работа на сайта.", "Без необходимите бисквитки за сесия и удостоверяване основни функции като кошница, плащане и вход в профил може да не работят правилно."]', 0),
    ('analytics', 'Optional first-party analytics', 'Незадължителна първостранна аналитика', '["If you accept analytics, the store sends minimal first-party events such as product view, filter use, add to cart, cart open, checkout start, delivery selection, order submission, payment redirect, and purchase confirmation.", "Analytics events stay on the Atelier Marie backend and are not sent to a third-party analytics provider. They are linked to the existing session cookie as a pseudonymous session key. They do not include email, phone, name, address, order notes, card details, advertising pixels, cross-site tracking, session replay, heatmaps, or profiling. Owner/legal review is required before production analytics is enabled."]', '["Ако приемете аналитика, магазинът изпраща минимални първостранни събития като преглед на продукт, използване на филтър, добавяне в кошница, отваряне на кошница, начало на плащане, избор на доставка, изпращане на поръчка, пренасочване към плащане и потвърдена покупка.", "Аналитичните събития остават в backend системата на Ателие Мари и не се изпращат към външен доставчик на аналитика. Те се свързват със съществуващата сесийна бисквитка като псевдонимен ключ. Те не включват имейл, телефон, име, адрес, бележки към поръчка, картови данни, рекламни пиксели, проследяване между сайтове, запис на сесии, heatmap-и или профилиране. Необходим е преглед от собственик/юрист преди активиране на аналитиката в продукция."]', 1),
    ('control', 'How to control cookies', 'Как да управлявате бисквитките', '["You can change analytics consent from Cookie settings or block/delete cookies through your browser settings. Blocking necessary cookies may break sign-in, cart, checkout, or locale features.", "For privacy questions, use the contact details in the Privacy Policy."]', '["Можете да промените съгласието за аналитика от настройките за бисквитки или да блокирате/изтриете бисквитки през настройките на браузъра. Блокирането на необходимите бисквитки може да наруши входа, кошницата, плащането или езиковите функции.", "За въпроси относно поверителността използвайте данните за контакт в Политиката за поверителност."]', 2)
ON CONFLICT DO NOTHING;

INSERT INTO site_banners (id, message_en, message_bg, link_label_en, link_label_bg, link_url, is_enabled, starts_at, ends_at, version)
VALUES
    ('default', 'Free shipping on orders over €50 ✨', 'Безплатна доставка за поръчки над 50€ ✨', NULL, NULL, NULL, 1, NULL, NULL, 1)
ON CONFLICT DO NOTHING;

INSERT INTO delivery_settings (id, speedy_office_enabled, speedy_door_enabled, econt_office_enabled, econt_door_enabled, cod_enabled, card_enabled, bank_transfer_enabled)
VALUES
    ('default', 1, 1, 1, 1, 1, 1, 1)
ON CONFLICT DO NOTHING;

INSERT INTO econt_settings (id, enabled, environment, shop_id, credential_source, sender_delivery_mode, sender_office_code, sender_city, sender_post_code, sender_address, sender_quarter, sender_street, sender_num, sender_other, default_pack_count, shipment_description, declared_value_enabled, default_payment_side, return_parcel_destination, days_until_return, return_parcel_payment_side, reject_action, reject_payment_side, reject_return_payment_side, courier_currency, currency_conversion_rate, office_locator_enabled, auto_confirm_on_label, auto_delivered_on_trace, last_health_status, last_health_checked_at, last_health_error)
VALUES
    ('default', 0, 'demo', NULL, 'env', 'office', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 1, 'Atelier Marie order', 0, 'receiver', 'sender', 7, 'sender', 'return_to_sender', 'sender', 'sender', 'EUR', NULL, 0, 0, 0, NULL, NULL, NULL)
ON CONFLICT DO NOTHING;

INSERT INTO inventory_settings (id, ledger_mode, valuation_enabled, valuation_method, effective_date, cogs_date_basis, rounding_policy, missing_cost_behavior, included_cost_components_json, write_off_mapping_json, currency, settings_version, accountant_reviewed, reviewed_by_admin_id, reviewed_by_name, reviewed_at, review_notes)
VALUES
    ('default', 'setup', 0, 'weighted_average', '2026-08-02', 'order_date', 'half_up_2dp', 'block_official', NULL, NULL, 'EUR', 1, 0, NULL, NULL, NULL, NULL)
ON CONFLICT DO NOTHING;

INSERT INTO about_sections (slug, type, heading_en, heading_bg, subheading_en, subheading_bg, body_en, body_bg, cta_label_en, cta_label_bg, cta_href, image_id, sort_order, is_published)
VALUES
    ('hero', 'hero', 'The Atelier Marie', 'The Atelier Marie', 'Handcrafted Elegance for Beautiful Spaces', 'Ръчно изработена елегантност за красиви пространства', 'At The Atelier Marie, we create handcrafted candles designed to bring beauty, warmth, and a touch of luxury into your home.

Inspired by the elegance of decorative objects, each creation is thoughtfully designed and carefully made in our atelier. From delicate floral arrangements to sculptural designs and personalised pieces, every candle reflects a passion for artistry, detail, and timeless aesthetics.

More than a candle, each creation is a small piece of décor — made to enhance your space, celebrate meaningful moments, and become part of the memories you cherish.', 'В The Atelier Marie създаваме ръчно изработени свещи, замислени да внесат красота, топлина и лек досег на лукс във вашия дом.

Вдъхновено от елегантността на декоративните предмети, всяко творение е обмислено с внимание и изработено грижливо в нашето ателие. От нежни флорални аранжировки до скулптурни форми и персонализирани изделия — всяка свещ отразява страст към майсторството, детайла и вечната естетика.

Повече от свещ, всяко творение е малко парче декор — създадено да разкраси вашето пространство, да отбележи значими мигове и да стане част от спомените, които пазите.', 'Explore our collection', 'Разгледайте нашата колекция', '/products', NULL, 0, 1),
    ('story', 'text_image', 'Our Story', 'Нашата история', 'From a Creative Idea to a Handmade Atelier', 'От творческа идея до ръчно ателие', 'The Atelier Marie began with a simple thought: *"I want something this beautiful in my own home."*

Inspired by the beauty of decorative candles, the journey started with creating pieces purely out of curiosity and a desire to bring something unique into everyday spaces.

What began as a creative hobby slowly became a passion for designing, experimenting, and creating beautiful objects by hand. Each candle became an opportunity to explore shapes, colours, textures, and fragrances while creating something truly special.

Over time, this passion grew into The Atelier Marie — a place where creativity, craftsmanship, and elegance come together to create candles designed to be enjoyed, admired, and remembered.', 'The Atelier Marie започна с една проста мисъл: *„Искам нещо толкова красиво в собствения си дом.“*

Вдъхновено от красотата на декоративните свещи, пътуването започна със създаването на изделия единствено от любопитство и от желание да внесем нещо уникално в ежедневните пространства.

Това, което започна като творческо хоби, постепенно се превърна в страст към проектирането, експериментирането и създаването на красиви предмети на ръка. Всяка свещ се превръщаше във възможност да изследваме форми, цветове, текстури и аромати, докато създаваме нещо наистина специално.

С времето тази страст прерасна в The Atelier Marie — място, където творчеството, майсторството и елегантността се срещат, за да създадат свещи, замислени да бъдат изживени, ценени и помнени.', NULL, NULL, NULL, NULL, 1, 1),
    ('philosophy', 'text_band', 'Our Philosophy', 'Нашата философия', 'Candles Designed to Be Admired', 'Свещи, създадени, за да им се възхищавате', 'We believe candles can be more than a source of light or fragrance.

They can become decorative pieces that add character, warmth, and beauty to a space. They can transform a room, create an atmosphere, and become part of meaningful moments.

At The Atelier Marie, every creation is designed with the intention of bringing together artistic expression, luxurious fragrance, and thoughtful craftsmanship.

Some pieces are created to be enjoyed through their scent and flame, while others are designed purely as decorative objects to be admired as part of your home.

Every candle is made to bring a little more beauty into everyday life.', 'Вярваме, че свещите могат да бъдат повече от източник на светлина или аромат.

Те могат да се превърнат в декоративни предмети, които придават характер, топлина и красота на пространството. Могат да преобразят стаята, да създадат атмосфера и да станат част от значими мигове.

В The Atelier Marie всяко творение е замислено с намерението да обедини артистичен изказ, луксозен аромат и премислено майсторство.

Някои изделия са създадени, за да бъдат изживени чрез своя аромат и пламък, а други са замислени единствено като декоративни предмети, на които да се възхищавате като част от вашия дом.

Всяка свещ е направена, за да внесе малко повече красота в ежедневието.', NULL, NULL, NULL, NULL, 2, 1),
    ('differentiators', 'cards', 'What Makes Our Candles Different', 'Какво отличава нашите свещи', 'More Than a Candle — A Piece of Art for Your Home', 'Повече от свещ — произведение на изкуството за вашия дом', NULL, NULL, NULL, NULL, NULL, NULL, 3, 1),
    ('process', 'timeline', 'The Art of Making', 'Изкуството на създаването', 'Crafted Slowly, Made With Care', 'Изработени бавно, създадени с грижа', 'Every creation begins with an idea.

Before a candle reaches your home, it goes through a careful process of design and craftsmanship. Shapes are considered, moulds are prepared, colours are carefully selected, and every decorative element is thoughtfully arranged.

Each piece is handcrafted through multiple stages, including pouring, shaping, adding details by hand, and allowing the candle time to properly set and develop its final appearance.

Some candles are created in small batches, while others are individually made as unique pieces.

Because every detail is created with patience and care, the process often takes several days. This allows us to focus on quality, beauty, and the small details that make each candle special.

Behind every candle is time, creativity, and a love for handmade design.', 'Всяко творение започва с идея.

Преди една свещ да стигне до вашия дом, тя преминава през внимателен процес на проектиране и изработка. Обмислят се формите, подготвят се калъпите, грижливо се подбират цветовете и всеки декоративен елемент се подрежда с внимание.

Всяко изделие се изработва на ръка през множество етапи — включително отливане, оформяне, добавяне на детайли на ръка и оставяне на свещта да се стегне правилно и да придобие своя завършен вид.

Някои свещи се създават в малки серии, а други се изработват индивидуално като уникални изделия.

Тъй като всеки детайл се създава с търпение и грижа, процесът често отнема няколко дни. Това ни позволява да се съсредоточим върху качеството, красотата и малките детайли, които правят всяка свещ специална.

Зад всяка свещ стоят време, творчество и любов към ръчния дизайн.', NULL, NULL, NULL, NULL, 4, 1),
    ('atelier', 'text_image', 'Inside Our Atelier', 'Вътре в нашето ателие', 'Where Every Candle Comes to Life', 'Където всяка свещ оживява', 'Behind every creation are countless small details.

Inside our atelier, each candle is carefully brought to life by hand. From preparing materials and creating unique designs to adding decorative elements and finishing every piece, each stage receives individual attention.

Our hands are involved in every step of the process, allowing us to create candles that feel personal, distinctive, and unlike mass-produced alternatives.

Through small-batch creations and individually made pieces, The Atelier Marie celebrates the beauty of craftsmanship and the charm of handmade design.

Every candle carries a little part of the process that created it.', 'Зад всяко творение стоят безброй малки детайли.

В нашето ателие всяка свещ се създава грижливо на ръка. От подготовката на материалите и създаването на уникални дизайни до добавянето на декоративни елементи и завършването на всяко изделие — всеки етап получава индивидуално внимание.

Нашите ръце участват във всяка стъпка от процеса, което ни позволява да създаваме свещи, които усещате като лични, отличителни и различни от масово произвежданите алтернативи.

Чрез творения в малки серии и индивидуално изработени изделия, The Atelier Marie възхвалява красотата на майсторството и очарованието на ръчния дизайн.

Всяка свещ носи малка част от процеса, който я е създал.', NULL, NULL, NULL, NULL, 5, 1),
    ('values', 'cards', 'Our Values', 'Нашите ценности', 'The Principles Behind Every Creation', 'Принципите зад всяко творение', NULL, NULL, NULL, NULL, NULL, NULL, 6, 1),
    ('collections', 'collections', 'Our Collections', 'Нашите колекции', 'Designed to Suit Every Space and Story', 'Създадени да подхождат на всяко пространство и история', NULL, NULL, NULL, NULL, NULL, NULL, 7, 1),
    ('emotional', 'text_band', 'A Little Beauty for Everyday Moments', 'Малко красота за ежедневните мигове', 'Designed to Become Part of Your Story', 'Създадени да станат част от вашата история', 'We believe the most beautiful objects are the ones that create a feeling.

A candle can transform a room, add warmth to your home, and become part of the moments you want to remember.

Whether chosen as a statement piece for your own space or as a meaningful gift for someone special, every creation from The Atelier Marie is designed to bring elegance, beauty, and emotion into everyday life.

From the first idea to the final detail, each candle is made with care so it can become more than decoration — it can become a small reminder of a beautiful moment.', 'Вярваме, че най-красивите предмети са тези, които създават усещане.

Една свещ може да преобрази стаята, да добави топлина към вашия дом и да стане част от миговете, които искате да запомните.

Независимо дали е избрана като акцентно изделие за собственото ви пространство, или като значим подарък за някого специален — всяко творение от The Atelier Marie е замислено да внесе елегантност, красота и емоция в ежедневието.

От първата идея до последния детайл, всяка свещ е изработена с грижа, за да може да стане повече от декорация — да се превърне в малко напомняне за един красив миг.', 'Discover the collection', 'Открийте колекцията', '/products', NULL, 8, 1),
    ('custom_cta', 'cta_band', 'Looking for Something Unique?', 'Търсите нещо уникално?', NULL, NULL, 'Create a personalised candle designed especially for you — a bespoke piece for a meaningful moment, or a truly one-of-a-kind gift.', 'Създайте персонализирана свещ, замислена специално за вас — изделие по поръчка за значим миг или наистина уникален подарък.', 'Request a Custom Order', 'Заявете индивидуална поръчка', '/contact', NULL, 9, 1)
ON CONFLICT DO NOTHING;

INSERT INTO about_items (section, title_en, title_bg, text_en, text_bg, image_id, link_href, sort_order, is_published)
VALUES
    ('differentiators', 'Handcrafted With Attention to Detail', 'Ръчна изработка с внимание към детайла', 'Every candle is individually created in our atelier. From the first design idea to the final finishing touches, every element is carefully considered.', 'Всяка свещ се създава индивидуално в нашето ателие. От първата идея за дизайна до последните завършващи щрихи — всеки елемент е обмислен внимателно.', NULL, NULL, 0, 1),
    ('differentiators', 'Designed as Home Décor', 'Замислени като декор за дома', 'Our candles are created to complement beautiful interiors and become part of your space. Whether displayed as a statement piece or enjoyed as a sensory experience, each design is made to bring elegance and personality into your home.', 'Нашите свещи са създадени да допълват красивите интериори и да станат част от вашето пространство. Независимо дали като акцентен детайл, или като сетивно изживяване, всеки дизайн внася елегантност и характер във вашия дом.', NULL, NULL, 1, 1),
    ('differentiators', 'A Luxury Fragrance Experience', 'Луксозно ароматно изживяване', 'Beautiful design deserves a beautiful scent. Our fragrances are carefully selected to create a warm and memorable atmosphere, turning everyday moments into something special.', 'Красивият дизайн заслужава красив аромат. Нашите аромати са внимателно подбрани, за да създадат топла и запомняща се атмосфера, превръщайки ежедневните мигове в нещо специално.', NULL, NULL, 2, 1),
    ('differentiators', 'Personalised Creations', 'Персонализирани творения', 'Some moments deserve something truly unique. We offer personalised designs, candle bouquets, and colour combinations for those looking for a meaningful piece created especially for them.', 'Някои мигове заслужават нещо наистина уникално. Предлагаме персонализирани дизайни, букети от свещи и цветови комбинации за тези, които търсят значимо изделие, създадено специално за тях.', NULL, NULL, 3, 1),
    ('process', 'Design', 'Дизайн', 'Every creation begins with an idea, a shape, and a vision.', 'Всяко творение започва с идея, форма и визия.', NULL, NULL, 0, 1),
    ('process', 'Moulds', 'Калъпи', 'Each shape is carefully prepared so the candle can take its intended form.', 'Всяка форма се подготвя грижливо, за да може свещта да приеме замисления си вид.', NULL, NULL, 1, 1),
    ('process', 'Colours', 'Цветове', 'Shades are selected and blended by hand to achieve the perfect tone.', 'Нюансите се подбират и смесват на ръка, за да се постигне съвършеният тон.', NULL, NULL, 2, 1),
    ('process', 'Handmade Details', 'Ръчни детайли', 'Every decorative element is carefully placed by hand.', 'Всеки декоративен елемент се поставя внимателно на ръка.', NULL, NULL, 3, 1),
    ('process', 'Setting', 'Стягане', 'Each candle is given time to set properly and develop its final appearance.', 'На всяка свещ се дава време да се стегне правилно и да придобие завършения си вид.', NULL, NULL, 4, 1),
    ('process', 'Finishing & Packaging', 'Завършек и опаковане', 'Each candle receives time and attention before leaving the atelier.', 'Всяка свещ получава време и внимание, преди да напусне ателието.', NULL, NULL, 5, 1),
    ('values', 'Craftsmanship', 'Майсторство', 'True beauty comes from attention to detail. We believe every element matters, from the overall design to the smallest finishing touch.', 'Истинската красота идва от вниманието към детайла. Вярваме, че всеки елемент има значение — от цялостния дизайн до най-малкия завършващ щрих.', NULL, NULL, 0, 1),
    ('values', 'Elegance', 'Елегантност', 'Our creations are inspired by timeless aesthetics, designed to complement your home and bring a refined sense of beauty to your surroundings.', 'Нашите творения са вдъхновени от вечната естетика, замислени да допълват вашия дом и да внесат изтънчено усещане за красота в заобикалящата ви среда.', NULL, NULL, 1, 1),
    ('values', 'Emotion', 'Емоция', 'The most meaningful objects are those connected to memories. Whether chosen for yourself or gifted to someone special, our candles are created to celebrate moments worth remembering.', 'Най-значимите предмети са тези, свързани със спомени. Независимо дали са избрани за вас, или подарени на някого специален, нашите свещи са създадени да отбележат мигове, които си заслужава да бъдат помнени.', NULL, NULL, 2, 1),
    ('values', 'Personal Touch', 'Личен досег', 'Every home and every occasion is unique. Through personalised creations, we aim to create pieces that feel truly yours.', 'Всеки дом и всеки повод са уникални. Чрез персонализирани творения се стремим да създаваме изделия, които усещате като истински ваши.', NULL, NULL, 3, 1),
    ('collections', 'Floral Collection', 'Флорална колекция', 'Romantic designs inspired by nature.', 'Романтични дизайни, вдъхновени от природата.', NULL, '/products?category=floral', 0, 1),
    ('collections', 'Sculptural Collection', 'Скулптурна колекция', 'Statement pieces designed to decorate your space.', 'Акцентни изделия, създадени да украсят вашето пространство.', NULL, '/products?category=sculptural', 1, 1),
    ('collections', 'Bespoke Collection', 'Колекция по поръчка', 'Custom creations made for meaningful moments.', 'Творения по поръчка за значими мигове.', NULL, '/products?category=bespoke', 2, 1)
ON CONFLICT DO NOTHING;

-- Keep identity sequences above seeded ids.

SELECT setval(pg_get_serial_sequence('faq_items', 'id'), COALESCE((SELECT MAX(id) FROM faq_items), 1));

SELECT setval(pg_get_serial_sequence('about_items', 'id'), COALESCE((SELECT MAX(id) FROM about_items), 1));
        """
    )
    # END generated schema completion


def downgrade() -> None:
    """Downgrade schema."""

    op.execute(
        """
        -- BEGIN generated downgrade drops
        DROP TABLE IF EXISTS cogs_ledger CASCADE;
        DROP TABLE IF EXISTS stock_count_lines CASCADE;
        DROP TABLE IF EXISTS production_batch_outputs CASCADE;
        DROP TABLE IF EXISTS production_batch_consumption CASCADE;
        DROP TABLE IF EXISTS inventory_valuation_layers CASCADE;
        DROP TABLE IF EXISTS product_inventory_profiles CASCADE;
        DROP TABLE IF EXISTS inventory_movements CASCADE;
        DROP TABLE IF EXISTS production_batches CASCADE;
        DROP TABLE IF EXISTS material_lots CASCADE;
        DROP TABLE IF EXISTS recipe_cost_snapshots CASCADE;
        DROP TABLE IF EXISTS recipe_components CASCADE;
        DROP TABLE IF EXISTS promotion_campaign_products CASCADE;
        DROP TABLE IF EXISTS product_cost_components CASCADE;
        DROP TABLE IF EXISTS order_return_events CASCADE;
        DROP TABLE IF EXISTS material_receipts CASCADE;
        DROP TABLE IF EXISTS inventory_adjustments CASCADE;
        DROP TABLE IF EXISTS accounting_documents CASCADE;
        DROP TABLE IF EXISTS about_items CASCADE;
        DROP TABLE IF EXISTS suppressed_emails CASCADE;
        DROP TABLE IF EXISTS stripe_events CASCADE;
        DROP TABLE IF EXISTS stripe_balance_transactions CASCADE;
        DROP TABLE IF EXISTS stock_counts CASCADE;
        DROP TABLE IF EXISTS site_settings CASCADE;
        DROP TABLE IF EXISTS site_setting_events CASCADE;
        DROP TABLE IF EXISTS site_banners CASCADE;
        DROP TABLE IF EXISTS recipe_versions CASCADE;
        DROP TABLE IF EXISTS reactions CASCADE;
        DROP TABLE IF EXISTS reaction_toggle_log CASCADE;
        DROP TABLE IF EXISTS promotion_campaigns CASCADE;
        DROP TABLE IF EXISTS product_cost_versions CASCADE;
        DROP TABLE IF EXISTS product_cost_settings CASCADE;
        DROP TABLE IF EXISTS payment_refunds CASCADE;
        DROP TABLE IF EXISTS payment_rate_limit_events CASCADE;
        DROP TABLE IF EXISTS order_returns CASCADE;
        DROP TABLE IF EXISTS order_items CASCADE;
        DROP TABLE IF EXISTS order_emails CASCADE;
        DROP TABLE IF EXISTS order_email_send_claims CASCADE;
        DROP TABLE IF EXISTS order_courier_events CASCADE;
        DROP TABLE IF EXISTS materials CASCADE;
        DROP TABLE IF EXISTS inventory_settings CASCADE;
        DROP TABLE IF EXISTS inventory_exceptions CASCADE;
        DROP TABLE IF EXISTS inventory_closes CASCADE;
        DROP TABLE IF EXISTS finance_export_packages CASCADE;
        DROP TABLE IF EXISTS finance_exceptions CASCADE;
        DROP TABLE IF EXISTS finance_audit_events CASCADE;
        DROP TABLE IF EXISTS expense_evidence_settings CASCADE;
        DROP TABLE IF EXISTS expense_evidence CASCADE;
        DROP TABLE IF EXISTS econt_settings CASCADE;
        DROP TABLE IF EXISTS delivery_settings CASCADE;
        DROP TABLE IF EXISTS contact_messages CASCADE;
        DROP TABLE IF EXISTS comments CASCADE;
        DROP TABLE IF EXISTS cod_settlements CASCADE;
        DROP TABLE IF EXISTS admin_alerts CASCADE;
        DROP TABLE IF EXISTS accounting_export_schema_settings CASCADE;
        DROP TABLE IF EXISTS accounting_category_mappings CASCADE;
        DROP TABLE IF EXISTS about_sections CASCADE;
        -- END generated downgrade drops
        DROP TABLE IF EXISTS privacy_sections CASCADE;
        DROP TABLE IF EXISTS privacy_page CASCADE;
        DROP TABLE IF EXISTS terms_sections CASCADE;
        DROP TABLE IF EXISTS terms_page CASCADE;
        DROP TABLE IF EXISTS faq_items CASCADE;
        DROP TABLE IF EXISTS faq_sections CASCADE;
        DROP TABLE IF EXISTS taxonomy_category_migration CASCADE;
        DROP TABLE IF EXISTS payment_events CASCADE;
        DROP TABLE IF EXISTS payments CASCADE;
        DROP TABLE IF EXISTS orders CASCADE;
        DROP TABLE IF EXISTS cart_items CASCADE;
        DROP TABLE IF EXISTS analytics_consents CASCADE;
        DROP TABLE IF EXISTS sessions CASCADE;
        DROP TABLE IF EXISTS vat_fiscal_settings_versions CASCADE;
        DROP TABLE IF EXISTS seller_legal_profile_versions CASCADE;
        DROP TABLE IF EXISTS finance_periods CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        DROP TABLE IF EXISTS product_videos CASCADE;
        DROP TABLE IF EXISTS product_images CASCADE;
        DROP TABLE IF EXISTS cookies_sections CASCADE;
        DROP TABLE IF EXISTS cookies_inventory CASCADE;
        DROP TABLE IF EXISTS cookies_page CASCADE;
        DROP TABLE IF EXISTS product_label_assignments CASCADE;
        DROP TABLE IF EXISTS product_labels CASCADE;
        DROP TABLE IF EXISTS product_categories CASCADE;
        DROP TABLE IF EXISTS product_types CASCADE;
        DROP TABLE IF EXISTS products CASCADE;
        """
    )
    op.execute("DROP FUNCTION IF EXISTS set_updated_at() CASCADE")
