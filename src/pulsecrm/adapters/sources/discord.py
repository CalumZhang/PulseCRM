"""discord source [STUB].

A skeleton for ingesting live messages from Discord. Fill in the marked spots to
make it work; install the extra with ``pip install "pulsecrm[discord]"``.

Unlike ``file_replay`` (finite/batch), this is a *streaming* source. The current
pipeline consumes a source fully before grouping, which suits finite sources. A
production streaming source should instead push events into an async queue and a
real-time debouncer should flush per-author groups on a timer — see the
``# TODO(adapter)`` notes below.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from pulsecrm.models import RawEvent
from pulsecrm.ports.source import SourceAdapter
from pulsecrm.registry import register


@register("source", "discord")
class DiscordSource(SourceAdapter):
    def __init__(self, token: str, guild_id: str | None = None, channel_ids: list[str] | None = None):
        self.token = token
        self.guild_id = guild_id
        self.channel_ids = set(channel_ids or [])
        self._queue: asyncio.Queue[RawEvent] = asyncio.Queue()

    @classmethod
    def build(cls, options: dict, ctx):  # noqa: ARG003
        import os

        token = options.get("token") or os.environ.get("DISCORD_BOT_TOKEN", "")
        return cls(
            token=token,
            guild_id=options.get("guild_id"),
            channel_ids=options.get("channel_ids"),
        )

    async def stream(self) -> AsyncIterator[RawEvent]:
        try:
            import discord  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                'The discord source needs the "discord" extra: pip install "pulsecrm[discord]"'
            ) from exc

        raise NotImplementedError(
            "DiscordSource is a stub. To implement:\n"
            "  1. Create a discord.Client with intents (guilds, guild_messages, message_content).\n"
            "  2. In on_message, build a RawEvent (translate author/channel/content/reply/attachments\n"
            "     into the RawEvent fields) and await self._queue.put(event).\n"
            "  3. client.start(self.token) in a background task; here, `yield await self._queue.get()`.\n"
            "  4. For correct grouping, add a real-time debouncer (flush per-author after window_seconds)\n"
            "     instead of relying on the batch grouper. See ARCHITECTURE.md."
        )
        # makes this an async generator for typing
        if False:  # pragma: no cover
            yield RawEvent(event_id="0", author_id="0")
