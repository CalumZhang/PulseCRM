"""templated drafter [WORKING].

Produces a suggested staff reply with no external calls. When a KB article is
provided it grounds the draft in the article's PUBLIC content only (never the
internal notes); otherwise it emits a generic fallback. Useful offline and as a
safe default.
"""

from __future__ import annotations

from pulsecrm.models import Draft, KBArticle, MessageGroup
from pulsecrm.ports.drafter import Drafter
from pulsecrm.registry import register


@register("drafter", "templated")
class TemplatedDrafter(Drafter):
    def __init__(self, fallback: str | None = None):
        self.fallback = fallback or (
            "Thanks for reaching out! Our team has seen your message and will follow up shortly."
        )

    async def draft(self, group: MessageGroup, article: KBArticle | None) -> Draft:
        if article and article.public_content:
            snippet = " ".join(article.public_content.split())
            if len(snippet) > 600:
                snippet = snippet[:599].rstrip() + "…"
            text = f"Thanks for flagging this! {snippet}"
            return Draft(
                text=text,
                source="kb",
                kb_article_id=article.id,
                kb_title=article.title,
            )
        return Draft(text=self.fallback, source="fallback")
