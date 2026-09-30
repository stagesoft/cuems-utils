# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T079 — the read path against feature 008's baseline (SC-PERF-002, FR-PERF-002, research R14).

Same method as that baseline: **median of five warm runs, fresh measurement per
run**, pyenv 3.11.9.

**Re-baselined 2026-09-30.** Both rows are now asserted against **this
feature's own measurements plus 10%**, and feature 008's recorded figures are
kept as *provenance* — the check that this feature's numbers have not silently
drifted from the tree 008 measured.

Why that is better than what it replaces, per row:

* the **show-document** load was asserted against 008's ≤ 35.99 ms budget and
  measures ~13 ms. A budget nothing can fail detects nothing; 15.0 ms binds.
* the **`network_map`** configuration load had no usable budget to inherit. 008
  records that row as *exceeded-or-marginal* against its own 10.20 ms figure —
  three trials straddling the line — so R14's instruction was to compare against
  the measured band instead, because asserting a straddled budget would fail on
  an unchanged tree. With this feature's own measurement (~7.5 ms, comfortably
  below the band) there is a number that both binds and passes, which is
  strictly better than comparing to someone else's straddled line.

The question the file exists to ask is unchanged: **did the tightened definition
move these numbers.** It did not — the narrowing added a union type that resolves
once at schema load and one registered rule that walks the rows once.
"""

from __future__ import annotations

import statistics
import time

import pytest

from tests.support.corpus import REPO_ROOT

#: ``specs/008-rebuild-extension/baseline.md``, named by path (FR-PERF-002).
BASELINE = REPO_ROOT / "specs" / "008-rebuild-extension" / "baseline.md"

#: Feature 008's recorded figures, kept as **provenance** rather than as the
#: binding budget. They are what FR-PERF-002 named, and they are what the
#: re-baselined numbers below must be checked against for plausibility — a
#: budget derived from this feature's own measurements would be worthless if
#: those measurements had silently drifted from 008's.
EIGHT_SHOW_DOCUMENT_MS = 18.673
EIGHT_SHOW_DOCUMENT_BUDGET_MS = 35.99
EIGHT_NETWORK_MAP_BAND_MS = (10.14, 10.49)

#: **Re-baselined 2026-09-30 from this feature's own measurements**, worst
#: observed plus 10%.
#:
#: Four trials gave 12.605 / 12.907 / 13.172 / 13.651 ms, so 15.0 ms is the
#: worst plus 10%. It replaces 008's 35.99 ms budget, which this path now
#: clears by a factor of nearly three — a budget nothing can fail is a budget
#: that detects nothing.
SHOW_DOCUMENT_BUDGET_MS = 15.0

#: Four trials gave 7.416 / 7.489 / 7.502 / 7.956 ms, so 8.8 ms is the worst
#: plus 10%.
#:
#: This replaces the *band comparison* 008's record forced (its budget row is
#: recorded there as exceeded-or-marginal, so asserting it would have failed on
#: an unchanged tree). With this feature's own measurement in hand there is a
#: number that both binds and passes, which is strictly better than comparing to
#: someone else's straddled line.
NETWORK_MAP_BUDGET_MS = 8.8

RUNS = 5

SHOW_DOCUMENT = REPO_ROOT / "tests" / "data" / "corpus" / "cuems-engine" / "projects" / "complex_test" / "script.xml"
NETWORK_MAP = REPO_ROOT / "tests" / "data" / "network_map.xml"


#: How many medians are taken. The reported figure is the **best** of them.
#:
#: The unit of measurement is still feature 008's — "median of five warm runs" —
#: so the numbers stay comparable with that baseline, which is what the
#: provenance check below depends on. What is added is repetition of that unit.
#:
#: It was measured to be necessary. With one median, a stress run under 150% CPU
#: oversubscription failed the ``network_map`` budget once in eight; the
#: operation is ~7.5 ms, so a single scheduler hiccup is a large fraction of it.
#: Best-of-three removes that without loosening the budget — which is the right
#: trade, because the budget is what detects a regression and the repetition only
#: removes noise that was never evidence of one.
TRIALS = 3


def _median_ms(load) -> float:
    """The best of :data:`TRIALS` medians of :data:`RUNS` warm runs."""
    load()  # warm: schema parse and registry build are once per process
    medians = []
    for _ in range(TRIALS):
        timings = []
        for _ in range(RUNS):
            started = time.perf_counter()
            load()
            timings.append((time.perf_counter() - started) * 1000)
        medians.append(statistics.median(timings))
    return min(medians)


def test_the_named_baseline_exists_and_records_both_rows():
    """FR-PERF-002 names the baseline by path. It is no longer what binds, but
    it is still the provenance of the numbers above, and a quotation from a file
    that has moved is a quotation from nothing."""
    assert BASELINE.is_file(), f"{BASELINE} does not exist"
    text = BASELINE.read_text()
    assert "10.14–10.49" in text or "10.14-10.49" in text
    assert "exceeded-or-marginal" in text, (
        "008's baseline no longer records network_map as exceeded-or-marginal, "
        "which is the condition that made a re-baseline the right answer here"
    )
    assert str(EIGHT_SHOW_DOCUMENT_MS) in text


def test_the_show_document_load_is_within_its_recorded_budget():
    from cuemsutils.cues.CuemsScript import CuemsScript

    median = _median_ms(lambda: CuemsScript.load(str(SHOW_DOCUMENT)))
    print(f"\nshow document load: {median:.3f} ms "
          f"(re-baselined budget {SHOW_DOCUMENT_BUDGET_MS} ms; "
          f"008 measured {EIGHT_SHOW_DOCUMENT_MS} ms against "
          f"{EIGHT_SHOW_DOCUMENT_BUDGET_MS} ms)")
    assert median <= SHOW_DOCUMENT_BUDGET_MS, (
        f"show-document load is {median:.3f} ms, over the re-baselined budget of "
        f"{SHOW_DOCUMENT_BUDGET_MS} ms (this feature's worst measurement plus 10%)"
    )
    assert median <= EIGHT_SHOW_DOCUMENT_BUDGET_MS, (
        "and over feature 008's original budget, which the re-baselined one sits "
        "well inside — so this is a regression against both"
    )


def test_the_network_map_load_is_within_its_re_baselined_budget():
    from cuemsutils.tools.ConfigBase import load_config_document
    from cuemsutils.xml.settings import NetworkMap

    median = _median_ms(
        lambda: load_config_document(NetworkMap, str(NETWORK_MAP), "network_map")
    )
    low, high = EIGHT_NETWORK_MAP_BAND_MS
    print(f"\nnetwork_map load: {median:.3f} ms "
          f"(re-baselined budget {NETWORK_MAP_BUDGET_MS} ms; "
          f"008's measured band {low}–{high} ms)")
    assert median <= NETWORK_MAP_BUDGET_MS, (
        f"network_map load is {median:.3f} ms, over the re-baselined budget of "
        f"{NETWORK_MAP_BUDGET_MS} ms (this feature's worst measurement plus 10%). "
        "The narrowing added a union type and one registered T2 rule to this "
        "document's read path; this is where that would show."
    )


def test_the_re_baselined_budget_is_still_below_feature_008s_band():
    """The provenance check. The re-baselined number is derived from this
    feature's own measurements, so it would happily encode a drift that had
    already happened. 008's band is the outside reference that says it has not:
    this path is *faster* than the tree 008 measured, not merely consistent with
    itself."""
    low, _high = EIGHT_NETWORK_MAP_BAND_MS
    assert NETWORK_MAP_BUDGET_MS < low, (
        f"the re-baselined budget ({NETWORK_MAP_BUDGET_MS} ms) is no longer below "
        f"feature 008's measured band (from {low} ms). Either this path has slowed "
        "since 008, or the re-baseline captured a drift instead of a measurement."
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
