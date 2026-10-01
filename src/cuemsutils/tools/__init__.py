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

**The package body stays otherwise empty on purpose.** Importing
``ConfigManager`` here would make ``import cuemsutils.tools.CTimecode`` pull in
``cuemsutils.xml`` and the whole schema layer — which is the import cost the
``from .module import Name`` convention across this codebase exists to avoid.
The two names below cost one small module each (``ids`` imports only ``re``,
``dataclasses`` and ``pathlib``; ``identity_check`` adds stdlib XML), and
``ids`` defers its own ``Uuid`` import into the one function that needs it.
"""

from .identity_check import SENTINEL
from .ids import coerce_identity

__all__ = ["SENTINEL", "coerce_identity"]
