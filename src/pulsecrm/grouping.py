"""Message grouping (debounce).

Bursts of consecutive messages from the same author within a short window are
treated as one unit of thought, so the classifier reasons over a complete
message rather than firing on every line.

``group_events`` is a pure function — given the same events it always returns
the same groups — which makes it trivial to unit-test and to run over a finite
batch (the offline reference path) or a micro-batch (a streaming source).
"""

from __future__ import annotations

from pulsecrm.models import MessageGroup, RawEvent


def group_events(
    events: list[RawEvent],
    *,
    window_seconds: int = 60,
    max_group_size: int = 20,
) -> list[MessageGroup]:
    """Split events into per-author bursts.

    A new group starts when the author changes, when the gap to the previous
    message from that author exceeds ``window_seconds``, or when the current
    group reaches ``max_group_size``. Groups are returned in the order their
    first message appeared.
    """
    if not events:
        return []

    ordered = sorted(events, key=lambda e: e.created_at)

    # open group per author
    open_groups: dict[str, list[RawEvent]] = {}
    last_ts: dict[str, float] = {}
    finished: list[tuple[float, list[RawEvent]]] = []  # (first_ts, events)

    def close(author_id: str) -> None:
        evs = open_groups.pop(author_id, None)
        if evs:
            finished.append((evs[0].created_at.timestamp(), evs))
        last_ts.pop(author_id, None)

    for ev in ordered:
        aid = ev.author_id
        ts = ev.created_at.timestamp()
        if aid in open_groups:
            gap = ts - last_ts[aid]
            if gap > window_seconds or len(open_groups[aid]) >= max_group_size:
                close(aid)
        open_groups.setdefault(aid, [])
        open_groups[aid].append(ev)
        last_ts[aid] = ts

    for aid in list(open_groups):
        close(aid)

    finished.sort(key=lambda pair: pair[0])

    groups: list[MessageGroup] = []
    for _first_ts, evs in finished:
        head = evs[0]
        groups.append(
            MessageGroup(
                author_id=head.author_id,
                author_display_name=head.author_display_name,
                author_handle=head.author_handle,
                events=evs,
            )
        )
    return groups


class Grouper:
    """Thin configurable wrapper around :func:`group_events`."""

    def __init__(self, window_seconds: int = 60, max_group_size: int = 20):
        self.window_seconds = window_seconds
        self.max_group_size = max_group_size

    def group_events(self, events: list[RawEvent]) -> list[MessageGroup]:
        return group_events(
            events,
            window_seconds=self.window_seconds,
            max_group_size=self.max_group_size,
        )
