"""Basic Segregation-of-Duties: `sod_conflict_rules` table, seeded with the
two example rules from the phase-1 scoping decision (see infrastructure/sod.py
for how these are interpreted). Both stay dormant until their referenced
modules/workflow states exist — vendor_invoices has no workflow configured
yet in this environment (Part 2 authors it) — matching simply never fires
until then, which is harmless.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-13T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sod_conflict_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("module_a", sa.String(length=64), nullable=False),
        sa.Column("action_a", sa.String(length=64), nullable=False),
        sa.Column("module_b", sa.String(length=64), nullable=False),
        sa.Column("action_b", sa.String(length=64), nullable=False),
        sa.Column("link_field", sa.String(length=64), nullable=True),
        sa.Column("enforcement", sa.String(length=16), server_default="block", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO sod_conflict_rules (name, module_a, action_a, module_b, action_b, link_field, enforcement) "
            "VALUES (:name, :ma, :aa, :mb, :ab, :lf, :enf)"
        ),
        [
            {
                "name": "Vendor bank-detail edit vs. payment execution",
                "ma": "vendors", "aa": "update",
                "mb": "payments", "ab": "create",
                "lf": "vendor_id", "enf": "block",
            },
            {
                "name": "Invoice creation vs. invoice approval",
                "ma": "vendor_invoices", "aa": "create",
                "mb": "vendor_invoices", "ab": "transition:approved",
                "lf": None, "enf": "block",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("sod_conflict_rules")
