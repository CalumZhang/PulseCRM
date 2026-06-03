# Concepts

A glossary of the moving parts. See [ARCHITECTURE.md](../ARCHITECTURE.md) for how they fit
together.

### Event
A single inbound message from a platform, normalized into a `RawEvent` (author, channel, content,
timestamp, optional reply context and attachments, a permalink). Source adapters are the only code
that knows a platform's native shape; they translate it into `RawEvent`.

### Group
A debounced burst of consecutive events from the **same author** within a time window (default
60s, max 20). Grouping is what lets the classifier reason about a complete thought instead of
firing on every line. Implemented as the pure function `Grouper.group_events()`.

### Taxonomy
*Your* set of intents, defined in config — each with a `name`, an `emoji`, a `label`, and an
`actionable` flag. The classifier prompt is rendered from the taxonomy, so changing categories
needs no code. Example intents: `purchase_interest`, `question`, `bug_report`, `feedback`,
`other`, `noise`.

### Classification
The LLM's verdict for a group: an `intent` from the taxonomy, a `confidence` (0–1), and two
independent booleans — `needs_troubleshoot` (does this person have a problem we can help with?
drives KB matching) and `needs_staff_action` (would a human actually need to act?).

### Gate
Three conditions that must *all* hold before an alert is emitted:
1. the intent is `actionable` in the taxonomy,
2. `confidence ≥ confidence_threshold`,
3. `needs_staff_action` is true (when `require_staff_action`).

Plus an `ignored_authors` list (e.g. your own staff) that skips the pipeline entirely. The gate is
deliberately conservative — the cost of a missed signal is low; the cost of alert fatigue is high.

### Knowledge base & draft
When `needs_troubleshoot` is set, the `KnowledgeBase` adapter finds the best-matching article. If
the match clears `match_confidence_threshold`, the `Drafter` writes a reply grounded in the
article's **public** content; otherwise it writes a generic fallback draft. Knowledge adapters
separate `public` from `internal` content so internal notes never leak into user-facing drafts.

### AlertEnvelope
The structured, versioned payload emitted after the gate passes. It is the **contract** between
detection and triage. See [wire-contract.md](wire-contract.md).

### Triage
Turning an `AlertEnvelope` into a `Ticket`: deduplicate against open tickets, classify fields
(priority, component, …), and file it. Can be done by a deterministic `TicketSink` adapter or by an
LLM **Skill** (`skills/triager/`). Both consume the same envelope.

### Enricher
An optional post-triage step that adds something the triager couldn't reach — e.g. uploading file
attachments from the source message, or looking up a phone number from a spreadsheet.
