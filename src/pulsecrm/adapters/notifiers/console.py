"""console notifier [WORKING].

Prints the emoji-tagged alert to stdout. Handy for local runs, demos, and CI.
The rendering mirrors the structured format a chat notifier (e.g. Slack) would
post, so what you see here is the human-readable view of the AlertEnvelope.
"""

from __future__ import annotations

import uuid

from pulsecrm.models import AlertEnvelope, AlertRef
from pulsecrm.ports.notifier import Notifier
from pulsecrm.registry import register


def render_alert(envelope: AlertEnvelope) -> str:
    author = envelope.author or {}
    name = author.get("display_name") or author.get("handle") or author.get("id") or "unknown"
    handle = f" @{author['handle']}" if author.get("handle") else ""
    channel = (envelope.channel or {}).get("name") or "unknown"

    lines = [
        f"{envelope.emoji} {envelope.intent_label}  (confidence: {envelope.confidence:.2f})",
        f"  User:    {name}{handle}",
        f"  Channel: #{channel}",
    ]
    if envelope.messages:
        lines.append("  Messages:")
        for m in envelope.messages:
            lines.append(f"    > {m.get('content', '')}")
    if envelope.kb_match:
        km = envelope.kb_match
        lines.append(f"  KB match: {km.get('title')} (conf {km.get('confidence')})")
    if envelope.draft:
        d = envelope.draft
        tag = "KB-grounded" if d.get("source") == "kb" else d.get("source")
        lines.append(f"  Suggested reply ({tag}):")
        lines.append(f"    {d.get('text', '')}")
    if envelope.permalink:
        lines.append(f"  Link: {envelope.permalink}")
    return "\n".join(lines)


@register("notifier", "console")
class ConsoleNotifier(Notifier):
    def __init__(self, prefix: str = "\n[ALERT]"):
        self.prefix = prefix

    async def send(self, envelope: AlertEnvelope) -> AlertRef:
        print(f"{self.prefix}\n{render_alert(envelope)}")
        return AlertRef(id=str(uuid.uuid4()))
