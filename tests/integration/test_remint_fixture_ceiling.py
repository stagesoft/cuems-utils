# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T078 — the `remint_200` fixture's wall-clock ceiling (SC-PERF-001).

**This ceiling is provisional**, and it is the one figure FR-PERF-001 states as
an estimate rather than a measurement. If the measurement lands well under it,
lower it to the measured figure plus headroom and record the change in
`baseline.md`.

**It moves downward only.** It is never raised to accommodate an
implementation — a ceiling that rises to meet whatever the code does is not a
budget, it is a record of the code.

The scale is part of the budget, not a detail: `remint_200` is 200 projects at
about 4 MB, and `library_fixture.remint_200` asserts its byte total against a
recorded band, so a fixture that grew could not quietly move this number with it.
"""

from __future__ import annotations

import time

import pytest

from cuemsutils.tools import remint
from tests.support.library_fixture import REMINT_200, nodes_for, remint_200

#: SC-PERF-001, seconds. **Provisional**, adjustable downward only.
#:
#: **Lowered from 2.0 s to 0.5 s on 2026-09-30**, per T078's instruction to
#: bring it to the measured figure plus headroom. The measurement is ~0.024 s
#: (``baseline.md`` §4), so 2.0 s was eighty times the truth and could not have
#: failed on anything short of a catastrophe.
#:
#: 0.5 s is ~20x the measured figure, which is deliberately generous for a
#: wall-clock assertion on a 2-vCPU VM: the alternative failure mode is a test
#: that goes red on an unrelated load spike, and a timing test that cries wolf
#: gets its budget raised rather than its cause investigated. It is still four
#: times tighter than what it replaces, and it would catch the regression that
#: matters — a per-file cost that grew by an order of magnitude.
CEILING_SECONDS = 0.5


@pytest.fixture(scope="module")
def timed(tmp_path_factory):
    base = tmp_path_factory.mktemp("ceiling")
    rows = nodes_for(2)
    library = remint_200(base / "lib", nodes=rows)
    table = remint.build_table([n.uuid for n in rows], controller=rows[0].uuid)
    documents = sorted(p for p in library.root.rglob("*.xml") if p.is_file())

    started = time.perf_counter()
    rewritten = remint.apply_table(table, documents, table_file=None)
    elapsed = time.perf_counter() - started
    return elapsed, library, len(rewritten)


def test_the_named_fixture_is_rewritten_within_the_ceiling(timed):
    elapsed, library, rewritten = timed
    assert elapsed <= CEILING_SECONDS, (
        f"remint_200 ({library.total_bytes} bytes, {rewritten} documents) took "
        f"{elapsed:.3f} s, over the {CEILING_SECONDS} s ceiling"
    )


def test_the_fixture_is_the_scale_the_ceiling_names(timed):
    """A ceiling stated for a named fixture means nothing if the fixture drifts."""
    _elapsed, library, _rewritten = timed
    low, high = REMINT_200["band"]
    assert len(library.projects) == REMINT_200["projects"] == 200
    assert low <= library.total_bytes <= high


def test_the_measured_figure_is_reported_for_the_record(timed):
    """Not an assertion — the number T081 records. Printed so a run of this file
    alone gives it, rather than requiring the harness to be instrumented."""
    elapsed, library, rewritten = timed
    print(
        f"\nremint_200: {library.total_bytes} bytes, {rewritten} documents, "
        f"{elapsed:.3f} s ({library.total_bytes / elapsed / 1_000_000:.1f} MB/s) "
        f"against a provisional {CEILING_SECONDS} s ceiling"
    )
    assert elapsed > 0
