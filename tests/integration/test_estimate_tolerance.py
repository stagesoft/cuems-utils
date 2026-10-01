# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T080 — the operator's duration estimate (SC-PERF-003).

**SC-PERF-003's ±25% is not met.** It was supplied by an analysis pass without
measurement; the measured error over eight samples is **+120% to +147%**, in the
**pessimistic** direction. The budget this file asserts was re-baselined on
2026-09-30 from those samples plus 10% — `predicted <= actual * 2.72` — and the
original ±25% is recorded as exceeded rather than restated as passing.

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
* the estimate must scale with the throughput the survey **observed**, not with
  a constant — asserted on synthetic surveys, so it stays true on a machine
  whose speed differs from the floor's.

The recorded figures are in ``baseline.md``.
"""

from __future__ import annotations

import shutil
import time

import pytest

from cuemsutils.tools import library_reach, remint
from tests.support.library_fixture import nodes_for, remint_200

#: SC-PERF-003's **original** stated tolerance, ±25%, supplied by an analysis
#: pass without measurement. Kept named because the gap between it and the
#: measurement is the finding, and a reader should be able to check the number
#: rather than take the claim.
STATED_TOLERANCE = 0.25

#: How optimistic the estimate may be. Small, and **not** re-baselined from the
#: measurement: the measured optimism is zero, and this is the dangerous
#: direction — an operator sizes a maintenance window against the figure. A
#: budget derived from "it has never happened" would be 0%, which no timing
#: assertion should be; 10% is the smallest number that is not that.
MAX_OPTIMISM = 0.10

#: How pessimistic it may be: ``predicted <= actual * (1 + MAX_PESSIMISM)``.
#:
#: **Re-baselined 2026-09-30 from the measurement**: eight samples ranged
#: +120% to +147%, so the worst observed ratio is 2.47x and this is that plus
#: 10%. It replaces a 2.0 chosen to sit above a single observation, which the
#: wider sample would have failed.
#:
#: A bound rather than a tolerance: the estimate is allowed to be conservative,
#: and is not allowed to drift further into being so. ``baseline.md`` §6 has
#: the samples and the reason the pessimism exists at all.
MAX_PESSIMISM = 1.72

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


def test_the_estimate_tracks_the_machine_and_not_a_constant():
    """FR-PERF-003's substance, asserted in a machine-independent way.

    **This test changed shape when the floor was re-baselined**, and the reason
    is worth recording. It used to show that dividing by FR-PERF-001's constant
    gave a badly wrong answer — easy to demonstrate while the constant was
    500 MB/s and the machine ran at 160. Now that the floor *is* 140 MB/s, the
    two happen to agree here, and a test built on that coincidence would have
    started passing for the wrong reason and then failed on the first machine
    where they diverged again.

    So it asserts the property instead, on two synthetic surveys: the same byte
    count observed at different throughputs must produce proportionally
    different predictions. A constant divisor cannot do that, and a node on
    slower storage or under load is exactly the case where the constant is wrong
    and the measurement is right.
    """
    megabyte = 1_000_000

    def survey_at(mb_per_second):
        return remint.Survey(
            documents=(), config_documents=(), library_documents=(),
            identities={}, node_identities=(),
            bytes_read=100 * megabyte, elapsed=100 / mb_per_second,
        )

    fast, _ = remint.estimate_seconds(survey_at(1000))
    slow, _ = remint.estimate_seconds(survey_at(100))

    assert fast == pytest.approx(0.1, rel=1e-6)
    assert slow == pytest.approx(1.0, rel=1e-6)
    assert slow == pytest.approx(fast * 10, rel=1e-6), (
        "the estimate does not scale with the throughput the survey observed — "
        "it is dividing by a constant, which is what FR-PERF-003 forbids"
    )


def test_the_floor_is_used_only_when_the_survey_cannot_time_itself():
    """The other half of the same requirement: the constant is a fallback, and
    a run that used it must **say** so, or a pessimistic bound gets presented as
    a measurement."""
    untimeable = remint.Survey(
        documents=(), config_documents=(), library_documents=(),
        identities={}, node_identities=(),
        bytes_read=4_000, elapsed=0.0001,
    )
    seconds, used_floor = remint.estimate_seconds(untimeable)
    assert used_floor is True
    assert seconds == 4_000 / remint.THROUGHPUT_FLOOR
    assert "not a measurement" in remint.render_estimate(untimeable)
