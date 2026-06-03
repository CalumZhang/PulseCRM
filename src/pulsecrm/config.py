"""Configuration models and loader.

A single YAML file wires the whole pipeline. Each stage names an adapter
``type`` and passes it ``options``. The taxonomy (your intents) and gating
thresholds are configuration, not code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class AdapterConfig(BaseModel):
    type: str
    options: dict = Field(default_factory=dict)


class KnowledgeConfig(AdapterConfig):
    match_confidence_threshold: float = 0.80


class IntentSpec(BaseModel):
    name: str
    emoji: str = ""
    label: str = ""
    actionable: bool = True

    def resolved_label(self) -> str:
        return self.label or self.name.replace("_", " ").title()


class TaxonomyConfig(BaseModel):
    intents: list[IntentSpec] = Field(default_factory=list)

    def by_name(self, name: str) -> IntentSpec | None:
        for i in self.intents:
            if i.name == name:
                return i
        return None

    @property
    def names(self) -> list[str]:
        return [i.name for i in self.intents]

    @property
    def actionable_names(self) -> set[str]:
        return {i.name for i in self.intents if i.actionable}


class GroupingConfig(BaseModel):
    window_seconds: int = 60
    max_group_size: int = 20


class GatingConfig(BaseModel):
    confidence_threshold: float = 0.65
    require_staff_action: bool = True
    ignored_authors: list[str] = Field(default_factory=list)


class GroupContextConfig(BaseModel):
    recent_messages: int = 10


def _default_taxonomy() -> TaxonomyConfig:
    return TaxonomyConfig(
        intents=[
            IntentSpec(name="purchase_interest", emoji="\U0001f4b0", label="Purchase Interest", actionable=True),
            IntentSpec(name="question", emoji="❓", label="Question", actionable=True),
            IntentSpec(name="bug_report", emoji="\U0001f41b", label="Bug Report", actionable=True),
            IntentSpec(name="feedback", emoji="\U0001f4a1", label="Feedback", actionable=True),
            IntentSpec(name="other", emoji="\U0001f4cc", label="Other", actionable=True),
            IntentSpec(name="noise", emoji="\U0001f4ac", label="Noise", actionable=False),
        ]
    )


class PulseConfig(BaseModel):
    source: AdapterConfig
    classifier: AdapterConfig
    notifier: AdapterConfig = AdapterConfig(type="console")
    knowledge: KnowledgeConfig | None = None
    drafter: AdapterConfig | None = None
    ticket_sink: AdapterConfig | None = None
    enrichers: list[AdapterConfig] = Field(default_factory=list)
    grouping: GroupingConfig = GroupingConfig()
    gating: GatingConfig = GatingConfig()
    taxonomy: TaxonomyConfig = Field(default_factory=_default_taxonomy)
    context: GroupContextConfig = GroupContextConfig()


@dataclass
class BuildContext:
    """Passed to every adapter's ``build()`` so it can resolve paths / read config."""

    base_dir: Path
    config: PulseConfig


def load_config(path: str | Path) -> tuple[PulseConfig, BuildContext]:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    raw = yaml.safe_load(p.read_text()) or {}
    config = PulseConfig.model_validate(raw)
    ctx = BuildContext(base_dir=p.parent, config=config)
    return config, ctx
