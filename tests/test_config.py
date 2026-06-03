from pathlib import Path

from pulsecrm.config import PulseConfig, _default_taxonomy, load_config

REPO = Path(__file__).resolve().parents[1]


def test_default_taxonomy_has_noise_non_actionable():
    taxo = _default_taxonomy()
    assert "noise" in taxo.names
    assert "noise" not in taxo.actionable_names
    assert "bug_report" in taxo.actionable_names


def test_load_quickstart_config():
    cfg, ctx = load_config(REPO / "examples" / "quickstart" / "pulse.yaml")
    assert cfg.source.type == "file_replay"
    assert cfg.classifier.type == "mock"
    assert cfg.knowledge is not None and cfg.knowledge.type == "markdown"
    assert cfg.ticket_sink is not None and cfg.ticket_sink.type == "jsonl"
    # paths are resolved relative to the config dir
    assert ctx.base_dir == (REPO / "examples" / "quickstart").resolve()


def test_minimal_config_uses_defaults():
    cfg = PulseConfig.model_validate(
        {"source": {"type": "file_replay"}, "classifier": {"type": "mock"}}
    )
    assert cfg.notifier.type == "console"  # default
    assert cfg.grouping.window_seconds == 60
    assert cfg.gating.confidence_threshold == 0.65
    assert "noise" in cfg.taxonomy.names  # default taxonomy
