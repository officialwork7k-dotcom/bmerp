"""infrastructure/fuzzy_match.py — only the pure LIKE-escaping helper is
unit-tested here without a live DB; fuzzy_search()'s actual ranking
behavior (typo/partial/case/tenant-isolation) needs a real Postgres with
pg_trgm and was verified live against the dev DB instead — this repo's
existing test suite has no DB-fixture precedent (see test_telegram_link_
service.py's docstring for the same reasoning)."""

from metaforge_api.infrastructure.fuzzy_match import _escape_like


def test_escape_like_neutralizes_percent_and_underscore():
    assert _escape_like("100% Cotton_Blend") == "100\\% Cotton\\_Blend"


def test_escape_like_neutralizes_backslash_first():
    # Must escape backslashes before % / _ so an input backslash doesn't
    # accidentally combine with the escaping we just inserted.
    assert _escape_like("a\\b") == "a\\\\b"


def test_escape_like_noop_on_plain_text():
    assert _escape_like("Meridian Office Supplies") == "Meridian Office Supplies"
