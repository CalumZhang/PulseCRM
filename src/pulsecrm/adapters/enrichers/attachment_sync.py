"""attachment_sync enricher [STUB].

Skeleton for backfilling file evidence onto a ticket that the triager couldn't
reach — e.g. images/recordings attached to the original chat message whose URLs
are private to the source platform and so can't be referenced directly by the
tracker.

Implementation notes:
  * Read the ticket's attachments (carried from the source RawEvents).
  * Download eligible files (images/videos, under a size cap, user-uploaded).
  * Upload them to the tracker's file API and attach to the ticket page/issue.
  * Be idempotent: skip if the ticket already has attachments. Per-file failures
    must not abort the others.
This pairs with the attachment-sync Skill (skills/attachment-sync/).
"""

from __future__ import annotations

from pulsecrm.models import Ticket
from pulsecrm.ports.enricher import Enricher
from pulsecrm.registry import register


@register("enricher", "attachment_sync")
class AttachmentSyncEnricher(Enricher):
    def __init__(self, max_bytes: int = 20 * 1024 * 1024):
        self.max_bytes = max_bytes

    @classmethod
    def build(cls, options: dict, ctx):  # noqa: ARG003
        return cls(max_bytes=int(options.get("max_bytes", 20 * 1024 * 1024)))

    async def enrich(self, ticket: Ticket, ticket_id: str) -> None:  # noqa: ARG002
        raise NotImplementedError(
            "AttachmentSyncEnricher is a stub. Implement enrich() to download the ticket's "
            "eligible attachments and upload them to your tracker's file API, idempotently."
        )
