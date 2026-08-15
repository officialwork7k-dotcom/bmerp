"""purchase_order_lines.item: free text -> LOOKUP(items)

Destructive/retyping change, applied by hand per the framework's
additive-only auto-migration policy (see infrastructure/schema_sync.py).
Converts the column from varchar to a uuid FK against biz_items, backfilling
existing rows by exact name match, and drops the temporary item_ref field
that stood in for this during development.

Revision ID: d4f8a1b23c56
Revises: 30bb9b605c97
Create Date: 2026-08-12T10:30:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d4f8a1b23c56"
down_revision = "30bb9b605c97"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("biz_purchase_order_lines", sa.Column("item_uuid", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        "UPDATE biz_purchase_order_lines l SET item_uuid = i.id FROM biz_items i WHERE i.name = l.item"
    )
    op.drop_column("biz_purchase_order_lines", "item")
    op.execute("ALTER TABLE biz_purchase_order_lines DROP COLUMN IF EXISTS item_ref")
    op.alter_column("biz_purchase_order_lines", "item_uuid", new_column_name="item")
    op.alter_column("biz_purchase_order_lines", "item", nullable=False)
    op.create_foreign_key(
        "biz_purchase_order_lines_item_fkey", "biz_purchase_order_lines", "biz_items", ["item"], ["id"]
    )
    op.create_index("ix_biz_purchase_order_lines_item", "biz_purchase_order_lines", ["item"])


def downgrade() -> None:
    # Destructive migrations are not auto-reversed; revert by hand if needed.
    pass
