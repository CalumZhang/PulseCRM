"""linear ticket sink [STUB].

Skeleton for filing tickets as issues in Linear via its GraphQL API. Set
``LINEAR_API_KEY`` and a target ``team_id``.

Implement ``upsert`` with an ``issueCreate`` mutation, mapping Ticket -> issue
(title, description=body, priority, labels=component/feature). ``find_duplicate``
can search open issues by title/labels before creating.
"""

from __future__ import annotations

import os

from pulsecrm.models import Ticket
from pulsecrm.ports.ticket_sink import TicketSink
from pulsecrm.registry import register


@register("ticket_sink", "linear")
class LinearTicketSink(TicketSink):
    def __init__(self, api_key: str | None = None, team_id: str | None = None):
        self.api_key = api_key or os.environ.get("LINEAR_API_KEY")
        self.team_id = team_id or os.environ.get("LINEAR_TEAM_ID")

    @classmethod
    def build(cls, options: dict, ctx):  # noqa: ARG003
        return cls(api_key=options.get("api_key"), team_id=options.get("team_id"))

    async def upsert(self, ticket: Ticket) -> str:  # noqa: ARG002
        raise NotImplementedError(
            "LinearTicketSink is a stub. Implement upsert() to call Linear's GraphQL "
            "issueCreate mutation (title, description=body, priority, teamId). Return the issue id."
        )
