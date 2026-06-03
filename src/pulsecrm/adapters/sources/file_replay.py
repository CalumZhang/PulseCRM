"""file_replay source [WORKING].

Reads events from a JSONL file — one JSON object per line — and yields them as
``RawEvent``s. Ideal for demos, fixtures, and benchmarking because it is finite
and deterministic.

Each line may use these keys (only ``content`` and an id are really needed):

    {
      "event_id": "1", "author_id": "u1", "author_display_name": "Alex",
      "author_handle": "alex", "channel_id": "c1", "channel_name": "general",
      "content": "the editor crashes when I save", "created_at": "2026-06-03T10:00:00Z",
      "reply_to_content": "...", "permalink": "https://...",
      "attachments": [{"url": "https://...", "name": "shot.png"}]
    }
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path

from pulsecrm.models import RawEvent
from pulsecrm.ports.source import SourceAdapter
from pulsecrm.registry import register


@register("source", "file_replay")
class FileReplaySource(SourceAdapter):
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @classmethod
    def build(cls, options: dict, ctx):
        raw = options.get("path", "messages.jsonl")
        p = Path(raw)
        if not p.is_absolute():
            p = (ctx.base_dir / p).resolve()
        return cls(path=p)

    async def stream(self) -> AsyncIterator[RawEvent]:
        if not self.path.exists():
            raise FileNotFoundError(f"file_replay source path not found: {self.path}")
        for i, line in enumerate(self.path.read_text().splitlines()):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            data = json.loads(line)
            data.setdefault("event_id", str(i + 1))
            data.setdefault("author_id", "unknown")
            data["created_at"] = _parse_ts(data.get("created_at"))
            data["source"] = "file_replay"
            yield RawEvent.model_validate(data)


def _parse_ts(value) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
