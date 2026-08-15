"""infrastructure/chat_service.py's _format_fuzzy_hits — the pure
formatting logic turning fuzzy_search results into the FOUND/POSSIBLE/
NOT FOUND lines the model reads. No DB involved."""

from metaforge_api.infrastructure.chat_service import _format_fuzzy_hits


def test_no_hits_is_not_found():
    assert _format_fuzzy_hits("Counterparty 'X'", "vendors", []) == "Counterparty 'X': NOT FOUND in vendors"


def test_confident_top_hit_is_found_with_percent():
    hits = [{"id": "abc", "label": "Meridian Office Supplies", "score": 0.95}]
    result = _format_fuzzy_hits("Counterparty 'Meridian'", "vendors", hits)
    assert result == "Counterparty 'Meridian': FOUND -> vendors/abc 'Meridian Office Supplies' (95%)"


def test_exactly_at_threshold_counts_as_found():
    hits = [{"id": "abc", "label": "X", "score": 0.90}]
    assert _format_fuzzy_hits("Item 'x'", "items", hits).startswith("Item 'x': FOUND ->")


def test_imperfect_top_hit_is_possible_with_all_candidates():
    hits = [
        {"id": "id1", "label": "Meridian Office Supplies", "score": 0.78},
        {"id": "id2", "label": "Meridian Trading Co", "score": 0.55},
    ]
    result = _format_fuzzy_hits("Counterparty 'Meridian Ofice Suplies'", "vendors", hits)
    assert result == (
        "Counterparty 'Meridian Ofice Suplies': POSSIBLE matches -> "
        "vendors/id1 'Meridian Office Supplies' (78%); vendors/id2 'Meridian Trading Co' (55%)"
    )
