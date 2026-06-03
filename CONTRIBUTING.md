# Contributing to PulseCRM

Thanks for helping make PulseCRM useful for more teams! This project is built so that the most
common contribution — **a new adapter for a platform you use** — is small, isolated, and safe.

## Development setup

```bash
git clone https://github.com/CalumZhang/PulseCRM
cd PulseCRM
python -m pip install -e ".[dev]"     # core + pytest + ruff
pre-commit-ish loop:
  ruff check .            # lint
  pytest -q               # tests
  pulsecrm bench --ci     # deterministic benchmark (no API keys)
```

Python 3.11+. The core install is intentionally tiny (pydantic, pyyaml, typer). Heavy SDKs
(`openai`, `discord.py`, `slack-sdk`, `httpx`) are **optional extras** so a base install stays
light — adapters import their SDK lazily, inside `build()`/`stream()`, never at module top level.

## Project layout

```
src/pulsecrm/
  ports/        # the typed contracts — one ABC per stage
  adapters/     # implementations, grouped by port
  pipeline.py   # the orchestrator that wires them
  grouping.py gating.py models.py config.py registry.py bench.py
skills/         # agent specs (SKILL.md + portable prompt.md)
examples/ eval/ tests/ docs/
```

## Writing an adapter (the common case)

Full guide: [docs/adapters.md](docs/adapters.md). The short version:

1. Pick the port (e.g. `Notifier`) and subclass it in `src/pulsecrm/adapters/<port>s/<name>.py`.
2. Decorate with `@register("<port>", "<name>")`.
3. Implement the port's methods. Import any third-party SDK **inside** the method, raising a clear
   message if the extra isn't installed.
4. Register it as a built-in in `registry._load_builtins()` (or, for an external package, via the
   `pulsecrm.adapters` entry-point group).
5. Add a line to the adapter table in `README.md` and, ideally, a test.

Adapters must be **import-safe without their SDK** — `pulsecrm list-adapters` imports every
built-in module, so a bare `import discord` at top level would break the CLI for everyone.

## Tests & benchmarks

- `pytest` must pass. Add tests for pure logic (grouping, gating, config, dedup).
- `pulsecrm bench --ci` runs the deterministic mock classifier and must stay above the thresholds
  in `eval/thresholds.yaml`. If you change the taxonomy or mock heuristics, update the golden data
  in `eval/golden/` and re-baseline thoughtfully.

## Genericity rule

PulseCRM is a generic product. **Do not** commit any company-specific or product-specific names,
internal IDs, private URLs, or non-English status strings anywhere — code, prompts, skills,
examples, or golden data. Use neutral placeholders (a fictional `acme-app`, generic intents,
generic statuses like `Triage / In Progress / Done`). CI greps for common offenders.

## Good first contributions

- Implement a `[STUB]` adapter (`slack` notifier, `notion`/`linear` ticket sink, `discord` source).
- Add golden examples to `eval/golden/intents.jsonl` for an intent that's under-tested.
- Improve the `mock` classifier's heuristics (and re-baseline the benchmark).
- Port a skill spec to another agent framework.

## Code of conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
