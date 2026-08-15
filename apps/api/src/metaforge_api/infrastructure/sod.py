"""Basic Segregation-of-Duties (SoD) conflict detection.

Two enforcement points, both driven by the same `sod_conflict_rules` table
(see models.SodConflictRule):

- **Action time** (`check`): before a mutating write goes through, has this
  *same actor* already performed the rule's `action_a` on the linked
  record? Queries `audit_log` — already written on every create/update/
  delete/transition — rather than tracking anything new.
- **Assignment time** (`check_assignment`): would granting this role set
  make a user *capable* of both sides of a rule at once (e.g. both editing
  a vendor's bank details and creating payments)? Pure permissions-matrix
  check, no DB query beyond the rules themselves.

Deliberately not a general authorization engine — every rule is exactly
"action_a on module_a, by the same actor, conflicts with action_b on
module_b", optionally cross-module via `link_field`. Extended SoD/ABAC was
explicitly descoped for phase 1.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.infrastructure.models import AuditLog, SodConflictRule


def _action_matches(action_row: str, changes: dict | None, pattern: str) -> bool:
    """Does a historical audit_log row satisfy an action_a pattern?
    "transition:<status>" matches a `transition` row whose changes contain
    any field that moved `new` to that status — the status field's name
    varies per module, so every value in `changes` is checked rather than
    assuming a fixed key."""
    if pattern.startswith("transition:"):
        target = pattern.split(":", 1)[1]
        if action_row != "transition" or not changes:
            return False
        return any(isinstance(v, dict) and v.get("new") == target for v in changes.values())
    return action_row == pattern


async def _prior_action_exists(
    session: AsyncSession, module: str, record_id: uuid.UUID, actor_id: uuid.UUID, pattern: str
) -> bool:
    rows = (
        await session.execute(
            select(AuditLog).where(
                AuditLog.module == module, AuditLog.record_id == record_id, AuditLog.actor_id == actor_id
            )
        )
    ).scalars().all()
    return any(_action_matches(r.action, r.changes, pattern) for r in rows)


async def check(
    session: AsyncSession,
    *,
    module_name: str,
    action: str,
    actor_id: uuid.UUID | None,
    record_id: uuid.UUID | None,
    data: dict[str, Any] | None,
    current_record: dict[str, Any] | None,
) -> list[str]:
    """Returns human-readable messages for every BLOCK-enforcement rule this
    write would violate (empty means clear — call site should proceed).
    WARN-enforcement matches never block; they're recorded as an
    `sod_warning` audit_log entry so they're visible in a record's history
    without stopping the write."""
    if actor_id is None:
        return []
    rules = (
        await session.execute(
            select(SodConflictRule).where(
                SodConflictRule.is_active.is_(True), SodConflictRule.module_b == module_name
            )
        )
    ).scalars().all()
    blocking: list[str] = []
    for rule in rules:
        if rule.action_b != action:
            continue
        if rule.link_field:
            link_value = None
            if data is not None and rule.link_field in data:
                link_value = data[rule.link_field]
            elif current_record is not None:
                link_value = current_record.get(rule.link_field)
            if link_value is None:
                continue
            try:
                record_id_a = link_value if isinstance(link_value, uuid.UUID) else uuid.UUID(str(link_value))
            except ValueError:
                continue
        else:
            if rule.module_a != module_name or record_id is None:
                continue
            record_id_a = record_id

        if not await _prior_action_exists(session, rule.module_a, record_id_a, actor_id, rule.action_a):
            continue

        message = (
            f"SoD conflict ('{rule.name}'): you already performed '{rule.action_a}' on {rule.module_a} "
            f"for this record — cannot also perform '{rule.action_b}' on {rule.module_b}"
        )
        if rule.enforcement == "block":
            blocking.append(message)
        else:
            session.add(
                AuditLog(
                    module=module_name,
                    record_id=record_id or record_id_a,
                    action="sod_warning",
                    actor_id=actor_id,
                    changes={"rule": rule.name, "message": message},
                )
            )
    return blocking


def _required_permission(action_pattern: str) -> str:
    """A workflow transition is gated by the "update" permission (see
    data.py's CanUpdate on /transition), so that's what an assignment-time
    capability check needs to test for a "transition:*" pattern. Every
    other pattern ("create"/"update"/"delete") already *is* the permission
    name it needs."""
    if action_pattern.startswith("transition:"):
        return "update"
    return action_pattern


def check_assignment(module_permissions: dict, rules: list[SodConflictRule]) -> list[str]:
    """Would this merged permission set make a user capable of both sides
    of any BLOCK rule at once? Pure function — the caller (admin.py) already
    has the merged module_permissions and the rule list."""
    violations: list[str] = []
    for rule in rules:
        if not rule.is_active or rule.enforcement != "block":
            continue
        has_a = bool(module_permissions.get(rule.module_a, {}).get(_required_permission(rule.action_a)))
        has_b = bool(module_permissions.get(rule.module_b, {}).get(_required_permission(rule.action_b)))
        if has_a and has_b:
            violations.append(
                f"SoD conflict ('{rule.name}'): this role set grants both '{rule.action_a}' on {rule.module_a} "
                f"and '{rule.action_b}' on {rule.module_b}"
            )
    return violations
