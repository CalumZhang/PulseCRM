from __future__ import annotations

from abc import abstractmethod

from pulsecrm.models import KBArticle, KBMatch

from .base import Adapter


class KnowledgeBase(Adapter):
    """A searchable store of help articles.

    Implementations must separate user-facing (``public_content``) from
    internal-only (``internal_content``) text so drafts never leak internal
    notes.
    """

    async def sync(self) -> None:
        """Refresh the local view of the knowledge base. Optional."""
        return None

    @abstractmethod
    async def match(self, query: str) -> KBMatch | None:  # pragma: no cover - interface
        ...

    @abstractmethod
    async def get(self, article_id: str) -> KBArticle | None:  # pragma: no cover - interface
        ...
