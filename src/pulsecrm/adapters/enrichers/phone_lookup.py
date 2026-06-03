"""phone_lookup enricher [STUB].

Skeleton for attaching a contact detail (e.g. a phone number) to a ticket by
matching the reporter's handle against an intake table (a spreadsheet, CSV, or
CRM export).

Implementation notes:
  * Load a mapping {handle -> contact field} from your source (path in options).
  * Match the ticket's reporter handle (case-insensitive); set the field if found.
  * Leave it empty when there's no match — never guess.
"""

from __future__ import annotations

from pathlib import Path

from pulsecrm.models import Ticket
from pulsecrm.ports.enricher import Enricher
from pulsecrm.registry import register


@register("enricher", "phone_lookup")
class PhoneLookupEnricher(Enricher):
    def __init__(self, table_path: str | Path | None = None, handle_column: str = "handle"):
        self.table_path = Path(table_path) if table_path else None
        self.handle_column = handle_column

    @classmethod
    def build(cls, options: dict, ctx):
        raw = options.get("table_path")
        p = Path(raw) if raw else None
        if p and not p.is_absolute():
            p = (ctx.base_dir / p).resolve()
        return cls(table_path=p, handle_column=options.get("handle_column", "handle"))

    async def enrich(self, ticket: Ticket, ticket_id: str) -> None:  # noqa: ARG002
        raise NotImplementedError(
            "PhoneLookupEnricher is a stub. Implement enrich() to look up the reporter's handle "
            "in your intake table and set the contact field on the ticket (leave empty if no match)."
        )
