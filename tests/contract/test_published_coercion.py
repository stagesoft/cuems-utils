# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T064 — the published rule and the library's own decoding agree (FR-030).

One consumer has mirrored this rule by hand (M-c). Publishing it is what lets
that copy be deleted rather than left to drift — and a published rule that
disagreed with the library's own behaviour would be worse than no published
rule, because a consumer would trust it.

So the assertion is not "the published rule behaves sensibly". It is
"``ids.coerce_identity`` and ``_UuidAdapter.decode`` return the same thing for
the same input", over every input class the rule distinguishes.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools import ids
from cuemsutils.tools.Uuid import Uuid
from cuemsutils.xml.adapters import adapter_for

INPUTS = [
    "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40",   # converged
    "0367f391-ebf4-11b2-9f26-000000000001",   # uuid1
    "74738ff5-5367-5958-9aee-98fffdcd1876",   # uuid5
    "6F1D2C3B-4A5E-4F60-8A71-9B8C7D6E5F40",   # upper-case uuid4
    ids.NOT_PROVISIONED_UUID,                 # the sentinel
    "not-a-uuid",
    "",
    None,
]


@pytest.mark.parametrize("value", INPUTS)
def test_the_published_rule_and_the_librarys_decoding_agree(value):
    published = ids.coerce_identity(value)
    decoded = adapter_for("NodeUuidType").decode(value)
    assert type(published) is type(decoded)
    assert published == decoded


def test_a_converged_value_becomes_the_identity_type():
    result = ids.coerce_identity("6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40")
    assert isinstance(result, Uuid)
    assert str(result) == "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40"


def test_a_uuid1_stays_a_string():
    result = ids.coerce_identity("0367f391-ebf4-11b2-9f26-000000000001")
    assert type(result) is str


def test_the_sentinel_stays_a_string_and_that_is_the_intended_result():
    """It is *admitted* by the schemas and is not *converged*, so it falls
    through the rule's second branch. That is what makes **one comparison**
    enough for a consumer to recognise an unprovisioned node before attempting
    a full load, which otherwise raises (M-d)."""
    result = ids.coerce_identity(ids.NOT_PROVISIONED_UUID)
    assert type(result) is str
    assert result == ids.NOT_PROVISIONED_UUID


def test_a_non_uuid_string_stays_a_string():
    assert ids.coerce_identity("not-a-uuid") == "not-a-uuid"


@pytest.mark.parametrize("empty", [None, ""])
def test_an_empty_value_becomes_nothing(empty):
    assert ids.coerce_identity(empty) is None


def test_an_identity_passed_in_comes_back_unchanged():
    """Idempotent, so a consumer can apply the rule without first checking
    whether the library already did."""
    identity = Uuid("6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40")
    assert ids.coerce_identity(identity) is identity


@pytest.mark.parametrize("value", [42, 42.5, True, b"x"])
def test_a_non_string_input_is_returned_unchanged_and_the_two_still_agree(value):
    """The gap `cuems-engine` found (its UR-6), pinned.

    The published rule's table is written in terms of *strings*, so what it does
    with a non-string was undocumented and untested — and the engine's
    hand-written mirror differed there: it did ``str(value)`` first, so
    ``as_id(42)`` returned ``"42"`` while ``coerce_identity(42)`` returns ``42``.
    No call site passes one, which is why nobody noticed.

    The library's two implementations **do** agree, because ``_UuidAdapter.decode``
    returns its original argument rather than the stringified one. That agreement
    is the thing worth pinning: it is what lets a consumer delete its mirror
    without reading both.

    Returning the value unchanged is also the better answer. Stringifying would
    silently turn an ``int`` into something that looks like an identity, and the
    caller would never learn it had passed the wrong thing.
    """
    assert ids.coerce_identity(value) is value
    assert adapter_for("NodeUuidType").decode(value) is value


def test_the_rule_lives_outside_the_xml_package():
    """FR-030, Q14: consumers may not import ``cuemsutils.xml``, so a rule
    published there would be published to nobody."""
    assert ids.coerce_identity.__module__ == "cuemsutils.tools.ids"
