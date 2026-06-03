# Benchmarking

A classifier you haven't measured is a liability. `pulsecrm bench` certifies that your taxonomy +
provider choices actually perform on labeled data before you point them at production.

```bash
pulsecrm bench --ci      # deterministic mock classifier (no API keys) — what CI runs
pulsecrm bench           # uses the classifier from your --config
pulsecrm bench --config examples/quickstart/pulse.yaml --dataset eval/golden/intents.jsonl
```

Exit code is non-zero if any suite falls below its threshold, so it doubles as a CI gate.

## The three suites

### 1. Classifier eval
Runs the classifier over `eval/golden/intents.jsonl` (each line: a message + its expected intent
and flags) and reports:

- **per-intent precision / recall / F1**
- **macro-F1** across intents
- **noise-rejection rate** — of messages that should *not* alert (non-actionable or
  `needs_staff_action=false`), the fraction correctly gated out. This is the metric that protects
  against alert fatigue.
- **actionable-gate accuracy** — agreement between the gate's decision and the labeled
  "should this have alerted?" ground truth.

### 2. Dedup eval
Runs the duplicate-detection baseline over `eval/golden/dedup.jsonl` (each line: two messages +
`same: true/false`) and reports precision / recall / F1 for the "same bug" decision.

### 3. Pipeline smoke
Runs the full offline pipeline on a fixture and asserts that it completes and that **every emitted
`AlertEnvelope` validates against the schema** and produces a ticket. This is the functional
guarantee that the wiring works end to end.

## Thresholds

Minimums live in [`eval/thresholds.yaml`](../eval/thresholds.yaml):

```yaml
classifier:
  min_macro_f1: 0.60
  min_noise_rejection: 0.70
dedup:
  min_f1: 0.55
```

The defaults are tuned for the deterministic `mock` classifier and the shipped golden data — a real
LLM should clear them comfortably (target ~0.80 precision per label). Raise them as your golden set
and provider improve.

## Bring your own data

The shipped golden data uses a fictional `acme-app` and generic support scenarios — it exists to
prove the harness runs, not to model your domain. To certify *your* setup:

1. Collect real (anonymized) messages and label them with your intents + "should alert?".
2. Append them to `eval/golden/intents.jsonl` (or point `--dataset` at your own file).
3. Run `pulsecrm bench --config your.yaml` with `classifier.type: openai` (or your provider).
4. Tune your taxonomy / prompt / thresholds until you clear the bar, then deploy.
