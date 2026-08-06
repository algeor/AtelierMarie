"""add rebrand taxonomy labels

Revision ID: 20260806_0003
Revises: 20260806_0002
Create Date: 2026-08-06 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260806_0003"
down_revision: str | Sequence[str] | None = "20260806_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        INSERT INTO product_labels (slug, name_en, name_bg, sort_order, is_active)
        VALUES
            ('sculptural', 'Sculptural', 'Скулптурни', 9, 1),
            ('bespoke', 'Bespoke', 'По поръчка', 10, 1)
        ON CONFLICT DO NOTHING;

        UPDATE about_items
        SET link_href = CASE link_href
            WHEN '/products?category=floral' THEN '/products?labels=floral'
            WHEN '/products?category=sculptural' THEN '/products?labels=sculptural'
            WHEN '/products?category=bespoke' THEN '/products?labels=bespoke'
            ELSE link_href
        END
        WHERE section = 'collections'
          AND link_href IN (
              '/products?category=floral',
              '/products?category=sculptural',
              '/products?category=bespoke'
          );
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        UPDATE about_items
        SET link_href = CASE link_href
            WHEN '/products?labels=floral' THEN '/products?category=floral'
            WHEN '/products?labels=sculptural' THEN '/products?category=sculptural'
            WHEN '/products?labels=bespoke' THEN '/products?category=bespoke'
            ELSE link_href
        END
        WHERE section = 'collections'
          AND link_href IN (
              '/products?labels=floral',
              '/products?labels=sculptural',
              '/products?labels=bespoke'
          );

        DELETE FROM product_labels WHERE slug IN ('sculptural', 'bespoke');
        """
    )
