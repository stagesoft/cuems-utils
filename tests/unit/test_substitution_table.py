# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T020 — the substitution table's five invariants (FR-006, FR-010, FR-014, §2.1).

They are checked rather than trusted. A minted collision is vanishingly
improbable, and that is exactly the argument that keeps a silent, permanent
failure out of a test suite: improbable is not impossible, and nothing
downstream would report it.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools import ids, remint
from cuemsutils.tools.Uuid import Uuid
from tests.support.cluster_fixture import SHAPES


def test_every_new_value_is_a_uuid4_minted_through_the_library_minter():
    """FR-006. ``Uuid`` refuses any shape but uuid4, so the table cannot hold a
    value the tightened pattern will reject — which is what makes the narrowing
    safe to land after this."""
    table = remint.build_table(
        [SHAPES["uuid1"], SHAPES["uuid5"], SHAPES["uuid4upper"]], controller="c"
    )
    for new in table.entries.values():
        assert ids.is_converged(new)
        assert Uuid(new)


def test_every_new_value_is_distinct():
    table = remint.build_table([f"{i:08x}-ebf4-11b2-9f26-{i:012x}" for i in range(50)],
                               controller="c")
    assert len(set(table.entries.values())) == len(table.entries) == 50


def test_no_new_value_appears_as_an_old_one():
    """A chained substitution would rewrite a node twice."""
    table = remint.build_table([SHAPES["uuid1"], SHAPES["uuid5"]], controller="c")
    assert not set(table.entries.values()) & set(table.entries)


def test_an_already_converged_node_has_no_entry():
    """FR-014, expressed as a property of the table rather than a special case
    in the apply loop — which is why a converged node's files are not rewritten
    at all rather than rewritten to the same bytes."""
    table = remint.build_table(
        [SHAPES["uuid4"], SHAPES["uuid1"], SHAPES["uuid4b"]], controller="c"
    )
    assert set(table.entries) == {SHAPES["uuid1"]}


def test_the_sentinel_gets_an_entry_because_it_is_not_converged():
    """The sentinel is *admitted*, never *converged* (data-model §1.2). A node
    carrying it was never provisioned and needs an identity, which is the
    re-mint's business as much as a uuid1 is."""
    table = remint.build_table([SHAPES["sentinel"]], controller="c")
    assert SHAPES["sentinel"] in table.entries


def test_keys_are_built_from_node_identities_only(tmp_path):
    """FR-010: the table is keyed from node identities, never from cue or media
    identifiers. That is what bounds where a replacement can land — a script's
    cue ids are uuid4 and stay exactly where they are."""
    from tests.support.cluster_fixture import build_cluster

    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    from cuemsutils.tools import library_reach

    found = remint.survey(cluster.conf, library_reach.reach_library(cluster.library))
    assert set(found.node_identities) == {SHAPES["uuid1"], SHAPES["uuid5"]}
    # the script's cue ids were *seen* by the survey and are not table keys
    assert len(found.identities) > len(found.node_identities)


@pytest.mark.parametrize("broken,why", [
    # a converged value mapping to itself — the invariant-4 case. Spelled with
    # a real uuid4 because the not-a-uuid4 check fires first and would mask it.
    ({"6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40": "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40"},
     "mapping to itself"),
    ({"a": "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40",
      "b": "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40"}, "one value twice"),
    ({"a": "not-a-uuid4"}, "not a converged"),
])
def test_a_broken_table_is_refused_rather_than_applied(broken, why):
    table = remint.SubstitutionTable(created="now", controller="c", entries=broken)
    with pytest.raises(remint.Abort) as raised:
        table.check_invariants()
    assert why in str(raised.value)


def test_a_chained_table_is_refused():
    table = remint.SubstitutionTable(
        created="now", controller="c",
        entries={"a": "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40",
                 "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40": "b2a41f0c-7d3e-4a11-9c02-1f3e5d7a9b01"},
    )
    with pytest.raises(remint.Abort) as raised:
        table.check_invariants()
    assert "twice" in str(raised.value)


def test_the_substituter_is_one_pass_and_cannot_chain():
    """Two properties in one assertion, because they have one cause. Sequential
    ``str.replace`` calls would turn ``a -> b`` and ``b -> c`` into ``a -> c``;
    one compiled alternation cannot. The same single pass is what keeps a
    ten-node run from being five times a two-node one over identical bytes."""
    table = remint.SubstitutionTable(created="now", controller="c",
                                     entries={"AAA": "BBB", "BBB": "CCC"})
    assert table.substituter()("AAA BBB") == "BBB CCC"


def test_the_digest_covers_the_mapping_and_not_the_progress():
    """The completion record's question is *which mapping was applied*, so a
    digest that moved as ``applied`` grew would name a different table at every
    step of one run."""
    table = remint.build_table([SHAPES["uuid1"]], controller="c")
    before = table.digest()
    table.applied.append("/some/path")
    assert table.digest() == before


def test_a_table_round_trips_through_disk(tmp_path):
    table = remint.build_table([SHAPES["uuid1"], SHAPES["uuid5"]], controller="c")
    table.applied.append("/x")
    path = tmp_path / "t.json"
    table.save(path)
    again = remint.SubstitutionTable.load(path)
    assert again == table
