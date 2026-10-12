# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T061 — one type for one value (FR-028, SC-010).

The defect this closes (M-a): on a provisioned node, the same node identity came
back as a ``str`` from ``ConfigManager.node_uuid`` and as a ``Uuid`` from a map
row, because ``network_map`` ran the adapter table and ``settings`` did not. A
consumer holding both had two types for one value and no way to know which it
had without checking.

The type now varies **only** between provisioned and not provisioned, and
identically from every accessor. That is the one documented exception in
FR-028, and the reason a consumer needs exactly one check (M-d) rather than a
conversion at every site.
"""

from __future__ import annotations

from cuemsutils.tools import ids
from cuemsutils.tools.ConfigManager import ConfigManager
from cuemsutils.tools.Uuid import Uuid
from tests.support.cluster_fixture import SHAPES, build_cluster


def _manager(tmp_path, identity):
    cluster = build_cluster(tmp_path, identities=[identity, SHAPES["uuid4b"]])
    manager = ConfigManager(config_dir=str(cluster.conf), load_all=False)
    manager.load_config()
    return manager, cluster


def test_the_own_identity_and_a_map_identity_have_the_same_type(tmp_path):
    manager, cluster = _manager(tmp_path, SHAPES["uuid4"])
    own = manager.node_uuid
    row = manager.network_map["node_list"][0]["node"]["uuid"]
    assert type(own) is type(row) is Uuid


def test_they_compare_equal(tmp_path):
    manager, _cluster = _manager(tmp_path, SHAPES["uuid4"])
    own = manager.node_uuid
    row = manager.network_map["node_list"][0]["node"]["uuid"]
    assert own == row
    assert hash(own) == hash(row)
    assert len({own, row}) == 1


def test_the_own_identity_matches_the_mappings_entry_too(tmp_path):
    """Three documents, one type. ``project_mappings`` is the third, and it had
    no opt-in of any kind before this feature."""
    manager, _cluster = _manager(tmp_path, SHAPES["uuid4"])
    own = manager.node_uuid
    # ``node_mappings`` is this node's own entry, resolved by ConfigManager from
    # default_mappings.xml — the accessor a consumer actually reads, rather than
    # the whole document.
    assert own == manager.node_mappings["uuid"]


def test_the_node_conf_dict_entry_agrees_with_the_accessor(tmp_path):
    """The other half of M-a: the accessor and the underlying dict entry must
    not disagree. Converting in the property rather than in decoding would have
    reproduced the two-types-for-one-value defect one layer down (research R1's
    second rejected alternative)."""
    manager, _cluster = _manager(tmp_path, SHAPES["uuid4"])
    assert manager.node_conf["uuid"] is manager.node_uuid


def test_the_identity_still_projects_to_its_string_form_on_the_wire(tmp_path):
    """Contract §5: wire payloads are unchanged. A ``Uuid`` leaking into a
    payload as an object would break the editor's websocket handler, which
    rejects a non-``str`` node identity by ``isinstance`` (census)."""
    manager, _cluster = _manager(tmp_path, SHAPES["uuid4"])
    wire = manager.node_conf.to_wire()
    assert wire["uuid"] == SHAPES["uuid4"]
    assert type(wire["uuid"]) is str


def test_a_provisioned_node_is_recognisable_by_one_check(tmp_path):
    """The whole point of FR-028's one exception: a consumer asks once."""
    manager, _cluster = _manager(tmp_path, SHAPES["uuid4"])
    assert manager.node_uuid != ids.NOT_PROVISIONED_UUID
    assert isinstance(manager.node_uuid, Uuid)
