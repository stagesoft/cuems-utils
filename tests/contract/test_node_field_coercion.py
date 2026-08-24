"""Ported from ``cuems-nodeconf/tests/test_node_field_coercion.py`` (T061-T064).

The 106-case regression test that used to guard ``nodeParser`` against
type-guessing free-text fields. It ports as a **guarantee test over the
derived adapter table**, not as a test of a guard (research R4): there is no
``key=`` argument left to drop, because typing comes from the schema now.
``STRING_TYPED_NODE_FIELDS`` does not migrate — carrying it across would
reintroduce the name-matching mechanism whose absence is the fix (C3, T064).

**What changed from the original 106 cases**: 14 adversarial values × 7
text fields becomes 14 × **6** — ``node_type`` leaves the set (it is
``NodeRoleType``, enumerated, now), the other six (``name``, ``ip``, ``mac``,
``role_id``, ``alias``, ``hostname``) are unchanged. ``adopted``/``online`` ->
``bool`` and ``uuid`` -> ``Uuid`` assertions carry across verbatim — the
schema always typed them, only whether the decode path *ran* that typing
changed (research R1).

Exercised directly against ``Mapper.decode_config`` rather than through XML
parsing: adapter application is a property of the decoded value, not of the
XML text it came from, and the derived table is exactly what this file
tests the shape of.
"""

from __future__ import annotations

import pytest

from cuemsutils.config.network_map import CuemsNetworkMapType, node
from cuemsutils.tools.NodeList import NodeRole
from cuemsutils.tools.Uuid import Uuid
from cuemsutils.xml.documents import iter_schema_errors
from cuemsutils.xml.mapper import Mapper

#: Stated from the schema (data-model.md §2), not imported from the
#: implementation, so these tests fail on behaviour rather than erroring on a
#: missing symbol if the guarantee is ever removed.
STRING_TYPED_FIELDS = ("name", "ip", "mac", "role_id", "alias", "hostname")

ADVERSARIAL_VALUES = [
    "none", "null", "n", "y", "off", "on", "no", "yes", "true", "false",
    "0", "1", "007", "42",
]


def _decode_node(**fields) -> dict:
    raw = {"node_list": [{"node": dict(fields)}]}
    decoded = Mapper("network_map").decode_config(raw)
    return decoded["node_list"][0]["node"]


class TestStringFieldsSurviveDecoding:
    """Values that look like bools/ints/none must stay strings."""

    @pytest.mark.parametrize("value", ADVERSARIAL_VALUES)
    @pytest.mark.parametrize("field", sorted(STRING_TYPED_FIELDS))
    def test_string_field_not_coerced(self, field, value):
        decoded = _decode_node(**{field: value})
        assert decoded[field] == value
        assert isinstance(decoded[field], str)

    def test_node_named_none_survives(self):
        """The hard-failure case: <name/> would violate NonEmptyString on
        write (T062)."""
        assert _decode_node(name="none")["name"] == "none"

    def test_identity_fields_survive(self):
        """The silent-corruption case: these validate, so they would persist
        (T063)."""
        decoded = _decode_node(role_id="n", alias="off", hostname="007")
        assert decoded["role_id"] == "n"
        assert decoded["alias"] == "off"
        assert decoded["hostname"] == "007"


class TestIntendedTypingPreserved:
    """node_role -> NodeRole, adopted/online -> bool, uuid -> Uuid — the
    typing this feature *adds*, ported verbatim from the bool/uuid half of
    the original suite (research R1, R2)."""

    @pytest.mark.parametrize("field", ["adopted", "online"])
    @pytest.mark.parametrize("text,expected", [("True", True), ("False", False)])
    def test_bools_still_coerced(self, field, text, expected):
        decoded = _decode_node(**{field: text})
        assert decoded[field] is expected

    def test_uuid_still_coerced(self):
        raw = "3f2504e0-4f89-41d3-9a0c-0305e82c3301"
        decoded = _decode_node(uuid=raw)
        assert decoded["uuid"] == raw
        assert isinstance(decoded["uuid"], Uuid)

    def test_node_role_is_coerced(self):
        decoded = _decode_node(node_role="controller")
        assert decoded["node_role"] is NodeRole.controller


class TestFullNodeRoundTrip:
    """A whole schema-valid node with adversarial values (T063's continuation
    of the original's TestFullNodeRoundTrip)."""

    def test_all_fields(self):
        node_in = {
            "uuid": "3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            "mac": "aa:bb:cc:dd:ee:ff",
            "name": "none",
            "node_role": "node",
            "ip": "10.0.0.7",
            "adopted": "True",
            "online": "True",
            "role_id": "n",
            "alias": "off",
            "hostname": "007",
        }
        decoded = _decode_node(**node_in)

        for field in STRING_TYPED_FIELDS:
            assert decoded[field] == node_in[field], f"{field} was coerced"
        assert decoded["adopted"] is True
        assert decoded["online"] is True
        assert decoded["uuid"] == node_in["uuid"]
        assert decoded["node_role"] is NodeRole.node


class TestFullNodeWriteRoundTrip:
    """T062, T063 — not just decode: a schema-valid document, written and
    re-read, with adversarial values in the free-text fields."""

    def _built_map(self, **node_fields) -> CuemsNetworkMapType:
        built = node(
            uuid="3f2504e0-4f89-41d3-9a0c-0305e82c3301",
            mac="aabbccddeeff",
            name="none",
            node_role=NodeRole.node,
            ip="10.0.0.7",
            **node_fields,
        )
        return CuemsNetworkMapType(node_list=[{"node": built}])

    def test_node_named_none_writes_and_validates(self, tmp_path):
        netmap = self._built_map()
        out = tmp_path / "out.xml"
        netmap.save(str(out))  # would raise SchemaError if <name/> resulted

        written = out.read_text()
        assert "<name>none</name>" in written

        from xml.etree.ElementTree import parse

        assert list(iter_schema_errors("network_map", parse(str(out)))) == []

    def test_identity_fields_survive_a_write_then_read_cycle(self, tmp_path):
        netmap = self._built_map(role_id="n", alias="off", hostname="007")
        out = tmp_path / "out.xml"
        netmap.save(str(out))

        from cuemsutils.xml.settings import NetworkMap

        reread = NetworkMap(str(out))
        reread_node = reread.get_dict()["node_list"][0]["node"]
        assert reread_node["role_id"] == "n"
        assert reread_node["alias"] == "off"
        assert reread_node["hostname"] == "007"


# -- T064: the structural claim, restated as its own assertion --------------


def test_no_node_specific_denylist_exists_anywhere_in_the_package():
    """C3 — ``STRING_TYPED_NODE_FIELDS`` (``cuems-nodeconf``'s node-specific
    denylist) does not migrate. The node guarantee is structural (the derived
    adapter table), not a list of node field names to check against.

    ``STRING_TYPED_KEYS`` (``xml/Parsers.py``) is a **different, pre-existing**
    denylist for an unrelated domain — the frozen, deprecated
    ``CuemsParser``'s cue/script field guessing (feature 004, ClickUp
    869cqbpxa), not node fields. It predates this feature, this feature does
    not touch ``CuemsParser`` or script parsing, and removing it is out of
    scope here — recorded as a finding (``migration-guide.md``) rather than
    silently asserted away.
    """
    import ast
    from pathlib import Path

    import cuemsutils

    root = Path(cuemsutils.__file__).parent
    offenders = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.Name) and ast_node.id == "STRING_TYPED_NODE_FIELDS":
                offenders.append((str(path), ast_node.id))
    assert offenders == []
