"""PulseCRM command-line interface."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import typer

from pulsecrm import __version__, registry
from pulsecrm.config import load_config

app = typer.Typer(
    add_completion=False,
    help="PulseCRM — turn community/customer chatter into triaged, ticketable signal.",
)


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


@app.command()
def version() -> None:
    """Print the PulseCRM version."""
    typer.echo(__version__)


@app.command("list-adapters")
def list_adapters() -> None:
    """List every registered adapter, grouped by port."""
    table = registry.available()
    for port in registry.PORTS:
        names = table.get(port, [])
        typer.echo(f"\n{port}:")
        if not names:
            typer.echo("  (none)")
        for name in names:
            typer.echo(f"  - {name}")


@app.command("validate-config")
def validate_config(
    config: Path = typer.Argument(..., help="Path to a pulse.yaml config file."),
) -> None:
    """Load and validate a config file, printing a summary of the wiring."""
    cfg, _ctx = load_config(config)
    typer.echo("✅ Config is valid.\n")
    typer.echo(f"  source:      {cfg.source.type}")
    typer.echo(f"  classifier:  {cfg.classifier.type}")
    typer.echo(f"  knowledge:   {cfg.knowledge.type if cfg.knowledge else '(none)'}")
    typer.echo(f"  drafter:     {cfg.drafter.type if cfg.drafter else '(none)'}")
    typer.echo(f"  notifier:    {cfg.notifier.type}")
    typer.echo(f"  ticket_sink: {cfg.ticket_sink.type if cfg.ticket_sink else '(none)'}")
    typer.echo(f"  enrichers:   {[e.type for e in cfg.enrichers] or '(none)'}")
    typer.echo(f"  intents:     {', '.join(cfg.taxonomy.names)}")
    typer.echo(
        f"  gating:      confidence>={cfg.gating.confidence_threshold}, "
        f"require_staff_action={cfg.gating.require_staff_action}, "
        f"ignored_authors={len(cfg.gating.ignored_authors)}"
    )


@app.command()
def run(
    config: Path = typer.Option(..., "--config", "-c", help="Path to a pulse.yaml config file."),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Log pipeline progress."),
) -> None:
    """Run the pipeline over the configured source."""
    _setup_logging(verbose)
    from pulsecrm.pipeline import build_pipeline

    cfg, ctx = load_config(config)
    pipeline = build_pipeline(cfg, ctx)
    stats = asyncio.run(pipeline.run())
    typer.echo(
        f"\n— done — events={stats['events']} groups={stats['groups']} "
        f"alerts={stats['alerts']} tickets={stats['tickets']}"
    )


@app.command()
def bench(
    config: Path = typer.Option(
        Path("examples/quickstart/pulse.yaml"), "--config", "-c", help="Config providing the classifier + taxonomy."
    ),
    dataset: Path = typer.Option(Path("eval/golden/intents.jsonl"), help="Labeled intents golden set."),
    dedup_dataset: Path = typer.Option(Path("eval/golden/dedup.jsonl"), help="Dedup golden set."),
    thresholds: Path = typer.Option(Path("eval/thresholds.yaml"), help="Pass/fail thresholds."),
    ci: bool = typer.Option(False, "--ci", help="Force the deterministic mock classifier (no API keys)."),
) -> None:
    """Benchmark the classifier, dedup, and end-to-end pipeline against thresholds."""
    from pulsecrm.bench import run_all

    results, passed = run_all(config, dataset, dedup_dataset, thresholds, ci=ci)

    typer.echo("\nPulseCRM benchmark")
    typer.echo("=" * 50)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        typer.echo(f"\n[{status}] {r.name}")
        typer.echo(f"  {r.detail}")
        for k, v in r.metrics.items():
            if k == "per_intent":
                typer.echo("  per_intent:")
                for intent, m in v.items():
                    typer.echo(
                        f"    {intent:18s} P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f}"
                    )
            else:
                typer.echo(f"  {k}: {v}")
    typer.echo("\n" + "=" * 50)
    typer.echo("OVERALL: " + ("PASS ✅" if passed else "FAIL ❌"))
    if not passed:
        raise typer.Exit(code=1)


@app.command("schema")
def schema() -> None:
    """Print the AlertEnvelope JSON Schema (the wire contract)."""
    from pulsecrm.models import AlertEnvelope

    typer.echo(json.dumps(AlertEnvelope.model_json_schema(), indent=2))


if __name__ == "__main__":
    app()
