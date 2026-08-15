"""Admin config surface for AUTO_NUMBER fields: prefix/pad width/reset
policy per (module, field). Not a generic module — same tier as Role/User
admin — because it's keyed against a live module+field pair rather than
being a shape FieldMetadata can express on its own.

A field can go a while with no number_series row at all: the counter is
created lazily on first allocation (see repository._allocate_number_series)
with defaults (prefix="", pad_width=5, reset_policy="never"). This router
lets an admin see and edit that config before or after that first use —
GET returns the defaults when nothing's been allocated yet rather than 404,
and PUT upserts against whichever period is currently active so an edit
never collides with the counter allocation's own row-locking.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from metaforge_api.api.deps import AdminUser, DbSession
from metaforge_api.domain.number_series import current_period_key

router = APIRouter(prefix="/api/admin/number-series", tags=["admin"])

_DEFAULTS = {"prefix": "", "pad_width": 5, "reset_policy": "never", "next_value": 1}


class NumberSeriesIn(BaseModel):
    prefix: str = ""
    pad_width: int = 5
    reset_policy: str = "never"


@router.get("/{module}/{field}")
async def get_number_series(module: str, field: str, session: DbSession, user: AdminUser):
    row = (
        await session.execute(
            text(
                "SELECT prefix, pad_width, reset_policy, next_value FROM number_series "
                "WHERE client_code = :c AND module = :m AND field = :f ORDER BY id DESC LIMIT 1"
            ),
            {"c": user.client_code, "m": module, "f": field},
        )
    ).mappings().first()
    return dict(row) if row else dict(_DEFAULTS)


@router.put("/{module}/{field}")
async def set_number_series(module: str, field: str, body: NumberSeriesIn, session: DbSession, user: AdminUser):
    period_key = current_period_key(body.reset_policy)
    await session.execute(
        text(
            "INSERT INTO number_series (client_code, module, field, period_key, prefix, pad_width, reset_policy) "
            "VALUES (:c, :m, :f, :p, :prefix, :pad, :policy) "
            "ON CONFLICT (client_code, module, field, period_key) "
            "DO UPDATE SET prefix = :prefix, pad_width = :pad, reset_policy = :policy"
        ),
        {"c": user.client_code, "m": module, "f": field, "p": period_key, "prefix": body.prefix, "pad": body.pad_width, "policy": body.reset_policy},
    )
    await session.commit()
    row = (
        await session.execute(
            text(
                "SELECT prefix, pad_width, reset_policy, next_value FROM number_series "
                "WHERE client_code = :c AND module = :m AND field = :f AND period_key = :p"
            ),
            {"c": user.client_code, "m": module, "f": field, "p": period_key},
        )
    ).mappings().one()
    return dict(row)
