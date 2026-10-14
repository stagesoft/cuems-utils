"""G3, T058 — SC-005a: zero fields change repairability classification and
zero per-field ``default`` facts change, compared against T003's snapshot
(FR-026a, the load-bearing invariant of the whole gate).
"""

from __future__ import annotations

from pathlib import Path

from tests.support.repairability import diff_against_snapshot

SNAPSHOT = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "015-consumer-gate-closure"
    / "snapshots"
    / "repairability-before.txt"
)


def test_zero_fields_changed_repairability_or_default():
    diff = diff_against_snapshot(SNAPSHOT)
    assert diff == [], f"{len(diff)} field(s) changed repairability or default: {diff[:5]}"
