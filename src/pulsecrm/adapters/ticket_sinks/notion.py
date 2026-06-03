"""notion ticket sink [STUB].

Skeleton for filing tickets as pages in a Notion database. Install the extra
with ``pip install "pulsecrm[notion]"`` and set ``NOTION_API_KEY`` +
``NOTION_DATABASE_ID``.

Map ``Ticket`` fields onto your database properties (Title, Priority, Component,
Status, Source, Reporter, Channel, Permalink, ...). ``find_duplicate`` should
query the database for open tickets and compare against the new one (the
triager Skill in skills/triager/ describes the dedup policy in detail).
"""

from __future__ import annotations

import os

from pulsecrm.models import Ticket
from pulsecrm.ports.ticket_sink import TicketSink
from pulsecrm.registry import register


@register("ticket_sink", "notion")
class NotionTicketSink(TicketSink):
    def __init__(self, api_key: str | None = None, database_id: str | None = None):
        self.api_key = api_key or os.environ.get("NOTION_API_KEY")
        self.database_id = database_id or os.environ.get("NOTION_DATABASE_ID")

    @classmethod
    def build(cls, options: dict, ctx):  # noqa: ARG003
        return cls(api_key=options.get("api_key"), database_id=options.get("database_id"))

    async def upsert(self, ticket: Ticket) -> str:  # noqa: ARG002
        try:
            import httpx  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                'The notion ticket sink needs the "notion" extra: pip install "pulsecrm[notion]"'
            ) from exc
        raise NotImplementedError(
            "NotionTicketSink is a stub. Implement upsert() to POST /v1/pages with "
            "parent={database_id: ...} and properties mapped from the Ticket. Map the page body "
            "(Summary + Original Messages) into block children. Return the created page id."
        )
