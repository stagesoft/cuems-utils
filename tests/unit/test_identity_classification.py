# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T005 — the identity classification (feature 012, data-model §1.3, FR-021c).

Every shape lands in **exactly one** class, and the one assertion this file
exists for: the sentinel is **not** ``not-converged``. Classifying it there
would send an operator to the cluster re-mint for a node that was simply never
provisioned, which is a different act with a different cost.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools import ids
from tests.support.cluster_fixture import SHAPES

EXPECTED = {
    "uuid4": ids.CONVERGED,
    "uuid4b": ids.CONVERGED,
    "uuid1": ids.NOT_CONVERGED,
    "uuid5": ids.NOT_CONVERGED,
    "uuid4upper": ids.NOT_CONVERGED,
    "sentinel": ids.NOT_PROVISIONED_CLASS,
    "nonsense": ids.UNRECOGNISED,
}


@pytest.mark.parametrize("shape,expected", sorted(EXPECTED.items()))
def test_each_shape_lands_in_its_class(shape, expected):
    assert ids.classify(SHAPES[shape]) == expected


@pytest.mark.parametrize("shape", sorted(EXPECTED))
def test_every_shape_lands_in_exactly_one_class(shape):
    """The classes are a partition, not a set of overlapping predicates.

    Asserted by counting rather than by inspecting the implementation: a future
    class added without a disjointness argument fails here.
    """
    value = SHAPES[shape]
    assert [ids.classify(value) == cls for cls in ids.CLASSES].count(True) == 1
    assert ids.classify(value) in ids.CLASSES


def test_the_sentinel_is_not_classified_not_converged():
    """The one assertion this file exists for (data-model §1.3)."""
    assert ids.classify(ids.NOT_PROVISIONED_UUID) == ids.NOT_PROVISIONED_CLASS
    assert ids.classify(ids.NOT_PROVISIONED_UUID) != ids.NOT_CONVERGED


def test_the_sentinel_is_admitted_but_never_converged():
    """``admitted`` and ``converged`` are two words for two sets (§1.2)."""
    assert ids.is_admitted(ids.NOT_PROVISIONED_UUID)
    assert not ids.is_converged(ids.NOT_PROVISIONED_UUID)
    assert ids.is_converged(SHAPES["uuid4"])
    assert ids.is_admitted(SHAPES["uuid4"])
    assert not ids.is_admitted(SHAPES["uuid1"])


def test_upper_case_uuid4_is_not_converged():
    """Case is part of the shape, not a presentation detail: two spellings of
    one identity are two tokens to a literal substitution, and the compound
    ``<identity>_<output>`` prefixes are matched literally (FR-009)."""
    lower = SHAPES["uuid4"]
    assert ids.is_converged(lower)
    assert not ids.is_converged(lower.upper())
    assert ids.classify(lower.upper()) == ids.NOT_CONVERGED


@pytest.mark.parametrize("value", [None, "", "   ", "6f1d2c3b-4a5e-4f60-8a71", "z" * 36])
def test_unnameable_values_are_unrecognised(value):
    """Not a failure mode with its own class: "inspect by hand" is the honest
    action for a value nothing here can name."""
    assert ids.classify(value) == ids.UNRECOGNISED


def test_the_admitted_pattern_is_the_union_of_the_two_named_halves():
    """FR-021c: two separately named definitions, and a union of them — so
    either half can be named, tested and removed on its own."""
    import re

    admitted = re.compile(f"^(?:{ids.ADMITTED_PATTERN})$")
    assert admitted.match(SHAPES["uuid4"])
    assert admitted.match(ids.NOT_PROVISIONED_UUID)
    assert not admitted.match(SHAPES["uuid1"])
    assert not admitted.match(SHAPES["uuid4upper"])
    # and the halves are genuinely separate, not one pattern read twice
    assert re.compile(f"^(?:{ids.CONVERGED_PATTERN})$").match(SHAPES["uuid4"])
    assert not re.compile(f"^(?:{ids.CONVERGED_PATTERN})$").match(ids.NOT_PROVISIONED_UUID)
    assert re.compile(f"^(?:{ids.SENTINEL_PATTERN})$").match(ids.NOT_PROVISIONED_UUID)
