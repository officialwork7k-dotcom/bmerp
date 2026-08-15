from metaforge_api.infrastructure.models import SodConflictRule
from metaforge_api.infrastructure.sod import _action_matches, check_assignment


def _rule(**overrides) -> SodConflictRule:
    defaults = dict(
        name="test rule",
        module_a="vendors",
        action_a="update",
        module_b="payments",
        action_b="create",
        link_field="vendor_id",
        enforcement="block",
        is_active=True,
    )
    defaults.update(overrides)
    return SodConflictRule(**defaults)


def test_check_assignment_flags_capability_conflict():
    rule = _rule()
    perms = {"vendors": {"update": True}, "payments": {"create": True}}
    violations = check_assignment(perms, [rule])
    assert len(violations) == 1
    assert "test rule" in violations[0]


def test_check_assignment_clears_when_only_one_side_granted():
    rule = _rule()
    perms = {"vendors": {"update": True}, "payments": {"create": False}}
    assert check_assignment(perms, [rule]) == []


def test_check_assignment_ignores_warn_rules():
    rule = _rule(enforcement="warn")
    perms = {"vendors": {"update": True}, "payments": {"create": True}}
    assert check_assignment(perms, [rule]) == []


def test_check_assignment_ignores_inactive_rules():
    rule = _rule(is_active=False)
    perms = {"vendors": {"update": True}, "payments": {"create": True}}
    assert check_assignment(perms, [rule]) == []


def test_check_assignment_transition_pattern_maps_to_update_permission():
    rule = _rule(module_a="vendor_invoices", action_a="create", module_b="vendor_invoices", action_b="transition:approved", link_field=None)
    perms = {"vendor_invoices": {"create": True, "update": True}}
    violations = check_assignment(perms, [rule])
    assert len(violations) == 1


def test_action_matches_literal_action():
    assert _action_matches("create", None, "create") is True
    assert _action_matches("update", None, "create") is False


def test_action_matches_transition_pattern_checks_any_changed_field():
    changes = {"status": {"old": "draft", "new": "approved"}, "note": "looks good"}
    assert _action_matches("transition", changes, "transition:approved") is True
    assert _action_matches("transition", changes, "transition:rejected") is False


def test_action_matches_transition_pattern_requires_transition_action():
    changes = {"status": {"old": "draft", "new": "approved"}}
    assert _action_matches("update", changes, "transition:approved") is False
