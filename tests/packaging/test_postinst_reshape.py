# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""010 T040 (FR-094) — the postinst reshapes ``/etc/cuems`` before anything reads it.

A field node's ``settings.xml`` and mappings are in the pre-013 device shape,
and the load path refuses that shape (013 has no version step, so
convert-on-read cannot help, T037a). The services read those documents at
start, so a node upgraded without a reshape does not start. Decision
(2026-10-17): this package's postinst runs ``cuems-reshape-devices`` over the
documents **directly in** ``$CUEMS_ETC``, before ``cuems-init-node`` (which
reads ``settings.xml``). dpkg configures this package before every dependent
one, so the reshape runs before any of them restarts a service. The **show
library is never touched here** (FR-095b): that stays an operator command.
Like every other step, it degrades to a warning and never fails the install.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pytest

from tests.packaging.conftest import DEBIAN, REPO_ROOT, STUBS

PRE_013 = REPO_ROOT / "tests" / "data" / "corpus" / "pre-013"
TOOL = Path(sys.executable).parent / "cuems-reshape-devices"


def _env(dirs, reshape: str) -> dict:
    env = dirs.env()  # CUEMS_INIT_NODE empty: this file is about the reshape step
    env["CUEMS_RESHAPE"] = reshape
    return env


def _seed_old_etc(dirs, library: Path) -> None:
    dirs.etc.mkdir(parents=True, exist_ok=True)
    settings = (PRE_013 / "settings.xml").read_text(encoding="utf-8")
    settings = settings.replace("/opt/cuems_library", str(library))
    (dirs.etc / "settings.xml").write_text(settings, encoding="utf-8")
    shutil.copyfile(PRE_013 / "project_mappings.xml", dirs.etc / "default_mappings.xml")


@pytest.mark.skipif(not TOOL.exists(), reason=f"{TOOL} is not installed in this interpreter's environment")
def test_configure_reshapes_etc_and_keeps_a_backup(dirs, run_maintainer_script, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    _seed_old_etc(dirs, library)
    originals = {name: (dirs.etc / name).read_bytes() for name in ("settings.xml", "default_mappings.xml")}

    result = run_maintainer_script("postinst", "configure", _env(dirs, str(TOOL)))

    assert result.returncode == 0, result.stderr
    settings = (dirs.etc / "settings.xml").read_text(encoding="utf-8")
    assert "<videoplayer>" not in settings and "<players>" in settings
    assert "<audio>" not in (dirs.etc / "default_mappings.xml").read_text(encoding="utf-8")
    for name, original in originals.items():
        backups = list(dirs.etc.glob(f"{name}.*.bak"))
        assert [b.read_bytes() for b in backups] == [original], f"{name}: the original must survive"


@pytest.mark.skipif(not TOOL.exists(), reason=f"{TOOL} is not installed in this interpreter's environment")
def test_configure_never_touches_the_show_library(dirs, run_maintainer_script, tmp_path):
    """FR-095b: the configuration reshape is in the upgrade path, the show library is not."""
    library = tmp_path / "library"
    (library / "projects" / "show").mkdir(parents=True)
    script = library / "projects" / "show" / "script.xml"
    shutil.copyfile(PRE_013 / "script.xml", script)
    before = script.read_bytes()
    _seed_old_etc(dirs, library)

    result = run_maintainer_script("postinst", "configure", _env(dirs, str(TOOL)))

    assert result.returncode == 0, result.stderr
    assert script.read_bytes() == before
    assert list(script.parent.glob("*.bak")) == []


def test_a_failing_or_hung_reshape_warns_and_the_install_still_succeeds(dirs, run_maintainer_script, tmp_path):
    dirs.etc.mkdir(parents=True)
    (dirs.etc / "settings.xml").write_text("<x/>", encoding="utf-8")
    marker = tmp_path / "argv"
    env = _env(dirs, str(STUBS / "cuems-init-node"))  # the generic stub: argv, exit, sleep
    env["CUEMS_STUB_MARKER"] = str(marker)

    result = run_maintainer_script("postinst", "configure", env)
    assert result.returncode == 0, result.stderr
    assert marker.read_text().split() == [str(dirs.etc / "settings.xml")], "explicit /etc paths only"

    env["CUEMS_STUB_EXIT"] = "1"
    result = run_maintainer_script("postinst", "configure", env)
    assert result.returncode == 0, result.stderr
    assert "cuems-reshape-devices" in result.stderr and "--check" in result.stderr

    env.pop("CUEMS_STUB_EXIT")
    env["CUEMS_STUB_SLEEP"] = "3"
    env["CUEMS_RESHAPE_TIMEOUT"] = "1s"
    result = run_maintainer_script("postinst", "configure", env)
    assert result.returncode == 0, result.stderr
    assert "cuems-reshape-devices" in result.stderr


def test_an_empty_etc_calls_nothing(dirs, run_maintainer_script, tmp_path):
    marker = tmp_path / "argv"
    env = _env(dirs, str(STUBS / "cuems-init-node"))
    env["CUEMS_STUB_MARKER"] = str(marker)
    result = run_maintainer_script("postinst", "configure", env)
    assert result.returncode == 0, result.stderr
    assert not marker.exists(), "a fresh install has nothing to reshape"


def test_the_reshape_runs_before_init_node_and_after_the_schemas():
    text = (DEBIAN / "cuems-utils.postinst").read_text(encoding="utf-8")
    body = text[text.index('case "$1" in'):]
    schemas = body.index("install_schemas")
    reshape = body.index("reshape_configuration")
    init_node = body.index('"$CUEMS_INIT_NODE" --no-overlay')
    assert schemas < reshape < init_node
    assert re.search(r'CUEMS_RESHAPE="\$\{CUEMS_RESHAPE-/usr/lib/cuems/bin/cuems-reshape-devices\}"', text)
