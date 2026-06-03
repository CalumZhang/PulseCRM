from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field

from pulsecrm.config import TaxonomyConfig
from pulsecrm.models import Classification, MessageGroup

from .base import Adapter


@dataclass
class ClassificationContext:
    """Everything the classifier may use besides the group itself."""

    taxonomy: TaxonomyConfig
    channel_summary: str = ""
    recent_messages: list[str] = field(default_factory=list)
    reply_context: str = ""


class ClassifierProvider(Adapter):
    """Assigns an intent (+ flags) to a message group."""

    @abstractmethod
    async def classify(
        self, group: MessageGroup, ctx: ClassificationContext
    ) -> Classification | None:  # pragma: no cover - interface
        ...
