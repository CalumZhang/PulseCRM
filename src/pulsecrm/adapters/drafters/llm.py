"""llm drafter [WORKING].

Writes a suggested staff reply with an OpenAI chat model, grounded strictly in
the matched KB article's PUBLIC content (or a generic fallback when no article
matched). Requires the ``openai`` extra and ``OPENAI_API_KEY``.
"""

from __future__ import annotations

import logging
import os

from pulsecrm.models import Draft, KBArticle, MessageGroup
from pulsecrm.ports.drafter import Drafter
from pulsecrm.registry import register

log = logging.getLogger("pulsecrm.drafter.llm")


@register("drafter", "llm")
class LLMDrafter(Drafter):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    @classmethod
    def build(cls, options: dict, ctx):  # noqa: ARG003
        return cls(model=options.get("model", "gpt-4o-mini"), api_key=options.get("api_key"))

    def _client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                'The llm drafter needs the "openai" extra: pip install "pulsecrm[openai]"'
            ) from exc
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        return OpenAI(api_key=self.api_key)

    async def draft(self, group: MessageGroup, article: KBArticle | None) -> Draft:
        user_text = "\n".join(f"- {t}" for t in group.texts)
        if article and article.public_content:
            system = (
                "You draft a concise, friendly support reply. Use ONLY the provided knowledge "
                "(do not invent facts). 2-4 sentences."
            )
            user = (
                f"Knowledge (public, safe to share):\n{article.public_content}\n\n"
                f"User messages:\n{user_text}\n\nWrite the reply."
            )
            source, aid, title = "kb", article.id, article.title
        else:
            system = (
                "You draft a concise, friendly support reply acknowledging the user and saying the "
                "team will follow up. Do not invent product facts. 1-3 sentences."
            )
            user = f"User messages:\n{user_text}\n\nWrite the reply."
            source, aid, title = "fallback", None, None

        try:
            client = self._client()
            resp = client.chat.completions.create(
                model=self.model,
                temperature=0.3,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            text = (resp.choices[0].message.content or "").strip()
        except Exception as exc:  # noqa: BLE001
            log.error("llm draft failed: %s", exc)
            return Draft(text="(draft generation failed)", source="none")
        return Draft(text=text, source=source, kb_article_id=aid, kb_title=title)
