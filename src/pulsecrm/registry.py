"""Adapter registry.

Maps ``(port, type-name)`` to an adapter class. Built-in adapters register
themselves via the ``@register`` decorator when their module is imported;
``_load_builtins()`` imports them lazily on first use. Third-party packages can
register adapters without forking by exposing a callable through the
``pulsecrm.adapters`` entry-point group.
"""

from __future__ import annotations

import importlib
from importlib import metadata
from typing import Callable

PORTS = (
    "source",
    "classifier",
    "knowledge",
    "drafter",
    "notifier",
    "ticket_sink",
    "enricher",
)

_REGISTRY: dict[str, dict[str, type]] = {p: {} for p in PORTS}
_BUILTINS_LOADED = False
_ENTRYPOINTS_LOADED = False

# Built-in adapter modules, imported on demand. Adding a built-in adapter =
# add its module path here (and decorate the class with @register).
_BUILTIN_MODULES = (
    "pulsecrm.adapters.sources.file_replay",
    "pulsecrm.adapters.sources.discord",
    "pulsecrm.adapters.classifiers.mock",
    "pulsecrm.adapters.classifiers.openai",
    "pulsecrm.adapters.knowledge.markdown",
    "pulsecrm.adapters.knowledge.notion",
    "pulsecrm.adapters.drafters.templated",
    "pulsecrm.adapters.drafters.llm",
    "pulsecrm.adapters.notifiers.console",
    "pulsecrm.adapters.notifiers.slack",
    "pulsecrm.adapters.ticket_sinks.jsonl",
    "pulsecrm.adapters.ticket_sinks.notion",
    "pulsecrm.adapters.ticket_sinks.linear",
    "pulsecrm.adapters.enrichers.attachment_sync",
    "pulsecrm.adapters.enrichers.phone_lookup",
)


def register(port: str, name: str) -> Callable[[type], type]:
    if port not in _REGISTRY:
        raise ValueError(f"Unknown port {port!r}. Valid ports: {', '.join(PORTS)}")

    def deco(cls: type) -> type:
        cls.adapter_port = port  # type: ignore[attr-defined]
        cls.adapter_type = name  # type: ignore[attr-defined]
        _REGISTRY[port][name] = cls
        return cls

    return deco


def _load_builtins() -> None:
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    _BUILTINS_LOADED = True
    for mod in _BUILTIN_MODULES:
        try:
            importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001 — a broken optional adapter shouldn't kill discovery
            # Adapters import their SDK lazily, so import failures here are unexpected;
            # surface them without crashing the whole registry.
            print(f"[registry] warning: could not import built-in {mod}: {exc}")


def _load_entrypoints() -> None:
    global _ENTRYPOINTS_LOADED
    if _ENTRYPOINTS_LOADED:
        return
    _ENTRYPOINTS_LOADED = True
    try:
        eps = metadata.entry_points(group="pulsecrm.adapters")
    except Exception:  # noqa: BLE001
        return
    for ep in eps:
        try:
            obj = ep.load()
            if callable(obj):
                obj()  # convention: a function that imports/registers the package's adapters
        except Exception as exc:  # noqa: BLE001
            print(f"[registry] warning: failed loading entry-point {ep.name!r}: {exc}")


def _ensure_loaded() -> None:
    _load_builtins()
    _load_entrypoints()


def get(port: str, name: str) -> type:
    _ensure_loaded()
    if port not in _REGISTRY:
        raise ValueError(f"Unknown port {port!r}")
    try:
        return _REGISTRY[port][name]
    except KeyError:
        available = ", ".join(sorted(_REGISTRY[port])) or "(none)"
        raise KeyError(
            f"No adapter registered for {port}.{name!r}. Available {port} adapters: {available}"
        ) from None


def available() -> dict[str, list[str]]:
    _ensure_loaded()
    return {port: sorted(names) for port, names in _REGISTRY.items()}
