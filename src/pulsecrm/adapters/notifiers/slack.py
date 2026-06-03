"""slack notifier [STUB].

Skeleton for posting alerts to Slack with threading + a claim button. Install
the extra with ``pip install "pulsecrm[slack]"`` and set ``SLACK_BOT_TOKEN`` and
a target channel.

Implementation notes (what the original design did and you should re-create):
  * Render the AlertEnvelope into Block Kit (header section + "I'm on it" button).
  * Thread follow-ups for the same author/day into one Slack thread; treat a
    claimed thread as closed so new signals start a fresh alert.
  * Use Socket Mode (slack_bolt) to handle the claim button interaction.
The console notifier's ``render_alert`` is a good starting point for the text.
"""

from __future__ import annotations

import os

from pulsecrm.models import AlertEnvelope, AlertRef
from pulsecrm.ports.notifier import Notifier
from pulsecrm.registry import register


@register("notifier", "slack")
class SlackNotifier(Notifier):
    def __init__(self, token: str | None = None, channel: str | None = None):
        self.token = token or os.environ.get("SLACK_BOT_TOKEN")
        self.channel = channel

    @classmethod
    def build(cls, options: dict, ctx):  # noqa: ARG003
        return cls(token=options.get("token"), channel=options.get("channel"))

    async def send(self, envelope: AlertEnvelope) -> AlertRef:  # noqa: ARG002
        try:
            import slack_sdk  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                'The slack notifier needs the "slack" extra: pip install "pulsecrm[slack]"'
            ) from exc
        raise NotImplementedError(
            "SlackNotifier is a stub. Implement send() to:\n"
            "  1. Build Block Kit blocks from the envelope (reuse notifiers/console.render_alert).\n"
            "  2. chat_postMessage to self.channel; on first message in a thread, reply with context.\n"
            "  3. Add an 'I'm on it' button (action_id) and handle it via Socket Mode.\n"
            "  4. Return AlertRef(id=ts, thread_id=thread_ts)."
        )
