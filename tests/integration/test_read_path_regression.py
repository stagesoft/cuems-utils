# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T079 — the read path against feature 008's baseline (SC-PERF-002, FR-PERF-002, research R14).

Same method as that baseline: **median of five warm runs, fresh measurement per
run**, pyenv 3.11.9.

**Two rows, two comparisons, and the difference is not a convenience** (R14).
Three baselines exist — features 006, 008 and the 011/010 re-measure — so "the
recorded baseline" picks none of them; this one names 008's by path and takes
each row on the terms *that document* records it in:

* the **show-document** load is asserted against its recorded **budget**, which
  008 records it as comfortably within;
* the **`network_map`** configuration load is asserted against its recorded
  **measured band**, 10.14–10.49 ms, because 008 records that row as
  *exceeded-or-marginal* against its own 10.20 ms budget. Asserting the budget
  would fail on a tree where this feature changed nothing — which tells a reader
  nothing about this feature and teaches them to ignore the test.

Comparing to the band asks the question that is actually useful: **did the
tightened definition move this number.**
"""

from __future__ import annotations

import statistics
import time

import pytest

from tests.support.corpus import REPO_ROOT

#: ``specs/008-rebuild-extension/baseline.md``, named by path (FR-PERF-002).
BASELINE = REPO_ROOT / "specs" / "008-rebuild-extension" / "baseline.md"

#: The show-document load's recorded **budget** (008 §T001/§ITEM E: ≤ 200% of
#: 17.994 ms and ≤ 50 ms absolute → 35.99 ms). 008 measured 18.673 ms against it.
SHOW_DOCUMENT_BUDGET_MS = 35.99

#: ``network_map``'s recorded **measured band** — three trials of five runs gave
#: medians 9.984 / 10.486 / 10.214 ms. The band is what this feature is compared
#: against; its 10.20 ms budget is recorded there as exceeded-or-marginal.
NETWORK_MAP_BAND_MS = (10.14, 10.49)

#: How far outside the band counts as "this feature moved it". Generous, because
#: the band is itself three trials wide on a ~10 ms operation and this is a
#: 2-vCPU VM; tight enough that a doubling fails.
BAND_TOLERANCE = 1.5

RUNS = 5

SHOW_DOCUMENT = REPO_ROOT / "tests" / "data" / "corpus" / "cuems-engine" / "projects" / "complex_test" / "script.xml"
NETWORK_MAP = REPO_ROOT / "tests" / "data" / "network_map.xml"


def _median_ms(load) -> float:
    load()  # warm: schema parse and registry build are once per process
    timings = []
    for _ in range(RUNS):
        started = time.perf_counter()
        load()
        timings.append((time.perf_counter() - started) * 1000)
    return statistics.median(timings)


def test_the_named_baseline_exists_and_records_both_rows():
    """FR-PERF-002 names the baseline by path. If it moved, the two figures
    above are quotations from nothing."""
    assert BASELINE.is_file(), f"{BASELINE} does not exist"
    text = BASELINE.read_text()
    assert "10.14–10.49" in text or "10.14-10.49" in text, (
        "008's baseline no longer records network_map's measured band; the "
        "comparison this test makes has lost its reference"
    )
    assert "exceeded-or-marginal" in text, (
        "008's baseline no longer records network_map as exceeded-or-marginal, "
        "which is the whole reason this test compares to the band and not the budget"
    )


def test_the_show_document_load_is_within_its_recorded_budget():
    from cuemsutils.cues.CuemsScript import CuemsScript

    median = _median_ms(lambda: CuemsScript.load(str(SHOW_DOCUMENT)))
    print(f"\nshow document load: {median:.3f} ms "
          f"(008 measured 18.673 ms; budget {SHOW_DOCUMENT_BUDGET_MS} ms)")
    assert median <= SHOW_DOCUMENT_BUDGET_MS, (
        f"show-document load is {median:.3f} ms, over feature 008's recorded "
        f"budget of {SHOW_DOCUMENT_BUDGET_MS} ms"
    )


def test_the_network_map_load_is_within_its_recorded_measured_band():
    from cuemsutils.tools.ConfigBase import load_config_document
    from cuemsutils.xml.settings import NetworkMap

    median = _median_ms(
        lambda: load_config_document(NetworkMap, str(NETWORK_MAP), "network_map")
    )
    low, high = NETWORK_MAP_BAND_MS
    print(f"\nnetwork_map load: {median:.3f} ms "
          f"(008's measured band {low}–{high} ms, tolerance {BAND_TOLERANCE}x)")
    assert median <= high * BAND_TOLERANCE, (
        f"network_map load is {median:.3f} ms against feature 008's measured band "
        f"of {low}–{high} ms. The narrowing added a union type and one registered "
        "T2 rule to this document's read path; this is where that would show."
    )


def test_the_narrowing_added_exactly_one_rule_to_the_map_read():
    """What the number above is a measurement *of*. Stated so a future reader
    knows what to suspect if it moves: the union type is resolved once at schema
    load, but the uniqueness rule runs per read and walks every row."""
    from cuemsutils.xml.validators import RULES

    on_the_map = [name for name, rule in RULES.items()
                  if any(cls == "node" for cls, _field in rule.applies_to)]
    assert on_the_map == ["node_uuid_unique"]


def test_a_colliding_map_does_not_make_the_read_pathologically_slow(tmp_path):
    """The uniqueness rule's failure path builds a message naming every row. On
    a large map that must not become quadratic — an operator diagnosing a
    collision is already having a bad day."""
    from cuemsutils.errors import ValidationError
    from cuemsutils.tools.ConfigBase import load_config_document
    from cuemsutils.xml.settings import NetworkMap
    from tests.support.cluster_fixture import NodeSpec, mac_for, network_map_xml

    rows = [NodeSpec("6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40", mac_for(i), "node",
                     f"n{i}", f"10.0.0.{i}") for i in range(60)]
    path = tmp_path / "network_map.xml"
    path.write_text(network_map_xml(rows), encoding="utf-8")

    started = time.perf_counter()
    with pytest.raises(ValidationError):
        load_config_document(NetworkMap, str(path), "network_map")
    elapsed = (time.perf_counter() - started) * 1000
    print(f"\n60-row colliding map refused in {elapsed:.1f} ms")
    assert elapsed < 500, f"refusing a 60-row colliding map took {elapsed:.1f} ms"
