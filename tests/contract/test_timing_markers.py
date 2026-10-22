# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Wall-clock budget tests never run under coverage (marker ``nocov``).

Coverage tracing slows each code path by a different factor: measured 2026-10-22, the show-document
load 2.5×, the remint rewrite 1.5×, and the substitution/no-substitution ratio 1.33×. So a budget
test run with ``--cov`` measures the tracer, not the code. Raising the budgets would have had to go
up to 2.4×, and that would stop them catching the regressions they exist for.

Instead every such test is marked ``slow`` **and** ``nocov``:

* a coverage run deselects it with ``-m "not slow"`` (``slow`` is the guarantee: every ``nocov``
  is ``slow``);
* it runs on its own, without ``--cov``: ``pytest -m nocov``;
* the other slow tests run as ``pytest -m "slow and not nocov"``.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: The wall-clock assertions this marker exists for. Module ids cover every test in the module.
TIMING = (
    "tests/integration/test_remint_throughput.py::",
    "tests/integration/test_remint_fixture_ceiling.py::",
    "tests/integration/test_read_path_regression.py::test_the_show_document_load_is_within_its_recorded_budget",
    "tests/integration/test_read_path_regression.py::test_the_network_map_load_is_within_its_re_baselined_budget",
    "tests/integration/test_read_path_regression.py::test_a_colliding_map_does_not_make_the_read_pathologically_slow",
)


def _collect(expression: str) -> list[str]:
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "--co", "-q", "-p", "no:cacheprovider", "-m", expression, "tests"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert run.returncode in (0, 5), run.stdout[-2000:] + run.stderr[-2000:]  # 5: none selected
    return [line for line in run.stdout.splitlines() if "::" in line]


def test_every_wall_clock_budget_test_is_marked_nocov():
    nocov = _collect("nocov")
    missing = [t for t in TIMING if not any(n.startswith(t) for n in nocov)]
    assert not missing, f"not marked nocov: {missing}"


def test_every_nocov_test_is_also_slow_so_coverage_runs_skip_it():
    assert _collect("nocov"), "nothing is marked nocov, so this check would hold vacuously"
    assert _collect("nocov and not slow") == []
