"""infrastructure/telegram_api.py — only the token-scrubbing behavior is
tested here without a live bot; the actual HTTP calls (getUpdates/
sendMessage/getFile) are exercised in the manual end-to-end pass since
they need a real bot token."""

from metaforge_api.infrastructure.telegram_api import _scrub


def test_scrub_removes_token_from_error_text():
    token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    msg = f"error calling bot{token}/getUpdates: 404"
    assert token not in _scrub(msg, token)
    assert "bot***" in _scrub(msg, token)


def test_scrub_is_noop_without_token():
    assert _scrub("some message", "") == "some message"
