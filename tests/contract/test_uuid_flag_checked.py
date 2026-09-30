# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T031 — an explicit ``--uuid`` that collides is refused (FR-019b).

One of the four routes by which two nodes come to share one identity (M-l),
and the most mundane: an operator provisions a replacement node and pastes the
identity of the node it replaces, or of the one they were looking at a moment
before. Nothing would notice — the tool would write it, the map would accept
it, and the divergence would surface as two nodes answering to one name with
one set of outputs between them.

The check reads the map with stdlib XML and **leniently**: a map that will not
parse refuses nothing. This exists to catch a typo, not to become a second
reason provisioning can fail.
"""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from cuemsutils.tools import init_node
from tests.support.cluster_fixture import SHAPES, mac_for, network_map_xml, NodeSpec


def _sysfs(tmp_path: Path) -> Path:
    root = tmp_path / "sys-class-net"
    (root / "ethernet0").mkdir(parents=True, exist_ok=True)
    (root / "ethernet0" / "address").write_text("aa:bb:cc:dd:ee:01\n")
    return root


def _run(conf, tmp_path, *extra) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = init_node.main([
            "--conf-dir", str(conf), "--state-dir", str(tmp_path / "state"),
            "--sysfs", str(_sysfs(tmp_path)), "--lock-file", str(tmp_path / "lock"),
            "--systemctl", "/bin/false", "--no-overlay", *extra,
        ])
    return code, out.getvalue() + err.getvalue()


@pytest.fixture
def conf_with_map(tmp_path):
    conf = tmp_path / "etc"
    conf.mkdir()
    rows = [
        NodeSpec(SHAPES["uuid4"], mac_for(0), "controller", "n0", "10.0.0.1"),
        NodeSpec(SHAPES["uuid4b"], mac_for(1), "node", "n1", "10.0.0.2"),
    ]
    (conf / "network_map.xml").write_text(network_map_xml(rows), encoding="utf-8")
    return conf


def test_a_colliding_identity_is_refused(conf_with_map, tmp_path):
    code, out = _run(conf_with_map, tmp_path, "--uuid", SHAPES["uuid4b"])
    assert code == 1
    assert SHAPES["uuid4b"] in out
    assert mac_for(1) in out
    assert not (conf_with_map / "settings.xml").exists(), "a refusal wrote something"


def test_the_refusal_says_why_it_matters(conf_with_map, tmp_path):
    """Not "duplicate value". The reason a shared identity is unrecoverable is
    that the library's compound ``<identity>_<output>`` prefix is the only
    record of which node an output belongs to."""
    code, out = _run(conf_with_map, tmp_path, "--uuid", SHAPES["uuid4b"])
    assert "output belongs to" in out


def test_a_non_colliding_uuid4_is_accepted(conf_with_map, tmp_path):
    fresh = "11111111-2222-4333-8444-555555555555"
    code, out = _run(conf_with_map, tmp_path, "--uuid", fresh)
    assert code == 0, out
    import xml.etree.ElementTree as ET

    assert ET.parse(conf_with_map / "settings.xml").getroot().findtext(".//uuid") == fresh


def test_claiming_a_row_that_is_not_this_node_is_refused_even_on_a_fresh_node(
        conf_with_map, tmp_path):
    """The controller's own identity, pasted onto a node being provisioned. This
    node has no ``settings.xml`` yet, so there is nothing to compare against
    except the map — which is exactly the case the check is for."""
    code, out = _run(conf_with_map, tmp_path, "--uuid", SHAPES["uuid4"])
    assert code == 1
    assert mac_for(0) in out


def test_reasserting_this_nodes_own_identity_is_not_a_collision(conf_with_map, tmp_path):
    """``--uuid <what this node already has>`` is a no-op, not a clash with
    itself. Refusing it would make the flag unusable for its most defensible
    purpose: stating explicitly what is already true.

    The node is provisioned first with a fresh identity, and the map row for it
    is then what ``--uuid`` re-asserts.
    """
    mine = "11111111-2222-4333-8444-555555555555"
    code, out = _run(conf_with_map, tmp_path, "--uuid", mine)
    assert code == 0, out

    code, out = _run(conf_with_map, tmp_path, "--uuid", mine)
    assert code == 0, out
    import xml.etree.ElementTree as ET

    assert ET.parse(conf_with_map / "settings.xml").getroot().findtext(".//uuid") == mine


def test_a_non_uuid4_is_still_refused_as_before(conf_with_map, tmp_path):
    """The shipped refusal, unchanged: the new check sits beside it, not over
    it."""
    code, out = _run(conf_with_map, tmp_path, "--uuid", SHAPES["uuid1"])
    assert code == 1 and "not a uuid4" in out


def test_the_collision_check_reads_an_unreadable_map_leniently(tmp_path):
    """Leniently, on purpose: a map that will not parse refuses **nothing**.
    This check exists to catch an operator's typo, not to become a second
    reason provisioning can fail.

    Asserted against the check itself rather than through the tool, because the
    tool already exits 2 on an unreadable map for a *different* and shipped
    reason — its strict read of the existing documents — and that behaviour is
    feature 011's, not this one's. The next test pins that it is unchanged.
    """
    conf = tmp_path / "etc"
    conf.mkdir()
    (conf / "network_map.xml").write_text("<broken", encoding="utf-8")
    assert init_node._map_identities(conf) == {}
    assert init_node._map_identities(tmp_path / "does-not-exist") == {}


def test_an_unreadable_map_still_exits_two_for_the_shipped_reason(tmp_path):
    """Feature 011's behaviour, unchanged: the strict read of the documents
    already present is what fails, and it is class 2 (unreadable input), not
    class 1 (refused). The new check sits beside that, not over it."""
    conf = tmp_path / "etc"
    conf.mkdir()
    (conf / "network_map.xml").write_text("<broken", encoding="utf-8")
    code, out = _run(conf, tmp_path, "--uuid", "11111111-2222-4333-8444-555555555555")
    assert code == 2
    assert "cannot be read" in out
