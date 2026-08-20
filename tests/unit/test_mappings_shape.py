"""FR-017, SC-007 (T043) — the mappings data has exactly **one** shape.

F15: three mutually incompatible readings of one document existed in this
package at once.

===============================================  ==========================================
where                                            what it indexed
===============================================  ==========================================
``ConfigManager.load_net_and_node_mappings``     ``node[section]`` as a list of port groups
``VideoCue.check_mappings``                      ``['video'][0]['outputs']``
``AudioCue.check_mappings``                      ``['audio'][0]['outputs']``
``ProjectMappings.process_network_mappings``     a fourth, flattened reshaping
===============================================  ==========================================

Two of them were **unreachable** — dead behind an unconditional
``return super().check_mappings()`` — and the fourth was called by nothing. So
three of the four were fossils, and preserving any of them would have meant
choosing between them on no evidence: *a shape assumption no test can reach is
not a contract*.

This file asserts the resolution rather than the deletion. The shape is stated
once, by the derived types in ``cuemsutils.config.mappings``, and the one live
consumer reads it. Nothing here checks that the old code is absent — a grep can
do that, and it would pass forever after the first commit. What it checks is
that no *alternative* is reachable.
"""

from __future__ import annotations

import inspect

import pytest

from cuemsutils.config import mappings as models
from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.VideoCue import VideoCue
from tests.support.config_inventory import build_config_manager


@pytest.fixture(scope="module")
def manager():
    return build_config_manager()


def test_the_shape_is_declared_once_per_level(manager):
    """Each level of the nesting is a named type, and only one.

    The nesting is real and stays: a node has devices, a device has port
    groups, a group has ports, a port has mappings. What went is rediscovering
    it by iteration at every level.
    """
    node = manager.node_mappings
    assert type(node) is models.NodeType

    groups = node["audio"]
    assert isinstance(groups, list), type(groups).__name__

    ports = groups[0]["outputs"]
    assert isinstance(ports, list)

    port = next(iter(ports[0].values()))
    assert type(port) is models.PutType
    assert set(port) <= set(models.PutType.declared_fields())

    assert isinstance(port["mappings"], list)
    assert all("mapped_to" in m for m in port["mappings"])


def test_the_video_shape_is_the_same_shape(manager):
    """``VideoPutType`` differs from ``PutType`` by ``canvas_region`` and
    nothing else — which is what the schema says, and is the only difference
    the deleted fossils could legitimately have been about."""
    node = manager.node_mappings
    video = node["video"]
    port = next(iter(video[0]["outputs"][0].values()))
    assert type(port) is models.VideoPutType
    assert set(models.VideoPutType.declared_fields()) - set(
        models.PutType.declared_fields()
    ) == {"canvas_region"}


def test_no_unreachable_alternative_survives():
    """Both ``check_mappings`` overrides are now delegations and nothing more.

    Asserted on the *reachable* body rather than by searching for deleted text:
    what matters is that the method cannot express a second shape, not that a
    particular string is absent.
    """
    import ast
    import textwrap

    for cls in (VideoCue, AudioCue):
        tree = ast.parse(textwrap.dedent(inspect.getsource(cls.check_mappings)))
        function = tree.body[0]
        statements = [
            node
            for node in function.body
            if not (
                isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
            )
        ]
        assert len(statements) == 1, (
            f"{cls.__name__}.check_mappings has {len(statements)} statements; "
            f"it must be the delegation and nothing else"
        )
        assert isinstance(statements[0], ast.Return), ast.dump(statements[0])


def test_the_reshaping_helper_is_gone():
    """``process_network_mappings`` was F15's fourth shape, called by nothing."""
    from cuemsutils.xml.settings import ProjectMappings

    assert not hasattr(ProjectMappings, "process_network_mappings")


def test_the_dead_config_xml_builders_are_gone():
    """``data2xml``/``buildxml`` — a second, shape-guessing XML writer (D3)."""
    from cuemsutils.xml.settings import Settings

    assert not hasattr(Settings, "data2xml")
    assert not hasattr(Settings, "buildxml")


def test_every_call_site_reads_the_same_shape(manager):
    """The two live readers agree, because they call the same helper.

    ``load_net_and_node_mappings`` and ``check_project_mappings`` both unwrap a
    port with ``_unwrap_put`` and both address the device sections through
    ``_DEVICE_SECTIONS``. That is what "one shape, identical at every call
    site" means operationally.
    """
    from cuemsutils.tools import ConfigManager as module

    for method in (
        module.ConfigManager.load_net_and_node_mappings,
        module.ConfigManager.check_project_mappings,
    ):
        source = inspect.getsource(method)
        assert "_DEVICE_SECTIONS" in source
        assert "_unwrap_put" in source
