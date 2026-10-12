# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The public configuration and node-identity façade (D15).

This package's modules are the ones a consumer names: ``ConfigManager``,
``ConfigBase``, ``NodeList``, ``CTimecode``, ``HubServices``, ``SignalEngine``.
``cuemsutils.config`` and ``cuemsutils.xml`` are internal by contrast — a
consumer may not import either (clarification Q14), which is why anything a
consumer must be able to *name* has to be reachable from here.

Feature 012 re-exports two such things (FR-030, FR-031). They are re-exported
rather than relocated (assumption 7): the names stay where they already were, so
nothing a consumer imports today has moved.

**The package body stays eager for exactly two names.** Importing
``ConfigManager`` here would make ``import cuemsutils.tools.CTimecode`` pull in
``cuemsutils.xml`` and the whole schema layer — which is the import cost the
``from .module import Name`` convention across this codebase exists to avoid.
``SENTINEL`` and ``coerce_identity`` cost one small module each (``ids`` imports
only ``re``, ``dataclasses`` and ``pathlib``; ``identity_check`` adds stdlib
XML), and ``ids`` defers its own ``Uuid`` import into the one function that
needs it.

Feature 013 publishes a third name, ``validate_config_document`` (FR-036), and it
is **lazy** rather than eager because ``config_validate`` does reach the schema
layer. The name is on the façade; the cost is paid when the name is used. This
is why the rule above is now "eager for two" rather than "otherwise empty": the
distinction that matters is not how many names are here, it is that importing
any *other* module in this package must not drag the schemas in —
``tests/contract/test_validate_config_document.py`` asserts that in a
subprocess, and asserts the laziness structurally on this file's AST.
"""

from .identity_check import SENTINEL
from .ids import coerce_identity

__all__ = ["SENTINEL", "coerce_identity", "validate_config_document"]

#: Lazily published names: ``attribute -> module`` within this package.
_LAZY = {"validate_config_document": ".config_validate"}


def __getattr__(name: str):
    """Resolve a lazily published name on first access."""
    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    return getattr(import_module(module_name, __package__), name)


def __dir__() -> list[str]:
    """``dir()`` answers with the published names, lazy ones included.

    Without this a lazily published name is invisible to ``dir()`` and to
    anything that enumerates the package — including the public-API snapshot,
    which is how this name is pinned (T061).
    """
    return sorted({*globals(), *_LAZY})
