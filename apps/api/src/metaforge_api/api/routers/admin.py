"""User & role administration — not a generic metadata-driven module: the
Role.module_permissions matrix is shaped against the dynamic, ever-changing
module list, which FieldMetadata has no way to express. Same tier as
/admin/builder: a small dedicated admin screen, gated to admin roles only.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import or_, select

from metaforge_api.api.deps import AdminUser, DbSession, merge_roles
from metaforge_api.infrastructure import cache, sod
from metaforge_api.infrastructure.models import ApprovalRule, Client, FiscalPeriod, Role, SodConflictRule, User

router = APIRouter(prefix="/api/admin", tags=["admin"])
_pwd = CryptContext(schemes=["argon2"], deprecated="auto")


class ClientIn(BaseModel):
    code: str
    name: str
    is_active: bool = True


@router.get("/clients")
async def list_clients(session: DbSession, _: AdminUser):
    rows = (await session.execute(select(Client))).scalars().all()
    return [{"id": str(c.id), "code": c.code, "name": c.name, "is_active": c.is_active} for c in rows]


@router.post("/clients")
async def create_client(body: ClientIn, session: DbSession, _: AdminUser):
    if (await session.execute(select(Client).where(Client.code == body.code))).scalar_one_or_none() is not None:
        raise HTTPException(409, f"client code '{body.code}' already exists")
    client = Client(code=body.code, name=body.name, is_active=body.is_active)
    session.add(client)
    await session.commit()
    return {"id": str(client.id), "code": client.code, "name": client.name, "is_active": client.is_active}


@router.put("/clients/{client_id}")
async def update_client(client_id: uuid.UUID, body: ClientIn, session: DbSession, _: AdminUser):
    client = (await session.execute(select(Client).where(Client.id == client_id))).scalar_one_or_none()
    if client is None:
        raise HTTPException(404, "client not found")
    client.name = body.name
    client.is_active = body.is_active
    await session.commit()
    return {"id": str(client.id), "code": client.code, "name": client.name, "is_active": client.is_active}


class RoleIn(BaseModel):
    name: str
    is_admin: bool = False
    module_permissions: dict = {}


@router.get("/roles")
async def list_roles(session: DbSession, _: AdminUser):
    rows = (await session.execute(select(Role))).scalars().all()
    return [
        {"id": str(r.id), "name": r.name, "is_admin": r.is_admin, "module_permissions": r.module_permissions}
        for r in rows
    ]


@router.post("/roles")
async def create_role(body: RoleIn, session: DbSession, _: AdminUser):
    role = Role(name=body.name, is_admin=body.is_admin, module_permissions=body.module_permissions)
    session.add(role)
    await session.commit()
    return {"id": str(role.id), "name": role.name, "is_admin": role.is_admin, "module_permissions": role.module_permissions}


@router.put("/roles/{role_id}")
async def update_role(role_id: uuid.UUID, body: RoleIn, session: DbSession, _: AdminUser):
    role = (await session.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if role is None:
        raise HTTPException(404, "role not found")
    role.name = body.name
    role.is_admin = body.is_admin
    role.module_permissions = body.module_permissions
    await session.commit()
    return {"id": str(role.id), "name": role.name, "is_admin": role.is_admin, "module_permissions": role.module_permissions}


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(role_id: uuid.UUID, session: DbSession, _: AdminUser):
    await session.execute(select(Role).where(Role.id == role_id))
    role = (await session.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if role is not None:
        await session.delete(role)
        await session.commit()


class UserIn(BaseModel):
    username: str
    display_name: str
    password: str | None = None
    role_ids: list[uuid.UUID] = []
    is_active: bool = True
    client_codes: list[str] = []
    default_client_code: str | None = None


async def _resolve_roles(session: DbSession, role_ids: list[uuid.UUID]) -> list[Role]:
    if not role_ids:
        return []
    roles = (await session.execute(select(Role).where(Role.id.in_(role_ids)))).scalars().all()
    return list(roles)


async def _resolve_clients(session: DbSession, client_codes: list[str]) -> list[Client]:
    if not client_codes:
        return []
    clients = (await session.execute(select(Client).where(Client.code.in_(client_codes)))).scalars().all()
    return list(clients)


async def _check_sod_assignment(session: DbSession, roles: list[Role]) -> None:
    """Rejects a role assignment that would make a user capable of both
    sides of a BLOCK-enforcement SoD rule at once — see sod.py's module
    docstring. Runs regardless of is_admin: an admin role still shouldn't
    be silently exempted from a conflict check the way permission checks
    exempt it (that exemption is a request-time bypass, not something this
    admin-configuration step should inherit)."""
    _, module_permissions = merge_roles(roles)
    rules = (await session.execute(select(SodConflictRule))).scalars().all()
    violations = sod.check_assignment(module_permissions, rules)
    if violations:
        raise HTTPException(409, {"error": "sod_conflict", "violations": violations})


def _default_client_for(body: UserIn, clients: list[Client]) -> str | None:
    """Falls back to the sole assigned client when the admin didn't pick one
    explicitly — matches _resolve_client_code's own single-client shortcut,
    so a one-client user never has to be told to also set a default."""
    if body.default_client_code:
        return body.default_client_code
    return clients[0].code if len(clients) == 1 else None


@router.get("/users")
async def list_users(session: DbSession, _: AdminUser):
    rows = (await session.execute(select(User))).scalars().all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "display_name": u.display_name,
            "is_active": u.is_active,
            "role_ids": [str(r.id) for r in u.roles],
            "client_codes": [c.code for c in u.clients],
            "default_client_code": u.default_client_code,
            "locked_until": u.locked_until.isoformat() if u.locked_until else None,
        }
        for u in rows
    ]


@router.post("/users")
async def create_user(body: UserIn, session: DbSession, _: AdminUser):
    if not body.password:
        raise HTTPException(400, "password required for a new user")
    roles = await _resolve_roles(session, body.role_ids)
    await _check_sod_assignment(session, roles)
    clients = await _resolve_clients(session, body.client_codes)
    user = User(
        username=body.username,
        display_name=body.display_name,
        password_hash=_pwd.hash(body.password),
        roles=roles,
        clients=clients,
        default_client_code=_default_client_for(body, clients),
        is_active=body.is_active,
    )
    session.add(user)
    await session.commit()
    return {"id": str(user.id), "username": user.username}


@router.patch("/users/{user_id}")
async def update_user(user_id: uuid.UUID, body: UserIn, session: DbSession, _: AdminUser):
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "user not found")
    user.display_name = body.display_name
    roles = await _resolve_roles(session, body.role_ids)
    await _check_sod_assignment(session, roles)
    user.roles = roles
    clients = await _resolve_clients(session, body.client_codes)
    user.clients = clients
    user.default_client_code = _default_client_for(body, clients)
    user.is_active = body.is_active
    if body.password:
        user.password_hash = _pwd.hash(body.password)
    await session.commit()
    return {"id": str(user.id), "username": user.username}


class SodRuleIn(BaseModel):
    name: str
    module_a: str
    action_a: str
    module_b: str
    action_b: str
    link_field: str | None = None
    enforcement: str = "block"
    is_active: bool = True


def _sod_rule_out(r: SodConflictRule) -> dict:
    return {
        "id": str(r.id), "name": r.name, "module_a": r.module_a, "action_a": r.action_a,
        "module_b": r.module_b, "action_b": r.action_b, "link_field": r.link_field,
        "enforcement": r.enforcement, "is_active": r.is_active,
    }


@router.get("/sod-rules")
async def list_sod_rules(session: DbSession, _: AdminUser):
    rows = (await session.execute(select(SodConflictRule))).scalars().all()
    return [_sod_rule_out(r) for r in rows]


@router.post("/sod-rules")
async def create_sod_rule(body: SodRuleIn, session: DbSession, _: AdminUser):
    rule = SodConflictRule(**body.model_dump())
    session.add(rule)
    await session.commit()
    return _sod_rule_out(rule)


@router.put("/sod-rules/{rule_id}")
async def update_sod_rule(rule_id: uuid.UUID, body: SodRuleIn, session: DbSession, _: AdminUser):
    rule = (await session.execute(select(SodConflictRule).where(SodConflictRule.id == rule_id))).scalar_one_or_none()
    if rule is None:
        raise HTTPException(404, "rule not found")
    for k, v in body.model_dump().items():
        setattr(rule, k, v)
    await session.commit()
    return _sod_rule_out(rule)


@router.delete("/sod-rules/{rule_id}", status_code=204)
async def delete_sod_rule(rule_id: uuid.UUID, session: DbSession, _: AdminUser):
    rule = (await session.execute(select(SodConflictRule).where(SodConflictRule.id == rule_id))).scalar_one_or_none()
    if rule is not None:
        await session.delete(rule)
        await session.commit()


class ApprovalRuleIn(BaseModel):
    module: str
    to_status: str
    approver_role_id: uuid.UUID
    amount_field: str | None = None
    min_amount: float | None = None
    is_active: bool = True


def _approval_rule_out(r: ApprovalRule) -> dict:
    return {
        "id": str(r.id), "client_code": r.client_code, "module": r.module, "to_status": r.to_status,
        "approver_role_id": str(r.approver_role_id), "amount_field": r.amount_field,
        "min_amount": float(r.min_amount) if r.min_amount is not None else None, "is_active": r.is_active,
    }


@router.get("/approval-rules")
async def list_approval_rules(session: DbSession, user: AdminUser):
    # A global rule (client_code IS NULL) is visible everywhere since it
    # genuinely governs every org's transitions — same visibility rule
    # /approvals/pending already uses. But that's read-only: create/update/
    # delete below are always scoped to the caller's *own* org, so one
    # tenant's admin can never author, edit, or remove another tenant's
    # rule, nor silently rewrite a system-wide global one from their own
    # per-org admin screen.
    query = select(ApprovalRule).where(or_(ApprovalRule.client_code == user.client_code, ApprovalRule.client_code.is_(None)))
    rows = (await session.execute(query)).scalars().all()
    return [_approval_rule_out(r) for r in rows]


@router.post("/approval-rules")
async def create_approval_rule(body: ApprovalRuleIn, session: DbSession, user: AdminUser):
    rule = ApprovalRule(**body.model_dump(), client_code=user.client_code)
    session.add(rule)
    await session.commit()
    return _approval_rule_out(rule)


@router.put("/approval-rules/{rule_id}")
async def update_approval_rule(rule_id: uuid.UUID, body: ApprovalRuleIn, session: DbSession, user: AdminUser):
    rule = (
        await session.execute(select(ApprovalRule).where(ApprovalRule.id == rule_id, ApprovalRule.client_code == user.client_code))
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(404, "rule not found")
    for k, v in body.model_dump().items():
        setattr(rule, k, v)
    await session.commit()
    return _approval_rule_out(rule)


@router.delete("/approval-rules/{rule_id}", status_code=204)
async def delete_approval_rule(rule_id: uuid.UUID, session: DbSession, user: AdminUser):
    rule = (
        await session.execute(select(ApprovalRule).where(ApprovalRule.id == rule_id, ApprovalRule.client_code == user.client_code))
    ).scalar_one_or_none()
    if rule is not None:
        await session.delete(rule)
        await session.commit()


def _fiscal_period_out(p: FiscalPeriod) -> dict:
    return {
        "id": str(p.id), "client_code": p.client_code, "period_key": p.period_key,
        "start_date": p.start_date.isoformat(), "end_date": p.end_date.isoformat(),
        "status": p.status, "closed_at": p.closed_at.isoformat() if p.closed_at else None,
    }


@router.get("/fiscal-periods")
async def list_fiscal_periods(session: DbSession, user: AdminUser):
    # Scoped to the admin's own active org, same as everywhere else in this
    # app — an admin managing another org's fiscal calendar switches into
    # it first (the same workflow every other cross-org action already
    # requires), rather than this endpoint trusting an arbitrary
    # caller-supplied client_code and returning/mutating a different
    # tenant's period calendar. `CurrentUser` only ever carries the active
    # session's own client_code, never a full membership list, so "scope to
    # user.client_code" is the only value this endpoint can trust.
    query = select(FiscalPeriod).where(FiscalPeriod.client_code == user.client_code).order_by(FiscalPeriod.period_key)
    rows = (await session.execute(query)).scalars().all()
    return [_fiscal_period_out(p) for p in rows]


class GenerateYearIn(BaseModel):
    year: int


@router.post("/fiscal-periods/generate-year")
async def generate_fiscal_year(body: GenerateYearIn, session: DbSession, user: AdminUser):
    """Creates the 12 open calendar-month periods for the admin's own
    active org/year in one call — the same shape the 0008 migration seeds
    for ORG1/2026, just reachable for every other year an admin adds
    later. Always the caller's own org (see list_fiscal_periods) — an
    admin generating periods for a *different* client switches into it
    first."""
    existing = (
        await session.execute(
            select(FiscalPeriod).where(
                FiscalPeriod.client_code == user.client_code, FiscalPeriod.period_key.startswith(f"{body.year:04d}-")
            )
        )
    ).scalars().all()
    if existing:
        raise HTTPException(409, f"fiscal year {body.year} already has periods for client '{user.client_code}'")
    created = []
    for month in range(1, 13):
        last_day = calendar.monthrange(body.year, month)[1]
        period = FiscalPeriod(
            client_code=user.client_code,
            period_key=f"{body.year:04d}-{month:02d}",
            start_date=date(body.year, month, 1),
            end_date=date(body.year, month, last_day),
        )
        session.add(period)
        created.append(period)
    await session.commit()
    return [_fiscal_period_out(p) for p in created]


@router.post("/fiscal-periods/{period_id}/close")
async def close_fiscal_period(period_id: uuid.UUID, session: DbSession, user: AdminUser):
    # Closing a period is a real financial control action (blocks further
    # postings into it) — without this filter, an admin whose only actual
    # membership is ORG1 could close/reopen ORG2's calendar outright.
    period = (
        await session.execute(select(FiscalPeriod).where(FiscalPeriod.id == period_id, FiscalPeriod.client_code == user.client_code))
    ).scalar_one_or_none()
    if period is None:
        raise HTTPException(404, "period not found")
    period.status = "closed"
    period.closed_by = uuid.UUID(user.id)
    period.closed_at = datetime.now(timezone.utc)
    await session.commit()
    return _fiscal_period_out(period)


@router.post("/fiscal-periods/{period_id}/reopen")
async def reopen_fiscal_period(period_id: uuid.UUID, session: DbSession, user: AdminUser):
    period = (
        await session.execute(select(FiscalPeriod).where(FiscalPeriod.id == period_id, FiscalPeriod.client_code == user.client_code))
    ).scalar_one_or_none()
    if period is None:
        raise HTTPException(404, "period not found")
    period.status = "open"
    period.closed_by = None
    period.closed_at = None
    await session.commit()
    return _fiscal_period_out(period)


@router.post("/users/{user_id}/force-logout")
async def force_logout(user_id: uuid.UUID, _: AdminUser):
    """Revokes every live session belonging to this user. Sessions are only
    ever tracked by jti->user_id in Valkey, not enumerable by user_id, so
    this instead bumps a per-user "sessions issued before this instant are
    void" marker that get_current_user checks — simpler than scanning
    Valkey keys, and works even for keys this process never touched."""
    await cache.revoke_all_sessions_for_user(str(user_id))
    return {"ok": True}
