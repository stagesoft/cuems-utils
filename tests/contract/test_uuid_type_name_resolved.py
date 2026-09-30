# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T044a — the overlap end state (FR-020c, FR-021d, FR-025, SC-009, research R13).

FR-025 calls removing ``UuidType`` from ``KNOWN_DIVERGENT_DECLARATIONS`` this
feature's **completion marker**, and R13 measured that the overlap ratchet
admits exactly one route to it.

The ratchet allows a twice-declared name two states and no third: recorded as an
*identical duplicate*, whose declarations must **match**, or recorded as
*divergent*, whose declarations must **still differ**. After the narrowing,
``network_map``'s node identity admits the sentinel and ``script.xsd``'s
``UuidType`` — which types cue and media ``id``, not a node identity — must not,
by FR-021. So the two could never match, the identical-duplicate route is
closed, and the divergent route *requires* the entry to stay. The marker would
be permanently unreachable.

Deleting ``network_map``'s declaration instead leaves the name declared
**once**, which is the one state in which ``test_the_allowlist_has_no_stale_entries``
*demands* the removal.

**Asserted against the shipped allowlist module itself**, so the four overlap
tests and this one cannot disagree about what is recorded.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.contract.test_schema_name_overlap import (
    KNOWN_DIVERGENT_DECLARATIONS,
    KNOWN_IDENTICAL_DUPLICATES,
    _named_type_declarations,
)

MOVED = ("ConvergedUuidType", "NotProvisionedUuidType", "NodeUuidType")
NARROWED_SCHEMAS = ("network_map", "project_mappings", "settings")


def test_uuid_type_is_declared_in_exactly_one_schema():
    """``script.xsd``'s is the survivor, and it is the only one left."""
    declarations = _named_type_declarations()["UuidType"]
    assert sorted(declarations) == ["script"], (
        f"UuidType is declared in {sorted(declarations)}. FR-020c deletes "
        "network_map's; while two remain, FR-025's completion marker is out of reach."
    )


def test_the_divergence_entry_is_gone_from_the_allowlist():
    """The completion marker itself (FR-025). Not merely permitted to be
    removed — **required**, because after the deletion the name overlaps no
    more and ``test_the_allowlist_has_no_stale_entries`` fails while the entry
    stays."""
    assert "UuidType" not in KNOWN_DIVERGENT_DECLARATIONS, (
        "UuidType is still recorded as a divergent declaration. Its overlap is "
        "resolved, so the entry is now stale and the ratchet says so."
    )


@pytest.mark.parametrize("type_name", MOVED)
def test_each_new_type_is_recorded_as_an_identical_duplicate(type_name):
    """FR-021d. Three declarations of one type is this project's established way
    of sharing across these schemas — none of the six includes or imports
    another (research R13) — so the anti-drift guarantee is a **test**, not a
    schema mechanism, and this is where it is registered."""
    assert type_name in KNOWN_IDENTICAL_DUPLICATES, (
        f"{type_name} is declared in three schemas and not recorded. "
        "test_no_unrecorded_type_name_is_declared_in_two_schemas fails on it."
    )
    assert tuple(KNOWN_IDENTICAL_DUPLICATES[type_name]) == NARROWED_SCHEMAS


@pytest.mark.parametrize("type_name", MOVED)
def test_each_new_type_is_declared_identically_in_the_three(type_name):
    """Whitespace-normalised, as the overlap test compares them: ``script.xsd``
    indents with two spaces and the rest with four, and indentation is not what
    is pinned."""
    declarations = _named_type_declarations()[type_name]
    assert sorted(declarations) == sorted(NARROWED_SCHEMAS)
    assert len(set(declarations.values())) == 1, (
        f"{type_name}'s three declarations have diverged: {declarations}"
    )


def test_the_narrowed_schemas_no_longer_declare_uuid_type():
    for name in NARROWED_SCHEMAS:
        text = (Path("src/cuemsutils/xml/schemas") / f"{name}.xsd").read_text()
        assert not re.search(r'<xs:simpleType name="UuidType">', text), (
            f"{name}.xsd still declares UuidType"
        )


def test_scripts_uuid_type_did_not_gain_the_sentinel():
    """The rejected alternative, pinned. Giving ``script.xsd``'s ``UuidType``
    the sentinel would have let the two declarations match — and would have made
    a nil cue id validate, which is not a placeholder but a bug (FR-021 admits
    the sentinel "for node identities and nowhere else")."""
    text = Path("src/cuemsutils/xml/schemas/script.xsd").read_text()
    body = re.search(r'<xs:simpleType name="UuidType">(.*?)</xs:simpleType>', text, re.S)
    assert body
    assert "00000000-0000-0000-0000-000000000000" not in body.group(1)
    assert "xs:union" not in body.group(1)
