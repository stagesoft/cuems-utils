# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T057 — ``debian/cuems-utils.postrm`` (feature 011, US5; FR-037, FR-038, D6):
purge removes exactly the nine paths and the write record, never recursively,
never another owner's file; every other argument is a no-op."""

from __future__ import annotations

import re

from tests.packaging.conftest import DEBIAN

NINE = (
    "settings.xml", "network_map.xml", "default_mappings.xml",
    "settings.xsd", "network_map.xsd", "project_mappings.xsd", "project_settings.xsd",
    "script.xsd", "hardware_outputs.xsd",
)
OTHERS = {
    "ap.conf": b"other package's conffile",
    "power-bridge.key": b"-----BEGIN OPENSSH PRIVATE KEY-----",
    "cluster.conf": b"cluster identity",
    "network_map.xml.dpkg-dist": b"parked by dpkg",
    "defaults.d/10-venue.toml": b"[settings.SettingsType]\n",
}


def _populate(dirs, with_others: bool) -> None:
    dirs.etc.mkdir(parents=True, exist_ok=True)
    for name in NINE:
        (dirs.etc / name).write_bytes(b"ours")
    if with_others:
        for name, content in OTHERS.items():
            path = dirs.etc / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    (dirs.state / "init-node").mkdir(parents=True, exist_ok=True)
    (dirs.state / "init-node" / "last-written.json").write_text("{}")


def test_purge_removes_exactly_ours_and_keeps_the_shared_directory(dirs, run_maintainer_script):
    _populate(dirs, with_others=True)
    result = run_maintainer_script("postrm", "purge", dirs.env())
    assert result.returncode == 0, result.stderr
    for name in NINE:
        assert not (dirs.etc / name).exists(), f"{name} survived purge"
    assert not (dirs.state / "init-node" / "last-written.json").exists()
    assert not (dirs.state / "init-node").exists() and not dirs.state.exists()
    for name, content in OTHERS.items():
        assert (dirs.etc / name).read_bytes() == content, f"{name} was touched by purge"
    assert dirs.etc.is_dir()


def test_purge_of_the_last_package_removes_the_empty_directory(dirs, run_maintainer_script):
    _populate(dirs, with_others=False)
    result = run_maintainer_script("postrm", "purge", dirs.env())
    assert result.returncode == 0, result.stderr
    assert not dirs.etc.exists()


def test_every_other_argument_touches_nothing(dirs, run_maintainer_script):
    for arg in ("remove", "upgrade", "failed-upgrade", "abort-install", "abort-upgrade", "disappear"):
        _populate(dirs, with_others=True)
        before = sorted(str(p.relative_to(dirs.etc)) for p in dirs.etc.rglob("*"))
        result = run_maintainer_script("postrm", arg, dirs.env(), extra_args=("1.0",))
        assert result.returncode == 0, (arg, result.stderr)
        assert sorted(str(p.relative_to(dirs.etc)) for p in dirs.etc.rglob("*")) == before, arg
        assert (dirs.state / "init-node" / "last-written.json").exists(), arg


def test_the_script_never_removes_recursively():
    text = (DEBIAN / "cuems-utils.postrm").read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert not re.search(r"\brm\s+-[a-zA-Z]*r", code), "rm -r is forbidden in this script"
    assert "rmdir" in code and "--ignore-fail-on-non-empty" in code
