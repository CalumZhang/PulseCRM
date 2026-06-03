"""Ports — the typed contracts the core pipeline depends on.

Each external dependency (chat platform, LLM, knowledge base, notifier, ticket
store) is reached only through one of these abstract base classes. Adapters
implement them; the registry selects an adapter by name at runtime.
"""

from .base import Adapter
from .classifier import ClassifierProvider
from .drafter import Drafter
from .enricher import Enricher
from .knowledge import KnowledgeBase
from .notifier import Notifier
from .source import SourceAdapter
from .ticket_sink import TicketSink

__all__ = [
    "Adapter",
    "SourceAdapter",
    "ClassifierProvider",
    "KnowledgeBase",
    "Drafter",
    "Notifier",
    "TicketSink",
    "Enricher",
]
