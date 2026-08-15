"""Generic approval queue: a request to move one record from one workflow
status to another. WHO may decide a request is no longer "any admin" —
see infrastructure/approval_rules.py: if an `ApprovalRule` matches the
request's (module, to_status, record), only someone holding that rule's
role (or an admin) may decide it; a request with no matching rule (e.g. the
RBAC-permission fallback in WorkflowBar.svelte, or a rule deleted after the
request was filed) still falls back to admin-only, preserving the original
behavior for anything not explicitly routed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from metaforge_api.api.deps import CurrentUserDep, DbSession, Repository
from metaforge_api.infrastructure import approval_rules
from metaforge_api.infrastructure.models import ApprovalRequest, AuditLog, Notification, Role, User

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class ApprovalRequestIn(BaseModel):
    module: str
    record_id: uuid.UUID
    from_status: str
    to_status: str
    note: str | None = None


def _out(a: ApprovalRequest) -> dict:
    return {
        "id": str(a.id),
        "module": a.module,
        "record_id": str(a.record_id),
        "from_status": a.from_status,
        "to_status": a.to_status,
        "status": a.status,
        "note": a.note,
        "requested_by": str(a.requested_by),
        "decided_by": str(a.decided_by) if a.decided_by else None,
        "created_at": a.created_at.isoformat(),
        "decided_at": a.decided_at.isoformat() if a.decided_at else None,
    }


async def _notify_eligible_approvers(
    session: DbSession, *, approval: ApprovalRequest, repo: Repository, requester_name: str
) -> None:
    """Proactive nudge at request-creation time (decision-time notification
    to the requester already existed; nobody was ever told a request was
    waiting on THEM). Notifies every user holding the matching rule's role,
    scoped to this client — or every admin in this client if no rule
    matches, so an ungoverned request is still someone's problem to see."""
    record = await repo.get(approval.module, approval.record_id)
    rule = None
    if record is not None:
        rule = await approval_rules.find_matching_rule(
            session, client_code=approval.client_code, module_name=approval.module, to_status=approval.to_status, record=record
        )
    query = select(User).join(User.roles).where(Role.is_admin.is_(True))
    if rule is not None:
        query = select(User).join(User.roles).where(Role.id == rule.approver_role_id)
    if approval.client_code is not None:
        from metaforge_api.infrastructure.models import user_clients

        query = query.where(User.id.in_(select(user_clients.c.user_id).where(user_clients.c.client_code == approval.client_code)))
    approvers = (await session.execute(query)).scalars().unique().all()
    for u in approvers:
        if u.id == approval.requested_by:
            continue
        session.add(
            Notification(
                user_id=u.id,
                client_code=approval.client_code,
                title="Approval requested",
                body=f"{requester_name} requested {approval.module} → {approval.to_status}" + (f": {approval.note}" if approval.note else ""),
                link=f"/{approval.module}/{approval.record_id}",
            )
        )


@router.post("")
async def request_approval(body: ApprovalRequestIn, session: DbSession, user: CurrentUserDep, repo: Repository):
    approval = ApprovalRequest(
        client_code=user.client_code,
        module=body.module,
        record_id=body.record_id,
        from_status=body.from_status,
        to_status=body.to_status,
        requested_by=uuid.UUID(user.id),
        note=body.note,
    )
    session.add(approval)
    await session.flush()
    # Filing a request is itself an event worth seeing on the record's own
    # History panel, not just something that shows up retroactively once a
    # decision lands (the transition it eventually produces) — otherwise a
    # record sitting in "pending approval" for days shows no trace of that.
    session.add(
        AuditLog(
            module=approval.module,
            record_id=approval.record_id,
            action="approval_requested",
            actor_id=approval.requested_by,
            changes={"to_status": approval.to_status, "note": approval.note},
        )
    )
    await _notify_eligible_approvers(session, approval=approval, repo=repo, requester_name=user.display_name)
    await session.commit()
    return _out(approval)


@router.get("/pending")
async def list_pending(session: DbSession, user: CurrentUserDep, repo: Repository):
    """Admins see every pending request in their client; everyone else sees
    only requests whose matching ApprovalRule names a role they hold (an
    ungoverned request — no rule matches — is admin-only, same as before
    this routing existed)."""
    query = select(ApprovalRequest).where(ApprovalRequest.status == "pending").order_by(ApprovalRequest.created_at)
    if user.client_code is not None:
        from sqlalchemy import or_

        query = query.where(or_(ApprovalRequest.client_code == user.client_code, ApprovalRequest.client_code.is_(None)))
    rows = (await session.execute(query)).scalars().all()

    if user.is_admin:
        return [_out(a) for a in rows]

    my_role_ids = await approval_rules.eligible_role_ids_for_user(session, uuid.UUID(user.id))
    visible = []
    for a in rows:
        record = await repo.get(a.module, a.record_id)
        if record is None:
            continue
        rule = await approval_rules.find_matching_rule(
            session, client_code=a.client_code, module_name=a.module, to_status=a.to_status, record=record
        )
        if rule is not None and rule.approver_role_id in my_role_ids:
            visible.append(a)
    return [_out(a) for a in visible]


@router.get("/history")
async def list_history(session: DbSession, user: CurrentUserDep, limit: int = 50):
    """Decided requests (approved/rejected) — once decide() runs, a request
    drops out of /pending forever with no other trace in the UI besides the
    record's own History panel. Admins see everything in their client;
    everyone else sees only requests they filed or personally decided."""
    from sqlalchemy import or_

    query = select(ApprovalRequest).where(ApprovalRequest.status != "pending").order_by(ApprovalRequest.decided_at.desc()).limit(min(limit, 200))
    if user.client_code is not None:
        query = query.where(or_(ApprovalRequest.client_code == user.client_code, ApprovalRequest.client_code.is_(None)))
    if not user.is_admin:
        actor_id = uuid.UUID(user.id)
        query = query.where(or_(ApprovalRequest.requested_by == actor_id, ApprovalRequest.decided_by == actor_id))
    rows = (await session.execute(query)).scalars().all()
    return [_out(a) for a in rows]


class DecisionIn(BaseModel):
    approve: bool
    note: str | None = None


@router.post("/{approval_id}/decide")
async def decide(approval_id: uuid.UUID, body: DecisionIn, session: DbSession, repo: Repository, user: CurrentUserDep):
    # Same org-boundary check /pending and /history already apply — without
    # it, an *admin* (the one caller that skips the role/rule check below
    # entirely) could approve or reject another org's request outright.
    # A non-admin is incidentally safe today since repo.get() below is
    # already client_code-scoped and returns None for another org's
    # record, but that's a side effect of a different check, not something
    # this endpoint should rely on.
    query = select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
    if user.client_code is not None:
        from sqlalchemy import or_

        query = query.where(or_(ApprovalRequest.client_code == user.client_code, ApprovalRequest.client_code.is_(None)))
    approval = (await session.execute(query)).scalar_one_or_none()
    if approval is None:
        raise HTTPException(404, "approval request not found")
    if approval.status != "pending":
        raise HTTPException(409, "already decided")

    actor_id = uuid.UUID(user.id)
    if not user.is_admin:
        record = await repo.get(approval.module, approval.record_id)
        rule = (
            await approval_rules.find_matching_rule(
                session, client_code=approval.client_code, module_name=approval.module, to_status=approval.to_status, record=record
            )
            if record is not None
            else None
        )
        allowed = rule is not None and await approval_rules.actor_can_decide(session, actor_id=actor_id, rule=rule)
        if not allowed:
            raise HTTPException(403, "you are not an authorized approver for this request")

    approval.status = "approved" if body.approve else "rejected"
    approval.decided_by = actor_id
    approval.decided_at = datetime.now(timezone.utc)
    approval.note = body.note or approval.note

    if body.approve:
        try:
            await repo.transition(
                approval.module, approval.record_id, approval.to_status,
                actor_id=actor_id, note="approved", bypass_approval_gate=True,
            )
        except (PermissionError, ValueError, LookupError) as exc:
            raise HTTPException(409, str(exc)) from None
    else:
        # A rejection never calls transition() — the record stays exactly
        # where it was — so without its own entry a rejected request would
        # leave no trace at all in the record's history, only the earlier
        # "approval_requested" line with no resolution ever shown.
        session.add(
            AuditLog(
                module=approval.module,
                record_id=approval.record_id,
                action="approval_rejected",
                actor_id=actor_id,
                changes={"to_status": approval.to_status, "note": approval.note},
            )
        )

    session.add(
        Notification(
            user_id=approval.requested_by,
            client_code=approval.client_code,
            title=f"Approval {'granted' if body.approve else 'rejected'}",
            body=f"{approval.module} → {approval.to_status}" + (f": {body.note}" if body.note else ""),
            link=f"/{approval.module}/{approval.record_id}",
        )
    )
    await session.commit()
    return _out(approval)
