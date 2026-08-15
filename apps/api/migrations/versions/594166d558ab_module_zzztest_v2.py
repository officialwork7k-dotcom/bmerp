"""module zzztest v2

Revision ID: 594166d558ab
Revises: b7e5a2f0c94d
Create Date: 2026-08-14T18:39:47.778430+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "594166d558ab"
down_revision = 'b7e5a2f0c94d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('biz_zzztest', sa.Column('field_3', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
