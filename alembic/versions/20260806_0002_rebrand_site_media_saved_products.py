"""add rebrand site media and saved products

Revision ID: 20260806_0002
Revises: 20260802_0001
Create Date: 2026-08-06 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260806_0002"
down_revision: str | Sequence[str] | None = "20260802_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE user_saved_products
        (
            user_id    TEXT        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            product_id TEXT        NOT NULL REFERENCES products (id) ON DELETE CASCADE,
            saved_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, product_id)
        );

        CREATE INDEX idx_user_saved_products_user_saved_at
            ON user_saved_products (user_id, saved_at DESC);
        CREATE INDEX idx_user_saved_products_product
            ON user_saved_products (product_id);

        CREATE TABLE site_media_assets
        (
            key           TEXT PRIMARY KEY,
            image_id      TEXT,
            image_url     TEXT,
            thumbnail_url TEXT,
            zoom_url      TEXT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TRIGGER site_media_assets_updated_at
        BEFORE UPDATE ON site_media_assets
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DROP TRIGGER IF EXISTS site_media_assets_updated_at ON site_media_assets;
        DROP TABLE IF EXISTS site_media_assets CASCADE;
        DROP TABLE IF EXISTS user_saved_products CASCADE;
        """
    )
