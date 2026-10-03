# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Package lifecycle in an unprivileged bookworm chroot (feature 011, research
R9). Marked ``slow``; skips without ``CUEMS_CHROOT_TAR`` and a built ``.deb``."""

from __future__ import annotations

import hashlib

import pytest

from tests.packaging.conftest import REPO_ROOT

pytestmark = pytest.mark.slow

SCHEMAS = ("settings", "network_map", "project_mappings", "project_settings", "script", "hardware_outputs")
XSD_DIR = REPO_ROOT / "src/cuemsutils/xml/schemas"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _install_ours(chroot, built_deb):
    result = chroot.dpkg_install(built_deb)
    assert result.returncode == 0, result.stderr + result.stdout
    return result


# -- US1 (T017, T018) -----------------------------------------------------------


def test_custody_transfer_both_orders(chroot, built_deb, sibling_deb, tmp_path):
    """The live map survives the handover, in either unpack order (research R3)."""
    old_common = _build_old_common_stub(tmp_path)
    new_common = sibling_deb("cuems-common")
    # An operator's topology: one real node row (an empty stub with no <node>
    # is the one case the recipe lets a freshly generated map replace).
    live_map = (
        b"<?xml version='1.0' encoding='utf-8'?>\n"
        b'<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/" doc_version="1"><node_list>'
        b"<node><uuid>8c8f4d5e-3d5b-4b0a-9f5d-0a0a0a0a0a0a</uuid><mac>0011aabbccdd</mac><name>controller</name>"
        b"<node_role>controller</node_role><ip>10.0.0.2</ip><adopted>true</adopted><online>true</online></node>"
        b"</node_list></cms:CuemsNetworkMap>\n"
    )

    def _fresh_old_common():
        assert chroot.dpkg_install(old_common, "--force-depends").returncode == 0
        (chroot.root / "etc/cuems/network_map.xml").write_bytes(live_map)

    def _assert_transferred(order):
        assert chroot.read("/etc/cuems/network_map.xml") == live_map, order
        siblings = sorted(p.name for p in (chroot.root / "etc/cuems").glob("network_map.*"))
        assert siblings == ["network_map.xml", "network_map.xsd"], (order, siblings)
        assert chroot.read("/etc/cuems/network_map.xsd") == (XSD_DIR / "network_map.xsd").read_bytes()
        status = chroot.run(["dpkg-query", "-W", "-f=${Status} ${Version}", "cuems-common"]).stdout
        assert status.startswith("install ok installed 1.3.0-23"), (order, status)
        r = chroot.run(["dpkg", "--purge", "cuems-common"], check=False)
        assert r.returncode == 0, r.stderr
        assert chroot.read("/etc/cuems/network_map.xml") == live_map, "purge of cuems-common removed the live map"
        chroot.run(["dpkg", "--purge", "cuems-utils"], check=False)

    # Order 1 — cuems-utils first. A bare dpkg -i is REFUSED by the Breaks
    # (positive control, research R3); apt resolves it by deconfiguring the old
    # cuems-common, which --auto-deconfigure mirrors: cuems-utils is configured,
    # the old cuems-common stays deconfigured until its upgrade lands.
    _fresh_old_common()
    refused = chroot.dpkg_install(built_deb)
    assert refused.returncode != 0 and "breaks cuems-common" in refused.stdout + refused.stderr
    r = chroot.dpkg_install(built_deb, "--auto-deconfigure")
    assert "De-configuring cuems-common" in r.stdout + r.stderr, r.stderr
    assert chroot.run(["dpkg-query", "-W", "-f=${Status}", "cuems-utils"]).stdout == "install ok installed"
    r = chroot.dpkg_install(new_common, "--force-depends")
    assert r.returncode == 0, r.stderr + r.stdout
    _assert_transferred("utils-first")

    # Order 2 — cuems-common unpacked first. Configuration is dependency-ordered
    # by dpkg itself (cuems-common Depends: cuems-utils, and its postinst refuses
    # to run without the venv), so the realistic form of this order is
    # unpack both, then configure — which is what apt does. dpkg's own
    # obsolete-conffile step parks a modified map as .dpkg-bak and removes the
    # .xsd at unpack; the postinst block must undo both.
    _fresh_old_common()
    chroot.copy_in(new_common, f"/tmp/{new_common.name}")
    chroot.copy_in(built_deb, f"/tmp/{built_deb.name}")
    r = chroot.run(["dpkg", "--unpack", "--auto-deconfigure", f"/tmp/{new_common.name}", f"/tmp/{built_deb.name}"], check=False)
    assert r.returncode == 0, r.stderr + r.stdout
    r = chroot.run(["dpkg", "--configure", "--force-depends", "-a"], check=False)
    assert r.returncode == 0, r.stderr + r.stdout
    _assert_transferred("common-unpacked-first")


def test_live_defects_resolve(chroot, built_deb):
    _install_ours(chroot, built_deb)
    for name in SCHEMAS:
        assert chroot.read(f"/etc/cuems/{name}.xsd") == (XSD_DIR / f"{name}.xsd").read_bytes()
    corpus = REPO_ROOT / "tests/data/corpus/cuems-engine"
    for document, schema in (("settings.xml", "settings"), ("default_mappings.xml", "project_mappings")):
        chroot.copy_in(corpus / document, f"/tmp/{document}")
        r = chroot.run([
            "/usr/lib/cuems/bin/python", "-c",
            f"import xmlschema; xmlschema.XMLSchema11('/etc/cuems/{schema}.xsd').validate('/tmp/{document}')",
        ], check=False)
        assert r.returncode == 0, r.stderr


def _build_old_common_stub(tmp_path):
    """A minimal ``cuems-common`` that ships the two paths as conffiles."""
    import subprocess

    root = tmp_path / "old-common"
    (root / "DEBIAN").mkdir(parents=True)
    (root / "etc/cuems").mkdir(parents=True)
    (root / "etc/cuems/network_map.xml").write_bytes(b"<node_list/>\n")
    (root / "etc/cuems/network_map.xsd").write_bytes(b"<stale schema/>\n")
    (root / "DEBIAN/control").write_text(
        "Package: cuems-common\nVersion: 1.3.0-22\nArchitecture: all\nMaintainer: test\n"
        "Description: stub of the pre-handover cuems-common\n"
    )
    (root / "DEBIAN/conffiles").write_text("/etc/cuems/network_map.xml\n/etc/cuems/network_map.xsd\n")
    out = tmp_path / "cuems-common_1.3.0-22_all.deb"
    subprocess.run(["dpkg-deb", "--root-owner-group", "-b", str(root), str(out)], check=True, capture_output=True)
    return out


# -- US2 (T030) -----------------------------------------------------------------


def test_identity_survives_upgrade_reinstall_remove(chroot, built_deb):
    """SC-002: upgrade, --reinstall, remove-then-install leave the triple byte-identical."""
    _install_ours(chroot, built_deb)
    documents = ("settings.xml", "network_map.xml", "default_mappings.xml")
    before = {d: _sha(chroot.read(f"/etc/cuems/{d}")) for d in documents}
    assert all(before.values())

    steps = (
        ["dpkg", "-i", f"/tmp/{built_deb.name}"],                    # upgrade (same version re-unpacked)
        ["dpkg", "-i", "--force-confmiss", f"/tmp/{built_deb.name}"],  # reinstall
        ["dpkg", "-r", "cuems-utils"],                                # remove keeps /etc
        ["dpkg", "-i", f"/tmp/{built_deb.name}"],                    # install again
    )
    for argv in steps:
        r = chroot.run(argv, check=False)
        assert r.returncode == 0, (argv, r.stderr)
        after = {d: _sha(chroot.read(f"/etc/cuems/{d}")) for d in documents}
        assert after == before, (argv, "identity or documents changed")


# -- US3 (T040) -----------------------------------------------------------------


def test_fresh_install_loads_and_is_unique(make_chroot, built_deb, tmp_path):
    """SC-001, SC-007, SC-008 across three fresh roots: install, load, and the sabotaged fallback."""
    import re

    chroot = make_chroot("rootfs")

    load = "from cuemsutils.tools.ConfigManager import ConfigManager; m = ConfigManager(load_all=True); print(m.node_conf['uuid'])"
    _install_ours(chroot, built_deb)
    r = chroot.run(["/usr/lib/cuems/bin/python", "-c", load])
    first = r.stdout.strip().splitlines()[-1]  # the library may log to stdout first
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", first), r.stderr
    grep = chroot.run(["grep", "-r", "00000000-0000-0000-0000-000000000000", "/etc/cuems"], check=False)
    assert grep.returncode == 1, f"sentinel token still present: {grep.stdout}"

    # a second root from the same tarball and .deb: a different identity
    second = make_chroot("rootfs2")
    _install_ours(second, built_deb)
    r2 = second.run(["/usr/lib/cuems/bin/python", "-c", load])
    assert r2.stdout.strip().splitlines()[-1] != first

    # sabotage: a fresh root where the tool cannot run (no ethernet0, no MAC) ->
    # the tool refuses, postinst installs the placeholders, warns, exits 0
    third = make_chroot("rootfs3")
    (third.root / "sys/class/net/ethernet0/address").unlink()
    r3 = third.dpkg_install(built_deb)
    assert r3.returncode == 0, r3.stderr
    assert "NOT PROVISIONED" in (r3.stderr + r3.stdout)
    assert third.exists("/etc/cuems/settings.xml")
    assert b"00000000-0000-0000-0000-000000000000" in third.read("/etc/cuems/settings.xml")

    # the other fallback branch: the tool itself is not executable (a broken
    # venv, the trap register's pyenv case) -> the same warning, still exit 0
    fourth = make_chroot("rootfs4")
    tool = fourth.root / "usr/lib/cuems/bin/cuems-init-node"
    r4 = fourth.dpkg_install(built_deb)
    assert r4.returncode == 0, r4.stderr
    # make it unrunnable and re-run configure with the documents removed
    tool.chmod(0o000)
    for d in ("settings.xml", "network_map.xml", "default_mappings.xml"):
        (fourth.root / "etc/cuems" / d).unlink()
    r5 = fourth.run(["dpkg-reconfigure", "-f", "noninteractive", "cuems-utils"], check=False)
    if r5.returncode != 0 and "not found" in r5.stderr:
        r5 = fourth.run(["sh", "/var/lib/dpkg/info/cuems-utils.postinst", "configure"], check=False)
    assert r5.returncode == 0, r5.stderr
    assert "NOT PROVISIONED" in (r5.stderr + r5.stdout) and "not executable" in (r5.stderr + r5.stdout)
    assert fourth.exists("/etc/cuems/settings.xml")



# -- US5 (T058) -----------------------------------------------------------------


def test_purge_alone_and_whole_stack(chroot, built_deb):
    """SC-003: purge of this package alone damages no other owner's file; purge of
    every CUEMS package leaves no /etc/cuems; purge then install mints a new uuid."""
    _install_ours(chroot, built_deb)
    load = "from cuemsutils.tools.ConfigManager import ConfigManager; print(ConfigManager(load_all=True).node_conf['uuid'])"
    first = chroot.run(["/usr/lib/cuems/bin/python", "-c", load]).stdout.strip().splitlines()[-1]
    others = {
        "ap.conf": b"other package's conffile\n",
        "power-bridge.key": b"-----BEGIN OPENSSH PRIVATE KEY-----\n",
        "cluster.conf": b"cluster identity\n",
        "defaults.d/10-venue.toml": b"[settings.SettingsType]\n",
    }
    for name, content in others.items():
        target = chroot.root / "etc/cuems" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    r = chroot.run(["dpkg", "--purge", "cuems-utils"], check=False)
    assert r.returncode == 0, r.stderr
    for name, content in others.items():
        assert chroot.read(f"/etc/cuems/{name}") == content, f"{name} damaged by purge"
    for gone in ("settings.xml", "network_map.xml", "default_mappings.xml", "settings.xsd", "script.xsd"):
        assert not chroot.exists(f"/etc/cuems/{gone}"), gone
    assert not chroot.exists("/var/lib/cuems-utils")
    assert chroot.exists("/etc/cuems")

    # the whole stack: nothing else is installed here, so remove the markers and purge again
    for name in others:
        (chroot.root / "etc/cuems" / name).unlink()
    (chroot.root / "etc/cuems/defaults.d").rmdir()
    _install_ours(chroot, built_deb)
    r = chroot.run(["dpkg", "--purge", "cuems-utils"], check=False)
    assert r.returncode == 0 and not chroot.exists("/etc/cuems"), "the last package must remove the empty directory"

    # purge then install: a new identity, by design
    _install_ours(chroot, built_deb)
    second = chroot.run(["/usr/lib/cuems/bin/python", "-c", load]).stdout.strip().splitlines()[-1]
    assert second != first
