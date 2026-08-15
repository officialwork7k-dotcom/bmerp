"""Fuzzy (typo/partial/punctuation-tolerant) text matching against a
dynamic module's table, backed by Postgres pg_trgm — see migration
f4d8e2a917cc for the extension + GIN trigram indexes this relies on.

Built for the AI receipt-scan master-data check (infrastructure/
chat_service.py's `_master_data_check`): a photographed document's
vision-extracted vendor/item text commonly has spelling mistakes, extra
or missing punctuation, or is only a partial name ("Diesel Fuel" for a
master record named "Diesel Fuel - Premium Grade (Bulk)"). A plain
`ILIKE '%query%'` substring check misses all of that except the partial-
name case. This is a generic capability, not chat-specific — any future
feature needing "did you mean X?" style lookup can reuse it.

No LLM involved: this is a single ranked SQL query per call, sub-
millisecond at the row counts a tenant's master data realistically
reaches (GIN trigram probe on a few hundred-to-thousand rows).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from metaforge_api.infrastructure.dynamic_tables import resolve_table

# Looser than pg_trgm's own 0.6 default — a typo'd partial match (e.g. OCR
# mangling one word of a multi-word item name) should still clear the WHERE
# gate; the final min_similarity cutoff on the combined score is what
# actually decides whether a candidate is worth surfacing.
_WORD_SIMILARITY_THRESHOLD = 0.50


def _escape_like(raw: str) -> str:
    # A literal '%' or '_' in OCR'd text (e.g. "100% Cotton") must not act
    # as a LIKE wildcard.
    return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def fuzzy_search(
    session: AsyncSession,
    registry,
    repo,
    *,
    module_name: str,
    field_name: str,
    query: str,
    limit: int = 3,
    min_similarity: float = 0.30,
) -> list[dict[str, Any]]:
    """Returns up to `limit` candidates, best match first, each
    `{"id": str, "label": str, "score": float in (0, 1]}`. Empty list for
    an unknown module/field, a blank query, or nothing scoring above
    `min_similarity`. Scoped to `repo.client_code` and excludes soft-
    deleted rows, same as every other read in this app.

    Combines three pg_trgm signals into one ranked query rather than a
    plain substring check:
    - similarity(a, b): whole-string trigram overlap — catches typos and
      punctuation variance on comparably-sized strings.
    - word_similarity(query, field): how well the query matches the BEST
      substring of the field — the principled fix for "short query
      inside a long field name" (e.g. "Diesel Fuel" inside "Diesel Fuel -
      Premium Grade (Bulk)" scores ~1.0 here), and unlike a plain LIKE
      check, this still works when that partial match itself has a typo.
    - word_similarity(field, query): the reverse direction, for a short
      master-data name appearing inside longer noisy extracted text.
    The forward/reverse word_similarity signals are weighted 0.95/0.90 so
    a partial-substring match never outranks a genuine near-exact
    whole-name match.
    """
    q = " ".join((query or "").split())
    if not q:
        return []
    try:
        module = registry.get(module_name)
    except KeyError:
        return []
    table = resolve_table(module, registry)
    if field_name not in table.c:
        return []

    col = table.c[field_name]
    lower_col = func.lower(col)
    lower_q = func.lower(q)

    score_expr = func.greatest(
        func.similarity(lower_col, lower_q),
        func.word_similarity(lower_q, lower_col) * 0.95,
        func.word_similarity(lower_col, lower_q) * 0.90,
    )
    like_pattern = f"%{_escape_like(q)}%"
    where_clause = or_(
        lower_col.op("%")(lower_q),
        lower_q.op("<%")(lower_col),
        lower_col.like(like_pattern, escape="\\"),
    )
    stmt = (
        select(table.c.id, col.label("label"), score_expr.label("score"))
        .where(table.c.deleted_at.is_(None), table.c.client_code == repo.client_code, where_clause)
        .order_by(score_expr.desc(), lower_col.asc(), table.c.id.asc())
        .limit(limit)
    )

    # SET LOCAL so both thresholds only affect this query, not the rest of
    # the (shared) session's transaction. min_similarity/threshold values
    # are internal floats, never user input, so direct interpolation here
    # is safe (no bind-param support for GUC values via SET).
    await session.execute(text(f"SET LOCAL pg_trgm.similarity_threshold = {min_similarity}"))
    await session.execute(text(f"SET LOCAL pg_trgm.word_similarity_threshold = {_WORD_SIMILARITY_THRESHOLD}"))
    rows = (await session.execute(stmt)).mappings().all()

    results = []
    for r in rows:
        score = float(r["score"])
        if score < min_similarity:
            continue
        results.append({"id": str(r["id"]), "label": str(r["label"]), "score": round(score, 2)})
    return results
