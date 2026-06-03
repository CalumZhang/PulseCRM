"""The pipeline orchestrator.

Wires the configured adapters and core stages together and processes each
message group: classify -> (KB match) -> gate -> draft -> envelope -> notify
-> (optional ticket sink) -> (optional enrichers).
"""

from __future__ import annotations

import logging

from pulsecrm import registry
from pulsecrm.config import BuildContext, PulseConfig
from pulsecrm.gating import Gate
from pulsecrm.grouping import Grouper
from pulsecrm.models import (
    AlertEnvelope,
    Classification,
    Draft,
    KBArticle,
    KBMatch,
    MessageGroup,
    RawEvent,
    Ticket,
)
from pulsecrm.ports.classifier import ClassificationContext

log = logging.getLogger("pulsecrm.pipeline")


def _build(port: str, cfg, ctx: BuildContext):
    if cfg is None:
        return None
    cls = registry.get(port, cfg.type)
    return cls.build(dict(cfg.options), ctx)


def build_pipeline(config: PulseConfig, ctx: BuildContext) -> "Pipeline":
    source = _build("source", config.source, ctx)
    classifier = _build("classifier", config.classifier, ctx)
    knowledge = _build("knowledge", config.knowledge, ctx)
    drafter = _build("drafter", config.drafter, ctx)
    notifier = _build("notifier", config.notifier, ctx)
    ticket_sink = _build("ticket_sink", config.ticket_sink, ctx)
    enrichers = [_build("enricher", e, ctx) for e in config.enrichers]
    return Pipeline(
        config=config,
        source=source,
        grouper=Grouper(config.grouping.window_seconds, config.grouping.max_group_size),
        classifier=classifier,
        gate=Gate(config.gating, config.taxonomy),
        knowledge=knowledge,
        drafter=drafter,
        notifier=notifier,
        ticket_sink=ticket_sink,
        enrichers=enrichers,
    )


class Pipeline:
    def __init__(
        self,
        *,
        config: PulseConfig,
        source,
        grouper: Grouper,
        classifier,
        gate: Gate,
        knowledge=None,
        drafter=None,
        notifier=None,
        ticket_sink=None,
        enrichers=None,
    ):
        self.config = config
        self.source = source
        self.grouper = grouper
        self.classifier = classifier
        self.gate = gate
        self.knowledge = knowledge
        self.drafter = drafter
        self.notifier = notifier
        self.ticket_sink = ticket_sink
        self.enrichers = enrichers or []
        self.taxonomy = config.taxonomy
        self.kb_threshold = (
            config.knowledge.match_confidence_threshold if config.knowledge else 1.0
        )

    # -- collection -------------------------------------------------------
    async def collect_events(self) -> list[RawEvent]:
        events: list[RawEvent] = []
        async for ev in self.source.stream():
            if self.gate.is_ignored(ev.author_id):
                continue
            events.append(ev)
        return events

    # -- main loop --------------------------------------------------------
    async def run(self) -> dict:
        """Run the offline/batch path. Returns a small run summary.

        A finite source (file replay) is fully consumed, grouped, then each
        group is processed. Streaming sources need a real-time debouncer — see
        the discord adapter stub.
        """
        events = await self.collect_events()
        groups = self.grouper.group_events(events)
        log.info("collected %d events -> %d groups", len(events), len(groups))

        stats = {"events": len(events), "groups": len(groups), "alerts": 0, "tickets": 0}
        if self.knowledge:
            await self.knowledge.sync()

        for group in groups:
            result = await self.process_group(group)
            if result.get("alerted"):
                stats["alerts"] += 1
            if result.get("ticket_id"):
                stats["tickets"] += 1

        if hasattr(self.source, "close"):
            await self.source.close()
        return stats

    async def process_group(self, group: MessageGroup) -> dict:
        classification = await self.classifier.classify(
            group,
            ClassificationContext(
                taxonomy=self.taxonomy,
                channel_summary=f"Channel: #{group.channel_name or 'unknown'}",
                recent_messages=[],
                reply_context=group.reply_context,
            ),
        )

        # KB match (independent of the gate; used for the draft + envelope)
        kb_match: KBMatch | None = None
        article: KBArticle | None = None
        if classification and classification.needs_troubleshoot and self.knowledge:
            kb_match = await self.knowledge.match(group.combined_text)
            if kb_match and kb_match.confidence >= self.kb_threshold:
                article = await self.knowledge.get(kb_match.article_id)

        decision = self.gate.evaluate(classification)
        if not decision.actionable:
            log.info(
                "skip group author=%s intent=%s reason=%s",
                group.author_id,
                classification.intent if classification else None,
                decision.reason,
            )
            return {"alerted": False, "reason": decision.reason}

        draft: Draft | None = None
        if self.drafter:
            draft = await self.drafter.draft(group, article)

        envelope = self.build_envelope(group, classification, draft, kb_match)

        if self.notifier:
            await self.notifier.send(envelope)

        ticket_id = None
        if self.ticket_sink:
            ticket = self.build_ticket(envelope, group)
            dup = await self.ticket_sink.find_duplicate(ticket)
            if dup:
                ticket.metadata["duplicate_of"] = dup
            ticket_id = await self.ticket_sink.upsert(ticket)
            for enricher in self.enrichers:
                try:
                    await enricher.enrich(ticket, ticket_id)
                except Exception as exc:  # noqa: BLE001 - one enricher must not break the run
                    log.warning("enricher %s failed: %s", type(enricher).__name__, exc)

        return {"alerted": True, "ticket_id": ticket_id, "envelope": envelope}

    # -- builders ---------------------------------------------------------
    def build_envelope(
        self,
        group: MessageGroup,
        classification: Classification,
        draft: Draft | None,
        kb_match: KBMatch | None,
    ) -> AlertEnvelope:
        spec = self.taxonomy.by_name(classification.intent)
        messages = [
            {
                "content": e.content,
                "permalink": e.permalink,
                "created_at": e.created_at.isoformat(),
            }
            for e in group.events
            if e.content
        ][:10]
        return AlertEnvelope(
            intent=classification.intent,
            intent_label=spec.resolved_label() if spec else classification.intent,
            emoji=spec.emoji if spec else "",
            confidence=classification.confidence,
            actionable=True,
            needs_troubleshoot=classification.needs_troubleshoot,
            author={
                "id": group.author_id,
                "display_name": group.author_display_name,
                "handle": group.author_handle,
            },
            channel={"id": group.channel_id, "name": group.channel_name},
            messages=messages,
            permalink=group.events[0].permalink if group.events else None,
            kb_match=(
                {
                    "article_id": kb_match.article_id,
                    "title": kb_match.title,
                    "confidence": kb_match.confidence,
                }
                if kb_match
                else None
            ),
            draft=(
                {
                    "text": draft.text,
                    "source": draft.source,
                    "kb_article_id": draft.kb_article_id,
                    "kb_title": draft.kb_title,
                }
                if draft
                else None
            ),
        )

    def build_ticket(self, envelope: AlertEnvelope, group: MessageGroup) -> Ticket:
        title = f"[{envelope.intent_label}] " + _summarize(group.combined_text)
        body_lines = ["## Summary", _summarize(group.combined_text, limit=400), "", "## Original Messages"]
        for m in envelope.messages:
            body_lines.append(f"> {m['content']}")
        author = envelope.author or {}
        return Ticket(
            title=title[:120],
            body="\n".join(body_lines),
            intent=envelope.intent,
            status="Triage",
            source="Bot",
            reporter=(
                f"{author.get('display_name') or author.get('handle') or author.get('id')}"
                + (f" (@{author.get('handle')})" if author.get("handle") else "")
            ),
            channel=(envelope.channel or {}).get("name"),
            permalink=envelope.permalink,
            kb_article=(envelope.kb_match or {}).get("article_id"),
            attachments=group.attachments,
            dedup_key=_dedup_key(envelope.intent, group.combined_text),
            metadata={"confidence": envelope.confidence, "emoji": envelope.emoji},
        )


def _summarize(text: str, limit: int = 80) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text or "(no text)"
    return text[: limit - 1].rstrip() + "…"


def _dedup_key(intent: str, text: str) -> str:
    import re

    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    key_words = sorted(set(w for w in words if len(w) > 3))[:8]
    return intent + ":" + "-".join(key_words)
