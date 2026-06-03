"""The actionable-alert gate.

Three independent conditions must all hold before an alert is emitted. The gate
is deliberately conservative: a missed signal is cheap, alert fatigue is
expensive.
"""

from __future__ import annotations

from dataclasses import dataclass

from pulsecrm.config import GatingConfig, TaxonomyConfig
from pulsecrm.models import Classification


@dataclass
class GateDecision:
    actionable: bool
    reason: str


class Gate:
    def __init__(self, gating: GatingConfig, taxonomy: TaxonomyConfig):
        self.confidence_threshold = gating.confidence_threshold
        self.require_staff_action = gating.require_staff_action
        self.ignored_authors = set(gating.ignored_authors)
        self.actionable_intents = taxonomy.actionable_names

    def is_ignored(self, author_id: str) -> bool:
        return author_id in self.ignored_authors

    def evaluate(self, classification: Classification | None) -> GateDecision:
        if classification is None:
            return GateDecision(False, "no_classification")

        # Gate 1: intent must be actionable in the taxonomy
        if classification.intent not in self.actionable_intents:
            return GateDecision(False, f"intent_not_actionable:{classification.intent}")

        # Gate 2: confidence must clear the threshold
        if classification.confidence < self.confidence_threshold:
            return GateDecision(
                False,
                f"below_confidence:{classification.confidence:.2f}<{self.confidence_threshold:.2f}",
            )

        # Gate 3: staff action must be needed (when required)
        if self.require_staff_action and not classification.needs_staff_action:
            return GateDecision(False, "no_staff_action_needed")

        return GateDecision(True, "ok")

    def is_actionable(self, classification: Classification | None) -> bool:
        return self.evaluate(classification).actionable
