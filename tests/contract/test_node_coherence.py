"""Contract C9 — coherence holds after the rename.

Restates data-model.md §5's assertions 1 and 3 as tests C1 does not already
cover: the model's declared fields match the schema's derived fields, and no
``network_map`` type is bound to ``GENERIC``. Assertion 2 (adapter coverage)
is T034 in ``test_node_typing.py``.
"""

from __future__ import annotations

from cuemsutils.config.network_map import node
from cuemsutils.xml.registry import get_registry
from cuemsutils.xml.spec import derive_named


def test_node_declared_fields_equal_the_schema_derived_fields():
    schema_names = {f.name for f in derive_named("network_map", "NodeType").fields}
    assert set(node.declared_fields()) == schema_names


def test_no_network_map_type_is_bound_to_generic():
    registry = get_registry("network_map")
    for type_name in registry.complex_type_names():
        binding = registry.binding_for(type_name)
        assert binding is not None, type_name
        assert not binding.is_generic, type_name
