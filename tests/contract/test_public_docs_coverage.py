# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every module carrying a public call that feature 015 adds is published.

Scoped to the feature's own modules, not to every export — a repository-wide
assertion would fail on gaps that pre-date it and get skipped.

``cuemsutils.xml.descriptor`` is **excluded on purpose**: ``cuemsutils.xml`` is
private by decision, and the descriptor contract (G3) is published at
``ConfigManager.get_schema_descriptor``. An exclusion with its reason is a
decision; without it, a later reader adds the module and re-opens that.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[2] / "docs"

FEATURE_MODULES = [
    "cuemsutils.helpers",              # to_wire's documented projection (S4)
    "cuemsutils.errors",               # NodeIdentityCollisionError (S1)
    "cuemsutils.tools.NodeList",       # NodeIndex.set_alias (G4)
    "cuemsutils.config.network_map",   # the one-runtime-writer warning
    "cuemsutils.tools.ConfigBase",     # must_exist (G1)
    "cuemsutils.tools.ConfigManager",  # project_settings, get_schema_descriptor (G1-G3)
]

EXCLUDED = {
    "cuemsutils.xml.descriptor": "cuemsutils.xml is private; G3 is published at "
    "ConfigManager.get_schema_descriptor",
}


def _rendered() -> set[str]:
    rendered = set()
    for page in DOCS.glob("*.md"):
        rendered.update(re.findall(r"^:::\s+(\S+)", page.read_text(), re.M))
    return rendered


@pytest.mark.parametrize("module", FEATURE_MODULES)
def test_the_module_is_rendered(module):
    assert module in _rendered(), (
        f"{module} carries a public addition of feature 015 and no docs/*.md "
        "mkdocstrings directive renders it"
    )


def test_the_exclusion_is_a_recorded_decision_not_an_oversight():
    assert not set(EXCLUDED) & _rendered(), "an excluded module was rendered; revisit its reason"
    assert all(EXCLUDED.values())
