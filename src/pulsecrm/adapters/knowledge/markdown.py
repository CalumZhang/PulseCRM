"""markdown knowledge base [WORKING].

Loads ``*.md`` files from a directory — one article per file. The article title
is the first ``# heading`` (or the filename). Content is split into public vs
internal using fenced tags so internal notes never reach a user-facing draft:

    # Editor crashes on save

    <public>
    Sorry about that! Please update to the latest version and try again.
    </public>

    <internal>
    Known issue tracked in ENG-123; fixed in build 412.
    </internal>

Text without tags is treated as public. Matching is a lightweight bag-of-words
overlap (token Jaccard weighted by query coverage) — good enough for a reference
KB; swap in embeddings via your own adapter for production.
"""

from __future__ import annotations

import re
from pathlib import Path

from pulsecrm.models import KBArticle, KBMatch
from pulsecrm.ports.knowledge import KnowledgeBase
from pulsecrm.registry import register

_PUBLIC_RE = re.compile(r"<public>(.*?)</public>", re.IGNORECASE | re.DOTALL)
_INTERNAL_RE = re.compile(r"<internal>(.*?)</internal>", re.IGNORECASE | re.DOTALL)
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "is", "are", "to", "of", "and", "or", "in", "on", "for", "it",
    "this", "that", "my", "i", "you", "with", "when", "how", "do", "does", "can", "be",
}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOP and len(t) > 2}


@register("knowledge", "markdown")
class MarkdownKnowledgeBase(KnowledgeBase):
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._articles: dict[str, KBArticle] = {}
        self._index: dict[str, set[str]] = {}

    @classmethod
    def build(cls, options: dict, ctx):
        raw = options.get("path", "kb")
        p = Path(raw)
        if not p.is_absolute():
            p = (ctx.base_dir / p).resolve()
        return cls(path=p)

    async def sync(self) -> None:
        self._articles.clear()
        self._index.clear()
        if not self.path.exists():
            return
        for md in sorted(self.path.glob("*.md")):
            text = md.read_text()
            title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else md.stem
            public_parts = _PUBLIC_RE.findall(text)
            internal_parts = _INTERNAL_RE.findall(text)
            if public_parts:
                public = "\n".join(p.strip() for p in public_parts)
            else:
                # No tags: strip any internal blocks, treat the rest as public.
                public = _INTERNAL_RE.sub("", text).strip()
            internal = "\n".join(p.strip() for p in internal_parts)
            article = KBArticle(
                id=md.stem,
                title=title,
                public_content=public,
                internal_content=internal,
            )
            self._articles[article.id] = article
            self._index[article.id] = _tokens(title + " " + public + " " + internal)

    async def match(self, query: str) -> KBMatch | None:
        if not self._articles:
            await self.sync()
        q = _tokens(query)
        if not q:
            return None
        best_id, best_score = None, 0.0
        for aid, toks in self._index.items():
            if not toks:
                continue
            overlap = len(q & toks)
            if overlap == 0:
                continue
            # query coverage (how much of the query the article explains) +
            # a small jaccard term to break ties toward focused articles.
            coverage = overlap / len(q)
            jaccard = overlap / len(q | toks)
            score = 0.8 * coverage + 0.2 * jaccard
            if score > best_score:
                best_id, best_score = aid, score
        if best_id is None:
            return None
        art = self._articles[best_id]
        return KBMatch(article_id=art.id, title=art.title, confidence=round(min(1.0, best_score), 3))

    async def get(self, article_id: str) -> KBArticle | None:
        if not self._articles:
            await self.sync()
        return self._articles.get(article_id)
