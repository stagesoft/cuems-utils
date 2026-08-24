"""Contract C4 — the round trip is a declared transformation, not byte identity.

For every normalised corpus ``network_map.xml`` (C4a — normalisation already
landed in Phase 1), the diff between the pre-state copy and what ``save()``
writes back is exactly the ``node_type`` -> ``node_role`` rename plus its
value mapping, and nothing else.
"""

from __future__ import annotations

import difflib
import warnings

import pytest

from cuemsutils.xml.mapper import Mapper, read_config_document
from cuemsutils.xml.settings import NetworkMap
from tests.support.corpus import REPO_ROOT

PRE_STATE = REPO_ROOT / "specs" / "007-node-model-migration" / "pre-state"

CASES = [
    ("tests/data/network_map.xml", "network_map.xml"),
    ("tests/data/corpus/cuems-utils/network_map.xml", "corpus/cuems-utils/network_map.xml"),
    ("tests/data/corpus/cuems-engine/network_map.xml", "corpus/cuems-engine/network_map.xml"),
]


def _decoded(path: str):
    """The typed ``CuemsNetworkMapType`` object a live file decodes to."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        netmap = NetworkMap(str(REPO_ROOT / path))
    raw = read_config_document(netmap.schema_object, str(REPO_ROOT / path))
    return Mapper("network_map").decode_config(raw)


@pytest.mark.parametrize("live_path,pre_state_relpath", CASES, ids=[c[0] for c in CASES])
def test_round_trip_diff_is_exactly_the_rename_and_value_mapping(
    live_path, pre_state_relpath, tmp_path
):
    out = tmp_path / "written.xml"
    _decoded(live_path).save(str(out))

    pre_state_text = (PRE_STATE / pre_state_relpath).read_text()
    produced_text = out.read_text()

    diff = list(
        difflib.unified_diff(
            pre_state_text.splitlines(), produced_text.splitlines(), lineterm=""
        )
    )
    body_lines = [
        line for line in diff
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    # Exactly one removed line and one added line: the whole document is one
    # line after normalisation (Phase 1), so the rename+mapping collapses the
    # diff to a single before/after pair.
    assert len(body_lines) == 2, body_lines
    removed_text = next(line[1:] for line in body_lines if line.startswith("-"))
    added_text = next(line[1:] for line in body_lines if line.startswith("+"))

    # node_type is gone, node_role has taken its place with the mapped value,
    # and every other byte is identical.
    assert "<node_type>" in removed_text
    assert "<node_type>" not in added_text
    assert "<node_role>" in added_text
    stripped_removed, stripped_added = removed_text, added_text
    for found, mapped in (("NodeType.master", "controller"), ("NodeType.slave", "node")):
        stripped_removed = stripped_removed.replace(f"<node_type>{found}</node_type>", "X")
        stripped_added = stripped_added.replace(f"<node_role>{mapped}</node_role>", "X")
    assert stripped_removed == stripped_added


@pytest.mark.parametrize("live_path", [c[0] for c in CASES])
def test_node_type_appears_in_zero_written_documents(live_path, tmp_path):
    out = tmp_path / "written.xml"
    _decoded(live_path).save(str(out))
    written = out.read_text()
    assert "<node_type>" not in written
    assert "NodeType." not in written
