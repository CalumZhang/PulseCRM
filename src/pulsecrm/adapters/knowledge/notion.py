"""notion knowledge base [STUB].

Skeleton for syncing help articles from one or more Notion databases/pages.
Install the extra with ``pip install "pulsecrm[notion]"`` (brings in httpx) and
set ``NOTION_API_KEY``.

Implement ``sync()`` to page through the database(s), fetch each page's block
children, and split content into public vs internal sections (e.g. by a toggle
labelled ``public``). ``match()``/``get()`` can mirror the markdown adapter.
"""

from __future__ import annotations

import os

from pulsecrm.models import KBArticle, KBMatch
from pulsecrm.ports.knowledge import KnowledgeBase
from pulsecrm.registry import register


@register("knowledge", "notion")
class NotionKnowledgeBase(KnowledgeBase):
    def __init__(self, api_key: str | None = None, database_ids: list[str] | None = None):
        self.api_key = api_key or os.environ.get("NOTION_API_KEY")
        self.database_ids = database_ids or []

    @classmethod
    def build(cls, options: dict, ctx):  # noqa: ARG003
        return cls(api_key=options.get("api_key"), database_ids=options.get("database_ids"))

    async def sync(self) -> None:
        raise NotImplementedError(
            "NotionKnowledgeBase is a stub. Implement sync() to:\n"
            "  1. POST /v1/databases/{id}/query (paginate) for each configured database.\n"
            "  2. For each page, GET /v1/blocks/{page_id}/children and flatten to text.\n"
            "  3. Split public vs internal content (e.g. content under a 'public' toggle).\n"
            "  4. Build KBArticle(id, title, public_content, internal_content) and index tokens.\n"
            "See adapters/knowledge/markdown.py for the matching approach to reuse."
        )

    async def match(self, query: str) -> KBMatch | None:  # noqa: ARG002
        raise NotImplementedError("NotionKnowledgeBase.match — see markdown adapter for reference.")

    async def get(self, article_id: str) -> KBArticle | None:  # noqa: ARG002
        raise NotImplementedError("NotionKnowledgeBase.get — return the synced article by id.")
