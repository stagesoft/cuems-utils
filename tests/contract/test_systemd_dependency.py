# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``systemd-python`` is a development dependency, and a Debian one in production.

* **Production:** ``debian/control`` depends on ``python3-systemd``. The shared venv sees it through
  ``dh_virtualenv --use-system-packages``. So the package build must never pip-install it: no
  ``[project].dependencies`` entry, no extra or requirements file in ``debian/rules``.
* **Development:** the hatch ``test`` environment installs it, with the extra's pin, so
  ``tests/unit/test_signalengine.py`` runs wherever the suite does. That needs ``libsystemd-dev``
  and ``pkg-config`` on the host. A missing ``systemd`` is an import failure, never a silent skip.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _named(requirements: list[str], name: str) -> list[str]:
    return [r for r in requirements if re.split(r"[<>=!~\[; ]", r, maxsplit=1)[0].lower() == name]


def test_the_test_environment_installs_systemd_python_with_the_extras_pin():
    pinned = _named(PYPROJECT["project"]["optional-dependencies"]["systemd"], "systemd-python")
    dev = _named(PYPROJECT["tool"]["hatch"]["envs"]["test"]["dependencies"], "systemd-python")
    assert dev == pinned, f"test env {dev} != the systemd extra {pinned}"


def test_the_package_build_never_pip_installs_it():
    assert not _named(PYPROJECT["project"]["dependencies"], "systemd-python")
    rules = (ROOT / "debian" / "rules").read_text(encoding="utf-8")
    dh = [line for line in rules.splitlines() if "dh_virtualenv" in line and "--python" in line]
    assert dh and all("--extras" not in line and "--requirements" not in line for line in dh), dh
    assert "--use-system-packages" in dh[0], dh
    assert not (ROOT / "requirements.txt").exists(), "dh_virtualenv installs requirements.txt by default"


def test_production_takes_it_from_debian():
    control = (ROOT / "debian" / "control").read_text(encoding="utf-8")
    depends = re.search(r"^Depends:(.*(?:\n[ \t].*)*)", control, re.M)
    assert depends and "python3-systemd" in depends.group(1)


def test_the_suite_never_skips_signalengine_for_a_missing_module():
    conftest = (ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "test_signalengine" not in conftest
    import systemd.daemon  # noqa: F401  (fails outside the hatch test environment, on purpose)
