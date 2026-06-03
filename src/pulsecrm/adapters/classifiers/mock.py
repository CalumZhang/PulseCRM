"""mock classifier [WORKING, deterministic].

A keyword-heuristic classifier with **no external calls**. It exists so the
reference pipeline, the tests, and the benchmark all run offline and
reproducibly. It is intentionally simple — a real deployment should use the
``openai`` classifier (or another LLM adapter) and certify it with
``pulsecrm bench``.

It maps a group's text onto whatever intents exist in your taxonomy, so it
degrades gracefully if you rename categories (unknown intents fall back to the
first non-actionable intent, or ``noise``).
"""

from __future__ import annotations

from pulsecrm.models import Classification, MessageGroup
from pulsecrm.ports.classifier import ClassificationContext, ClassifierProvider
from pulsecrm.registry import register

# Ordered by priority: the first intent whose keywords match wins.
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (
        "bug_report",
        (
            "crash", "crashes", "crashed", "broken", "bug", "error", "freeze", "frozen",
            "stuck", "won't", "wont", "doesn't work", "doesnt work", "not working",
            "glitch", "fails", "failing", "can't load", "cant load", "keeps closing",
        ),
    ),
    (
        "purchase_interest",
        (
            "buy", "purchase", "pre-order", "preorder", "price", "pricing", "how much",
            "in stock", "available to order", "where can i get", "cost", "checkout",
        ),
    ),
    (
        "feedback",
        (
            "feature request", "would be nice", "wish there was", "suggestion", "suggest",
            "you should add", "please add", "it'd be great", "feedback:", "improve",
        ),
    ),
    (
        "other",
        ("partnership", "press", "collaborate", "collaboration", "sponsor", "media inquiry"),
    ),
    (
        "question",
        (
            "how do i", "how to", "how can i", "is there a way", "where do i", "what is",
            "can someone help", "help me", "anyone know", "?",
        ),
    ),
]

_TROUBLESHOOT_HINTS = (
    "crash", "broken", "bug", "error", "freeze", "stuck", "won't", "wont", "not working",
    "doesn't work", "doesnt work", "how do i", "how to", "help me", "can't", "cant",
)

_PEER_HELP_HINTS = (
    "you can try", "the fix", "what worked for me", "i did", "try changing", "happened to me",
    "i think you", "you should be able",
)

_GRATITUDE = ("thank", "thanks", "appreciate", "got it working", "nvm", "never mind", "resolved")


def _norm(text: str) -> str:
    return (text or "").lower()


@register("classifier", "mock")
class MockClassifier(ClassifierProvider):
    def __init__(self, default_intent: str = "noise"):
        self.default_intent = default_intent

    async def classify(
        self, group: MessageGroup, ctx: ClassificationContext
    ) -> Classification | None:
        text = _norm(group.combined_text)
        reply = _norm(ctx.reply_context)
        valid = set(ctx.taxonomy.names) or {"noise"}

        intent = self.default_intent if self.default_intent in valid else "noise"
        confidence = 0.5
        matched = False
        for name, kws in _KEYWORDS:
            if name not in valid:
                continue
            if any(k in text for k in kws):
                intent = name
                matched = True
                # multi-word/strong signals get higher confidence
                strong = any(len(k) > 5 and k in text for k in kws)
                confidence = 0.9 if strong else 0.72
                break

        if not matched:
            # No actionable keyword — treat as noise if available.
            intent = "noise" if "noise" in valid else intent
            confidence = 0.6

        needs_troubleshoot = any(h in text for h in _TROUBLESHOOT_HINTS)

        # Staff action heuristic: actionable intent, but suppressed for gratitude
        # or when the author is clearly giving peer help.
        actionable = intent in ctx.taxonomy.actionable_names
        giving_help = any(h in text for h in _PEER_HELP_HINTS) or any(h in reply for h in _PEER_HELP_HINTS)
        gratitude_only = any(g in text for g in _GRATITUDE) and not needs_troubleshoot
        needs_staff_action = actionable and not giving_help and not gratitude_only

        reasoning = f"keyword match -> {intent}" if matched else "no actionable keyword -> noise"
        return Classification(
            intent=intent,
            confidence=confidence,
            needs_troubleshoot=needs_troubleshoot,
            needs_staff_action=needs_staff_action,
            reasoning=reasoning,
        )
