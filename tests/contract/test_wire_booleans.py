"""FR-010 (T032) — booleans on the wire are the **strings** ``"True"``/``"False"``.

``cms:BoolType`` is an ``xs:string`` restricted to those two literals, not an
``xs:boolean``. So the payload carries the capitalised Python spelling as text,
the Angular UI reads ``cueData.enabled === true || cueData.enabled === 'True'``,
and **writes back the string form**.

Decoding them to JSON booleans is the single most natural "improvement"
available in this code and would break every consumer of the payload at once.
It is deferred item X1 and a file-format migration; it is explicitly forbidden
here.

Both halves are asserted — ``is "True"`` **and** ``is not True`` — because
``True == 1`` and ``"True" != True`` are different questions, and a test that
only checked truthiness would pass on either encoding.
"""

from __future__ import annotations

import json
import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from tests.support.corpus import GOLDEN_ROOT, loadable_script_documents
from tests.support.public_api import assert_no_xml_import

#: The documents that reach the object layer — ``script_documents()`` minus
#: the two ``legacy/`` entries pinned as ``to_objects: error``, which must
#: stay rejected (FR-025) and so cannot be loaded to be projected.
SCRIPT_DOCS = loadable_script_documents()
IDS = [d.relpath for d in SCRIPT_DOCS]

#: Every ``cms:BoolType`` element in ``script.xsd``.
BOOLEAN_FIELDS = ("autoload", "enabled", "timecode")


def _boolean_values(node, path="$", out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        for key, value in node.items():
            if key in BOOLEAN_FIELDS:
                out.append((f"{path}.{key}", value))
            _boolean_values(value, f"{path}.{key}", out)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _boolean_values(item, f"{path}[{index}]", out)
    return out


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_every_boolean_field_is_the_string_form(doc):
    found = _boolean_values(CuemsScript.load(doc.path).to_wire())
    assert found, f"{doc.relpath} carries no boolean fields to check"
    for path, value in found:
        assert not isinstance(value, bool), f"{path} is a JSON boolean"
        assert isinstance(value, str), f"{path} is {type(value).__name__}"
        assert value in ("True", "False"), f"{path} == {value!r}"


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_the_json_text_carries_no_bare_json_booleans_for_those_fields(doc):
    """The same claim at the bytes, where a consumer actually meets it."""
    text = CuemsScript.load(doc.path).to_json()
    for field in BOOLEAN_FIELDS:
        assert f'"{field}": true' not in text
        assert f'"{field}": false' not in text


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_the_object_still_holds_real_python_booleans(doc):
    """The wire form is a *projection*, not the model's own type.

    ``_Bool.decode`` turns ``"True"`` into ``True`` so the engine can branch on
    it. If the object started holding strings, every ``if cue.enabled:`` in
    ``cuems-engine`` would become unconditionally true.
    """
    script = CuemsScript.load(doc.path)
    assert isinstance(script.cuelist.enabled, bool)


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_a_boolean_survives_the_json_round_trip_as_a_boolean(doc):
    script = CuemsScript.load(doc.path)
    rebuilt = CuemsScript.from_json(json.dumps(script.to_wire()))
    assert isinstance(rebuilt.cuelist.enabled, bool)
    assert rebuilt.cuelist.enabled == script.cuelist.enabled


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
