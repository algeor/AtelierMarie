"""add crafted-later fulfillment fields

Revision ID: 20260815_0006
Revises: 20260808_0005
Create Date: 2026-08-15 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260815_0006"
down_revision: str | Sequence[str] | None = "20260808_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE orders
            ADD COLUMN fulfillment_status TEXT NOT NULL DEFAULT 'ready'
                CHECK (fulfillment_status IN ('ready', 'awaiting_production'));

        ALTER TABLE order_items
            ADD COLUMN allocated_quantity INTEGER,
            ADD COLUMN backordered_quantity INTEGER;

        UPDATE order_items
        SET allocated_quantity = quantity,
            backordered_quantity = 0
        WHERE allocated_quantity IS NULL OR backordered_quantity IS NULL;

        CREATE OR REPLACE FUNCTION set_order_item_fulfillment_defaults()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.allocated_quantity IS NULL AND NEW.backordered_quantity IS NULL THEN
                NEW.allocated_quantity := NEW.quantity;
                NEW.backordered_quantity := 0;
            ELSIF NEW.allocated_quantity IS NULL THEN
                NEW.allocated_quantity := NEW.quantity - NEW.backordered_quantity;
            ELSIF NEW.backordered_quantity IS NULL THEN
                NEW.backordered_quantity := NEW.quantity - NEW.allocated_quantity;
            END IF;

            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER order_items_fulfillment_defaults
        BEFORE INSERT OR UPDATE ON order_items
        FOR EACH ROW
        EXECUTE FUNCTION set_order_item_fulfillment_defaults();

        ALTER TABLE order_items
            ALTER COLUMN allocated_quantity SET NOT NULL,
            ALTER COLUMN backordered_quantity SET NOT NULL;

        ALTER TABLE order_items
            ADD CONSTRAINT order_items_allocated_quantity_nonnegative
                CHECK (allocated_quantity >= 0),
            ADD CONSTRAINT order_items_backordered_quantity_nonnegative
                CHECK (backordered_quantity >= 0),
            ADD CONSTRAINT order_items_fulfillment_quantity_sum_check
                CHECK (allocated_quantity + backordered_quantity = quantity);
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DROP TRIGGER IF EXISTS order_items_fulfillment_defaults ON order_items;
        DROP FUNCTION IF EXISTS set_order_item_fulfillment_defaults();

        ALTER TABLE order_items
            DROP CONSTRAINT IF EXISTS order_items_fulfillment_quantity_sum_check,
            DROP CONSTRAINT IF EXISTS order_items_backordered_quantity_nonnegative,
            DROP CONSTRAINT IF EXISTS order_items_allocated_quantity_nonnegative;

        ALTER TABLE order_items
            DROP COLUMN IF EXISTS backordered_quantity,
            DROP COLUMN IF EXISTS allocated_quantity;

        ALTER TABLE orders
            DROP COLUMN IF EXISTS fulfillment_status;
        """
    )
