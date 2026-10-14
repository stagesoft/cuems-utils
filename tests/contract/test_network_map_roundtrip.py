"""Contract C4 — the round trip is a declared transformation, not byte identity.

For every normalised corpus ``network_map.xml`` (C4a — normalisation already
landed in Phase 1), the only differences between the pre-state copy and what
``save()`` writes back are the three independent, named normalisations below
— and nothing else.

**Re-authored for S3 (feature 015, T090a).** This test used to compare the
two documents by **unified-diff line count**, on the stated ground that "the
whole document is one line after normalisation, so the rename+mapping
collapses the diff to a single before/after pair." Once the writer indents
(S3), that collapse no longer happens: each of the three independent
normalisations below lands on its own line, so a line-count diff would see
several hunks where it used to see one. The comparison is now **full
equality after applying the same three normalisations to both sides**,
which does not depend on how many lines the document spans. The pre-state
documents themselves are re-indented to match the writer's new output form,
exactly as the live corpus documents already are — a comparison, not a
content change, since every value they carry is untouched.
"""

from __future__ import annotations

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


def _normalize_pre_state(text: str) -> str:
    """007's rename, applied to the *old*-shape text: ``node_type`` ->
    ``node_role``, with the value mapping."""
    for found, role in (("NodeType.master", "controller"), ("NodeType.slave", "node")):
        text = text.replace(f"<node_type>{found}</node_type>", f"<node_role>{role}</node_role>")
    return text


def _normalize_produced(text: str) -> str:
    """The two independent, later normalisations the *new*-shape text picks
    up on every write, stripped so this test stays about the 007 rename
    alone.

    ``doc_version``'s value is read from the registry rather than spelled,
    because it moves whenever the schema does and this test is not about
    that: feature 012 took ``network_map`` to 2, and hardcoding "1" here
    would have made a correct version bump look like a broken rename.
    """
    from cuemsutils.xml.versioning import CURRENT_VERSION

    text = text.replace(f' doc_version="{CURRENT_VERSION["network_map"]}"', "")
    return text


def _normalize_pre_state_booleans(text: str) -> str:
    """Feature 014 (X1): ``adopted``/``online`` are ``xs:boolean`` now,
    whose lexical space is ``true``/``false``, where ``cms:BoolType``'s was
    ``True``/``False``.

    The pre-state document is **not** rewritten to match this one — it is
    007's frozen historical record of what was on disk before that rename,
    and a landed feature's own directory is not retroactively edited to keep
    a later feature's test green — the normalisation goes on the side that
    moved, applied here rather than stored in the file.
    """
    for old_form, new_form in (("True", "true"), ("False", "false")):
        for name in ("adopted", "online"):
            text = text.replace(f"<{name}>{old_form}</{name}>", f"<{name}>{new_form}</{name}>")
    return text


@pytest.mark.parametrize("live_path,pre_state_relpath", CASES, ids=[c[0] for c in CASES])
def test_round_trip_diff_is_exactly_the_rename_and_value_mapping(
    live_path, pre_state_relpath, tmp_path
):
    out = tmp_path / "written.xml"
    _decoded(live_path).save(str(out))

    pre_state_text = (PRE_STATE / pre_state_relpath).read_text()
    produced_text = out.read_text()

    # The rename must actually be present on each side before normalising
    # it away, or the comparison below would pass vacuously on two
    # documents that never differed in the first place.
    assert "<node_type>" in pre_state_text
    assert "<node_type>" not in produced_text
    assert "<node_role>" in produced_text

    normalized_pre_state = _normalize_pre_state_booleans(_normalize_pre_state(pre_state_text))
    normalized_produced = _normalize_produced(produced_text)

    assert normalized_pre_state == normalized_produced


@pytest.mark.parametrize("live_path", [c[0] for c in CASES])
def test_node_type_appears_in_zero_written_documents(live_path, tmp_path):
    out = tmp_path / "written.xml"
    _decoded(live_path).save(str(out))
    written = out.read_text()
    assert "<node_type>" not in written
    assert "NodeType." not in written
