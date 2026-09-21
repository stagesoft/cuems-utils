"""T085 — an empty ``<node_list/>`` resolves to ``ValueError``, never ``TypeError``.

Reported upstream by ``cuems-nodeconf``'s feature ``002-public-network-map-path``
(``specs/010-consumer-migration/empty-node-list-report.md``), measured rather
than inferred: ``NetworkMap.get_node`` raised
``TypeError: 'NoneType' object is not iterable`` on the map
``../cuems-common`` actually ships.

**Why that is a merge blocker and not a rough edge.** ``cuems-common`` has
shipped ``/etc/cuems/network_map.xml`` with an empty ``<node_list/>`` since its
``f78c876`` — removing the placeholder controller, which was correct, because
the placeholder misrouted chrony and the log collector. So the failing input is
what *every* fresh install reads. ``cuems-nodeconf`` then finds the file
present, takes its "read the existing map" branch, and dies: its
``read_network_map`` catches ``ValueError`` (deliberately narrowly, so that
``SchemaError`` and friends still fail loudly) and nothing catches ``TypeError``.
Its unit is ``Restart=on-failure``/``RestartSec=10``, so it retries and fails
identically forever — and **only** ``cuems-nodeconf`` writes a node into the
map, so nothing breaks the loop. ``cuems-engine``'s ``load_config()`` calls the
same ``load_network_map()`` and is exposed the same way.

**The trap in the fix**, recorded because the obvious repair does not work:
``node_list`` is ``minOccurs="0"``, and an empty ``<node_list/>`` decodes to a
key that is **present with value ``None``** — so ``.get('node_list', [])``
never fires its default. The neighbouring code at ``settings.py:187``/``:236``
is safe by its ``if not node_list:`` check, not by its default.

**The contract.** ``ConfigManager.node_network_map`` documents
``ValueError: if no node in the map carries this node's uuid``. An empty map is
precisely "no node carries this uuid", so ``ValueError`` is the answer already
specified — not a new one invented here. The message is pinned too: a consumer
logs it and ``cuems-nodeconf``'s
``test_reads_a_map_that_does_not_list_this_node_yet`` matches on it (FR-2).

Cases (a)-(c) below failed against ``6fd85fc`` and pass after the guard;
(d) and (e) are what make the fix *sufficient* rather than merely quieter —
the fresh-node boot sequence completes, and the found case is unchanged.

Every document here is an inline constant, following
``tests/contract/test_save_permissions.py`` (written the same way for the
previous report from this same consumer): no sibling checkout is needed for
the test to mean what it says. ``EMPTY_MAP`` is byte-identical to what
``../cuems-common`` ships at ``f2fc0f5`` (200 bytes).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

TESTS_DATA = Path(__file__).resolve().parent.parent / "data"

# Byte-identical to ../cuems-common's etc/cuems/network_map.xml at f2fc0f5.
EMPTY_MAP = b"""<?xml version='1.0' encoding='utf-8'?>
<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <node_list/>
</cms:CuemsNetworkMap>
"""

# The other minOccurs="0" shape: no <node_list> element at all. Equally valid
# against network_map.xsd, and a different decode (absent key, not None key),
# so a guard that only handles one of the two would pass half this file.
NO_NODE_LIST_MAP = b"""<?xml version='1.0' encoding='utf-8'?>
<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
"""

# One real node, so the guard can be shown not to have changed the found case.
# Its uuid is the one tests/data/settings.xml carries as this node's.
PRESENT_UUID = "0367f391-ebf4-48b2-9f26-000000000001"
ABSENT_UUID = "0367f391-ebf4-48b2-9f26-0000000000ff"

POPULATED_MAP = (
    "<?xml version='1.0' encoding='utf-8'?>\n"
    '<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<node_list><node>"
    f"<uuid>{PRESENT_UUID}</uuid>"
    "<mac>2cf05d21cca3</mac>"
    "<name>2cf05d21cca3._cuems_nodeconf._tcp.local.</name>"
    "<node_role>controller</node_role>"
    "<ip>192.168.1.10</ip>"
    "<adopted>True</adopted>"
    "<online>True</online>"
    "</node></node_list>"
    "</cms:CuemsNetworkMap>"
).encode("utf-8")


def _map_file(tmp_path: Path, payload: bytes, name: str = "network_map.xml") -> str:
    target = tmp_path / name
    target.write_bytes(payload)
    return str(target)


def _network_map(path: str):
    from cuemsutils.xml.settings import NetworkMap

    return NetworkMap(path)


# --------------------------------------------------------------------------
# (a) and (b) — the reported defect, in both minOccurs="0" shapes
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload, shape",
    [
        (EMPTY_MAP, "an empty <node_list/>"),
        (NO_NODE_LIST_MAP, "no <node_list> element at all"),
    ],
    ids=["empty-node-list", "absent-node-list"],
)
def test_get_node_raises_value_error_when_the_map_lists_no_nodes(tmp_path, payload, shape):
    """The report's reproduction. Fails against 6fd85fc with ``TypeError``."""
    netmap = _network_map(_map_file(tmp_path, payload))

    with pytest.raises(ValueError) as excinfo:
        netmap.get_node(PRESENT_UUID)

    assert not isinstance(excinfo.value, TypeError), (
        f"a map with {shape} raised TypeError; 'no nodes at all' is the same "
        "answer as 'no node with this uuid', which consumers catch as ValueError"
    )
    # FR-2: the wording is load-bearing — cuems-nodeconf logs it and pins it.
    assert str(excinfo.value) == f"Node with uuid {PRESENT_UUID} not found"


# --------------------------------------------------------------------------
# (c) — the same, at the public boundary consumers actually call
# --------------------------------------------------------------------------


@pytest.fixture
def conf_dir_with(tmp_path, monkeypatch):
    """A scratch copy of ``tests/data`` whose ``network_map.xml`` is ours.

    ``ConfigManager`` needs the whole configuration directory (``ConfigBase``
    loads ``settings.xml`` on construction, which is where ``node_uuid`` comes
    from), so the map cannot be tested through it in isolation.
    """

    def _make(payload: bytes):
        conf = tmp_path / "conf"
        shutil.copytree(TESTS_DATA, conf, ignore=shutil.ignore_patterns("corpus"))
        (conf / "network_map.xml").write_bytes(payload)
        monkeypatch.setenv("CUEMS_CONF_PATH", str(conf))
        return conf

    return _make


@pytest.mark.parametrize(
    "payload", [EMPTY_MAP, NO_NODE_LIST_MAP], ids=["empty-node-list", "absent-node-list"]
)
def test_config_manager_load_network_map_raises_value_error_on_a_map_with_no_nodes(
    conf_dir_with, payload
):
    """``load_network_map``'s last step resolves *this* node through
    ``get_node``, so every consumer reaches the defect through here."""
    from cuemsutils.tools.ConfigManager import ConfigManager

    conf_dir_with(payload)
    manager = ConfigManager(load_all=False)

    with pytest.raises(ValueError) as excinfo:
        manager.load_network_map()

    assert not isinstance(excinfo.value, TypeError)
    assert "not found" in str(excinfo.value)


def test_constructing_a_config_manager_on_an_empty_map_also_raises_value_error(
    conf_dir_with,
):
    """The engine's actual call shape: ``ConfigManager()`` loads everything,
    so the exception surfaces from the constructor rather than from a method."""
    from cuemsutils.tools.ConfigManager import ConfigManager

    conf_dir_with(EMPTY_MAP)

    with pytest.raises(ValueError) as excinfo:
        ConfigManager()

    assert not isinstance(excinfo.value, TypeError)


# --------------------------------------------------------------------------
# (d) — the fresh-node boot sequence: load, refill, save, re-read
# --------------------------------------------------------------------------


def _a_node(uuid: str = PRESENT_UUID):
    from cuemsutils.config.network_map import node
    from cuemsutils.tools.NodeList import NodeRole

    return node(
        {
            "uuid": uuid,
            "mac": "2cf05d21cca3",
            "name": "2cf05d21cca3._cuems_nodeconf._tcp.local.",
            "node_role": NodeRole.controller,
            "ip": "192.168.1.10",
            "adopted": True,
            "online": True,
        }
    )


def test_an_empty_map_loads_refills_saves_and_re_reads(tmp_path):
    """FR-3 — what makes the fix sufficient rather than merely quieter.

    This is the sequence a fresh node performs on first boot: read the shipped
    empty map, write itself into it, and read it back. Every step but the first
    already worked; the first is what this feature repairs.
    """
    path = _map_file(tmp_path, EMPTY_MAP)

    document = _network_map(path).get_dict()
    assert not document.get("node_list"), "the shipped map starts with no nodes"

    document["node_list"] = [{"node": _a_node()}]
    document.save(path)

    reread = _network_map(path)
    found = reread.get_node(PRESENT_UUID)
    assert found["uuid"] == PRESENT_UUID
    assert found["mac"] == "2cf05d21cca3"
    # And the map is a normal populated map again in every other respect.
    with pytest.raises(ValueError):
        reread.get_node(ABSENT_UUID)


def test_refresh_fills_an_empty_map_from_discovery_and_writes_it(tmp_path):
    """The same sequence through ``refresh`` — the domain entry point
    ``cuems-nodeconf`` drives, rather than a hand-assigned ``node_list``.

    ``refresh`` already guards its own iteration with ``or []``; this keeps it
    that way, because it is the step immediately after the one that was
    broken and a regression there would resurrect the same boot failure.
    """
    path = _map_file(tmp_path, EMPTY_MAP)
    document = _network_map(path).get_dict()

    wrote = document.refresh({"2cf05d21cca3": _a_node()}, path)

    assert wrote is True, "an empty map plus one discovered node is a change"
    assert _network_map(path).get_node(PRESENT_UUID)["uuid"] == PRESENT_UUID


# --------------------------------------------------------------------------
# (e) — the found case is untouched
# --------------------------------------------------------------------------


def test_a_populated_map_still_resolves_a_present_uuid(tmp_path):
    netmap = _network_map(_map_file(tmp_path, POPULATED_MAP))

    found = netmap.get_node(PRESENT_UUID)

    assert found["uuid"] == PRESENT_UUID
    assert found["ip"] == "192.168.1.10"


def test_a_populated_map_still_raises_value_error_for_an_absent_uuid(tmp_path):
    """The pre-existing behaviour the guard must not widen: a map *with*
    nodes, none of which is the one asked for, answers exactly as before."""
    netmap = _network_map(_map_file(tmp_path, POPULATED_MAP))

    with pytest.raises(ValueError) as excinfo:
        netmap.get_node(ABSENT_UUID)

    assert str(excinfo.value) == f"Node with uuid {ABSENT_UUID} not found"
