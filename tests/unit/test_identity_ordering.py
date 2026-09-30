# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T063 — the identity type gains a total ordering (FR-029, data-model §6.2).

``sorted()`` over a collection of identities raises ``TypeError`` today. That
removes the failure for **every** consumer at once, including the ones that have
not been fixed (M-b) — which is the argument for putting it in the library
rather than asking each of them to convert.

Ordering **completes** an existing set rather than introducing new comparison
semantics: the type already defines equality and hashing against both itself and
``str``, so the only consistent ordering is the string form's.

**Not added**: slicing, ``len`` and ``split``. They would invite consumers to
treat an identity as a string in ways the compound-form parsing already handles
elsewhere, and the census (R4) found no site that needs them. Asserted as an
absence, because that is what a deliberate omission is.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools.Uuid import Uuid

VALUES = [
    "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40",
    "b2a41f0c-7d3e-4a11-9c02-1f3e5d7a9b01",
    "11111111-2222-4333-8444-555555555555",
]


def test_a_collection_of_identities_sorts():
    identities = [Uuid(v) for v in VALUES]
    assert [str(u) for u in sorted(identities)] == sorted(VALUES)


def test_the_ordering_agrees_with_the_string_form():
    for left in VALUES:
        for right in VALUES:
            a, b = Uuid(left), Uuid(right)
            assert (a < b) is (left < right)
            assert (a <= b) is (left <= right)
            assert (a > b) is (left > right)
            assert (a >= b) is (left >= right)


def test_ordering_against_a_plain_string_works_both_ways():
    """Equality already crosses the boundary, so ordering must too — a
    comparison set that worked for ``==`` and raised for ``<`` would be the more
    confusing outcome."""
    low, high = sorted(VALUES)[0], sorted(VALUES)[-1]
    assert Uuid(low) < high
    assert not Uuid(high) < low
    assert Uuid(high) > low


def test_a_mixed_collection_of_identities_and_strings_sorts():
    """Which is what a consumer actually has: some values converted, some not."""
    mixed = [Uuid(VALUES[0]), VALUES[1], Uuid(VALUES[2])]
    assert [str(x) for x in sorted(mixed, key=str)] == sorted(VALUES)


def test_ordering_against_an_unrelated_type_is_not_silently_true():
    with pytest.raises(TypeError):
        Uuid(VALUES[0]) < 42


def test_equality_and_hashing_are_unchanged():
    """Ordering completes the set; it must not have moved the rest of it."""
    a, b = Uuid(VALUES[0]), Uuid(VALUES[0])
    assert a == b and a == VALUES[0]
    assert hash(a) == hash(b) == hash(VALUES[0])
    assert a != Uuid(VALUES[1])
    assert len({a, b}) == 1


@pytest.mark.parametrize("operation", [len, list, iter])
def test_string_like_operations_are_still_absent(operation):
    with pytest.raises(TypeError):
        operation(Uuid(VALUES[0]))


def test_slicing_and_split_are_still_absent():
    identity = Uuid(VALUES[0])
    with pytest.raises(TypeError):
        identity[0:8]
    assert not hasattr(identity, "split")


def test_an_identity_is_not_a_str_subclass():
    """Stated because one consumer's websocket handler rejects a non-``str``
    node identity by ``isinstance`` (census, "One site named"). The type is
    deliberately not a ``str``, and that site is a reason not to let it leak
    into wire payloads — not a reason to make it one."""
    assert not isinstance(Uuid(VALUES[0]), str)
