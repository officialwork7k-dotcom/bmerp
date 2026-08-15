"""infrastructure/chat_service.py's deterministic master-data check —
formatting-only cases that don't need a live DB (the found/not-found
branches themselves are exercised against the real dev DB in this
session's manual verification, matching this repo's existing test-suite
convention of pure-logic tests only, see test_telegram_link_service.py)."""

import asyncio

from metaforge_api.infrastructure.chat_service import _master_data_check


def test_not_applicable_when_direction_unknown_and_no_lines():
    result = asyncio.run(_master_data_check(None, None, None, {"doc_direction": "unknown", "line_items": []}))
    assert result == "Master data check: not applicable"
