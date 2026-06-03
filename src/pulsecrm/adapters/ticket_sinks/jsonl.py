"""jsonl ticket sink [WORKING].

Appends each ticket as one JSON line to a file. Deduplication is a lexical
baseline: tickets sharing a ``dedup_key`` (intent + salient tokens) are treated
as the same issue, and a repeat appends a note instead of creating a new row.
Offline, dependency-free, and the default for the reference path.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from pulsecrm.models import Ticket
from pulsecrm.ports.ticket_sink import TicketSink
from pulsecrm.registry import register


@register("ticket_sink", "jsonl")
class JsonlTicketSink(TicketSink):
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def build(cls, options: dict, ctx):
        raw = options.get("path", "out/tickets.jsonl")
        p = Path(raw)
        if not p.is_absolute():
            p = (ctx.base_dir / p).resolve()
        return cls(path=p)

    def _read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    async def find_duplicate(self, ticket: Ticket) -> str | None:
        if not ticket.dedup_key:
            return None
        for row in self._read_all():
            if row.get("dedup_key") and row["dedup_key"] == ticket.dedup_key:
                return row.get("id")
        return None

    async def upsert(self, ticket: Ticket) -> str:
        rows = self._read_all()
        # dedup: append a "reported again" note to the existing row
        if ticket.dedup_key:
            for row in rows:
                if row.get("dedup_key") == ticket.dedup_key:
                    row.setdefault("reports", 1)
                    row["reports"] += 1
                    row.setdefault("notes", []).append(ticket.permalink or ticket.title)
                    self._write_all(rows)
                    return row["id"]

        ticket_id = str(uuid.uuid4())
        record = ticket.model_dump(mode="json")
        record["id"] = ticket_id
        record["reports"] = 1
        with self.path.open("a") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return ticket_id

    def _write_all(self, rows: list[dict]) -> None:
        with self.path.open("w") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
