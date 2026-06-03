from __future__ import annotations

from abc import abstractmethod

from pulsecrm.models import Ticket

from .base import Adapter


class TicketSink(Adapter):
    """Files tickets in a tracker (Notion / Linear / Jira / a file / ...).

    ``find_duplicate`` powers deduplication: return the id of an existing open
    ticket describing the same underlying issue, or ``None``. ``upsert`` either
    appends to that ticket or creates a new one, returning the ticket id.
    """

    async def find_duplicate(self, ticket: Ticket) -> str | None:  # noqa: ARG002
        return None

    @abstractmethod
    async def upsert(self, ticket: Ticket) -> str:  # pragma: no cover - interface
        ...
