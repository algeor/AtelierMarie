"""initial postgres schema

Revision ID: 20260802_0001
Revises:
Create Date: 2026-08-02 12:02:43.324902

"""

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


def downgrade() -> None:
    """Downgrade schema."""

    op.execute(
        """
        DROP TABLE IF EXISTS privacy_sections CASCADE;
        DROP TABLE IF EXISTS privacy_page CASCADE;
        DROP TABLE IF EXISTS terms_sections CASCADE;
        DROP TABLE IF EXISTS terms_page CASCADE;
        DROP TABLE IF EXISTS faq_items CASCADE;
        DROP TABLE IF EXISTS faq_sections CASCADE;
        DROP TABLE IF EXISTS taxonomy_category_migration CASCADE;
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
