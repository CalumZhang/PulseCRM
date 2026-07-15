"""Base class shared by all adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pulsecrm.config import BuildContext


class Adapter:
    """Common base for every adapter.

    The registry sets ``adapter_port`` / ``adapter_type`` when an adapter is
    registered. ``build()`` is the factory the pipeline calls — override it to
    resolve paths against ``ctx.base_dir`` or to read ``ctx.config``/taxonomy.
    The default simply forwards ``options`` as keyword arguments.
    """

    adapter_port: ClassVar[str] = ""
    adapter_type: ClassVar[str] = ""

    @classmethod
    def build(cls, options: dict, ctx: BuildContext):  # noqa: ARG003
        return cls(**options)
