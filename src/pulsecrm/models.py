"""Domain models that flow through the PulseCRM pipeline.

These are the only types the core pipeline knows about. Adapters translate
between a platform's native shape and these models, so the core stays
provider-agnostic.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class Attachment(BaseModel):
    url: str
    name: str | None = None
    content_type: str | None = None
    size: int | None = None


class RawEvent(BaseModel):
    """A single inbound message/event, normalized from a source platform."""

    source: str = "unknown"  # adapter type name, e.g. "discord", "file_replay"
    event_id: str
    author_id: str
    author_display_name: str | None = None
    author_handle: str | None = None
    channel_id: str | None = None
    channel_name: str | None = None
    content: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    reply_to_event_id: str | None = None
    reply_to_author_id: str | None = None
    reply_to_content: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)
    permalink: str | None = None
    metadata: dict = Field(default_factory=dict)


class MessageGroup(BaseModel):
    """A debounced burst of events from a single author."""

    author_id: str
    author_display_name: str | None = None
    author_handle: str | None = None
    events: list[RawEvent]

    @property
    def texts(self) -> list[str]:
        return [e.content for e in self.events if e.content and e.content.strip()]

    @property
    def combined_text(self) -> str:
        return "\n".join(self.texts)

    @property
    def last(self) -> RawEvent:
        return self.events[-1]

    @property
    def channel_id(self) -> str | None:
        return self.last.channel_id

    @property
    def channel_name(self) -> str | None:
        return self.last.channel_name

    @property
    def reply_context(self) -> str:
        parts = []
        for e in self.events:
            if e.reply_to_content:
                who = e.reply_to_author_id or "someone"
                parts.append(f"[Replying to @{who}]: {e.reply_to_content}")
        return "\n".join(parts)

    @property
    def attachments(self) -> list[Attachment]:
        out: list[Attachment] = []
        for e in self.events:
            out.extend(e.attachments)
        return out


class Classification(BaseModel):
    intent: str
    confidence: float = 0.0
    needs_troubleshoot: bool = False
    needs_staff_action: bool = False
    reasoning: str = ""


class KBArticle(BaseModel):
    id: str
    title: str
    public_content: str = ""
    internal_content: str = ""


class KBMatch(BaseModel):
    article_id: str
    title: str
    confidence: float


class Draft(BaseModel):
    text: str
    source: str = "none"  # "kb" | "fallback" | "none"
    kb_article_id: str | None = None
    kb_title: str | None = None


class AlertEnvelope(BaseModel):
    """The versioned wire contract between detection and triage.

    See docs/wire-contract.md. Anything that consumes an alert (a Slack
    notifier, an LLM triager skill, a deterministic ticket sink) depends only
    on this schema.
    """

    version: str = "1.0"
    intent: str
    intent_label: str
    emoji: str = ""
    confidence: float
    actionable: bool = True
    needs_troubleshoot: bool = False
    author: dict = Field(default_factory=dict)
    channel: dict = Field(default_factory=dict)
    messages: list[dict] = Field(default_factory=list)
    permalink: str | None = None
    kb_match: dict | None = None
    draft: dict | None = None
    recent_activity: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    metadata: dict = Field(default_factory=dict)


class AlertRef(BaseModel):
    """Handle returned by a notifier after sending an alert."""

    id: str
    thread_id: str | None = None
    raw: dict = Field(default_factory=dict)


class Ticket(BaseModel):
    """A triaged, ticketable record. Generic by design.

    Field names intentionally avoid any product/company-specific vocabulary;
    statuses default to a neutral lifecycle (Triage / In Progress / Done).
    """

    title: str
    body: str = ""
    intent: str = ""
    priority: str | None = None  # e.g. P0/P1/P2/P3 — team-defined
    component: list[str] = Field(default_factory=list)  # generic component tags
    feature: list[str] = Field(default_factory=list)
    status: str = "Triage"
    source: str = "Bot"  # "Bot" (from an AlertEnvelope) or "Internal Triage"
    reporter: str | None = None
    channel: str | None = None
    permalink: str | None = None
    kb_article: str | None = None
    regression: str = "New"
    attachments: list[Attachment] = Field(default_factory=list)
    dedup_key: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    metadata: dict = Field(default_factory=dict)
