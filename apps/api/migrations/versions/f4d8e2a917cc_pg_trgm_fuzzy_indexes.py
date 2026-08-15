"""pg_trgm extension + trigram expression indexes for fuzzy master-data
matching (AI receipt-scan vendor/item/tax-code lookups — see
infrastructure/fuzzy_match.py). Indexes are on lower(<col>) because
pg_trgm's similarity()/word_similarity()/%/<% operators are
case-sensitive (unlike ILIKE) — only an expression index on the
lowercased column actually gets used by a lowercased comparison.

Known limitation, not solved here: these indexes reference physical
columns of builder-managed dynamic tables. The builder's schema-diff/sync
path is additive-only, so a rename/drop of vendors.name / items.name /
customers.name / tax_codes.code already requires manual migration review
— at that point a stale trigram index here needs manual drop/recreate.

Revision ID: f4d8e2a917cc
Revises: c7a91e4f3b56
Create Date: 2026-08-16T00:00:00+00:00
"""
from alembic import op

revision = "f4d8e2a917cc"
down_revision = "c7a91e4f3b56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX IF NOT EXISTS ix_trgm_biz_vendors_lower_name ON biz_vendors USING GIN (lower(name) gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_trgm_biz_customers_lower_name ON biz_customers USING GIN (lower(name) gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_trgm_biz_items_lower_name ON biz_items USING GIN (lower(name) gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_trgm_biz_tax_codes_lower_code ON biz_tax_codes USING GIN (lower(code) gin_trgm_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_trgm_biz_vendors_lower_name")
    op.execute("DROP INDEX IF EXISTS ix_trgm_biz_customers_lower_name")
    op.execute("DROP INDEX IF EXISTS ix_trgm_biz_items_lower_name")
    op.execute("DROP INDEX IF EXISTS ix_trgm_biz_tax_codes_lower_code")
    # Do NOT drop the extension in downgrade — other objects/DBs may share it.
