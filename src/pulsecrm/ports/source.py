from __future__ import annotations

from abc import abstractmethod
from collections.abc import AsyncIterator

from pulsecrm.models import RawEvent

from .base import Adapter


class SourceAdapter(Adapter):
    """Ingests events from a platform and yields normalized ``RawEvent``s.

    Implementations should translate the platform's native message shape into
    ``RawEvent`` and yield them. A finite source (e.g. a file replay) should
    return when exhausted; a streaming source (e.g. a live chat gateway) may
    run indefinitely.
    """

    @abstractmethod
    async def stream(self) -> AsyncIterator[RawEvent]:  # pragma: no cover - interface
        ...
        if False:  # pragma: no cover - makes this an async generator for typing
            yield  # type: ignore[misc]

    async def close(self) -> None:
        """Release any resources. Optional."""
        return None
