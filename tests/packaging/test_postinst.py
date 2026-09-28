# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``debian/cuems-utils.postinst`` at script level (feature 011): every branch
of FR-015–FR-019, run against temp directories through the path overrides and
under a simulated ``set -e`` autoscript stanza (research R21)."""

from __future__ import annotations

from pathlib import Path

from tests.packaging.conftest import REPO_ROOT

SCHEMAS = ("settings", "network_map", "project_mappings", "project_settings", "script", "hardware_outputs")
DOCUMENTS = ("settings.xml", "network_map.xml", "default_mappings.xml")


def _seed_pristine(share: Path) -> None:
    for name in DOCUMENTS:
        (share / "defaults" / name).write_bytes(f"<pristine {name}/>".encode())


# -- US1 (T016) -----------------------------------------------------------------


def test_schemas_are_installed_always(dirs, run_maintainer_script):
    dirs.etc.mkdir()
    (dirs.etc / "network_map.xsd").write_bytes(b"<stale/>")
    _seed_pristine(dirs.share)

    result = run_maintainer_script("postinst", "configure", dirs.env())

    assert result.returncode == 0, result.stderr
    for name in SCHEMAS:
        installed = dirs.etc / f"{name}.xsd"
        assert installed.read_bytes() == (REPO_ROOT / "src/cuemsutils/xml/schemas" / f"{name}.xsd").read_bytes()
        assert installed.stat().st_mode & 0o777 == 0o644


def test_postinst_exits_zero_even_when_share_is_missing(dirs, run_maintainer_script):
    """FR-015 in its bluntest form: nothing to install must not fail the stack."""
    env = dirs.env()
    env["CUEMS_SHARE"] = str(dirs.share / "does-not-exist")
    result = run_maintainer_script("postinst", "configure", env)
    assert result.returncode == 0, result.stderr
    assert "WARNING" in result.stderr


# -- US2 (T028) -----------------------------------------------------------------


def test_documents_installed_only_when_absent(dirs, run_maintainer_script):
    """Per file, only where absent; a present file is never touched; the overlay
    is never read. CUEMS_INIT_NODE is EMPTY here so the tool step is skipped —
    this test must not depend on US3's block."""
    dirs.etc.mkdir()
    _seed_pristine(dirs.share)
    present = {
        "settings.xml": b"<real identity/>",
        "network_map.xml": b"<node_list/>",  # a cuems-common stub is "present"
    }
    for name, content in present.items():
        (dirs.etc / name).write_bytes(content)
    (dirs.etc / "defaults.d").mkdir()
    (dirs.etc / "defaults.d" / "00-broken.toml").write_text("this is = = not toml")

    result = run_maintainer_script("postinst", "configure", dirs.env())

    assert result.returncode == 0, result.stderr
    for name, content in present.items():
        assert (dirs.etc / name).read_bytes() == content, f"{name} was modified"
    assert (dirs.etc / "default_mappings.xml").read_bytes() == b"<pristine default_mappings.xml/>"
    assert (dirs.etc / "default_mappings.xml").stat().st_mode & 0o777 == 0o644
    assert "NOT PROVISIONED" in result.stderr


def test_a_sentinel_document_is_left_alone(dirs, run_maintainer_script):
    dirs.etc.mkdir()
    _seed_pristine(dirs.share)
    sentinel = b"<settings><uuid>00000000-0000-0000-0000-000000000000</uuid></settings>"
    (dirs.etc / "settings.xml").write_bytes(sentinel)
    result = run_maintainer_script("postinst", "configure", dirs.env())
    assert result.returncode == 0
    assert (dirs.etc / "settings.xml").read_bytes() == sentinel


# -- US3 (T039) -----------------------------------------------------------------


def test_tool_invocation_and_fallback(dirs, run_maintainer_script, stub_init_node, tmp_path):
    """Under the simulated ``set -e`` stanza a missing ``set +e`` fails these."""
    _seed_pristine(dirs.share)
    marker = tmp_path / "argv"
    env = dirs.env(init_node=str(stub_init_node))
    env["CUEMS_STUB_MARKER"] = str(marker)

    # success path: the tool is called with exactly the no-operator-input flags
    result = run_maintainer_script("postinst", "configure", env)
    assert result.returncode == 0, result.stderr
    assert marker.read_text().split() == ["--no-overlay", "--install-missing"]
    assert (dirs.state / "init-node").is_dir()
    assert "NOT PROVISIONED" not in result.stderr

    # failure path: the tool exits 1 -> placeholders for the absent documents, warnings, exit 0
    env["CUEMS_STUB_EXIT"] = "1"
    for name in DOCUMENTS:
        (dirs.etc / name).unlink(missing_ok=True)
    result = run_maintainer_script("postinst", "configure", env)
    assert result.returncode == 0, result.stderr
    for name in DOCUMENTS:
        assert (dirs.etc / name).read_bytes() == f"<pristine {name}/>".encode()
    assert "cuems-init-node" in result.stderr and "NOT PROVISIONED" in result.stderr

    # timeout path: a hung tool is cut off and the script still exits 0
    env.pop("CUEMS_STUB_EXIT")
    env["CUEMS_STUB_SLEEP"] = "3"
    env["CUEMS_INIT_TIMEOUT"] = "1s"
    for name in DOCUMENTS:
        (dirs.etc / name).unlink(missing_ok=True)
    result = run_maintainer_script("postinst", "configure", env)
    assert result.returncode == 0, result.stderr
    assert "NOT PROVISIONED" in result.stderr
    assert all((dirs.etc / name).exists() for name in DOCUMENTS)


def test_pinned_wording_is_shared_with_the_tool():
    """FR-UX-001: one constant, asserted verbatim on both sides."""
    from cuemsutils.tools import init_node

    text = (REPO_ROOT / "debian" / "cuems-utils.postinst").read_text(encoding="utf-8")
    assert init_node.NOT_PROVISIONED in text


# -- US4 (T053) -----------------------------------------------------------------


def test_overlay_never_read(dirs, run_maintainer_script, tmp_path):
    """SC-009 with the real tool: a malformed overlay changes nothing about install."""
    import shlex
    import subprocess
    import sys

    _seed_pristine(dirs.share)
    dirs.etc.mkdir()
    (dirs.etc / "defaults.d").mkdir()
    (dirs.etc / "defaults.d" / "00.toml").write_text("this = = is not toml")
    wrapper = tmp_path / "cuems-init-node"
    sysfs = tmp_path / "sys"
    (sysfs / "ethernet0").mkdir(parents=True)
    (sysfs / "ethernet0" / "address").write_text("aa:bb:cc:dd:ee:ff\n")
    wrapper.write_text(
        f"#!/bin/sh\nexec {shlex.quote(sys.executable)} -m cuemsutils.tools.init_node "
        f"--conf-dir {shlex.quote(str(dirs.etc))} --state-dir {shlex.quote(str(dirs.state))} "
        f"--sysfs {shlex.quote(str(sysfs))} --lock-file {shlex.quote(str(tmp_path / 'lock'))} "
        f"--systemctl /bin/false \"$@\"\n"
    )
    wrapper.chmod(0o755)
    result = run_maintainer_script("postinst", "configure", dirs.env(init_node=str(wrapper)))
    assert result.returncode == 0, result.stderr
    assert "NOT PROVISIONED" not in result.stderr, result.stderr
    reference = subprocess.run(
        [sys.executable, "-m", "cuemsutils.tools.init_node", "--conf-dir", str(tmp_path / "ref"),
         "--state-dir", str(tmp_path / "refstate"), "--sysfs", str(sysfs), "--lock-file", str(tmp_path / "l2"),
         "--systemctl", "/bin/false", "--no-overlay", "--uuid", "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40"],
        capture_output=True, text=True,
    )
    assert reference.returncode == 0, reference.stderr
    # same seed values, no overlay applied: the settings differ only by identity
    import re

    def strip(b):
        return re.sub(rb"<(uuid|mac|name|ip)>[^<]*</\1>", b"", b)

    assert strip((dirs.etc / "settings.xml").read_bytes()) == strip((tmp_path / "ref" / "settings.xml").read_bytes())
