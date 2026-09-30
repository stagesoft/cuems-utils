# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T033 — the estimate divides by the **measured** throughput (FR-PERF-003).

Not by FR-PERF-001's 500 MB/s floor. The floor is a lower bound T077 asserts
the implementation *beats*, so dividing by it overstates every estimate by
exactly the margin of the beating: at a real 1 GB/s the estimate would be twice
the actual duration, failing SC-PERF-003's ±25% while the implementation was
entirely correct. An earlier draft of this feature had it that way, and the
arithmetic here is what would have caught it.

The floor is the **fallback only**, for a survey too small to time
meaningfully — and the output must say when it was used, so a pessimistic bound
is never presented as a measurement.
"""

from __future__ import annotations

from cuemsutils.tools import remint
from tests.support.cluster_fixture import build_cluster
from tests.support.remint_harness import run_remint, state_dir


def _survey(bytes_read, elapsed):
    """A survey with a known byte count and a known elapsed time, so the
    assertion is about the arithmetic and not about this machine."""
    return remint.Survey(
        documents=(), config_documents=(), library_documents=(),
        identities={}, node_identities=(),
        bytes_read=bytes_read, elapsed=elapsed,
    )


def test_the_estimate_is_bytes_over_the_observed_throughput():
    """4 MB surveyed in 40 ms is 100 MB/s, so 4 MB takes 40 ms to rewrite."""
    found = _survey(4_000_000, 0.040)
    assert found.observed_throughput == 4_000_000 / 0.040
    seconds, used_floor = remint.estimate_seconds(found)
    assert used_floor is False
    assert seconds == 0.040


def test_the_estimate_is_not_bytes_over_the_floor():
    """The specific wrong answer this test exists to exclude. At 1 GB/s
    measured, dividing by the 500 MB/s floor would predict twice the truth."""
    found = _survey(1_000_000_000, 1.0)          # 1 GB/s measured
    seconds, used_floor = remint.estimate_seconds(found)
    assert used_floor is False
    assert seconds == 1.0
    floor_answer = 1_000_000_000 / remint.THROUGHPUT_FLOOR
    assert abs(floor_answer - 2.0) < 1e-9, "the floor's answer is 2 s — twice the truth"
    assert seconds != floor_answer


def test_a_survey_too_small_to_time_falls_back_to_the_floor():
    found = _survey(4_000, 0.0001)
    assert found.observed_throughput is None
    seconds, used_floor = remint.estimate_seconds(found)
    assert used_floor is True
    assert seconds == 4_000 / remint.THROUGHPUT_FLOOR


def test_the_fallback_says_so_in_its_output():
    """A pessimistic bound presented as a measurement is worse than no
    estimate: an operator would size a maintenance window against it and
    believe the number."""
    text = remint.render_estimate(_survey(4_000, 0.0001))
    assert "floor" in text
    assert "not a measurement" in text


def test_a_measured_estimate_says_what_it_measured():
    text = remint.render_estimate(_survey(4_000_000, 0.040))
    assert "measured by the survey on this machine" in text
    assert "100.0 MB/s" in text


def test_an_empty_survey_does_not_divide_by_zero():
    found = _survey(0, 0.0)
    assert found.observed_throughput is None
    seconds, used_floor = remint.estimate_seconds(found)
    assert seconds == 0.0 and used_floor is True


def test_the_real_survey_reports_bytes_and_its_own_elapsed_time(tmp_path):
    """The survey already reads every byte the apply pass will read, which is
    what makes the measurement free."""
    from cuemsutils.tools import library_reach

    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], projects=3)
    found = remint.survey(cluster.conf, library_reach.reach_library(cluster.library))
    on_disk = sum(p.stat().st_size for p in found.documents)
    assert found.bytes_read == on_disk
    assert found.elapsed > 0


def test_a_dry_run_writes_nothing_at_all_not_even_a_table(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    before = {p for p in tmp_path.rglob("*") if p.is_file()}

    code, out = run_remint(cluster, state, extra=["--dry-run"])

    assert code == 0, out
    assert {p for p in tmp_path.rglob("*") if p.is_file()} == before
    assert "estimated" in out


def test_the_estimate_is_shown_with_the_confirmation(tmp_path):
    """Principle III: the operator confirms a destructive step, and confirms it
    knowing how long it will take."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    seen = []

    args = _args(cluster, state)
    code = remint.run(args, confirm=lambda text: (seen.append(text), False)[1])

    assert code == 1, "declining the confirmation must abandon the run"
    assert seen, "the operator was never asked"
    assert "estimated" in seen[0] and "MB to rewrite" in seen[0]


def test_declining_the_confirmation_writes_nothing(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    before = {p for p in tmp_path.rglob("*") if p.is_file()}

    code = remint.run(_args(cluster, state), confirm=lambda _text: False)

    assert code == 1
    assert {p for p in tmp_path.rglob("*") if p.is_file()} == before


def _args(cluster, state):
    from cuemsutils.tools import init_node

    return init_node._parser().parse_args([
        "--remint", "--conf-dir", str(cluster.conf), "--state-dir", str(state),
        "--library", str(cluster.library),
    ])
