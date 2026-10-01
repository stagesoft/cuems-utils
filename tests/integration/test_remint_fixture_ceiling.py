# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T078 — the `remint_200` fixture's wall-clock ceiling (SC-PERF-001).

**Re-baselined 2026-09-30**: 2.0 s → **0.027 s**, the worst measured figure plus
10%. The 2.0 s it replaces was the one figure FR-PERF-001 admitted as an
estimate rather than a measurement, and it was eighty times the truth.

**It moves downward only.** It is never raised to accommodate an
implementation — a ceiling that rises to meet whatever the code does is not a
budget, it is a record of the code. If it flakes, add repeats.

The scale is part of the budget, not a detail: `remint_200` is 200 projects at
about 4 MB, and `library_fixture.remint_200` asserts its byte total against a
recorded band, so a fixture that grew could not quietly move this number with it.
"""

from __future__ import annotations

import time

import pytest

from cuemsutils.tools import remint
from tests.support.library_fixture import REMINT_200, nodes_for, remint_200

#: SC-PERF-001, seconds. **Re-baselined 2026-09-30 from the measurement.**
#:
#: The stated ceiling was 2.0 s, and it was an estimate — the one figure
#: FR-PERF-001 admitted as such. Measured best-of-three across five trials, the
#: fixture is rewritten in **0.024 s**, so 2.0 s was eighty times the truth and
#: could not have failed on anything short of a catastrophe.
#:
#: 0.027 s is the worst measured figure plus 10%. That is a tight wall-clock
#: bound and the tightness is deliberate: it is what makes the number a budget
#: rather than a formality. It is affordable only because the measurement is
#: **best-of-three** — a single sample on this machine carries a ~20% outlier
#: about one run in five, which a 10% bound would catch as a failure. If this
#: does turn out to flake in CI, the answer is more repeats, not a larger
#: number: the ceiling moves **downward only**.
CEILING_SECONDS = 0.027


@pytest.fixture(scope="module")
def timed(tmp_path_factory):
    base = tmp_path_factory.mktemp("ceiling")
    rows = nodes_for(2)
    library = remint_200(base / "lib", nodes=rows)
    documents = sorted(p for p in library.root.rglob("*.xml") if p.is_file())

    # Best of three, for the reason test_remint_throughput.py's REPEATS
    # documents: on this machine one run in five carries a ~20% outlier, and a
    # wall-clock ceiling set from a single sample is a ceiling set from noise.
    best, rewritten = float("inf"), 0
    for _ in range(3):
        table = remint.build_table([n.uuid for n in rows], controller=rows[0].uuid)
        started = time.perf_counter()
        applied = remint.apply_table(table, documents, table_file=None)
        best = min(best, time.perf_counter() - started)
        rewritten = max(rewritten, len(applied))
        reverse = remint.SubstitutionTable(
            created=table.created, controller=table.controller,
            entries={new: old for old, new in table.entries.items()},
        )
        remint.apply_table(reverse, documents, table_file=None)
    return best, library, rewritten


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
    """Not an assertion — the number ``baseline.md`` §4 records. Printed so a
    run of this file alone gives it, rather than requiring the harness to be
    instrumented."""
    elapsed, library, rewritten = timed
    print(
        f"\nremint_200: {library.total_bytes} bytes, {rewritten} documents, "
        f"{elapsed:.3f} s ({library.total_bytes / elapsed / 1_000_000:.1f} MB/s) "
        f"against a {CEILING_SECONDS} s ceiling"
    )
    assert elapsed > 0
