# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T077 — throughput, and the per-node-pass defect (SC-PERF-001, FR-PERF-001, research R8).

FR-PERF-001 states two budgets, both non-provisional: **≥ 500 MB/s** scanned and
rewritten, and the two node counts' elapsed times agreeing within a **1.10×
ratio**. The second passes. **The first does not, and cannot** — recorded here
and in ``baseline.md`` as exceeded rather than restated as passing, which is this
repository's standing practice and this feature's plan's explicit instruction.

## Why the 500 MB/s floor cannot be met, measured rather than argued

:func:`test_the_no_substitution_pass_is_the_machines_own_ceiling` measures a pass
that reads every document and atomically rewrites it **with no substitution at
all**. On this machine and this fixture that is ~13 ms — about **300 MB/s**. The
budget allows 7.9 ms. So no implementation can meet it, however good its
substitution, while the operation keeps the atomicity the contract requires
(temporary plus ``os.replace``, per file).

The floor conflates two different costs. ``remint_200`` is 400 documents of about
10 KB each, so the pass is dominated by **per-file syscalls**, not by bytes moved:
400 atomic replaces cost what they cost. A 500 MB/s figure describes streaming a
few large files, which is not the shape of a project library.

**What is asserted instead**, and why it is the better test: the implementation
must come within a stated factor of the machine's *own* no-substitution ceiling,
measured in the same run. That is portable across machines, it catches the
regression an absolute figure was reaching for — a substitution that has become
the bottleneck — and it does not measure the disk and call the result a verdict
on this code. The absolute figure is still reported, for ``baseline.md``.

**SC-PERF-001's whole point is the second one.** A single wall-clock number on
one fixture cannot see an implementation that loops files per node — it would
just be slower, and "slower than what?" has no answer from one measurement. Two
node counts over the **same library bytes** turn the defect into a divergence
between two measurements, which is a test rather than a judgement.

**A ratio, not a percentage.** The fixture runs in single-digit milliseconds
where the 1% an earlier draft carried is ~80 µs — below this machine's timing
jitter, so the assertion would have measured noise. A test that fails on jitter
and a test that cannot fail are the same test. 1.10× keeps the discriminating
power, because a per-node repeated pass makes the 10-node run about **5×** the
2-node one, not 1.1×.

**"Identical library bytes", arranged rather than assumed.** A script's length
does not depend on how many nodes exist — every identity is 36 characters — but
`mappings.xml` lists one entry per node, so it does. Both libraries are therefore
generated from the **same** node rows, and only the *table* varies: 2 entries
against 10, over byte-identical trees. That is exactly the axis the defect lives
on.
"""

from __future__ import annotations

import os
import shutil
import time

import pytest

from cuemsutils.tools import remint
from tests.support.library_fixture import nodes_for, remint_200

#: FR-PERF-001, in bytes per second. A **floor**, not a target — and one this
#: operation cannot reach at ``remint_200``'s file count; see the module
#: docstring. Kept named here because the estimate still uses it as its
#: fallback, and because a reader arriving at a failure needs the number.
FLOOR = remint.THROUGHPUT_FLOOR

#: How much of the machine's own no-substitution ceiling the full pass may cost.
#: The substitution reads every byte once more and writes the result, so some
#: overhead is inherent; 2.5x leaves room for that and still fails on a
#: substituter that has become the dominant cost.
CEILING_FACTOR = 2.5

#: FR-PERF-001. The slower run's elapsed time over the faster's.
AGREEMENT_RATIO = 1.10

NODE_COUNTS = (2, 10)


def _apply_once(library, table):
    """Rewrite every document once, timed. No table persistence: the per-file
    `save` is real work the apply loop does, but it is not the pass this budget
    measures, and including it would time the state directory's filesystem."""
    documents = sorted(p for p in library.rglob("*.xml") if p.is_file())
    started = time.perf_counter()
    remint.apply_table(table, documents, table_file=None)
    return time.perf_counter() - started


@pytest.fixture(scope="module")
def measured(tmp_path_factory):
    """``{node_count: (elapsed, bytes)}`` over byte-identical libraries."""
    base = tmp_path_factory.mktemp("throughput")
    rows = nodes_for(2)                 # the library's content, held fixed
    source = remint_200(base / "source", nodes=rows)
    total = sum(p.stat().st_size for p in source.root.rglob("*.xml") if p.is_file())

    results = {}
    for count in NODE_COUNTS:
        target = base / f"run{count}"
        shutil.copytree(source.root, target)
        # The table is what varies: one entry per node in the cluster, over the
        # same library. A per-node pass would scan the whole tree once per entry.
        table = remint.build_table(
            [n.uuid for n in nodes_for(count)], controller=rows[0].uuid
        )
        assert len(table.entries) == count
        results[count] = (_apply_once(target, table), total)
    return results


@pytest.fixture(scope="module")
def ceiling(tmp_path_factory):
    """The machine's own cost for read + atomic rewrite, no substitution.

    The same fixture, the same file count, the same syscalls per file — and no
    substitution at all. Whatever this costs is the floor **any** correct
    implementation of this operation sits above, so it is the right thing to
    measure the implementation against.
    """
    base = tmp_path_factory.mktemp("ceiling-ref")
    rows = nodes_for(2)
    library = remint_200(base / "lib", nodes=rows)
    documents = sorted(p for p in library.root.rglob("*.xml") if p.is_file())
    total = sum(p.stat().st_size for p in documents)

    best = float("inf")
    for _ in range(3):
        started = time.perf_counter()
        for path in documents:
            data = path.read_bytes()
            temporary = f"{path}.ceiling.tmp"
            handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            try:
                os.write(handle, data)
            finally:
                os.close(handle)
            os.replace(temporary, str(path))
        best = min(best, time.perf_counter() - started)
    return best, total


def test_the_no_substitution_pass_is_the_machines_own_ceiling(ceiling):
    """The measurement that makes the module docstring's claim checkable rather
    than an opinion: if this ever comes in under FR-PERF-001's budget, the floor
    becomes reachable and this file should be reconsidered."""
    elapsed, total = ceiling
    throughput = total / elapsed
    print(f"\nno-substitution ceiling: {throughput / 1_000_000:.0f} MB/s "
          f"({elapsed * 1000:.1f} ms for {total} bytes in atomic per-file rewrites)")
    assert throughput < FLOOR, (
        f"read + atomic rewrite alone now reaches {throughput / 1_000_000:.0f} MB/s, "
        f"at or above FR-PERF-001's {FLOOR / 1_000_000:.0f} MB/s floor. The floor is "
        "reachable on this machine after all — re-open the budget rather than "
        "leaving it recorded as exceeded."
    )


@pytest.mark.parametrize("count", NODE_COUNTS)
def test_the_substitution_is_not_the_bottleneck(measured, ceiling, count):
    """The assertion that replaces the unreachable absolute figure.

    Within :data:`CEILING_FACTOR` of a pass that does no substitution at all, so
    a substituter that became the dominant cost — a pass per entry, a decode/
    encode round trip, a quadratic scan — fails here.
    """
    elapsed, total = measured[count]
    reference, _ = ceiling
    print(f"\n{count} nodes: {total / elapsed / 1_000_000:.0f} MB/s "
          f"({elapsed * 1000:.1f} ms), ceiling {reference * 1000:.1f} ms, "
          f"ratio {elapsed / reference:.2f}x")
    assert elapsed <= reference * CEILING_FACTOR, (
        f"{count} nodes took {elapsed * 1000:.1f} ms against a no-substitution "
        f"ceiling of {reference * 1000:.1f} ms — {elapsed / reference:.2f}x, over "
        f"{CEILING_FACTOR}x. The substitution has become the dominant cost."
    )


@pytest.mark.parametrize("count", NODE_COUNTS)
def test_the_absolute_figure_is_reported_for_the_record(measured, count):
    """Not an assertion against the floor — the number T081 records, and the
    number a reader needs in order to check the module docstring's arithmetic."""
    elapsed, total = measured[count]
    throughput = total / elapsed
    print(f"\n{count} nodes: {throughput / 1_000_000:.1f} MB/s over {total} bytes "
          f"in {elapsed * 1000:.1f} ms (FR-PERF-001's floor: "
          f"{FLOOR / 1_000_000:.0f} MB/s — EXCEEDED, see baseline.md)")
    assert throughput > 0


def test_the_two_node_counts_agree_within_the_ratio(measured):
    """The assertion SC-PERF-001 exists for. A per-node repeated pass makes the
    10-node run about 5× the 2-node one; 1.10× catches that with ~0.8 ms of
    headroom on this fixture, comfortably above the machine's jitter."""
    two, ten = measured[2][0], measured[10][0]
    slower, faster = max(two, ten), min(two, ten)
    assert slower <= faster * AGREEMENT_RATIO, (
        f"2 nodes: {two * 1000:.2f} ms, 10 nodes: {ten * 1000:.2f} ms — a ratio of "
        f"{slower / faster:.2f}×, over {AGREEMENT_RATIO}×. The library bytes are "
        "identical, so an implementation whose cost scales with the node count is "
        "making a pass per node."
    )


def test_both_runs_actually_did_the_work(measured, tmp_path_factory):
    """The control. A substituter that matched nothing would be fast, agree
    perfectly across node counts, and prove nothing at all."""
    base = tmp_path_factory.mktemp("control")
    rows = nodes_for(2)
    library = remint_200(base / "lib", nodes=rows)
    table = remint.build_table([n.uuid for n in rows], controller=rows[0].uuid)
    documents = sorted(p for p in library.root.rglob("*.xml") if p.is_file())

    rewritten = remint.apply_table(table, documents, table_file=None)

    assert len(rewritten) == len(documents), "some documents were not rewritten"
    haystack = "".join(p.read_text() for p in documents)
    for old, new in table.entries.items():
        assert old not in haystack
        assert new in haystack
