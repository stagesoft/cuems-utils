# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every test lives in, and is marked by, its kind's directory (feature 017, FR-063, SC-012).

The kinds are ``tests/unit/``, ``tests/integration/``, ``tests/contract/`` and
``tests/packaging/``. ``tests/conftest.py`` adds the matching marker from the path, so
``pytest -m unit`` selects exactly the unit tests, and so on. Nothing lives at the ``tests/`` root:
the release line used to add its tests there, and every reconciliation then had to re-file them.
See ``specs/017-release-line-reconciliation/contracts/test-layout.md``.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]
KINDS = ("unit", "integration", "contract", "packaging")

# Printed by a throwaway plugin during collection: one line per item, its node id and markers.
_PLUGIN = '''
def pytest_collection_finish(session):
    for item in session.items:
        names = sorted({m.name for m in item.iter_markers()})
        print("ITEM", item.nodeid, "MARKERS", ",".join(names))
'''


def test_no_test_module_sits_at_the_tests_root():
    stray = sorted(p.name for p in TESTS.glob("test_*.py"))
    assert not stray, (
        f"move these into tests/{{{','.join(KINDS)}}}/ (contracts/test-layout.md): {stray}"
    )


def test_every_collected_test_carries_exactly_one_directory_marker(tmp_path):
    plugin = tmp_path / "layout_probe.py"
    plugin.write_text(_PLUGIN)
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
         "-p", "layout_probe", str(TESTS)],
        capture_output=True, text=True, cwd=TESTS.parent,
        env={**os.environ, "PYTHONPATH": f"{tmp_path}:{TESTS.parent / 'src'}"},
    )
    items = [line for line in run.stdout.splitlines() if line.startswith("ITEM ")]
    assert items, run.stdout[-2000:] + run.stderr[-2000:]
    wrong = []
    for line in items:
        nodeid, markers = line[5:].split(" MARKERS ")
        kinds = [k for k in KINDS if k in markers.split(",")]
        if len(kinds) != 1:
            wrong.append(f"{nodeid}: {kinds or 'no directory marker'}")
    assert not wrong, f"{len(wrong)} of {len(items)} items:\n  " + "\n  ".join(wrong[:20])


def test_every_collect_ignore_glob_still_matches_a_module():
    """``tests/conftest.py`` skips modules whose optional dependency is missing (``pynng``,
    ``systemd``) by path. A glob left behind by a move matches nothing, so the module is
    collected and errors on a box without the dependency. Found when 017 moved the root
    modules into their kind directories."""
    source = (TESTS / "conftest.py").read_text()
    globs = [g for line in source.splitlines() if "collect_ignore_glob +=" in line
             for g in re.findall(r'"([^"]+\.py)"', line)]
    assert globs, "expected the optional-dependency globs in tests/conftest.py"
    stale = [g for g in globs if not list(TESTS.glob(g))]
    assert not stale, f"collect_ignore_glob entries that match no module: {stale}"
