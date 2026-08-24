"""Contracts C10, C11 — the node public path, and no node-specific override."""

from __future__ import annotations

import cuemsutils.config as config_package
from cuemsutils.config.network_map import CuemsNetworkMapType, node, node_list
from cuemsutils.helpers import CuemsDict
from tests.support.config_inventory import build_config_manager


# -- C10 ----------------------------------------------------------------------


def test_cuemsutils_config_exports_nothing_publicly():
    assert config_package.__all__ == []


def test_node_role_and_node_index_import_from_tools_nodelist():
    from cuemsutils.tools.NodeList import NodeIndex, NodeRole  # noqa: F401


def test_node_re_exports_from_tools_nodelist_too():
    from cuemsutils.tools.NodeList import node as reexported_node

    assert reexported_node is node


# -- C11 ------------------------------------------------------------------


def _same_implementation(a, b) -> bool:
    """``a is b`` for a plain method; ``classmethod`` rebinds on every
    access, so ``A.declared_fields is B.declared_fields`` is always ``False``
    even when both resolve to the same underlying function — compare the
    underlying function instead."""
    return getattr(a, "__func__", a) is getattr(b, "__func__", b)


def test_node_answers_the_shared_protocol_through_inherited_implementations():
    """No node-specific override — node is the same kind of thing as every
    other model in the package."""
    assert _same_implementation(node.declared_fields, CuemsDict.declared_fields)
    assert node.items is CuemsDict.items
    assert node.to_wire is CuemsDict.to_wire
    assert node.to_json is CuemsDict.to_json
    assert node.__eq__ is CuemsDict.__eq__


def test_node_list_and_network_map_type_answer_through_the_same_implementations():
    for cls in (node_list, CuemsNetworkMapType):
        assert _same_implementation(cls.declared_fields, CuemsDict.declared_fields)
        assert cls.items is CuemsDict.items
        assert cls.to_wire is CuemsDict.to_wire
        assert cls.to_json is CuemsDict.to_json


def test_node_equality_and_copy_behave_like_every_other_model():
    """``copy`` is inherited from ``dict`` unmodified (no node-specific
    override) — including ``dict.copy``'s own behaviour of returning a plain
    ``dict``, not the subclass. That is the same behaviour every other model
    in the package has; asserting it here is asserting the *absence* of an
    override, not a preference for it."""
    cm = build_config_manager()
    n = cm.network_map["node_list"][0]["node"]

    assert node.copy is CuemsDict.copy is dict.copy
    copy = n.copy()
    assert dict(copy) == dict(n)
    assert copy is not n
    assert type(copy) is dict
