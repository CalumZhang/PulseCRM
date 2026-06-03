"""Built-in adapters, grouped by port.

Each module registers its adapter(s) with the registry via ``@register`` when
imported. ``registry._load_builtins()`` imports them on demand.
"""
