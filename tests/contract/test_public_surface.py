# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T065 — the sentinel and the coercion rule are public (FR-031, FR-030).

"Public" here means one specific thing: a consumer must be able to **name** it,
and nothing in ``cuemsutils.xml`` counts, because consumers may not import that
package (clarification Q14). A rule published somewhere a consumer cannot reach
is published to nobody.

Both are declared in ``__all__`` as well as importable, because ``__all__`` is
what says *this is surface* rather than *this happens to be reachable*.
"""

from __future__ import annotations

import importlib


def test_the_sentinel_constant_is_reachable_from_cuemsutils_tools():
    import cuemsutils.tools as tools

    assert tools.SENTINEL == "00000000-0000-0000-0000-000000000000"
    assert "SENTINEL" in tools.__all__


def test_the_coercion_rule_is_reachable_from_cuemsutils_tools():
    import cuemsutils.tools as tools

    assert callable(tools.coerce_identity)
    assert "coerce_identity" in tools.__all__


def test_the_sentinel_is_declared_in_the_module_it_lives_in():
    """T070. Declared public **where it already was** (assumption 7) rather than
    relocated, so nothing a consumer imports has moved."""
    from cuemsutils.tools import identity_check

    assert "SENTINEL" in identity_check.__all__
    assert identity_check.SENTINEL == "00000000-0000-0000-0000-000000000000"


def test_the_two_sentinels_are_distinguished_by_documentation():
    """The tool holds two constants that answer to the name, and both are
    published (library-surface.md §3). Each must say which question it answers,
    or a consumer will compare an identity against a human-readable status
    string and get ``False`` forever.
    """
    from cuemsutils.tools import identity_check, ids

    assert identity_check.SENTINEL != identity_check.NOT_PROVISIONED
    assert identity_check.NOT_PROVISIONED == "NOT PROVISIONED"

    import inspect
    import re

    def flat(text):
        """Comment markers and line wrapping removed, so the assertion is about
        the words rather than about where the 79th column fell."""
        return re.sub(r"\s+", " ", text.replace("#:", " "))

    head = flat(inspect.getsource(identity_check).split("UUID_TOKEN")[0])
    assert "is this node provisioned" in head
    assert "what should this line of output say" in head

    # ``ids`` is where the value is defined, so it carries the same
    # distinction: a reader who arrives at the constant rather than at the
    # re-export must find it there too.
    published = flat(inspect.getsource(ids))
    assert "is this node provisioned" in published
    assert "what should this line of output say" in published


def test_the_one_value_has_one_definition():
    """Two names for one string is fine; two *spellings* of it is a drift
    waiting to happen."""
    from cuemsutils.tools import identity_check, ids

    assert identity_check.SENTINEL is ids.NOT_PROVISIONED_UUID


def test_neither_is_published_from_cuemsutils_xml():
    """FR-030's placement requirement, asserted rather than assumed."""
    xml = importlib.import_module("cuemsutils.xml")

    assert xml.__all__ == []
    assert not hasattr(xml, "coerce_identity")


def test_importing_the_facade_does_not_drag_in_the_schema_layer():
    """The reason this package's body stayed empty for two features. A consumer
    that wanted one constant must not pay for the whole XML engine, and a
    ``__init__`` that imported ``ConfigManager`` would make every
    ``cuemsutils.tools.*`` import do exactly that."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; import cuemsutils.tools; "
         "print('cuemsutils.xml.schema' in sys.modules); "
         "print('xmlschema' in sys.modules)"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.split() == ["False", "False"], result.stdout
