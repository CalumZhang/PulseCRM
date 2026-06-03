# Writing an adapter

Adding a platform to PulseCRM means writing **one class** against **one port**. The core never
changes.

## 1. Pick the port

| You want to… | Port | Folder |
|---|---|---|
| Ingest from a new chat platform | `SourceAdapter` | `adapters/sources/` |
| Use a different LLM / classifier | `ClassifierProvider` | `adapters/classifiers/` |
| Read a different knowledge base | `KnowledgeBase` | `adapters/knowledge/` |
| Draft replies differently | `Drafter` | `adapters/drafters/` |
| Alert via a different channel | `Notifier` | `adapters/notifiers/` |
| File tickets in a different tracker | `TicketSink` | `adapters/ticket_sinks/` |
| Backfill extra data post-triage | `Enricher` | `adapters/enrichers/` |

## 2. Subclass and register

```python
# src/pulsecrm/adapters/notifiers/mychat.py
from pulsecrm.ports.notifier import Notifier
from pulsecrm.models import AlertEnvelope, AlertRef
from pulsecrm.registry import register

@register("notifier", "mychat")
class MyChatNotifier(Notifier):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    @classmethod
    def build(cls, options: dict, ctx):
        # ctx.base_dir, ctx.config available if you need them
        return cls(webhook_url=options["webhook_url"])

    async def send(self, envelope: AlertEnvelope) -> AlertRef:
        import httpx  # import the SDK INSIDE the method, not at module top level
        # ... post envelope to your platform ...
        return AlertRef(id="...", raw={})
```

## 3. Make it discoverable

**Built-in** (in this repo): add one import line to `registry._load_builtins()`.

**External package** (no fork): expose it through the entry-point group in *your* `pyproject.toml`:

```toml
[project.entry-points."pulsecrm.adapters"]
mychat = "my_package.adapters:register_all"   # a function that imports your modules
```

`pulsecrm list-adapters` and the config loader call both discovery paths automatically.

## 4. Rules

- **Import SDKs lazily.** `pulsecrm list-adapters` imports every built-in adapter module; a bare
  `import discord` at the top would crash the CLI for users who didn't install that extra. Import
  inside `build()`/`send()`/`stream()` and raise a friendly message if the extra is missing.
- **`build(options, ctx)` is the factory.** The default just does `cls(**options)`. Override it to
  resolve file paths against `ctx.base_dir` or to read `ctx.config`/taxonomy.
- **Stay generic.** No company/product names, IDs, or private URLs (see CONTRIBUTING.md).
- **Reference it in config** via `type: mychat` and add a row to the README adapter table.

## Worked examples in this repo

- `adapters/sources/file_replay.py` — minimal working source (reads JSONL).
- `adapters/classifiers/openai.py` — calls an external LLM, parses JSON, validates the schema.
- `adapters/knowledge/markdown.py` — sync + match + public/internal split.
- `adapters/sources/discord.py` — a `[STUB]` showing the shape of a streaming source to fill in.
