"""infrastructure/telegram_link_service.py — only the pure code-generation
helper is unit-tested here; generate_link_code/consume_link_code/unlink
all need a live DB session and are exercised in the manual end-to-end
pass instead (this repo's existing test suite has no DB-fixture
precedent — see the other test_*.py files, all pure-logic)."""

from metaforge_api.infrastructure.telegram_link_service import _CODE_ALPHABET, _CODE_LENGTH, _generate_code


def test_generated_code_has_expected_length():
    assert len(_generate_code()) == _CODE_LENGTH == 8


def test_generated_code_uses_unambiguous_alphabet_only():
    code = _generate_code()
    assert all(c in _CODE_ALPHABET for c in code)
    # 0/O/1/I are excluded — they're the classic "read aloud and mistype" pairs.
    assert not set(code) & {"0", "O", "1", "I"}


def test_generated_codes_are_not_trivially_predictable():
    codes = {_generate_code() for _ in range(200)}
    assert len(codes) == 200  # no collisions across 200 draws from a big keyspace
