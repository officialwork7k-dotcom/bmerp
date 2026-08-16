"""Seeds the curated org-assignable roles (Org Admin/Approver/Operator/
Viewer) — org_admin.py's invite endpoint can only hand out one of these
by name, and Org Admin itself may already exist from provisioning.py's
lazy-create path (self-service signup runs before any org exists to
invite anyone into), so this is idempotent on role name.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-16T00:00:00+00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

_ROLES = [
    ("Org Admin", '{"*": {"read": true, "create": true, "update": true, "delete": true}, "system.org_users": {"manage": true}, "system.ai_settings": {"manage": true}}'),
    ("Org Approver", '{"*": {"read": true, "update": true}}'),
    ("Org Operator", '{"*": {"read": true, "create": true, "update": true}}'),
    ("Org Viewer", '{"*": {"read": true}}'),
]


def upgrade() -> None:
    conn = op.get_bind()
    for name, permissions_json in _ROLES:
        conn.execute(
            sa.text(
                "INSERT INTO roles (name, is_admin, module_permissions) VALUES (:name, false, CAST(:perms AS jsonb)) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"name": name, "perms": permissions_json},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for name, _ in _ROLES:
        conn.execute(sa.text("DELETE FROM roles WHERE name = :name"), {"name": name})
