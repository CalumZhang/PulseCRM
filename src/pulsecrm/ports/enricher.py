from __future__ import annotations

from abc import abstractmethod

from pulsecrm.models import Ticket

from .base import Adapter


class Enricher(Adapter):
    """An optional post-triage step that adds data a triager couldn't reach.

    Examples: uploading file attachments from the source message to the ticket,
    or looking up a phone number from an intake spreadsheet. Enrichers receive
    the filed ticket (with its ``metadata`` populated, including any sink id) and
    mutate the tracker as needed.
    """

    @abstractmethod
    async def enrich(self, ticket: Ticket, ticket_id: str) -> None:  # pragma: no cover - interface
        ...
