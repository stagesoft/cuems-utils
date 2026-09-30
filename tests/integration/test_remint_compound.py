# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T024 — the compound output form, and every other byte unchanged (FR-009).

``<output_name>`` values of the form ``<old>_<output>`` carry the new identity
with the rest of the value byte-identical. This is the measurement that makes
literal substitution the instrument rather than a structural rewrite: the
element is a ``NameStringType`` and stays one, so a stale prefix here is
**schema-valid** and nothing downstream would report it (data-model §1.1a,
research R12).

The second assertion is the one that catches a re-serialiser: every byte of the
file that is not one of the 36-character tokens is exactly where it was.
"""

from __future__ import annotations

from tests.support.cluster_fixture import SHAPES, build_cluster
from tests.support.remint_harness import run_remint, state_dir
from cuemsutils.tools import remint


def test_the_compound_prefix_carries_the_new_identity(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    script = cluster.script_path("project_0")
    before = script.read_text()
    assert f"{SHAPES['uuid1']}_0" in before
    assert f"{SHAPES['uuid1']}_custom_1" in before

    code, out = run_remint(cluster, state)
    assert code == 0, out

    table = remint.SubstitutionTable.load(remint.table_path(state))
    new = table.entries[SHAPES["uuid1"]]
    after = script.read_text()
    assert f"{new}_0" in after
    assert f"{new}_custom_1" in after
    assert SHAPES["uuid1"] not in after


def test_the_suffix_survives_byte_identically(tmp_path):
    """``_custom_1`` is not re-derived, re-numbered or normalised — it is the
    part of the value the substitution does not touch."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    script = cluster.script_path("project_0")
    before = script.read_text()
    run_remint(cluster, state)
    after = script.read_text()

    table = remint.SubstitutionTable.load(remint.table_path(state))
    restored = after
    for old, new in table.entries.items():
        restored = restored.replace(new, old)
    assert restored == before, "something other than the 36-character tokens moved"


def test_every_other_byte_in_the_file_is_unchanged(tmp_path):
    """Including the XML declaration, the namespace prefix, the attribute
    order and the absence of pretty-printing — none of which a rewrite through
    the library's writer would preserve."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    mappings = cluster.mappings_path("project_0")
    before = mappings.read_bytes()
    run_remint(cluster, state)
    after = mappings.read_bytes()

    assert len(after) == len(before), "the substitution is length-preserving (FR-011b)"
    table = remint.SubstitutionTable.load(remint.table_path(state))
    restored = after.decode()
    for old, new in table.entries.items():
        restored = restored.replace(new, old)
    assert restored.encode() == before


def test_a_hand_edited_document_is_not_reformatted(tmp_path):
    """Operators hand-edit these files. A re-mint that reflowed one would make
    the diff unreadable and lose every comment in it."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    path = cluster.conf / "default_mappings.xml"
    text = path.read_text().replace(
        "<nodes>", "<!-- hand-edited: do not reformat -->\n    <nodes>"
    )
    path.write_text(text, encoding="utf-8")

    run_remint(cluster, state)

    after = path.read_text()
    assert "<!-- hand-edited: do not reformat -->" in after
    assert "\n    <nodes>" in after
