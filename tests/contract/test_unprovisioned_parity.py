# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T062 — on an unprovisioned node, every accessor yields the sentinel constant
(FR-028, US4 scenario 2).

The one documented exception to "one type for one value" is *provisioned versus
not*, and it only helps a consumer if it is the **same** exception everywhere. An
accessor that answered with the identity type here and another that answered with
the string would put the consumer back to checking each one.

The sentinel stays a plain ``str`` because it is *admitted* by the schemas and is
never *converged* (data-model §1.2), so the published coercion rule's second
branch catches it. That is what makes a single ``== SENTINEL`` comparison enough
to recognise an unprovisioned node **before** attempting a full load, which
otherwise raises (M-d) — and ``cuems-engine`` already does exactly that at
startup (``BaseEngine.py:316``).
"""

from __future__ import annotations

from cuemsutils.tools import SENTINEL, ids
from cuemsutils.tools.ConfigManager import ConfigManager
from cuemsutils.tools.Uuid import Uuid
from tests.support.cluster_fixture import build_cluster


def _unprovisioned(tmp_path):
    cluster = build_cluster(tmp_path, identities=[ids.NOT_PROVISIONED_UUID])
    manager = ConfigManager(config_dir=str(cluster.conf), load_all=False)
    manager.load_config()
    return manager


def test_the_own_identity_accessor_yields_the_published_constant(tmp_path):
    manager = _unprovisioned(tmp_path)
    assert manager.node_uuid == SENTINEL
    assert type(manager.node_uuid) is str


def test_the_map_row_yields_the_same_constant(tmp_path):
    manager = _unprovisioned(tmp_path)
    row = manager.network_map["node_list"][0]["node"]["uuid"]
    assert row == SENTINEL
    assert type(row) is str


def test_the_mappings_entry_yields_the_same_constant(tmp_path):
    manager = _unprovisioned(tmp_path)
    entry = manager.node_mappings["uuid"]
    assert entry == SENTINEL
    assert type(entry) is str


def test_no_accessor_yields_the_identity_type_here(tmp_path):
    """The exception is *provisioned versus not*, and nothing else. A ``Uuid``
    appearing on an unprovisioned node would make the exception depend on which
    accessor was asked, which is the defect this feature closes."""
    manager = _unprovisioned(tmp_path)
    values = [
        manager.node_uuid,
        manager.node_conf["uuid"],
        manager.network_map["node_list"][0]["node"]["uuid"],
        manager.node_mappings["uuid"],
    ]
    assert not any(isinstance(v, Uuid) for v in values)
    assert all(v == SENTINEL for v in values)


def test_one_comparison_distinguishes_the_two_states(tmp_path):
    """What a consumer actually writes, both ways round."""
    unprovisioned = _unprovisioned(tmp_path)
    assert unprovisioned.node_uuid == SENTINEL

    provisioned = build_cluster(tmp_path / "prov", shapes=["uuid4"])
    manager = ConfigManager(config_dir=str(provisioned.conf), load_all=False)
    manager.load_config()
    assert manager.node_uuid != SENTINEL


def test_host_name_still_works_on_an_unprovisioned_node(tmp_path):
    """The derived accessor is a ``str`` in both states — it is the one place in
    this library that consumes the identity as text, and the type change must
    not have made it state-dependent."""
    manager = _unprovisioned(tmp_path)
    assert manager.host_name == "000000000000.local"
    assert type(manager.host_name) is str
