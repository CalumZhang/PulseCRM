from __future__ import annotations

from abc import abstractmethod

from pulsecrm.models import Draft, KBArticle, MessageGroup

from .base import Adapter


class Drafter(Adapter):
    """Writes a suggested staff reply for a message group.

    When ``article`` is provided, the draft must be grounded in its
    ``public_content`` only. When it is ``None``, the drafter produces a generic
    fallback (``Draft.source == "fallback"``).
    """

    @abstractmethod
    async def draft(
        self, group: MessageGroup, article: KBArticle | None
    ) -> Draft:  # pragma: no cover - interface
        ...
