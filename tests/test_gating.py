from pulsecrm.config import GatingConfig, _default_taxonomy
from pulsecrm.gating import Gate
from pulsecrm.models import Classification

TAXO = _default_taxonomy()


def make_gate(**kw):
    return Gate(GatingConfig(**kw), TAXO)


def test_actionable_intent_passes_all_gates():
    g = make_gate(confidence_threshold=0.65, require_staff_action=True)
    c = Classification(intent="bug_report", confidence=0.9, needs_staff_action=True)
    d = g.evaluate(c)
    assert d.actionable and d.reason == "ok"


def test_noise_intent_blocked():
    g = make_gate()
    c = Classification(intent="noise", confidence=0.99, needs_staff_action=True)
    assert not g.is_actionable(c)
    assert g.evaluate(c).reason.startswith("intent_not_actionable")


def test_below_confidence_blocked():
    g = make_gate(confidence_threshold=0.65)
    c = Classification(intent="bug_report", confidence=0.5, needs_staff_action=True)
    assert not g.is_actionable(c)
    assert g.evaluate(c).reason.startswith("below_confidence")


def test_no_staff_action_blocked_when_required():
    g = make_gate(require_staff_action=True)
    c = Classification(intent="bug_report", confidence=0.9, needs_staff_action=False)
    assert not g.is_actionable(c)
    assert g.evaluate(c).reason == "no_staff_action_needed"


def test_staff_action_not_required():
    g = make_gate(require_staff_action=False)
    c = Classification(intent="bug_report", confidence=0.9, needs_staff_action=False)
    assert g.is_actionable(c)


def test_ignored_authors():
    g = make_gate(ignored_authors=["staff_1"])
    assert g.is_ignored("staff_1")
    assert not g.is_ignored("user_2")


def test_none_classification():
    g = make_gate()
    assert not g.is_actionable(None)
