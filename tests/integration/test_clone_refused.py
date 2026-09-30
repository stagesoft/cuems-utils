# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T030 — a cloned disk is refused (FR-019d, research R6).

**This amends feature 011's D13**, and the amendment is the point. D13 says
"mint iff there is none", and that rule is precisely what makes a cloned disk
keep the original's identity: the preserve branch prefers the *stored* MAC over
the hardware's, so a clone never consults its own NIC. Cloning a provisioned
disk is how venues provision, so D13 leaves uuid4 convergence delivering a
cluster that re-collides on the next clone.

It **refuses** rather than re-minting, and that is not caution. A MAC can also
differ because a NIC was replaced on the *same* node, where preserving the
identity is correct and re-minting would cost an adoption — which §9.5
establishes is now permanent. The two cases are indistinguishable from here, so
the tool asks the one party that can tell them apart.
"""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from cuemsutils.tools import init_node


def _sysfs(tmp_path: Path, mac: str) -> Path:
    root = tmp_path / "sys-class-net"
    (root / "ethernet0").mkdir(parents=True, exist_ok=True)
    (root / "ethernet0" / "address").write_text(mac + "\n")
    return root


def _run(conf, state, sysfs, tmp_path, *extra) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = init_node.main([
            "--conf-dir", str(conf), "--state-dir", str(state), "--sysfs", str(sysfs),
            "--lock-file", str(tmp_path / "lock"), "--systemctl", "/bin/false",
            "--no-overlay", *extra,
        ])
    return code, out.getvalue() + err.getvalue()


@pytest.fixture
def provisioned(tmp_path):
    """A node provisioned on hardware whose MAC is ``aa:bb:cc:dd:ee:01``."""
    conf, state = tmp_path / "etc", tmp_path / "state"
    sysfs = _sysfs(tmp_path, "aa:bb:cc:dd:ee:01")
    code, out = _run(conf, state, sysfs, tmp_path)
    assert code == 0, out
    import xml.etree.ElementTree as ET

    identity = ET.parse(conf / "settings.xml").getroot().findtext(".//uuid")
    return conf, state, identity


def test_a_stored_identity_on_other_hardware_is_refused(provisioned, tmp_path):
    """The disk image was restored onto a different machine."""
    conf, state, identity = provisioned
    other = _sysfs(tmp_path / "clone", "aa:bb:cc:dd:ee:99")

    code, out = _run(conf, state, other, tmp_path)

    assert code == 1
    assert identity in out
    assert "aabbccddee01" in out and "aabbccddee99" in out
    import xml.etree.ElementTree as ET

    assert ET.parse(conf / "settings.xml").getroot().findtext(".//uuid") == identity, \
        "a refusal wrote something"


def test_the_refusal_names_both_readings_and_both_ways_out(provisioned, tmp_path):
    """Refusing is only useful if it hands the operator the decision it cannot
    make. Both readings are named, and both remedies."""
    conf, state, _identity = provisioned
    other = _sysfs(tmp_path / "clone", "aa:bb:cc:dd:ee:99")

    code, out = _run(conf, state, other, tmp_path)

    assert "restored onto other hardware" in out
    assert "replaced NIC" in out
    assert "--force-new-identity" in out
    assert "--mac" in out


def test_a_matching_mac_still_preserves_the_identity(provisioned, tmp_path):
    """The behaviour D13 exists for, and it is unchanged. A re-run on the same
    hardware must not re-mint — that is the whole of feature 011's US3."""
    conf, state, identity = provisioned
    same = _sysfs(tmp_path, "aa:bb:cc:dd:ee:01")

    code, out = _run(conf, state, same, tmp_path)

    assert code == 0, out
    import xml.etree.ElementTree as ET

    assert ET.parse(conf / "settings.xml").getroot().findtext(".//uuid") == identity


def test_force_new_identity_is_the_way_through(provisioned, tmp_path):
    conf, state, identity = provisioned
    other = _sysfs(tmp_path / "clone", "aa:bb:cc:dd:ee:99")

    code, out = _run(conf, state, other, tmp_path, "--force-new-identity", "--yes")

    assert code == 0, out
    import xml.etree.ElementTree as ET

    assert ET.parse(conf / "settings.xml").getroot().findtext(".//uuid") != identity
    assert "must be re-adopted" in out


def test_confirming_the_nic_swap_with_mac_is_the_other_way_through(provisioned, tmp_path):
    """The NIC-replacement reading: the operator says so, the identity is kept
    and the stored MAC is corrected."""
    conf, state, identity = provisioned
    other = _sysfs(tmp_path / "clone", "aa:bb:cc:dd:ee:99")

    code, out = _run(conf, state, other, tmp_path, "--mac", "aabbccddee99")

    assert code == 0, out
    import xml.etree.ElementTree as ET

    root = ET.parse(conf / "settings.xml").getroot()
    assert root.findtext(".//uuid") == identity
    assert root.findtext(".//mac") == "aabbccddee99"


def test_an_unreadable_sysfs_stays_a_non_event_on_the_preserve_path(provisioned, tmp_path):
    """Research R6's "Cost": deriving the MAC unconditionally adds a sysfs read
    to every run, including ``postinst``'s. It must not be able to *fail* one —
    a node whose sysfs cannot be read is not thereby a clone."""
    conf, state, identity = provisioned
    empty = tmp_path / "no-sysfs-here"

    code, out = _run(conf, state, empty, tmp_path)

    assert code == 0, out
    import xml.etree.ElementTree as ET

    assert ET.parse(conf / "settings.xml").getroot().findtext(".//uuid") == identity
