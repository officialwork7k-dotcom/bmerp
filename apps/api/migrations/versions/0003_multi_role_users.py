"""Multiple roles per user: replace users.role_id (single FK) with a
user_roles association table. Effective permissions become the union of
every assigned role's module_permissions (OR per action), and is_admin if
ANY assigned role is_admin — see api.deps.merge_roles().

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-12T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )

    # Carry every existing single-role assignment over as a one-row
    # membership before the column disappears — otherwise this migration
    # would silently strip every user's permissions on upgrade.
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT id, role_id FROM users WHERE role_id IS NOT NULL
        """
    )

    op.drop_column("users", "role_id")


def downgrade() -> None:
    op.add_column("users", sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=True))
    # Best-effort: a user with several roles can only keep one on downgrade,
    # so pick an arbitrary (first) assignment rather than losing the row.
    op.execute(
        """
        UPDATE users SET role_id = (
            SELECT role_id FROM user_roles WHERE user_roles.user_id = users.id LIMIT 1
        )
        """
    )
    op.drop_table("user_roles")
