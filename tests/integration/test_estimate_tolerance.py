# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T080 — the operator's duration estimate (SC-PERF-003).

**SC-PERF-003's ±25% is not met, and is recorded as exceeded rather than
restated as passing** — this repository's standing practice, and this feature's
plan's explicit instruction. The measured error is about **+115%**: the estimate
is roughly twice the actual duration, in the **pessimistic** direction.

## Why, measured rather than argued

FR-PERF-003 divides surveyed bytes by the throughput **the survey observed on
this machine**, and that part is right and is what this file's last test
protects. But research R8's supporting premise — "the survey already reads every
byte the apply pass will read, so the measurement is free" — is true of the
*read* and not of the *work*. The two passes do different things per byte:

============  ==========================================  ==============
Pass          Per byte                                    Measured
============  ==========================================  ==============
survey        read, then find **any** uuid-shaped token
              (five character classes, every position)     ~69 MB/s
apply         read, substitute **known literal** tokens
              (fast literal search), write                 ~150 MB/s
============  ==========================================  ==============

The survey's scan is the more expensive of the two even though it writes
nothing, so dividing by its throughput overstates the apply pass by about the
ratio between them. ``ids.scan_values`` already removed the larger part of that
gap — the survey used to run the full occurrence scanner and was **ten** times
out — and what remains is inherent to asking a broader question.

## What is asserted instead

The direction matters more than the magnitude, and it is the thing an operator
is actually exposed to:

* the estimate must **never be optimistic** beyond a small margin. An operator
  told 8 minutes who needs 25 has a problem; one told 50 who needs 25 does not.
  This is the assertion that would fail if someone "fixed" the estimate by
  dividing by the read throughput alone;
* it must stay within a **measured, recorded** pessimism bound, so the estimate
  cannot quietly drift from twice the truth to ten times it — which is exactly
  what a regression in the survey's scan would look like, and exactly what
  happened before ``scan_values``;
* dividing by FR-PERF-001's floor must remain **worse and in the dangerous
  direction**, which is the specific wrong implementation this test excludes.

The recorded figures are in ``baseline.md``.
"""

from __future__ import annotations

import shutil
import time

import pytest

from cuemsutils.tools import library_reach, remint
from tests.support.library_fixture import nodes_for, remint_200

#: SC-PERF-003's stated tolerance. **Not met** — kept named so the failure the
#: module docstring describes is a number a reader can check, not a claim.
STATED_TOLERANCE = 0.25

#: How optimistic the estimate may be. Small, because this is the dangerous
#: direction: an operator sizes a maintenance window against it.
MAX_OPTIMISM = 0.10

#: How pessimistic it may be, measured on this machine (~+115%) plus headroom.
#: A bound rather than a tolerance: the estimate is allowed to be conservative,
#: and is not allowed to drift further into being so.
MAX_PESSIMISM = 2.0

NODE_COUNTS = (2, 10)


@pytest.fixture(scope="module")
def clusters(tmp_path_factory):
    """One library per node count, over the same content, each with its own
    survey and its own timed apply pass."""
    base = tmp_path_factory.mktemp("estimate")
    rows = nodes_for(2)
    source = remint_200(base / "source", nodes=rows)

    results = {}
    for count in NODE_COUNTS:
        target = base / f"run{count}"
        shutil.copytree(source.root, target)
        reach = library_reach.reach_library(target)
        found = remint.survey(base / "no-conf", reach)
        predicted, used_floor = remint.estimate_seconds(found)

        table = remint.build_table(
            [n.uuid for n in nodes_for(count)], controller=rows[0].uuid
        )
        documents = sorted(p for p in target.rglob("*.xml") if p.is_file())
        started = time.perf_counter()
        remint.apply_table(table, documents, table_file=None)
        actual = time.perf_counter() - started

        results[count] = (predicted, actual, used_floor, found)
    return results


@pytest.mark.parametrize("count", NODE_COUNTS)
def test_the_survey_timed_itself_rather_than_falling_back(clusters, count):
    """The precondition for the tolerance to mean anything. A 4 MB survey is
    well above the timeable threshold, so a fallback here would mean the survey
    stopped reading the bytes it claims to."""
    _predicted, _actual, used_floor, found = clusters[count]
    assert used_floor is False, (
        "the survey fell back to the throughput floor on a 4 MB fixture; the "
        "estimate is then a pessimistic bound and this tolerance does not apply"
    )
    assert found.observed_throughput is not None
    assert found.bytes_read > 3_000_000


@pytest.mark.parametrize("count", NODE_COUNTS)
def test_the_prediction_is_never_optimistic(clusters, count):
    """The dangerous direction, and the one an operator is exposed to."""
    predicted, actual, _used_floor, _found = clusters[count]
    print(f"\n{count} nodes: predicted {predicted * 1000:.1f} ms, "
          f"actual {actual * 1000:.1f} ms, "
          f"{(predicted / actual - 1) * 100:+.0f}%")
    assert predicted >= actual * (1 - MAX_OPTIMISM), (
        f"{count} nodes: predicted {predicted:.4f} s against an actual "
        f"{actual:.4f} s — the estimate is optimistic. An operator sizes a "
        "maintenance window against this figure."
    )


@pytest.mark.parametrize("count", NODE_COUNTS)
def test_the_prediction_stays_within_the_measured_pessimism_bound(clusters, count):
    """The regression this file mainly guards. Before ``ids.scan_values`` the
    survey ran the full occurrence scanner and the estimate was **ten** times
    the truth; that is what a bound catches and a direction check does not."""
    predicted, actual, _used_floor, _found = clusters[count]
    assert predicted <= actual * (1 + MAX_PESSIMISM), (
        f"{count} nodes: predicted {predicted:.4f} s against an actual "
        f"{actual:.4f} s — {predicted / actual:.1f}x, past the recorded "
        f"{1 + MAX_PESSIMISM:.1f}x bound. The survey is doing more work per byte "
        "than it was; its elapsed time is the operator's estimate."
    )


@pytest.mark.parametrize("count", NODE_COUNTS)
def test_the_stated_tolerance_is_recorded_as_exceeded(clusters, count):
    """SC-PERF-003 as written, measured and reported — not asserted.

    Recorded here as well as in ``baseline.md`` so that the gap is visible from
    the test file rather than only from a document nobody runs. If this ever
    comes in **under** the stated tolerance, the budget is met after all and the
    two bounds above should be replaced by it.
    """
    predicted, actual, _used_floor, _found = clusters[count]
    error = abs(predicted - actual) / actual
    print(f"\n{count} nodes: SC-PERF-003 error {error * 100:.0f}% against a "
          f"stated tolerance of {STATED_TOLERANCE * 100:.0f}% — EXCEEDED "
          f"(pessimistic), see baseline.md")
    if error <= STATED_TOLERANCE:
        pytest.fail(
            f"the estimate now meets SC-PERF-003 ({error * 100:.0f}% <= "
            f"{STATED_TOLERANCE * 100:.0f}%). Replace the pessimism bound with "
            "the stated tolerance and update baseline.md — the budget is met."
        )


def test_dividing_by_the_floor_would_have_failed_this(clusters):
    """The specific wrong implementation this test excludes, shown rather than
    described. Named so the next person to "simplify" the estimate sees what
    they would be reintroducing."""
    predicted, actual, _used_floor, found = clusters[2]
    floor_prediction = found.bytes_read / remint.THROUGHPUT_FLOOR
    floor_error = abs(floor_prediction - actual) / actual
    print(f"\ndividing by the 500 MB/s floor would predict "
          f"{floor_prediction * 1000:.1f} ms against an actual "
          f"{actual * 1000:.1f} ms — {floor_error * 100:.0f}% out")
    assert floor_error > STATED_TOLERANCE, (
        "dividing by the floor happens to land inside the tolerance on this "
        "machine, so this test is not currently discriminating between the two "
        "implementations. It still is on a machine whose throughput differs more "
        "from the floor; recorded rather than deleted."
    )
    # And in the dangerous direction: the floor *under*estimates here.
    assert floor_prediction < actual, (
        "dividing by the floor is not optimistic on this machine, so the "
        "asymmetry this test describes does not currently hold here"
    )
