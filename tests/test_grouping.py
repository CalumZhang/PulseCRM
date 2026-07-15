from datetime import UTC, datetime, timedelta

from pulsecrm.grouping import group_events
from pulsecrm.models import RawEvent

BASE = datetime(2026, 6, 3, 10, 0, 0, tzinfo=UTC)


def _ev(author, secs, content="hi", eid=None):
    return RawEvent(
        event_id=eid or f"{author}-{secs}",
        author_id=author,
        content=content,
        created_at=BASE + timedelta(seconds=secs),
    )


def test_empty():
    assert group_events([]) == []


def test_single_author_burst_is_one_group():
    evs = [_ev("a", 0), _ev("a", 10), _ev("a", 20)]
    groups = group_events(evs, window_seconds=60)
    assert len(groups) == 1
    assert len(groups[0].events) == 3
    assert groups[0].author_id == "a"


def test_gap_exceeding_window_splits():
    evs = [_ev("a", 0), _ev("a", 200)]  # 200s > 60s window
    groups = group_events(evs, window_seconds=60)
    assert len(groups) == 2


def test_different_authors_split():
    evs = [_ev("a", 0), _ev("b", 5), _ev("a", 10)]
    groups = group_events(evs, window_seconds=60)
    # a's two messages within window stay together; b is separate
    by_author = {g.author_id: g for g in groups}
    assert len(by_author["a"].events) == 2
    assert len(by_author["b"].events) == 1


def test_max_group_size():
    evs = [_ev("a", i) for i in range(5)]
    groups = group_events(evs, window_seconds=600, max_group_size=2)
    assert all(len(g.events) <= 2 for g in groups)
    assert sum(len(g.events) for g in groups) == 5


def test_combined_text_and_helpers():
    evs = [_ev("a", 0, "one"), _ev("a", 5, "two")]
    g = group_events(evs)[0]
    assert g.texts == ["one", "two"]
    assert g.combined_text == "one\ntwo"
    assert g.last.content == "two"
