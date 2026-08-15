"""module delivery_lines v1

Revision ID: e871043d61c4
Revises: 7d867102ad7a
Create Date: 2026-08-13T09:13:50.906946+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e871043d61c4"
down_revision = '7d867102ad7a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'biz_delivery_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuidv7()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('client_code', sa.String(length=10), sa.ForeignKey('clients.code'), server_default='ORG1', nullable=False),
        sa.Column('item', postgresql.UUID(as_uuid=True), sa.ForeignKey('biz_items.id'), nullable=False),
        sa.Column('qty', sa.Numeric(18, 4), nullable=False),
    )
    op.create_index('ix_biz_delivery_lines_client_code', 'biz_delivery_lines', ['client_code'])


def downgrade() -> None:
    # Additive-only migrations are not auto-reversed; revert by hand if needed.
    pass
