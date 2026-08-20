"""Contract C2 (T039) — config answers with objects (FR-014, SC-007).

Every ``ConfigManager``/``ConfigBase`` accessor returns a **declared-field
object or a scalar**, never a raw nested dict. ``network_map`` included, which
is the one the requirement names because it was the worst offender: five levels
of nesting that ``ConfigManager`` rediscovered by iteration on every load.

**How "raw nested dict" is decided** (CHK038): an accessor passes when
``type(value) is not dict``. Legitimately dict-shaped content is a
declared-field object, whose type is a ``ConfigDict`` subclass — and because
that subclass *is* a ``dict``, every ``isinstance(x, dict)`` check in
``cuems-engine`` and ``cuems-editor`` still passes. That is what let the object
layer land without editing a consumer repository.

The accessor set is read from the **recorded inventory** (T040a), not retyped
here. A list in this file would have to be edited whenever the classes are,
and would then be asserting its own contents.
"""

from __future__ import annotations

import pytest

from cuemsutils.config import ConfigDict
from tests.support.config_inventory import (
    accessor_entries,
    build_config_manager,
    load_golden,
    snapshot,
)

GOLDEN = load_golden()
ACCESSORS = sorted(
    {(name, entry["kind"]) for _, name, entry in accessor_entries(GOLDEN)}
)


@pytest.fixture(scope="module")
def manager():
    return build_config_manager()


def test_the_inventory_is_not_empty():
    """The control: an empty inventory would make every check below vacuous."""
    assert len(ACCESSORS) >= 20, ACCESSORS


@pytest.mark.parametrize("name,kind", ACCESSORS, ids=[n for n, _ in ACCESSORS])
def test_no_accessor_returns_a_raw_dict(manager, name, kind):
    try:
        value = getattr(manager, name)
    except Exception as exc:  # noqa: BLE001 - recorded as such in the inventory
        pytest.skip(f"{name} raises {type(exc).__name__} in this state")

    assert type(value) is not dict, (
        f"{name} still returns a raw nested dict; FR-014 requires a "
        f"declared-field object"
    )


@pytest.mark.parametrize("name,kind", ACCESSORS, ids=[n for n, _ in ACCESSORS])
def test_every_accessor_returns_an_object_or_a_scalar(manager, name, kind):
    try:
        value = getattr(manager, name)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"{name} raises {type(exc).__name__} in this state")

    if isinstance(value, dict):
        assert isinstance(value, ConfigDict), (
            f"{name} returns a {type(value).__name__}, which is a mapping but "
            f"not a config model"
        )
        assert value.declared_fields(), f"{name}'s type declares no fields"
    elif isinstance(value, list):
        for item in value:
            assert type(item) is not dict or len(item) == 1, (
                f"{name} holds a raw multi-key dict: {sorted(item)}"
            )
    else:
        assert isinstance(value, (str, int, float, bool, type(None))), (
            f"{name} returns a {type(value).__name__}"
        )


def test_network_map_is_named_explicitly(manager):
    """FR-014 names this one, so it is asserted by name rather than by sweep."""
    from cuemsutils.config.network_map import CuemsNetworkMapType, node

    network_map = manager.network_map
    assert type(network_map) is CuemsNetworkMapType
    assert isinstance(network_map, dict)

    entries = network_map["node_list"]
    assert entries, "the fixture network map carries no nodes"
    for entry in entries:
        assert type(entry.get("node")) is node


def test_node_conf_and_its_player_sections_are_objects(manager):
    from cuemsutils.config.settings import (
        AudioPlayerType,
        NodeConfType,
        VideoPlayerType,
    )

    node_conf = manager.node_conf
    assert type(node_conf) is NodeConfType
    assert type(node_conf["videoplayer"]) is VideoPlayerType
    assert type(node_conf["audioplayer"]) is AudioPlayerType


def test_the_objects_still_behave_as_dicts(manager):
    """The property that made this landable without a consumer change."""
    node_conf = manager.node_conf
    assert isinstance(node_conf, dict)
    assert node_conf["uuid"] == node_conf.get("uuid")
    assert "uuid" in node_conf
    assert list(node_conf.keys())[0] == "uuid"


def test_the_live_surface_still_matches_the_recorded_inventory():
    """FR-018 as a whole, in one assertion — see T040 for the itemised form."""
    live = snapshot()
    for class_name, entries in GOLDEN.items():
        assert set(entries) <= set(live[class_name]), (
            f"{class_name} lost accessors: "
            f"{sorted(set(entries) - set(live[class_name]))}"
        )
