"""Org-scoped admin surface — everything here is gated by require_system
(a role capability, not is_admin) and hard-filtered to the caller's own
client_code. Deliberately a separate router from admin.py rather than
loosening that one: admin.py is the platform-admin surface (cross-org,
gated by is_admin only); this one is what an Org Admin role (see
provisioning.py's seeded role) can reach for their own org alone. See
deps.require_system's docstring for the permission primitive this runs on.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from metaforge_api.api.deps import CurrentUserDep, DbSession, require_system
from metaforge_api.infrastructure.models import AiSettingsOverride, OrgInvite, Role, User

router = APIRouter(prefix="/api/org", tags=["org-admin"])

_INVITE_TTL = timedelta(days=7)
# Curated set an org admin may hand out — never a role with is_admin or
# any system.* grant, so an org admin can never mint another platform
# admin or a peer with capabilities they don't themselves have reviewed.
_ASSIGNABLE_ROLE_NAMES = {"Org Admin", "Org Approver", "Org Operator", "Org Viewer"}


async def _assignable_roles(session: DbSession) -> list[Role]:
    rows = (await session.execute(select(Role).where(Role.name.in_(_ASSIGNABLE_ROLE_NAMES)))).scalars().all()
    return list(rows)


# --------------------------------------------------------------------------
# Users in my org (read-only list here; invites are how new ones join)
# --------------------------------------------------------------------------


@router.get("/users", dependencies=[Depends(require_system("org_users"))])
async def list_org_users(session: DbSession, user: CurrentUserDep):
    rows = (await session.execute(select(User))).scalars().all()
    return [
        {
            "id": str(u.id), "username": u.username, "display_name": u.display_name,
            "is_active": u.is_active, "role_names": [r.name for r in u.roles],
        }
        for u in rows
        if user.client_code in {c.code for c in u.clients}
    ]


@router.post("/users/{user_id}/deactivate", dependencies=[Depends(require_system("org_users"))])
async def deactivate_org_user(user_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    row = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if row is None or user.client_code not in {c.code for c in row.clients}:
        raise HTTPException(404, "user not found in your organization")
    if str(row.id) == user.id:
        raise HTTPException(400, "cannot deactivate your own account")
    row.is_active = False
    await session.commit()
    return {"ok": True}


# --------------------------------------------------------------------------
# Invites
# --------------------------------------------------------------------------


class InviteIn(BaseModel):
    email: str
    role_name: str


def _invite_out(inv: OrgInvite, role_name: str) -> dict:
    return {
        "id": str(inv.id), "email": inv.email, "role_name": role_name, "status": inv.status,
        "expires_at": inv.expires_at.isoformat(), "created_at": inv.created_at.isoformat(),
    }


@router.get("/invites", dependencies=[Depends(require_system("org_users"))])
async def list_invites(session: DbSession, user: CurrentUserDep):
    rows = (
        await session.execute(
            select(OrgInvite, Role.name).join(Role, Role.id == OrgInvite.role_id).where(OrgInvite.client_code == user.client_code)
        )
    ).all()
    return [_invite_out(inv, role_name) for inv, role_name in rows]


@router.post("/invites", dependencies=[Depends(require_system("org_users"))])
async def create_invite(body: InviteIn, session: DbSession, user: CurrentUserDep):
    if body.role_name not in _ASSIGNABLE_ROLE_NAMES:
        raise HTTPException(400, f"role must be one of: {sorted(_ASSIGNABLE_ROLE_NAMES)}")
    role = (await session.execute(select(Role).where(Role.name == body.role_name))).scalar_one_or_none()
    if role is None:
        raise HTTPException(400, f"role '{body.role_name}' does not exist yet — ask a platform admin to seed it")
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "invalid email")

    existing = (
        await session.execute(
            select(OrgInvite).where(
                OrgInvite.client_code == user.client_code, OrgInvite.email == email, OrgInvite.status == "pending"
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.status = "revoked"  # re-inviting supersedes the old pending row

    invite = OrgInvite(
        client_code=user.client_code, email=email, role_id=role.id, invited_by=uuid.UUID(user.id),
        status="pending", expires_at=datetime.now(timezone.utc) + _INVITE_TTL,
    )
    session.add(invite)
    await session.commit()
    return _invite_out(invite, role.name)


@router.delete("/invites/{invite_id}", status_code=204, dependencies=[Depends(require_system("org_users"))])
async def revoke_invite(invite_id: uuid.UUID, session: DbSession, user: CurrentUserDep):
    invite = (
        await session.execute(select(OrgInvite).where(OrgInvite.id == invite_id, OrgInvite.client_code == user.client_code))
    ).scalar_one_or_none()
    if invite is not None and invite.status == "pending":
        invite.status = "revoked"
        await session.commit()


# --------------------------------------------------------------------------
# Per-org AI settings override
# --------------------------------------------------------------------------


def _override_out(row: AiSettingsOverride | None) -> dict:
    if row is None:
        return {
            "provider": None, "gemini_model": None, "openai_model": None,
            "gemini_key_set": False, "openai_key_set": False, "discount_tax_treatment": None,
        }
    return {
        "provider": row.provider,
        "gemini_model": row.gemini_model,
        "openai_model": row.openai_model,
        "gemini_key_set": bool(row.gemini_api_key),
        "openai_key_set": bool(row.openai_api_key),
        "discount_tax_treatment": row.discount_tax_treatment,
    }


class AiOverrideIn(BaseModel):
    provider: str | None = None
    gemini_api_key: str | None = None  # None = leave unchanged; "" = clear it (revert to platform default)
    gemini_model: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    discount_tax_treatment: str | None = None


@router.get("/ai-settings", dependencies=[Depends(require_system("ai_settings"))])
async def get_ai_override(session: DbSession, user: CurrentUserDep):
    row = (await session.execute(select(AiSettingsOverride).where(AiSettingsOverride.client_code == user.client_code))).scalar_one_or_none()
    return _override_out(row)


@router.put("/ai-settings", dependencies=[Depends(require_system("ai_settings"))])
async def set_ai_override(body: AiOverrideIn, session: DbSession, user: CurrentUserDep):
    row = (await session.execute(select(AiSettingsOverride).where(AiSettingsOverride.client_code == user.client_code))).scalar_one_or_none()
    if row is None:
        row = AiSettingsOverride(client_code=user.client_code)
        session.add(row)
    row.provider = body.provider or None
    row.gemini_model = body.gemini_model or None
    row.openai_model = body.openai_model or None
    row.discount_tax_treatment = body.discount_tax_treatment or None
    if body.gemini_api_key is not None:
        row.gemini_api_key = body.gemini_api_key or None
    if body.openai_api_key is not None:
        row.openai_api_key = body.openai_api_key or None
    await session.commit()
    return _override_out(row)
