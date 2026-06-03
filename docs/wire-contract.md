# The AlertEnvelope wire contract

`AlertEnvelope` is the single payload that decouples **detection** (the pipeline) from **triage**
(a human in Slack, an LLM triager Skill, or a `TicketSink`). Every consumer depends only on this
schema, so the pipeline and the triager can evolve independently.

It is **versioned** via the `version` field. Bump the minor version for additive changes; bump the
major version for breaking ones, and have consumers check it.

## Shape

```jsonc
{
  "version": "1.0",
  "intent": "bug_report",          // an intent name from the taxonomy
  "intent_label": "Bug Report",     // human label
  "emoji": "🐛",                    // routing key; triagers can filter on this
  "confidence": 0.92,
  "actionable": true,
  "needs_troubleshoot": true,
  "author":  { "id": "u_123", "display_name": "Alex", "handle": "alex" },
  "channel": { "id": "c_general", "name": "general" },
  "messages": [
    { "content": "the editor crashes when I hit save", "permalink": "https://...", "created_at": "2026-06-03T10:00:00Z" }
  ],
  "permalink": "https://...",       // link to the first/triggering message
  "kb_match": { "article_id": "kb-007", "title": "Editor crashes", "confidence": 0.86 },
  "draft": { "text": "Sorry about that! ...", "source": "kb", "kb_article_id": "kb-007", "kb_title": "Editor crashes" },
  "recent_activity": [ { "summary": "3 messages in #general on 2026-06-02" } ],
  "created_at": "2026-06-03T10:00:05Z",
  "metadata": {}
}
```

The canonical definition is the pydantic `AlertEnvelope` model in
[`src/pulsecrm/models.py`](../src/pulsecrm/models.py); a JSON Schema is generated from it via
`AlertEnvelope.model_json_schema()` and is what `skills/triager/schema.json` is kept consistent
with.

## Field notes

| Field | Notes |
|---|---|
| `emoji` | The routing key. The original design routed bug tickets on a 🐛 tag and ignored other emoji; triagers can do the same. Comes from the taxonomy. |
| `actionable` | Always `true` for an emitted envelope (the gate already passed). Present so downstream consumers don't re-derive it. |
| `draft.source` | `"kb"` (grounded in a matched article), `"fallback"` (generic, no good match), or `"none"`. |
| `kb_match` | Present only when a knowledge-base article matched, even if below the draft threshold. |
| `messages` | Quoted content of the group, each with its own permalink. Capped (default 10). |
| `recent_activity` | Optional lightweight history for triager context; source adapters may leave it empty. |

## Consuming it

- **Human (Slack notifier):** render the envelope into a threaded, emoji-tagged message with a
  claim button. (See the `slack` notifier adapter.)
- **LLM triager Skill:** parse the envelope per `skills/triager/`, dedupe, classify, file a ticket,
  and reply in-thread with the ticket link.
- **Deterministic TicketSink:** the pipeline maps the envelope to a `Ticket` and calls
  `ticket_sink.upsert()`. This is the no-LLM-needed triage path used by the reference config.
