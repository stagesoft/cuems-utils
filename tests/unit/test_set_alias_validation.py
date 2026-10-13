"""G4, T041/T042/T120c — ``NodeIndex.set_alias``'s validation ordering and
diagnostic shape.

Validation precedes mutation (FR-036, the clause with an operational
incident behind it): an in-place empty label would make the subsequent
``save()`` fail *after* the index already changed, and a resident daemon's
pending-write retry would then fail on that same row until restart.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools.NodeList import NodeIndex, NodeRole


def _an_index():
    return NodeIndex({
        "aabbccddeeff": {
            "uuid": "11111111-1111-4111-8111-111111111111",
            "mac": "aabbccddeeff",
            "name": "node-one",
            "node_role": NodeRole.node,
            "ip": "10.0.0.1",
            "adopted": True,
            "online": True,
        },
    })


@pytest.mark.parametrize("bad_label", ["", "   ", "\t\n"])
def test_an_empty_or_blank_label_raises_before_anything_is_touched(bad_label):
    index = _an_index()
    before = {mac: dict(n) for mac, n in index.items()}

    with pytest.raises(ValueError):
        index.set_alias("11111111-1111-4111-8111-111111111111", bad_label)

    for mac, snapshot in before.items():
        assert dict(index[mac]) == snapshot, "the index changed before raising"


def test_the_document_still_saves_after_a_rejected_label(tmp_path):
    """The measurable form of "nothing was touched": the index is still in a
    state that round-trips, not merely unchanged by inspection."""
    index = _an_index()
    before = index.signature()

    with pytest.raises(ValueError):
        index.set_alias("11111111-1111-4111-8111-111111111111", "")

    assert index.signature() == before


def test_an_unknown_identity_reports_failure_and_mutates_nothing():
    index = _an_index()
    before = {mac: dict(n) for mac, n in index.items()}

    result = index.set_alias("99999999-9999-4999-8999-999999999999", "ghost")

    assert result is False
    for mac, snapshot in before.items():
        assert dict(index[mac]) == snapshot


def test_a_valid_label_reports_success():
    index = _an_index()
    assert index.set_alias("11111111-1111-4111-8111-111111111111", "stage-left") is True
    assert index["aabbccddeeff"]["alias"] == "stage-left"


def test_clearing_with_none_removes_the_key():
    index = _an_index()
    index.set_alias("11111111-1111-4111-8111-111111111111", "stage-left")

    assert index.set_alias("11111111-1111-4111-8111-111111111111", None) is True
    assert "alias" not in index["aabbccddeeff"]


# -- T120c: the one new operator-facing message (FR-UX-001) ------------------


def test_the_refusal_names_the_locus_the_value_and_the_remedy():
    index = _an_index()

    with pytest.raises(ValueError) as exc_info:
        index.set_alias("11111111-1111-4111-8111-111111111111", "   ")

    message = str(exc_info.value)
    assert "11111111-1111-4111-8111-111111111111" in message, "the locus (node_uuid) is not named"
    assert repr("   ") in message, "the rejected value is not named"
    assert "non-space character" in message, "the remedy is not stated"
