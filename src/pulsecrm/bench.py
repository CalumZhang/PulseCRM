"""Benchmark / evaluation harness behind ``pulsecrm bench``.

Three suites, each checked against ``eval/thresholds.yaml``:
  1. classifier eval — per-intent precision/recall/F1, macro-F1, noise-rejection
  2. dedup eval      — precision/recall/F1 of the duplicate-detection baseline
  3. pipeline smoke  — the offline pipeline runs and every envelope is schema-valid

See docs/benchmarking.md.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from pulsecrm import dedup as dedup_mod
from pulsecrm import registry
from pulsecrm.config import BuildContext, PulseConfig, load_config
from pulsecrm.gating import Gate
from pulsecrm.grouping import group_events
from pulsecrm.models import AlertEnvelope, RawEvent
from pulsecrm.ports.classifier import ClassificationContext


@dataclass
class SuiteResult:
    name: str
    passed: bool
    metrics: dict = field(default_factory=dict)
    detail: str = ""


# --------------------------------------------------------------------------
# metric helpers
# --------------------------------------------------------------------------
def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return round(precision, 3), round(recall, 3), round(f1, 3)


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rows.append(json.loads(line))
    return rows


def _group_from_text(text: str, channel: str | None = None):
    ev = RawEvent(
        event_id="bench",
        author_id="bench_user",
        channel_name=channel,
        content=text,
        created_at=datetime.now(UTC),
    )
    return group_events([ev])[0]


# --------------------------------------------------------------------------
# suite 1: classifier eval
# --------------------------------------------------------------------------
def run_classifier_eval(
    config: PulseConfig, ctx: BuildContext, dataset: Path, thresholds: dict
) -> SuiteResult:
    rows = _read_jsonl(dataset)
    classifier = registry.get("classifier", config.classifier.type).build(
        dict(config.classifier.options), ctx
    )
    gate = Gate(config.gating, config.taxonomy)
    cctx_base = config.taxonomy

    async def _classify_all():
        out = []
        for r in rows:
            group = _group_from_text(r["text"], r.get("channel"))
            cls = await classifier.classify(
                group,
                ClassificationContext(
                    taxonomy=cctx_base,
                    channel_summary=f"Channel: #{r.get('channel', 'unknown')}",
                    reply_context=r.get("reply_context", ""),
                ),
            )
            out.append(cls)
        return out

    preds = asyncio.run(_classify_all())

    labels = config.taxonomy.names
    tp = dict.fromkeys(labels, 0)
    fp = dict.fromkeys(labels, 0)
    fn = dict.fromkeys(labels, 0)

    alert_tp = alert_fp = alert_tn = alert_fn = 0
    noise_total = noise_rejected = 0

    for r, cls in zip(rows, preds, strict=True):
        expected = r["expected_intent"]
        predicted = cls.intent if cls else "noise"
        if predicted == expected:
            tp[expected] = tp.get(expected, 0) + 1
        else:
            fp[predicted] = fp.get(predicted, 0) + 1
            fn[expected] = fn.get(expected, 0) + 1

        should_alert = bool(r.get("should_alert", False))
        did_alert = gate.is_actionable(cls)
        if should_alert and did_alert:
            alert_tp += 1
        elif should_alert and not did_alert:
            alert_fn += 1
        elif not should_alert and did_alert:
            alert_fp += 1
        else:
            alert_tn += 1

        if not should_alert:
            noise_total += 1
            if not did_alert:
                noise_rejected += 1

    per_intent = {}
    f1s = []
    for label in labels:
        p, rc, f1 = _prf(tp.get(label, 0), fp.get(label, 0), fn.get(label, 0))
        per_intent[label] = {"precision": p, "recall": rc, "f1": f1}
        # only count labels present in the gold set toward macro-F1
        if any(row["expected_intent"] == label for row in rows):
            f1s.append(f1)

    macro_f1 = round(sum(f1s) / len(f1s), 3) if f1s else 0.0
    noise_rejection = round(noise_rejected / noise_total, 3) if noise_total else 1.0
    gate_acc = round((alert_tp + alert_tn) / len(rows), 3) if rows else 0.0

    min_macro_f1 = thresholds.get("classifier", {}).get("min_macro_f1", 0.0)
    min_noise = thresholds.get("classifier", {}).get("min_noise_rejection", 0.0)
    passed = macro_f1 >= min_macro_f1 and noise_rejection >= min_noise

    return SuiteResult(
        name="classifier",
        passed=passed,
        metrics={
            "samples": len(rows),
            "classifier": config.classifier.type,
            "macro_f1": macro_f1,
            "noise_rejection": noise_rejection,
            "actionable_gate_accuracy": gate_acc,
            "per_intent": per_intent,
        },
        detail=f"macro_f1 {macro_f1} (>= {min_macro_f1}), noise_rejection {noise_rejection} (>= {min_noise})",
    )


# --------------------------------------------------------------------------
# suite 2: dedup eval
# --------------------------------------------------------------------------
def run_dedup_eval(dataset: Path, thresholds: dict) -> SuiteResult:
    rows = _read_jsonl(dataset)
    tp = fp = fn = tn = 0
    for r in rows:
        pred = dedup_mod.is_duplicate(r["a"], r["b"])
        truth = bool(r["same"])
        if pred and truth:
            tp += 1
        elif pred and not truth:
            fp += 1
        elif not pred and truth:
            fn += 1
        else:
            tn += 1
    p, rc, f1 = _prf(tp, fp, fn)
    min_f1 = thresholds.get("dedup", {}).get("min_f1", 0.0)
    passed = f1 >= min_f1
    return SuiteResult(
        name="dedup",
        passed=passed,
        metrics={"samples": len(rows), "precision": p, "recall": rc, "f1": f1},
        detail=f"f1 {f1} (>= {min_f1})",
    )


# --------------------------------------------------------------------------
# suite 3: pipeline smoke
# --------------------------------------------------------------------------
def run_pipeline_smoke(config: PulseConfig, ctx: BuildContext) -> SuiteResult:
    from pulsecrm.pipeline import build_pipeline

    async def _run():
        pipeline = build_pipeline(config, ctx)
        events = await pipeline.collect_events()
        groups = pipeline.grouper.group_events(events)
        if pipeline.knowledge:
            await pipeline.knowledge.sync()
        envelopes_valid = 0
        alerts = 0
        for group in groups:
            result = await pipeline.process_group(group)
            if result.get("alerted"):
                alerts += 1
                env = result.get("envelope")
                # validate against the schema by round-tripping the model
                AlertEnvelope.model_validate(env.model_dump())
                envelopes_valid += 1
        return len(events), len(groups), alerts, envelopes_valid

    n_events, n_groups, alerts, valid = asyncio.run(_run())
    passed = n_events > 0 and n_groups > 0 and alerts > 0 and valid == alerts
    return SuiteResult(
        name="pipeline_smoke",
        passed=passed,
        metrics={"events": n_events, "groups": n_groups, "alerts": alerts, "valid_envelopes": valid},
        detail=f"{alerts} alerts, {valid} schema-valid envelopes",
    )


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------
def run_all(
    config_path: Path,
    dataset: Path,
    dedup_dataset: Path,
    thresholds_path: Path,
    *,
    ci: bool = False,
) -> tuple[list[SuiteResult], bool]:
    config, ctx = load_config(config_path)
    if ci:
        # deterministic, no external calls
        config.classifier.type = "mock"
        config.classifier.options = {}
    thresholds = yaml.safe_load(thresholds_path.read_text()) if thresholds_path.exists() else {}

    results = [
        run_classifier_eval(config, ctx, dataset, thresholds),
        run_dedup_eval(dedup_dataset, thresholds),
        run_pipeline_smoke(config, ctx),
    ]
    all_passed = all(r.passed for r in results)
    return results, all_passed
