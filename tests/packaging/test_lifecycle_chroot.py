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
