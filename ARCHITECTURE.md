# Architecture

PulseCRM is a **ports-and-adapters (hexagonal)** application. A small, provider-agnostic core
owns the pipeline logic; everything that touches the outside world (chat platforms, LLMs,
knowledge bases, notifiers, ticket stores) is an **adapter** that implements a **port** and is
selected at runtime by a **config-driven registry**.

```
            inbound                         core (provider-agnostic)                       outbound
        ┌───────────────┐   ┌──────────────────────────────────────────────────┐   ┌──────────────────┐
events ▶│ SourceAdapter │ ▶ │ Grouper ▶ Classifier ▶ Gate ▶ KB+Drafter (enrich) │ ▶ │ Notifier         │
        └───────────────┘   └──────────────────────────────────────────────────┘   │ TicketSink       │
                                                                                     │ Enricher(s)      │
                                                                                     └──────────────────┘
                                                          emits ▼
                                                   ┌────────────────────┐
                                                   │   AlertEnvelope     │  (versioned wire contract)
                                                   └────────────────────┘
                                                   consumed by a human (Slack),
                                                   an LLM triager Skill, or a TicketSink.
```

## Why this shape

The internal predecessor of PulseCRM coupled one chat platform, one LLM, one KB, one notifier, and
one ticket store directly together. Two things kept it *almost* generic already:

1. A **structured, emoji-tagged alert format** between detection and triage.
2. A **stable ticket schema** the triager wrote to.

PulseCRM promotes those two implicit contracts into explicit, versioned artifacts (the
`AlertEnvelope` model + JSON schema, and the `Ticket` model / skill `schema.json`) and puts a typed
port in front of every other dependency. The result: you can replace any single piece without the
others noticing.

## Core components (`src/pulsecrm/`)

- **`models.py`** — the domain types that flow through the pipeline: `RawEvent`, `MessageGroup`,
  `Classification`, `KBArticle`, `KBMatch`, `Draft`, **`AlertEnvelope`**, `Ticket`, `AlertRef`.
- **`grouping.py`** — `Grouper.group_events()`: a pure function that debounces a list of events into
  per-author bursts using a sliding time window + max size. Pure → trivially testable.
- **`gating.py`** — `Gate`: the three-gate decision for whether staff should be alerted
  (actionable intent ∧ confidence ≥ threshold ∧ staff-action-needed) plus the `ignored_authors`
  filter. Configuration, not code, decides which intents are actionable.
- **`pipeline.py`** — `Pipeline`: wires the stages and processes each group:
  classify → (KB match if `needs_troubleshoot`) → gate → draft → build envelope → notify →
  (optional) ticket sink → (optional) enrichers.
- **`config.py`** — pydantic models for the YAML config + a loader that resolves relative paths
  against the config file's directory.
- **`registry.py`** — maps `(port, type-name)` → adapter class. Discovers built-ins lazily and
  third-party adapters via the `pulsecrm.adapters` entry-point group.
- **`bench.py`** — the evaluation harness behind `pulsecrm bench`.

## Ports (`src/pulsecrm/ports/`)

Each port is an `ABC` with a `build(options, ctx)` classmethod (so adapters can resolve paths /
read taxonomy at construction) and the methods the core calls:

| Port | Key method(s) |
|---|---|
| `SourceAdapter` | `async stream() -> AsyncIterator[RawEvent]` |
| `ClassifierProvider` | `async classify(group, ctx) -> Classification` |
| `KnowledgeBase` | `async sync()`, `async match(text) -> KBMatch?`, `async get(id) -> KBArticle?` |
| `Drafter` | `async draft(group, article?) -> Draft` |
| `Notifier` | `async send(envelope) -> AlertRef` |
| `TicketSink` | `async upsert(ticket) -> str`, `async find_duplicate(ticket) -> str?` |
| `Enricher` | `async enrich(ticket_ref) -> None` |

## The AlertEnvelope contract

`AlertEnvelope` is the single fork point of the system. The notifier serializes it (e.g. into a
Slack message); a triager — whether the LLM **Skill** in `skills/triager/` or a deterministic
`TicketSink` — consumes it to create a ticket. Because both sides depend only on the schema
(`docs/wire-contract.md`), they evolve independently. The schema is versioned (`version` field) so
consumers can detect breaking changes.

## Extending

Adding support for a new platform is writing one adapter against one port — see
[docs/adapters.md](docs/adapters.md). You never modify the core to add a platform.
