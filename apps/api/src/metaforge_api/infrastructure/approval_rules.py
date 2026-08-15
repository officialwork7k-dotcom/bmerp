"""Approval routing: WHO is authorized to approve a given transition, and
whether a given record even needs approval at all.

Previously `approval_requests` (see api/routers/approvals.py) only ever got
used as a fallback for users with zero `update` permission on a module, and
"who decides" was hardcoded to "any admin" — a pure RBAC accident, not a
business control. `approval_rules` (see models.ApprovalRule) makes both
questions configurable: a rule targets a (module, to_status) transition,
names the role required to decide it, and can optionally gate on an amount
threshold read straight off the record (`amount_field`/`min_amount`) for
tiered approval — small documents post straight through, large ones need a
named role's sign-off regardless of who's holding the pen.

Once a rule matches, the transition is *always* routed through the request/
decide queue — even for a user who holds the approver role themselves —
so every gated transition leaves a real ApprovalRequest row (requested_by/
decided_by/decided_at) tied to that one document. This is the "four-eyes"
choice: self-transitioning past a configured approval gate is never
allowed, only deciding someone else's request is.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.infrastructure.models import ApprovalRule, User


class ApprovalRequiredError(Exception):
    def __init__(self, message: str, rule_id: uuid.UUID):
        super().__init__(message)
        self.rule_id = rule_id


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


async def find_matching_rule(
    session: AsyncSession, *, client_code: str | None, module_name: str, to_status: str, record: dict[str, Any]
) -> ApprovalRule | None:
    """The rule (if any) gating this transition for this specific record.
    Scoped to this client or a global rule (client_code IS NULL). When
    several rules target the same (module, to_status) at different
    thresholds, the highest threshold the record still clears wins — a
    record can only ever be one tier's problem, the strictest one it
    qualifies for."""
    query = select(ApprovalRule).where(
        ApprovalRule.module == module_name,
        ApprovalRule.to_status == to_status,
        ApprovalRule.is_active.is_(True),
        or_(ApprovalRule.client_code == client_code, ApprovalRule.client_code.is_(None)),
    )
    rules = (await session.execute(query)).scalars().all()
    matching = []
    for rule in rules:
        if rule.amount_field:
            value = _to_decimal(record.get(rule.amount_field))
            if rule.min_amount is not None and value < rule.min_amount:
                continue
        matching.append(rule)
    if not matching:
        return None
    matching.sort(key=lambda r: (r.min_amount is not None, r.min_amount or Decimal("0")), reverse=True)
    return matching[0]


async def actor_can_decide(session: AsyncSession, *, actor_id: uuid.UUID, rule: ApprovalRule) -> bool:
    """True if the actor holds the rule's approver role — or is an admin,
    since role-routing is meant to narrow who else can decide something,
    never to lock admins out of their own instance."""
    user = (await session.execute(select(User).where(User.id == actor_id))).scalar_one_or_none()
    if user is None:
        return False
    if any(r.is_admin for r in user.roles):
        return True
    return any(r.id == rule.approver_role_id for r in user.roles)


async def eligible_role_ids_for_user(session: AsyncSession, actor_id: uuid.UUID) -> set[uuid.UUID]:
    """This user's own role ids, for filtering the pending-approvals list to
    'requests I'm actually allowed to decide' without a role check per row."""
    user = (await session.execute(select(User).where(User.id == actor_id))).scalar_one_or_none()
    if user is None:
        return set()
    return {r.id for r in user.roles}
