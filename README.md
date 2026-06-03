<h1 align="center">PulseCRM</h1>

<p align="center">
  <b>Turn noisy community & customer chatter into triaged, ticketable signal.</b><br>
  A platform-agnostic, config-driven pipeline you can drop into <i>any</i> CRM stack.
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#adapters">Adapters</a> ·
  <a href="#benchmarking">Benchmarking</a> ·
  <a href="docs/adapters.md">Write an adapter</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

---

Teams lose high-intent signals — purchase interest, bug reports, confused users — in the
firehose of a busy Discord/Slack/Telegram/community channel. PulseCRM watches your channels,
**groups** bursts of messages, **classifies** intent with an LLM, **grounds** troubleshooting in
your knowledge base, **drafts** a reply, and emits a structured **AlertEnvelope** that either a
human-in-the-loop notifier (Slack) or an automated/agentic triager turns into a categorized
ticket (Notion / Linear / Jira / a file).

Every external system — chat platform, LLM, knowledge base, notifier, ticket store — is a
**swappable adapter behind a typed port**. Pick the ones you use, write your own for the ones you
don't, and prove the whole thing works on *your* data with the built-in benchmark.

```
 source ─▶ group ─▶ classify ─▶ gate ─▶ enrich(KB+draft) ─▶ notify ─▶ ┌─ AlertEnvelope ─┐
 (ingest)   core      LLM       3 gates        core            sink     │  triager skill  │─▶ ticket
                                                                        │  or ticket sink │
                                                                        └─────────────────┘
```

## Quickstart

Runs end-to-end **with zero API keys** — the default config uses a deterministic mock classifier,
a local Markdown knowledge base, a console notifier, and a JSONL ticket sink.

```bash
pip install -e .                      # or: pip install pulsecrm  (once published)

pulsecrm validate-config examples/quickstart/pulse.yaml
pulsecrm list-adapters                # see what's available, by port
pulsecrm run --config examples/quickstart/pulse.yaml
# → prints emoji-tagged alerts to the console and appends tickets to out/tickets.jsonl
```

Flip a single line in `examples/quickstart/pulse.yaml` (`classifier.type: openai`) and export
`OPENAI_API_KEY` to run the same path on a real LLM.

## How it works

| Stage | What it does | Port (swappable) |
|---|---|---|
| **Ingest** | Stream raw messages/events from a platform | `SourceAdapter` |
| **Group** | Debounce bursts from one author into a single unit (sliding window) | core (`grouping.py`) |
| **Classify** | LLM assigns an intent from *your* taxonomy + `needs_troubleshoot` / `needs_staff_action` flags | `ClassifierProvider` |
| **Gate** | Three gates decide if staff should be alerted: actionable intent **∧** confidence ≥ threshold **∧** staff-action-needed | core (`gating.py`) |
| **Enrich** | Match a knowledge-base article and draft a grounded reply | `KnowledgeBase` + `Drafter` |
| **Notify** | Emit a structured, emoji-tagged **AlertEnvelope** (the wire contract) | `Notifier` |
| **Triage** | A triager (agent **Skill** or deterministic `TicketSink`) dedupes & files a ticket | `TicketSink` / `skills/triager` |
| **Backfill** | Optional enrichers add evidence the triager can't reach (e.g. attachments) | `Enricher` |

The **AlertEnvelope** ([docs/wire-contract.md](docs/wire-contract.md)) is the contract that
decouples detection from triage: the same envelope can be consumed by a human via Slack, by an
LLM triager agent, or by a code-level ticket sink — none of them know about each other.

## Adapters

`[WORKING]` ships runnable today; `[STUB]` is an import-safe skeleton with `# TODO(adapter)`
guidance and a docstring pointing at the port contract — fill it in for your stack.

| Port | Built-in adapters |
|---|---|
| Source | `file_replay` `[WORKING]` · `discord` `[STUB]` |
| Classifier | `mock` `[WORKING, deterministic]` · `openai` `[WORKING]` |
| Knowledge | `markdown` `[WORKING]` · `notion` `[STUB]` |
| Drafter | `templated` `[WORKING]` · `llm` `[WORKING]` |
| Notifier | `console` `[WORKING]` · `slack` `[STUB]` |
| Ticket sink | `jsonl` `[WORKING]` · `notion` `[STUB]` · `linear` `[STUB]` |
| Enricher | `attachment_sync` `[STUB]` · `phone_lookup` `[STUB]` |

Third-party packages can register their own adapters via the `pulsecrm.adapters` entry-point group
— no fork required. See [docs/adapters.md](docs/adapters.md).

## Skills (agentic triage)

The triage step can be run by an LLM agent. PulseCRM ships generic, parameterized agent specs in
[`skills/`](skills/), each as a Claude Agent Skill (`SKILL.md`) **and** a framework-agnostic
`prompt.md` + `schema.json`:

- **triager** — reads AlertEnvelopes (and free-form staff messages), dedupes against open tickets, classifies fields, files a ticket.
- **regression-classifier** — owns the `New → Fixed → Regressed → Re-fixed` lifecycle.
- **attachment-sync** — backfills file evidence a triager can't fetch.

## Benchmarking

Don't trust a classifier you haven't measured. `pulsecrm bench` runs three suites against
thresholds in [`eval/thresholds.yaml`](eval/thresholds.yaml):

```bash
pulsecrm bench --ci      # deterministic mock classifier — used in CI, no keys, free
pulsecrm bench           # uses whatever classifier your config points at
```

1. **Classifier eval** — per-intent precision/recall/F1, macro-F1, and **noise-rejection rate** over a labeled golden set.
2. **Dedup eval** — precision/recall of the duplicate-detection baseline.
3. **Pipeline smoke** — the full offline pipeline runs and every emitted envelope validates against the schema.

Bring your own `golden/*.jsonl` to certify your taxonomy + provider before going live. See
[docs/benchmarking.md](docs/benchmarking.md).

## Configuration

One YAML file wires the whole pipeline. Each `type:` resolves to an adapter; `options:` is passed
to it. Define your own intents and routing in `taxonomy:` without touching code.

```yaml
source:     { type: file_replay, options: { path: messages.jsonl } }
classifier: { type: mock }              # or: { type: openai, options: { model: gpt-4o-mini } }
knowledge:  { type: markdown, options: { path: kb }, match_confidence_threshold: 0.80 }
drafter:    { type: templated }
notifier:   { type: console }
ticket_sink:{ type: jsonl, options: { path: out/tickets.jsonl } }
gating:     { confidence_threshold: 0.65, require_staff_action: true, ignored_authors: [] }
taxonomy:
  intents:
    - { name: bug_report, emoji: "🐛", label: "Bug Report", actionable: true }
    - { name: noise,      emoji: "💬", label: "Noise",      actionable: false }
```

## Status

Alpha. The core pipeline, the working reference path, the benchmark harness, and the skill specs
are functional. Most platform adapters are stubs awaiting contributions — see
[good first issues](CONTRIBUTING.md#good-first-contributions).

## License

[MIT](LICENSE).
