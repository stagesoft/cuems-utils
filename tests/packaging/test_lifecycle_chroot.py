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
    live_map = b"<map>operator topology</map>\n"

    for order in (("utils", "common"), ("common", "utils")):
        assert chroot.dpkg_install(old_common).returncode == 0
        (chroot.root / "etc/cuems/network_map.xml").write_bytes(live_map)
        for which in order:
            deb = built_deb if which == "utils" else new_common
            r = chroot.dpkg_install(deb)
            assert r.returncode == 0, f"{order}/{which}: {r.stderr}{r.stdout}"
        assert chroot.read("/etc/cuems/network_map.xml") == live_map, order
        siblings = sorted(p.name for p in (chroot.root / "etc/cuems").glob("network_map.*"))
        assert siblings == ["network_map.xml", "network_map.xsd"], (order, siblings)
        assert chroot.read("/etc/cuems/network_map.xsd") == (XSD_DIR / "network_map.xsd").read_bytes()
        r = chroot.run(["dpkg", "--purge", "cuems-common"], check=False)
        assert r.returncode == 0, r.stderr
        assert chroot.read("/etc/cuems/network_map.xml") == live_map, "purge of cuems-common removed the live map"
        chroot.run(["dpkg", "--purge", "cuems-utils"], check=False)


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


def test_fresh_install_loads_and_is_unique(chroot, built_deb, tmp_path):
    """SC-001, SC-007, SC-008 in one chroot: install, load, and the sabotaged fallback."""
    import re
    import shutil

    load = "from cuemsutils.tools.ConfigManager import ConfigManager; m = ConfigManager(load_all=True); print(m.node_conf['uuid'])"
    _install_ours(chroot, built_deb)
    r = chroot.run(["/usr/lib/cuems/bin/python", "-c", load])
    first = r.stdout.strip()
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", first), r.stderr
    grep = chroot.run(["grep", "-r", "00000000-0000-0000-0000-000000000000", "/etc/cuems"], check=False)
    assert grep.returncode == 1, f"sentinel token still present: {grep.stdout}"

    # a second chroot from the same tarball and .deb: a different identity
    second_root = tmp_path / "rootfs2"
    shutil.copytree(chroot.root, second_root, symlinks=True)
    second = type(chroot)(root=second_root)
    for d in ("settings.xml", "network_map.xml", "default_mappings.xml"):
        (second_root / "etc/cuems" / d).unlink()
    second.run(["dpkg", "-i", "--force-confmiss", f"/tmp/{built_deb.name}"], check=False)
    r2 = second.run(["/usr/lib/cuems/bin/python", "-c", load])
    assert r2.stdout.strip() != first

    # sabotage: the venv interpreter unrunnable -> placeholders, warning, exit 0
    third_root = tmp_path / "rootfs3"
    shutil.copytree(chroot.root, third_root, symlinks=True)
    third = type(chroot)(root=third_root)
    for d in ("settings.xml", "network_map.xml", "default_mappings.xml"):
        (third_root / "etc/cuems" / d).unlink()
    py = third_root / "usr/lib/cuems/bin/python"
    py.unlink()
    py.write_text("not an interpreter\n")
    r3 = third.run(["dpkg", "-i", "--force-confmiss", f"/tmp/{built_deb.name}"], check=False)
    assert r3.returncode == 0, r3.stderr
    assert "NOT PROVISIONED" in (r3.stderr + r3.stdout)
    assert third.exists("/etc/cuems/settings.xml")
    assert b"00000000-0000-0000-0000-000000000000" in third.read("/etc/cuems/settings.xml")
