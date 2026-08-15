"""Stock/quantity ledger engine: stock_balances (locked, on-hand +
moving-average cost) + stock_movements (append-only) — see
infrastructure/stock.py. ModuleMetadata.stock_rules is pure JSONB on the
existing modules.metadata column.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-13T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code"), nullable=True),
        sa.Column("item_module", sa.String(length=64), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("on_hand_qty", sa.Numeric(18, 4), server_default="0", nullable=False),
        sa.Column("avg_cost", sa.Numeric(18, 4), server_default="0", nullable=False),
        sa.UniqueConstraint("client_code", "item_module", "item_id", name="uq_stock_balances_item"),
    )
    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("client_code", sa.String(length=10), sa.ForeignKey("clients.code"), nullable=True),
        sa.Column("item_module", sa.String(length=64), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column("resulting_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("resulting_avg_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("document_module", sa.String(length=64), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_stock_movements_item", "stock_movements", ["item_module", "item_id"])


def downgrade() -> None:
    op.drop_table("stock_movements")
    op.drop_table("stock_balances")
