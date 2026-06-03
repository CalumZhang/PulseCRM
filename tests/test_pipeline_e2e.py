"""End-to-end test of the offline reference path on a temp workspace:
file_replay -> mock classifier -> markdown KB -> console notifier -> jsonl sink.
"""

import json
from pathlib import Path

from pulsecrm.config import BuildContext, PulseConfig
from pulsecrm.models import AlertEnvelope
from pulsecrm.pipeline import build_pipeline

MESSAGES = [
    {"event_id": "1", "author_id": "u1", "author_handle": "alex", "channel_name": "support",
     "content": "the editor crashes when I save", "created_at": "2026-06-03T10:00:00Z"},
    {"event_id": "2", "author_id": "u2", "author_handle": "bea", "channel_name": "general",
     "content": "lol nice meme", "created_at": "2026-06-03T10:01:00Z"},
    {"event_id": "3", "author_id": "u3", "author_handle": "cy", "channel_name": "general",
     "content": "how much does the pro plan cost?", "created_at": "2026-06-03T10:02:00Z"},
]


def _write_workspace(tmp_path: Path) -> Path:
    (tmp_path / "messages.jsonl").write_text(
        "\n".join(json.dumps(m) for m in MESSAGES)
    )
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "editor-crash.md").write_text(
        "# Editor crashes on save\n\n<public>\nUpdate and clear the cache, then save again.\n</public>\n"
        "<internal>\nsecret internal note\n</internal>\n"
    )
    return tmp_path


def _config(tmp_path: Path) -> PulseConfig:
    return PulseConfig.model_validate(
        {
            "source": {"type": "file_replay", "options": {"path": "messages.jsonl"}},
            "classifier": {"type": "mock"},
            "knowledge": {"type": "markdown", "options": {"path": "kb"}, "match_confidence_threshold": 0.2},
            "drafter": {"type": "templated"},
            "notifier": {"type": "console"},
            "ticket_sink": {"type": "jsonl", "options": {"path": "out/tickets.jsonl"}},
            "grouping": {"window_seconds": 120},
            "gating": {"confidence_threshold": 0.65, "require_staff_action": True},
        }
    )


async def test_pipeline_end_to_end(tmp_path):
    _write_workspace(tmp_path)
    cfg = _config(tmp_path)
    ctx = BuildContext(base_dir=tmp_path, config=cfg)
    pipeline = build_pipeline(cfg, ctx)

    stats = await pipeline.run()

    # 3 authors -> 3 groups; the bug + purchase alert, the meme is noise (gated out)
    assert stats["events"] == 3
    assert stats["groups"] == 3
    assert stats["alerts"] == 2
    assert stats["tickets"] == 2

    tickets_path = tmp_path / "out" / "tickets.jsonl"
    assert tickets_path.exists()
    rows = [json.loads(line) for line in tickets_path.read_text().splitlines() if line.strip()]
    assert len(rows) == 2
    intents = {r["intent"] for r in rows}
    assert "bug_report" in intents
    assert "purchase_interest" in intents

    # the bug ticket should reference the KB article and never leak internal notes
    bug = next(r for r in rows if r["intent"] == "bug_report")
    assert bug["kb_article"] == "editor-crash"
    assert "secret internal note" not in bug["body"]


async def test_envelopes_are_schema_valid(tmp_path):
    _write_workspace(tmp_path)
    cfg = _config(tmp_path)
    ctx = BuildContext(base_dir=tmp_path, config=cfg)
    pipeline = build_pipeline(cfg, ctx)

    events = await pipeline.collect_events()
    await pipeline.knowledge.sync()
    seen = 0
    for group in pipeline.grouper.group_events(events):
        result = await pipeline.process_group(group)
        if result.get("alerted"):
            AlertEnvelope.model_validate(result["envelope"].model_dump())
            seen += 1
    assert seen == 2
