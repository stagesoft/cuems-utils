# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Assertions on the built ``.deb`` (feature 011). Every test here skips when no
``../cuems-utils_*.deb`` exists and re-runs after ``dpkg-buildpackage``; see
``contracts/packaging.md`` for the invariants."""

from __future__ import annotations

import re
import subprocess

from tests.packaging.conftest import REPO_ROOT, deb_control_file, deb_file, deb_paths

SCHEMAS = ("settings", "network_map", "project_mappings", "project_settings", "script", "hardware_outputs")
DOCUMENTS = ("settings.xml", "network_map.xml", "default_mappings.xml")
SENTINEL = b"00000000-0000-0000-0000-000000000000"


# -- US1 (T015) -----------------------------------------------------------------


def test_schemas_ship_under_usr_share(built_deb):
    paths = set(deb_paths(built_deb))
    for name in SCHEMAS:
        member = f"usr/share/cuems/schemas/{name}.xsd"
        assert f"/{member}" in paths, f"{member} not in the package"
        bundled = (REPO_ROOT / "src/cuemsutils/xml/schemas" / f"{name}.xsd").read_bytes()
        assert deb_file(built_deb, member) == bundled, f"{member} differs from the bundled schema"


def test_nothing_under_etc_cuems_is_a_conffile(built_deb):
    conffiles = deb_control_file(built_deb, "conffiles")
    assert "/etc/cuems" not in conffiles, conffiles
    assert not any(p.startswith("/etc/cuems") for p in deb_paths(built_deb)), (
        "the manifest must ship nothing under /etc/cuems (D5)"
    )


# -- US2 (T029) -----------------------------------------------------------------


def test_pristine_defaults_ship(built_deb):
    paths = set(deb_paths(built_deb))
    for name in DOCUMENTS:
        member = f"usr/share/cuems/defaults/{name}"
        assert f"/{member}" in paths, member
        assert SENTINEL in deb_file(built_deb, member), f"{member} does not carry the sentinel"
    toml = deb_file(built_deb, "usr/share/cuems/defaults/system-defaults.toml")
    assert toml == (REPO_ROOT / "src/cuemsutils/defaults/system-defaults.toml").read_bytes()


# -- US7 (T065, T066) -----------------------------------------------------------


def test_hygiene(built_deb):
    assert not (REPO_ROOT / "debian/compat").exists(), "debian/compat must be gone (compat 13 via Build-Depends)"
    control = (REPO_ROOT / "debian/control").read_text(encoding="utf-8")
    assert "debhelper-compat (= 13)" in control
    version = re.search(r"^Standards-Version:\s*(\S+)", control, re.M).group(1)
    assert tuple(int(x) for x in version.split(".")[:3]) >= (4, 6, 2), version
    postinst = deb_control_file(built_deb, "postinst")
    assert "dh_python2" not in postinst
    autoscript = postinst.find("dh-virtualenv postinst autoscript")
    set_plus_e = postinst.find("set +e")
    tool = postinst.find('"$CUEMS_INIT_NODE"')  # the invocation, not the header comment
    assert 0 <= autoscript < set_plus_e < tool, "expected autoscript, then set +e, then the tool block"
    pyvenv = deb_file(built_deb, "usr/lib/cuems/pyvenv.cfg").decode()
    assert re.search(r"^home = /usr/bin$", pyvenv, re.M), pyvenv
    listing = subprocess.run(["dpkg-deb", "-c", str(built_deb)], check=True, capture_output=True, text=True).stdout
    python_link = next(line for line in listing.splitlines() if line.rstrip().endswith("./usr/lib/cuems/bin/python") or "./usr/lib/cuems/bin/python ->" in line)
    assert "->" in python_link and "/usr/bin/python3" not in python_link.split("->")[1].strip().lstrip("./"), python_link
    for name in ("rules", "cuems-utils.postinst", "cuems-utils.postrm", "cuems-utils.links"):
        path = REPO_ROOT / "debian" / name
        if path.exists():
            assert not re.search(r"python3\.1[0-9]", path.read_text(encoding="utf-8")), f"{name} embeds an interpreter version (FR-044)"


def test_no_manifest_overlap_with_siblings(built_deb):
    ours = {p for p in deb_paths(built_deb) if p.startswith(("/usr/lib/cuems/", "/usr/bin/", "/usr/share/cuems/")) and not p.endswith("/")}
    for sibling in ("cuems-common", "cuems-nodeconf", "cuems-power-bridge"):
        install = REPO_ROOT.parent / sibling / "debian" / "install"
        if not install.exists():
            continue
        theirs = set()
        for line in install.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            src, dest = line.split()[0], line.split()[-1]
            theirs.add("/" + dest.strip("/") + "/" + src.rsplit("/", 1)[-1])
        overlap = ours & theirs
        assert not overlap, f"{sibling} also ships {sorted(overlap)}"
