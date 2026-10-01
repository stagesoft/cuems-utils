# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T058 — ``partition_by_adoption`` is reachable from ``cuemsutils.tools`` (FR-035, SC-014).

UR-1: the non-mutating adoption split existed only at
``cuemsutils.xml.settings.NetworkMap.partition_by_adoption``, and a consumer may
not import ``cuemsutils.xml`` (clarification Q14). So the one correct way to use
it was unavailable, and the mutating ``get_nodes_by_adoption`` was the only
reachable option.

**This test calls it.** An unused import of the name would pass without proving
the public function works, which is the failure mode SC-014 names.

**This module does not import ``cuemsutils.xml``**, and that is an assertion in
itself: ``import cuemsutils.tools.NodeList`` must not drag in the schema stack.
The assertions below are *copied* from ``tests/contract/test_adoption_selection.py``
rather than imported from it — importing that module would import whatever it
imports, and the point here is what this file's own import graph pulls in.
"""

from __future__ import annotations

import sys

from cuemsutils.tools.NodeList import partition_by_adoption


def _map(*nodes) -> dict:
    """A map shaped like ``ConfigManager.network_map``.

    ``node_list`` entries are ``{"node": <node>}`` wrappers — the config layer
    preserves that shape rather than collapsing it (feature 006's measured
    fact), so a test that hands in bare nodes would be testing a shape no
    caller holds.
    """
    return {"node_list": [{"node": dict(node)} for node in nodes]}


def test_the_name_is_importable_from_the_public_path():
    assert callable(partition_by_adoption)


def test_it_is_in_node_list_all():
    from cuemsutils.tools import NodeList

    assert "partition_by_adoption" in NodeList.__all__


def test_importing_node_list_does_not_load_the_schema_stack():
    """The reason this is a re-export with a module ``__getattr__``, not an import.

    A module-level ``from ..xml.settings import NetworkMap`` would load
    ``mapper``, then ``adapters``, and ``adapters._register_enums()`` imports
    ``NodeRole`` back out of ``NodeList`` while that module is still
    initializing — ``ImportError`` on a partially initialized module.
    """
    for name in [m for m in sys.modules if m.startswith("cuemsutils")]:
        del sys.modules[name]
    import cuemsutils.tools.NodeList  # noqa: F401

    assert "cuemsutils.xml.settings" not in sys.modules


def test_the_re_export_is_the_same_function_not_a_wrapper():
    from cuemsutils.xml.settings import NetworkMap

    assert partition_by_adoption is NetworkMap.partition_by_adoption


def test_it_partitions_adopted_from_unadopted():
    adopted, unadopted = partition_by_adoption(
        _map(
            {"uuid": "a", "adopted": True},
            {"uuid": "b", "adopted": False},
            {"uuid": "c", "adopted": True},
        )
    )
    assert isinstance(adopted, tuple) and isinstance(unadopted, tuple)
    assert [n["uuid"] for n in adopted] == ["a", "c"]
    assert [n["uuid"] for n in unadopted] == ["b"]


def test_both_results_are_bare_nodes_not_wrappers():
    adopted, unadopted = partition_by_adoption(
        _map({"uuid": "a", "adopted": True}, {"uuid": "b", "adopted": False})
    )
    for side in (adopted, unadopted):
        for element in side:
            assert "node" not in element, (
                "the result carries the config layer's {'node': ...} wrapper; "
                "the contract is bare node objects"
            )


def test_an_empty_side_is_an_empty_tuple():
    adopted, unadopted = partition_by_adoption(_map({"uuid": "a", "adopted": True}))
    assert unadopted == ()
    adopted, unadopted = partition_by_adoption(_map({"uuid": "a", "adopted": False}))
    assert adopted == ()


def test_the_string_shape_of_adopted_is_still_accepted():
    """A caller may hold the pre-typing shape; the conversion is tolerant."""
    adopted, unadopted = partition_by_adoption(
        _map({"uuid": "a", "adopted": "True"}, {"uuid": "b", "adopted": "False"})
    )
    assert [n["uuid"] for n in adopted] == ["a"]
    assert [n["uuid"] for n in unadopted] == ["b"]


def test_the_input_map_is_unchanged():
    """Non-mutating is the whole reason this function exists (research R7)."""
    import copy

    network_map = _map(
        {"uuid": "a", "adopted": True}, {"uuid": "b", "adopted": False}
    )
    before = copy.deepcopy(network_map)
    partition_by_adoption(network_map)
    assert network_map == before


def test_this_test_module_does_not_import_cuemsutils_xml():
    """The surface claim, asserted on this file's own source."""
    from pathlib import Path

    source = Path(__file__).read_text(encoding="utf-8")
    # One deliberate exception: ``test_the_re_export_is_the_same_function_not_a_wrapper``
    # has to name the implementation to assert identity with it. Every other
    # line must reach the function through ``cuemsutils.tools``.
    offenders = [
        line
        for line in source.splitlines()
        if "import" in line
        and "cuemsutils.xml" in line
        and "NetworkMap" not in line
    ]
    assert offenders == [], offenders
