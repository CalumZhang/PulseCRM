---
name: pulsecrm-regression-classifier
description: >
  Maintain the regression lifecycle of tickets in a tracker. Use when a ticket's
  state may have changed (a fix shipped, an issue reappeared) and the Regression
  field needs updating across the New → Fixed → Regressed → Re-fixed cycle. This
  is the ONLY agent that changes the Regression field; the triager only sets
  "New" on creation. Generic and configurable.
---

# Regression Classifier

You own one field: **Regression**, which tracks whether a known issue is currently
broken or fixed over time. The triager creates tickets with `Regression = New`
and never touches the field again — you advance it.

## The lifecycle

```
New ──fix ships──▶ Fixed ──issue reappears──▶ Regressed ──fix ships again──▶ Re-fixed ──▶ (Regressed ⇄ Re-fixed)…
```

| Value | Meaning |
|---|---|
| `New` | Freshly reported; not yet fixed. (Set by the triager.) |
| `Fixed` | A fix has shipped/verified for this issue. |
| `Regressed` | A previously `Fixed` issue is broken again. |
| `Re-fixed` | A `Regressed` issue has been fixed again. |

## When to act

Run when you have a signal that a ticket's real-world state changed, e.g.:

- A new report matches an existing `Fixed` ticket → set it to `Regressed` and bump
  the last-reported date.
- A release note / staff confirmation says an issue is fixed → `New`/`Regressed`
  → `Fixed`/`Re-fixed` accordingly.
- A new report matches a ticket already `Regressed` → leave `Regressed`, just bump
  last-reported date and append the report.

Match tickets by **root cause**, the same way the triager deduplicates (see
`../triager/SKILL.md`). Do not create tickets — that is the triager's job.

## Rules

- Only ever write the **Regression** field (and last-reported date / an appended
  note when a report recurs). Touch nothing else.
- Never skip states illegally: a `New` ticket can become `Fixed`; only a `Fixed`
  ticket can become `Regressed`; only a `Regressed` ticket can become `Re-fixed`.
- When the signal is ambiguous, leave the field unchanged and take no action.
- Stay generic: read the tracker location and any state-detection rules from your
  config; assume no specific product.
