"""allow internal delivery method

Revision ID: 20260806_0004
Revises: 20260806_0003
Create Date: 2026-08-06 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260806_0004"
down_revision: str | Sequence[str] | None = "20260806_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_delivery_method_check;
        ALTER TABLE orders
            ADD CONSTRAINT orders_delivery_method_check
            CHECK (delivery_method IN ('office', 'door', 'internal'));
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        UPDATE orders
        SET delivery_method = NULL,
            delivery_details = NULL
        WHERE delivery_method = 'internal';

        ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_delivery_method_check;
        ALTER TABLE orders
            ADD CONSTRAINT orders_delivery_method_check
            CHECK (delivery_method IN ('office', 'door'));
        """
    )
