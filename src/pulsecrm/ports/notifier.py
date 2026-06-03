from __future__ import annotations

from abc import abstractmethod

from pulsecrm.models import AlertEnvelope, AlertRef

from .base import Adapter


class Notifier(Adapter):
    """Delivers an ``AlertEnvelope`` to wherever staff watch for signal.

    Returns an ``AlertRef`` so callers can thread follow-ups. Threading and
    claim/ack interactions are platform-specific and optional.
    """

    @abstractmethod
    async def send(self, envelope: AlertEnvelope) -> AlertRef:  # pragma: no cover - interface
        ...
