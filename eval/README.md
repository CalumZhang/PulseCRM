# eval/

Golden datasets and thresholds for `pulsecrm bench`. See
[../docs/benchmarking.md](../docs/benchmarking.md) for the full guide.

| File | Purpose |
|---|---|
| `golden/intents.jsonl` | Labeled messages → expected intent + `should_alert`. Drives the classifier eval. |
| `golden/dedup.jsonl` | Message pairs → `same` (same underlying issue?). Drives the dedup eval. |
| `thresholds.yaml` | Minimum metrics each suite must clear (CI gate). |

The shipped data uses a fictional `acme-app` and generic support scenarios — it
exists to prove the harness runs, not to model any real product. **Replace it
with your own labeled data** to certify your taxonomy + provider:

```bash
# certify your real setup before deploying
pulsecrm bench --config your.yaml --dataset eval/golden/intents.jsonl
```

Run from the repository root so the default relative paths resolve.
