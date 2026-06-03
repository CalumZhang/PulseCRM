"""Lexical deduplication baseline.

A simple, dependency-free "are these two reports about the same issue?" predicate
used by the jsonl ticket sink and benchmarked by ``pulsecrm bench``. Swap in a
semantic/LLM dedup via a custom ticket sink for production.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "is", "are", "to", "of", "and", "or", "in", "on", "for", "it",
    "this", "that", "my", "i", "you", "with", "when", "how", "do", "does", "can", "be",
    "keeps", "every", "time", "im", "ive",
}


def tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOP and len(t) > 2}


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def is_duplicate(a: str, b: str, threshold: float = 0.4) -> bool:
    return similarity(a, b) >= threshold
