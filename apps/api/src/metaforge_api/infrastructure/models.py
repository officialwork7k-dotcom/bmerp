"""Framework-owned registry tables (static ORM models, migrated normally by
Alembic autogenerate) — distinct from the dynamic per-module business
tables managed by schema_sync."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Table, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from metaforge_api.infrastructure.db import Base

# Plain many-to-many association table (no extra columns of its own), so a
# lightweight Table + `secondary=` is enough — no need for its own mapped
# class the way ApiToken/AuditLog need real columns and independent queries.
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# Mirrors user_roles: which SAP-MANDT-style client codes a user may sign
# into. A user typically has exactly one; multi-client is supported for
# admins/consultants who work across ORG1/ORG2/etc.
user_clients = Table(
    "user_clients",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("client_code", String(10), ForeignKey("clients.code", ondelete="CASCADE"), primary_key=True),
)


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Role(Base):
    """RBAC role. `is_admin` roles bypass per-module permission checks
    entirely (and are the only roles allowed into /admin/builder and
    /admin/roles) — everyone else is gated by `module_permissions`, a
    `{module_name: {"read"|"create"|"update"|"delete": bool}}` map. Default
    is deny: a module missing from the map, or an action missing from a
    module's entry, means no access. This isn't expressible as an ordinary
    metadata-driven module (the module list it configures against is
    dynamic), so — like the Builder — it gets its own small dedicated admin
    screen rather than forcing it through FieldControl."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    module_permissions: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OauthIdentity(Base):
    """Binds one external OAuth/OIDC identity (Google, later Microsoft) to
    a MetaForge User. `(provider, subject)` — the provider's own stable
    subject id — is the actual login key, never email: an email can be
    reused/reassigned at the provider, but `sub` never is. `email` is kept
    as a snapshot for display/matching against pending org_invites, with
    `email_verified` recording whether the provider itself attested it at
    the time this identity was created — Google always verifies for a
    normal consumer account; some providers (Microsoft) don't guarantee
    it, which matters for how an invite may be auto-accepted (see the
    provisioning/invite-resolution code paths for the actual check)."""

    __tablename__ = "oauth_identities"
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_oauth_identities_provider_subject"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OrgInvite(Base):
    """An org admin's invitation for a specific email to join their org
    with a specific role — resolved at OAuth callback time (see
    api/routers/oauth.py) by matching the provider's VERIFIED email
    against a pending, unexpired invite for that address. No accept-token:
    the OIDC provider's own verified-email attestation is the assurance
    that email-based invites otherwise lack, so requiring a second
    clicked link would add phishing surface without adding real trust.
    `status` moves pending -> accepted|revoked|expired; a partial unique
    index (see migration) allows re-inviting the same address only after
    the prior pending row has moved off `pending`."""

    __tablename__ = "org_invites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str] = mapped_column(String(10), ForeignKey("clients.code", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiSettingsOverride(Base):
    """Per-org override of a subset of the AiSettings singleton — one row
    per client_code, all-nullable, NULL meaning "inherit the platform
    default." Deliberately NOT merged into AiSettings itself (see that
    class's docstring): roughly half of AiSettings is structurally
    instance-level (Telegram bot config, the auto-post amount cap and
    write-allowed-modules guardrails) and must never be overridable by a
    tenant — this table only ever carries the fields that are genuinely
    safe to let an org customize (which provider/key/model it uses, and
    its own discount-tax-treatment default). Same masked-secret discipline
    as AiSettings applies wherever this is read back out over the API."""

    __tablename__ = "ai_settings_overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str] = mapped_column(String(10), ForeignKey("clients.code", ondelete="CASCADE"), nullable=False, unique=True)
    provider: Mapped[str | None] = mapped_column(String(16), nullable=True)
    gemini_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    gemini_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    openai_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    openai_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    discount_tax_treatment: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Client(Base):
    """A tenant, SAP-MANDT style: every dynamic module row is stamped with
    one of these codes (see repository.py's client_code scoping) and every
    read/write the app layer performs is filtered to the signed-in user's
    active client. Not Postgres RLS — enforced in the repository, the single
    choke-point all dynamic-module data access already goes through."""

    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # Nullable for an OAuth-only user (see OauthIdentity) — there is no
    # password to verify for an account that only ever signs in via
    # Google/Microsoft. auth.py's password-login path must check for None
    # explicitly rather than relying on argon2 to reject it.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # UI theme choice ("bm"|"yellow"|"blue"|"orange"|"dark") — per-user, not
    # per-role/global, so two people signed into the same instance can each
    # see their own last-picked theme. Free-text rather than an enum column:
    # new themes only ever get added on the frontend's THEMES list, never
    # need a migration to register.
    theme: Mapped[str] = mapped_column(String(20), nullable=False, server_default="bm")
    # Which of this user's assigned clients (see `clients` below) a login
    # picks by default when none is explicitly requested. Nullable so a
    # brand-new user with no client assignment yet doesn't block on a FK.
    default_client_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("clients.code", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Many small roles rather than one: a user's effective permissions are
    # the union of every assigned role's module_permissions (OR per action),
    # and is_admin if ANY assigned role is_admin — see deps.merge_roles().
    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, lazy="selectin")
    # Which client codes (tenants) this user may sign into — see Client.
    clients: Mapped[list["Client"]] = relationship(secondary=user_clients, lazy="selectin")


class ApiToken(Base):
    """Scoped personal-access token for integrations — hashed at rest
    (same argon2 context as passwords), never stored/returned in plain
    text after creation."""

    __tablename__ = "api_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code"), nullable=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    events: Mapped[list] = mapped_column(JSONB, nullable=False, server_default='["create","update","delete"]')
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NumberSeries(Base):
    """Counter for AUTO_NUMBER fields — allocated inside the owning
    create() transaction via SELECT ... FOR UPDATE, never buffered
    client-side, so numbers are gapless-per-commit (a rolled-back create
    still consumes its number, same tradeoff SAP documents for buffered
    number ranges — acceptable here since nothing pools/pre-allocates)."""

    __tablename__ = "number_series"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    prefix: Mapped[str] = mapped_column(String(32), nullable=False, server_default="")
    pad_width: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    reset_policy: Mapped[str] = mapped_column(String(16), nullable=False, server_default="never")  # never|yearly|monthly
    period_key: Mapped[str] = mapped_column(String(16), nullable=False, server_default="")
    next_value: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")


class SavedView(Base):
    """Per-user (or shared) saved list-page configuration: filters, sort,
    grouping, visible/ordered columns. `user_id IS NULL` means shared
    (visible to everyone) — the simplest "roams with the user, some views
    are shared" model without a separate sharing/ACL table."""

    __tablename__ = "saved_views"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # Nullable for the same reason Clearing/ApprovalRule are: existing rows
    # from before this column existed have no org to backfill from, and
    # NULL here reads as "visible everywhere" — same as a NULL
    # ApprovalRule.client_code — rather than silently orphaning them.
    # Every *new* shared view is stamped with the creator's org (see
    # routers/saved_views.py), so a "shared" view means "shared within my
    # org," not "shared with every tenant in the system."
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code"), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # The org the linked record lives in — without this, a notification
    # generated while working in one org still shows (and its `link` still
    # points into) an org a multi-client user has since switched away from;
    # the record fetch behind that link then 404s. Nullable for rows written
    # before this column existed, and for notifications with no record link.
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(2000), nullable=False, server_default="")
    link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JournalEntry(Base):
    """Append-only header for a posting-engine result — see
    infrastructure/posting.py's module docstring for why this is a
    hand-built engine table, not a Builder module. `document_module` +
    `document_id` point back at whichever dynamic-module record triggered
    the posting; no FK (the target table varies per module, which a static
    FK can't express). A `reversal_of` self-reference chains a correction
    entry back to the original it reverses."""

    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code"), nullable=True)
    document_module: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    posting_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="posted")  # posted|reversed
    reversal_of: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True)
    posted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JournalLine(Base):
    """Immutable — post_document()/reverse() only ever INSERT here, never
    UPDATE. account_code/account_name are snapshotted at post time rather
    than looked up live, so a later rename/retype of the source account
    never rewrites already-posted history."""

    __tablename__ = "journal_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    account_code: Mapped[str] = mapped_column(String(64), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="0")


class Clearing(Base):
    """Header for a manual open-item clearing — see infrastructure/
    clearing.py. `status` 'reversed' keeps the record (audit trail, same
    append-only stance as the posting engine's reversal) while excluding
    its items from the "already cleared" / "still open" checks."""

    __tablename__ = "clearings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code"), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")  # active|reversed
    cleared_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    cleared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClearingItem(Base):
    """One document matched into a Clearing. `amount` is the *signed*
    amount at clearing time (module.clearing_config's sign applied) — the
    set of a Clearing's items' amounts always sums to (approximately) zero,
    that's what makes the clearing valid in the first place."""

    __tablename__ = "clearing_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    clearing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clearings.id", ondelete="CASCADE"), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)


class StockBalance(Base):
    """Locked (SELECT ... FOR UPDATE) row per (client, item_module,
    item_id) — the on-hand quantity/moving-average cost live *here*,
    updated in place by infrastructure/stock.py's post_movement(); they are
    never independently editable. `item_module` is generic (whichever
    dynamic module represents "material"/"item" in a given install), not
    hardcoded — Part 2 authors that module, this engine doesn't care what
    it's named."""

    __tablename__ = "stock_balances"
    __table_args__ = (UniqueConstraint("client_code", "item_module", "item_id", name="uq_stock_balances_item"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code"), nullable=True)
    item_module: Mapped[str] = mapped_column(String(64), nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    on_hand_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="0")


class StockMovement(Base):
    """Append-only ledger — post_movement() only INSERTs here.
    `resulting_qty`/`resulting_avg_cost` snapshot the balance immediately
    after this movement (SAP MSEG-style running balance), so a history view
    never has to replay the whole ledger to show "on hand as of this
    movement." """

    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code"), nullable=True)
    item_module: Mapped[str] = mapped_column(String(64), nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)  # receipt|issue|adjustment
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)  # signed
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    resulting_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    resulting_avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    document_module: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentFlowLink(Base):
    """One "copied this much of this source line into that target line"
    record — see infrastructure/document_flow.py. The sum of a source
    line's links is how open_quantity() computes what's left to copy
    forward (PO qty ordered minus qty already receipted, etc.), so this
    table is the *only* source of truth for "how much is still open" —
    nothing on the source/target dynamic tables tracks it independently."""

    __tablename__ = "document_flow_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code"), nullable=True)
    source_module: Mapped[str] = mapped_column(String(64), nullable=False)
    source_line_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_module: Mapped[str] = mapped_column(String(64), nullable=False)
    target_line_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Report(Base):
    """A saved report definition — see infrastructure/reports.py.
    `definition` holds {source_module, group_by, measures, filters}, kept
    as one JSONB blob (mirrors modules.metadata's own shape) rather than
    normalized columns, since its shape is inherently variable per report."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code"), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PeriodicRun(Base):
    """Log-gated record of a synchronous periodic operation (depreciation,
    recurring billing, ...) — see infrastructure/periodic_runs.py. No ARQ
    dependency (phase 1's explicit constraint, see that module's docstring):
    runs execute directly in the triggering HTTP request and this table is
    what makes re-triggering the same (client, run_type, period) safe — a
    completed run is never re-executed, just returned."""

    __tablename__ = "periodic_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code"), nullable=True)
    run_type: Mapped[str] = mapped_column(String(64), nullable=False)
    period_key: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="running")  # running|completed|failed
    result_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FiscalPeriod(Base):
    """One calendar-month posting period per client (SAP-style: a fiscal
    year is just its 12 — or 13, with an adjustment period — periods).
    `period_key` is "YYYY-MM". A `closed` period blocks create/update/
    delete on any record whose period-gate date field (see
    FieldMetadata.is_period_gate) falls inside it — see
    infrastructure/fiscal.py for the actual gate check, invoked from
    DataRepository the same way workflow-lock and client-code scoping are."""

    __tablename__ = "fiscal_periods"
    __table_args__ = (UniqueConstraint("client_code", "period_key", name="uq_fiscal_periods_client_period"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str] = mapped_column(String(10), ForeignKey("clients.code", ondelete="CASCADE"), nullable=False)
    period_key: Mapped[str] = mapped_column(String(7), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="open")  # open|closed
    closed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SodConflictRule(Base):
    """Basic Segregation-of-Duties: `action_b` on `module_b` conflicts with a
    prior `action_a` on `module_a` by the *same* actor. Same-record by
    default (module_a == module_b, e.g. "you approved the invoice you
    created"); `link_field` allows a cross-module rule where module_b's row
    points at the module_a record via a lookup field (e.g. payments.vendor_id
    linking a payment back to the vendor whose bank details were edited).

    Actions are "create"|"update"|"delete"|"transition:<status>" — see
    infrastructure/sod.py, the only code that interprets these strings.
    Enforced at two points: role-assignment time (a user must never be
    *capable* of both sides — see admin.py) and action time (queries
    audit_log for the actor's own prior action_a — see data.py)."""

    __tablename__ = "sod_conflict_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    module_a: Mapped[str] = mapped_column(String(64), nullable=False)
    action_a: Mapped[str] = mapped_column(String(64), nullable=False)
    module_b: Mapped[str] = mapped_column(String(64), nullable=False)
    action_b: Mapped[str] = mapped_column(String(64), nullable=False)
    link_field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enforcement: Mapped[str] = mapped_column(String(16), nullable=False, server_default="block")  # block|warn
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    # Nullable for backward compatibility with rows written before this
    # column existed; every new request is stamped from the requester's
    # own session so it only ever surfaces in that org's approval queue.
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code", ondelete="CASCADE"), nullable=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    from_status: Mapped[str] = mapped_column(String(64), nullable=False)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")  # pending|approved|rejected
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalRule(Base):
    """WHO approves WHAT: a record in `module` transitioning to `to_status`
    requires sign-off from someone holding `approver_role_id` — always, or
    only once `amount_field` on the record reaches `min_amount` (tiered
    approval: small documents post straight through, large ones need a
    named role). Multiple rules can target the same module/to_status at
    different thresholds — `approval_rules.find_matching_rule()` picks the
    highest threshold the record still clears. `client_code` NULL means the
    rule applies to every tenant; set it to scope a rule to one org, same
    convention the rest of the framework's config tables use."""

    __tablename__ = "approval_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code", ondelete="CASCADE"), nullable=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    approver_role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    amount_field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    min_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiSettings(Base):
    """Instance-level (NOT tenant-scoped) config for the AI chat assistant —
    deliberately NOT a business module field, unlike everything else in
    this app. A field on a dynamic module is readable through the generic
    list/get/export/CSV machinery and the generic UI renderer; API keys
    living there would be one permission misconfiguration away from a
    tenant-wide leak. This table is only ever touched by the dedicated
    admin-only ai_settings router, which masks the key fields on every read
    (returns `*_key_set: bool`, never the raw value back out).

    Treated as a singleton: exactly one row is expected to exist (the
    dedicated router upserts it), read via `ORDER BY created_at ASC LIMIT
    1` rather than a fixed id, matching how a from-scratch install has no
    row at all (assistant reports itself disabled) without needing a
    seed migration.

    `write_allowed_modules` is the generic-tool-layer's write allowlist —
    P2P/O2C document modules an admin has opted into AI-driven
    create/transition, deliberately excluding cash-movement modules
    (payments, general_journal) by default since that's where a wrong
    auto-post hurts most. Shape: [{"module": str, "amount_field": str |
    None}]. When `amount_field` is set and a transition would fire a
    posting-trigger status, infrastructure/ai_tools.py compares that
    field's value on the record against `auto_post_amount_cap` and, if it
    exceeds it, returns "requires_confirmation" instead of executing —
    the one server-side (not merely prompted) guardrail on "auto-post
    when confident," per this feature's design review."""

    __tablename__ = "ai_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    provider: Mapped[str] = mapped_column(String(16), nullable=False, server_default="gemini")  # gemini|openai
    gemini_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    gemini_model: Mapped[str] = mapped_column(String(64), nullable=False, server_default="gemini-2.0-flash")
    openai_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    openai_model: Mapped[str] = mapped_column(String(64), nullable=False, server_default="gpt-4o-mini")
    auto_post_amount_cap: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    write_allowed_modules: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    # Governs how chat_service._system_prompt instructs the assistant to map
    # a scanned document's discount onto vendor_invoices/customer_invoices'
    # discount fields (see their FieldMetadata: line-level discount_percent
    # nets out of line_total *before* tax_amount is computed from it, so a
    # discount recorded there reduces the taxable base; header-level
    # discount_amount is subtracted from grand_total *after* tax_total, so
    # it never touches the taxable base). "before_tax" is standard invoicing
    # practice — the deduction reduces what tax is charged on — and is
    # therefore the default; "after_tax" is for the less common case of a
    # settlement/early-payment discount that applies to the already-taxed
    # total. A per-instance setting rather than a per-scan guess because a
    # given organization's vendors overwhelmingly follow one convention or
    # the other, and the assistant should not have to (mis)infer it fresh
    # from each photo — see the #5537-adjacent AL Construction invoice
    # incident this setting was added to fix.
    discount_tax_treatment: Mapped[str] = mapped_column(String(16), nullable=False, server_default="before_tax")
    # --- Telegram integration: a second front door onto the exact same
    # assistant (infrastructure/chat_service.py's run_chat_turn), so it
    # lives on this same singleton row rather than a sibling table — same
    # audience (admin), same secrecy pattern (write-only, masked reads),
    # same lifecycle. telegram_bot_token is masked identically to the
    # gemini/openai keys above (see ai_settings.py router). public_base_url
    # has no other home in this app (no instance-settings table exists) —
    # it's what turns a reply's internal [label](/module/id) link into a
    # clickable absolute URL in a Telegram message. telegram_update_offset
    # is the long-poller's getUpdates cursor, persisted here (not Valkey,
    # which isn't running in this environment) so a restart doesn't replay
    # or drop the backlog — see infrastructure/telegram_poller.py.
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    telegram_bot_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    telegram_bot_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    public_base_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    telegram_update_offset: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TelegramLinkCode(Base):
    """A one-time, short-lived code a user generates from their AI
    Assistant settings and sends to the bot (`/link CODE`) to connect
    their own Telegram account to their own MetaForge identity — see
    infrastructure/telegram_handler.py's consume_link_code(). Generating a
    new code deletes any existing one for that user first (one live code
    at a time); successful consumption deletes the row outright rather
    than marking it used, so a consumed or expired code can never be
    replayed — there is nothing left to replay."""

    __tablename__ = "telegram_link_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TelegramLink(Base):
    """The actual Telegram<->MetaForge identity link, one per user (v1).
    `telegram_chat_id` is the hot lookup key for every inbound Telegram
    update — deliberately its own table rather than columns on `User`
    (see this feature's design notes): the link carries its own mutable
    lifecycle state (`preferred_client_code` via the `/org` command,
    `conversation_id` — the single persistent AI conversation this link's
    messages append to, see chat_service.run_chat_turn) that would rot as
    nullable clutter on the auth table, and unlink/relink is a clean
    delete/insert of one row rather than nulling out several User columns."""

    __tablename__ = "telegram_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code", ondelete="SET NULL"), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_conversations.id", ondelete="SET NULL"), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiToolCall(Base):
    """Audit trail for every tool the AI chat assistant invoked — kept
    separate from `AiConversationMessage` (the visible chat transcript,
    added later) because a write the assistant performed must stay
    reconstructable even if a user deletes the conversation it happened
    in. One row per tool call, `conversation_id` groups all calls from the
    same chat turn/session so a sequence of "search vendor -> create
    invoice -> transition to posted" reads as one story. Deliberately NOT
    foreign-keyed to `ai_conversations.id` — same reasoning as
    `AuditLog.record_id` having no FK: this row must survive the
    conversation being deleted, not cascade with it."""

    __tablename__ = "ai_tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    client_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("clients.code", ondelete="CASCADE"), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    tool: Mapped[str] = mapped_column(String(64), nullable=False)
    args: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[str] = mapped_column(String(24), nullable=False)  # executed|rejected|requires_confirmation
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiConversation(Base):
    """One saved AI-assistant chat. `seq_number` is scoped to (user_id,
    client_code) — not global — so numbering restarts per org per user:
    "chat 1" always means the caller's own first conversation in the org
    they're currently in, and the get_conversation_history tool (see
    infrastructure/ai_tools.py) can never resolve a number into another
    org's data, since the lookup query is scoped by client_code the exact
    same way every other read in this app is. `title` is auto-derived from
    the first user message (see ai_chat.py) and never re-derived after,
    even if the conversation drifts topic — simpler than a "smart
    re-titling" pass, and matches how every other list-with-a-label in
    this app behaves (a document's number doesn't change either)."""

    __tablename__ = "ai_conversations"
    __table_args__ = (UniqueConstraint("user_id", "client_code", "seq_number", name="uq_ai_conversations_user_client_seq"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_code: Mapped[str] = mapped_column(String(10), ForeignKey("clients.code", ondelete="CASCADE"), nullable=False)
    seq_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AiConversationMessage(Base):
    """One turn of a saved conversation. Only the user-visible (role,
    content) pairs are stored — never the internal tool-call/tool-result
    scaffolding a turn generates along the way (see ai_chat.py's tool
    loop). That's deliberate, not an omission: replaying that scaffolding
    into a LATER turn's prompt would make every conversation's prompt size
    grow without bound the longer it runs, which is exactly the kind of
    self-inflicted latency the AI assistant was already flagged for. What
    a past turn actually DID (writes performed) is separately reconstructable
    from `AiToolCall` if ever needed — this table exists purely to answer
    "what did we say to each other," not "what did the model do internally."
    """

    __tablename__ = "ai_conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user|assistant
    content: Mapped[str] = mapped_column(String, nullable=False)
    # The attached scan itself (already preprocessed — grayscale, capped at
    # ~1568px, JPEG — by either imagePrep.ts or infrastructure/image_prep.py
    # before it ever reaches here), so a reopened conversation can still
    # show the photo, not just the "[Scanned document attached]" text
    # marker. Stored directly in Postgres rather than via infrastructure/
    # storage.py's S3 adapter: that adapter has no working endpoint/
    # credentials in this environment (same class of gap as Valkey), and at
    # a few hundred KB per scan a bytea column is simple and self-contained
    # — no external dependency for something this feature needs to just
    # work out of the box. Never populated on the assistant's own reply row.
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    image_mime_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
