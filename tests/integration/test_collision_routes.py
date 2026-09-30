# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T082 — the four collision routes are closed or refused (SC-013, M-l).

Two nodes sharing one identity is the failure this feature exists to make
impossible, not merely to repair once. M-l enumerated four ways a cluster gets
there; this file walks all four in one place, because each is closed by a
different mechanism in a different module and nothing else asserts that the set
is covered.

**Why a shared identity is unrecoverable rather than merely wrong**: in the
configuration documents the MAC discriminates, so a split would be safe. In the
project library it does not exist — the compound ``<identity>_<output>`` prefix
is the only record of which node an output belongs to. A tool that split a
shared identity would silently reassign one node's entire output set, and the
first symptom would be a show with outputs resolving to nothing.
"""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from cuemsutils.errors import ValidationError
from cuemsutils.tools import init_node, remint
from cuemsutils.tools.ConfigBase import load_config_document
from cuemsutils.xml.settings import NetworkMap
from tests.support.cluster_fixture import (
    SHAPES,
    NodeSpec,
    build_cluster,
    mac_for,
    network_map_xml,
)
from tests.support.remint_harness import documents_snapshot, run_remint, state_dir


def _sysfs(tmp_path: Path, mac: str) -> Path:
    root = tmp_path / "sys-class-net"
    (root / "ethernet0").mkdir(parents=True, exist_ok=True)
    (root / "ethernet0" / "address").write_text(mac + "\n")
    return root


def _init_node(conf, tmp_path, sysfs, *extra) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = init_node.main([
            "--conf-dir", str(conf), "--state-dir", str(tmp_path / "state"),
            "--sysfs", str(sysfs), "--lock-file", str(tmp_path / "lock"),
            "--systemctl", "/bin/false", "--no-overlay", *extra,
        ])
    return code, out.getvalue() + err.getvalue()


# --- route 1: cloning a provisioned disk (FR-019d) --------------------------


def test_route_1_a_cloned_disk_is_refused(tmp_path):
    """Amends feature 011's D13. "Mint iff there is none" is precisely what
    makes a clone keep the original's identity — and cloning a provisioned disk
    is how venues provision."""
    conf = tmp_path / "etc"
    code, out = _init_node(conf, tmp_path, _sysfs(tmp_path, "aa:bb:cc:dd:ee:01"))
    assert code == 0, out
    import xml.etree.ElementTree as ET

    original = ET.parse(conf / "settings.xml").getroot().findtext(".//uuid")

    # the same disk, different hardware
    code, out = _init_node(conf, tmp_path, _sysfs(tmp_path / "clone", "aa:bb:cc:dd:ee:99"))

    assert code == 1
    assert "restored onto other hardware" in out
    assert ET.parse(conf / "settings.xml").getroot().findtext(".//uuid") == original


# --- route 2: an explicit --uuid that collides (FR-019b) --------------------


def test_route_2_a_colliding_explicit_identity_is_refused(tmp_path):
    conf = tmp_path / "etc"
    conf.mkdir()
    rows = [
        NodeSpec(SHAPES["uuid4"], mac_for(0), "controller", "n0", "10.0.0.1"),
        NodeSpec(SHAPES["uuid4b"], mac_for(1), "node", "n1", "10.0.0.2"),
    ]
    (conf / "network_map.xml").write_text(network_map_xml(rows), encoding="utf-8")

    code, out = _init_node(conf, tmp_path, _sysfs(tmp_path, "aa:bb:cc:dd:ee:01"),
                           "--uuid", SHAPES["uuid4b"])

    assert code == 1
    assert mac_for(1) in out
    assert not (conf / "settings.xml").exists(), "a refusal wrote something"


# --- route 3: a map that already collides (FR-019, FR-019a) -----------------


def test_route_3a_the_re_mint_aborts_over_an_existing_collision(tmp_path):
    cluster = build_cluster(tmp_path, identities=[SHAPES["uuid1"], SHAPES["uuid1"]])
    before = documents_snapshot(cluster)

    code, out = run_remint(cluster, state_dir(tmp_path))

    assert code == 1
    assert mac_for(0) in out and mac_for(1) in out
    assert documents_snapshot(cluster) == before
    assert not remint.table_path(state_dir(tmp_path)).is_file()


def test_route_3b_the_library_refuses_to_read_a_colliding_map(tmp_path):
    """The same route, closed a second time and at a different layer. Before
    this feature such a map *loaded* — ``NodeIndex.merge`` collapsed the
    duplicate silently — so every consumer saw one node where there were two."""
    rows = [
        NodeSpec(SHAPES["uuid4"], mac_for(0), "controller", "n0", "10.0.0.1"),
        NodeSpec(SHAPES["uuid4"], mac_for(1), "node", "n1", "10.0.0.2"),
    ]
    path = tmp_path / "network_map.xml"
    path.write_text(network_map_xml(rows), encoding="utf-8")

    with pytest.raises(ValidationError) as raised:
        load_config_document(NetworkMap, str(path), "network_map")
    assert mac_for(0) in str(raised.value) and mac_for(1) in str(raised.value)


def test_route_3c_the_silent_collapse_that_used_to_hide_it(tmp_path):
    """What the refusal replaced, asserted so the change is legible. ``merge``
    still collapses by identity — that is its job — which is exactly why the
    document must never contain a duplicate in the first place."""
    from cuemsutils.tools.NodeList import NodeIndex

    index = NodeIndex({
        mac_for(0): {"uuid": SHAPES["uuid4"], "mac": mac_for(0), "adopted": True},
        mac_for(1): {"uuid": SHAPES["uuid4"], "mac": mac_for(1), "adopted": False},
    })
    index.merge({mac_for(0): {"uuid": SHAPES["uuid4"], "mac": mac_for(0)}})
    # Both rows still exist in the index, but they answer to one identity — the
    # ambiguity the schema-level refusal now prevents from ever being written.
    assert len(index) == 2
    assert len({n["uuid"] for n in index.values()}) == 1


# --- route 4: two nodes minting independently (FR-019c) ---------------------


def test_route_4_a_plain_node_cannot_mint_its_own_table(tmp_path):
    """Closed by design rather than by a check: the table is built **once**, on
    the controller. A node that minted its own would give itself an identity the
    rest of the cluster has never heard of."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], self_index=1)
    state = state_dir(tmp_path)
    before = documents_snapshot(cluster)

    code, out = run_remint(cluster, state)

    assert code == 1
    assert "not the controller and no substitution table" in out
    assert not remint.table_path(state).is_file()
    assert documents_snapshot(cluster) == before


def test_route_4b_a_table_from_an_unauthorised_minter_is_refused(tmp_path):
    """The other half: even *with* a table, one minted by something that is not
    the cluster's controller is refused."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], self_index=1)
    rogue = remint.build_table([SHAPES["uuid1"], SHAPES["uuid5"]],
                               controller=SHAPES["uuid5"])
    handed = tmp_path / "rogue.json"
    rogue.save(handed)

    code, out = run_remint(cluster, state_dir(tmp_path),
                           extra=["--table", str(handed)])

    assert code == 1 and "no authority" in out


def test_route_4c_the_table_the_controller_built_is_accepted(tmp_path):
    """The control. A refusal that also refused the legitimate case would close
    the route by closing the operation."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], self_index=1)
    good = remint.build_table([SHAPES["uuid1"], SHAPES["uuid5"]],
                              controller=SHAPES["uuid1"],
                              scope=remint.CONFIGURATION)
    handed = tmp_path / "good.json"
    good.save(handed)

    code, out = run_remint(cluster, state_dir(tmp_path),
                           extra=["--table", str(handed)])

    assert code == 0, out


# --- the set itself ---------------------------------------------------------


def test_the_minted_values_cannot_collide_with_each_other(tmp_path):
    """A fifth way in, and the one nobody would think to check: the table's own
    minting. Vanishingly improbable, checked rather than trusted, because the
    failure would be silent and permanent."""
    table = remint.build_table(
        [f"{i:08x}-ebf4-11b2-9f26-{i:012x}" for i in range(200)], controller="c"
    )
    assert len(set(table.entries.values())) == len(table.entries) == 200
    table.check_invariants()


def test_every_route_is_covered_by_a_test_in_this_file():
    """The set is the deliverable (SC-013), so the enumeration is asserted too.
    A fifth route discovered later fails here until it is covered."""
    import inspect
    import sys

    source = inspect.getsource(sys.modules[__name__])
    for route in ("route_1", "route_2", "route_3a", "route_3b", "route_4", "route_4b"):
        assert f"def test_{route}" in source
