"""Self-service org provisioning — turns a brand-new OAuth identity with no
existing org membership into a fresh, usable tenant: a Client row, a User
seeded as that org's Admin, and a minimal starter chart of accounts +
fiscal-year calendar so the org isn't completely empty on first login.

Deliberately NOT a metadata-module create_record call: this runs during
the OAuth callback, before any DataRepository/CurrentUser context exists
for the brand-new user, and the starter rows are simple enough (a handful
of GL accounts, no formulas/aggregates in play) that a direct insert
through the dynamic table is both correct and far simpler than wiring up
a full repository for a one-shot seed.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.infrastructure.dynamic_tables import resolve_table
from metaforge_api.infrastructure.models import Client, FiscalPeriod, Role, User
from metaforge_api.infrastructure.module_registry import SessionModuleRegistry

ORG_ADMIN_ROLE_NAME = "Org Admin"

# A deliberately small, generic starter chart of accounts — enough for a
# brand-new org to record its first transactions without an accountant
# having to build the GL from nothing. Real charts vary a lot by country/
# industry; this is a baseline, not a template of record.
_STARTER_GL_ACCOUNTS = [
    {"account_code": "1000", "account_name": "Cash", "account_type": "Asset"},
    {"account_code": "1100", "account_name": "Accounts Receivable", "account_type": "Asset"},
    {"account_code": "1200", "account_name": "Inventory", "account_type": "Asset"},
    {"account_code": "2000", "account_name": "Accounts Payable", "account_type": "Liability"},
    {"account_code": "2100", "account_name": "Tax Payable", "account_type": "Liability"},
    {"account_code": "3000", "account_name": "Common Stock", "account_type": "Equity"},
    {"account_code": "3900", "account_name": "Retained Earnings", "account_type": "Equity"},
    {"account_code": "4000", "account_name": "Sales Revenue", "account_type": "Revenue"},
    {"account_code": "5000", "account_name": "Cost of Goods Sold", "account_type": "Expense"},
    {"account_code": "6000", "account_name": "Operating Expenses", "account_type": "Expense"},
]


async def _next_org_code(session: AsyncSession) -> str:
    """`C0001`, `C0002`, ... — self-registered orgs get an auto-generated
    code distinct from the hand-picked ORG1/ORG2-style codes used
    elsewhere in this project, so the two schemes never collide."""
    count = (await session.execute(select(func.count()).select_from(Client))).scalar_one()
    for attempt in range(count + 1, count + 1000):
        code = f"C{attempt:04d}"
        exists = (await session.execute(select(Client.id).where(Client.code == code))).scalar_one_or_none()
        if exists is None:
            return code
    raise RuntimeError("could not allocate an org code")


async def _seed_starter_data(session: AsyncSession, client_code: str) -> None:
    registry = SessionModuleRegistry()
    await registry.load_all(session)

    gl_module = registry.get("gl_accounts")
    gl_table = resolve_table(gl_module, registry)
    for row in _STARTER_GL_ACCOUNTS:
        await session.execute(insert(gl_table).values(id=uuid.uuid4(), client_code=client_code, **row))

    year = date.today().year
    for month in range(1, 13):
        last_day = calendar.monthrange(year, month)[1]
        session.add(
            FiscalPeriod(
                client_code=client_code,
                period_key=f"{year:04d}-{month:02d}",
                start_date=date(year, month, 1),
                end_date=date(year, month, last_day),
            )
        )


async def _org_admin_role(session: AsyncSession) -> Role:
    role = (await session.execute(select(Role).where(Role.name == ORG_ADMIN_ROLE_NAME))).scalar_one_or_none()
    if role is not None:
        return role
    role = Role(
        name=ORG_ADMIN_ROLE_NAME,
        is_admin=False,
        module_permissions={
            "*": {"read": True, "create": True, "update": True, "delete": True},
            "system.org_users": {"manage": True},
            "system.ai_settings": {"manage": True},
        },
    )
    session.add(role)
    await session.flush()
    return role


async def provision_org(session: AsyncSession, *, email: str, display_name: str, org_name: str | None = None) -> User:
    """Creates a brand-new Client + User (seeded as that org's Org Admin)
    + starter data, all in one transaction — the caller commits (or the
    caller's own transaction context does), so a failure partway through
    never leaves a half-provisioned org behind."""
    client_code = await _next_org_code(session)
    client = Client(code=client_code, name=org_name or f"{display_name}'s Organization", is_active=True)
    session.add(client)
    await session.flush()

    role = await _org_admin_role(session)

    user = User(username=email, display_name=display_name, password_hash=None, default_client_code=client_code)
    user.roles.append(role)
    user.clients.append(client)
    session.add(user)
    await session.flush()

    await _seed_starter_data(session, client_code)
    return user
